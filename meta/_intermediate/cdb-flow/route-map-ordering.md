# ROUTE_MAP — Phase B 書込み順依存スキャンノート

対象テーブル: `ROUTE_MAP`
Consumer: `frrcfgd.BGPConfigDaemon` (`sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`)
スキャン範囲: L2669-2676, L2894-2995, L3109-3148, L2205-2253, L2298-2315 全行精読

---

## 検出した順序依存・タイミング依存

### 1. `route_operation` が先行必須（同一エントリ内フィールド順序）

- `frrcfgd.py` L3113-3126: ROUTE_MAP エントリ処理時、最初に `route_operation` フィールドを確認。`route_operation` が存在しない（または `OP_NONE`）場合は FRR への `route-map <name> permit|deny <seq>` コマンドを発行しない。
- その後 L3131-3133: `map_name not in self.route_map or seq_no not in self.route_map[map_name]` ならば `LOG_ERR('route-map {} seq {} not found for update')` で `continue`（全 match_*/set_* フィールド処理をスキップ）。
- **同一キー `ROUTE_MAP|<name>|<seq>` に対して `route_operation` を含む最初の書き込みで FRR エントリを確立してから、後続の `match_*` / `set_*` フィールドを書き込むこと。** `route_operation` なしで `match_prefix_set` 等を書き込んでも silent drop。
- evidence: `frrcfgd.py:3113-3133`

### 2. `match_prefix_set` / `match_next_hop_set` — PREFIX_SET が先行必須

- `frrcfgd.py` L2669-2676: ROUTE_MAP の SET イベント処理時、`match_prefix_set` および `match_next_hop_set` の値を `prefix_set_list` 内で参照し AF（IPv4/IPv6）を特定する。
- `pfx_set_name not in self.prefix_set_list` の場合 `tbl_key` に AF が設定されず、FRR コマンドの `match ip address prefix-list` / `match ipv6 address prefix-list` の IPv4/IPv6 判定ができない。結果として FRR コマンドが発行されず **silent drop**。
- `prefix_set_list` は起動時 L2228-2232 で `PREFIX_SET` テーブルから初期化され、L2894-2908 のイベントループで動的に更新される。
- **`PREFIX_SET|<name>` を先に作成（mode=IPv4 または mode=IPv6 付き）してから `ROUTE_MAP` の `match_prefix_set` を書き込むこと。**
- evidence: `frrcfgd.py:2669-2676`, `frrcfgd.py:2228-2232`, `frrcfgd.py:2894-2908`

### 3. `set_community_ref` — COMMUNITY_SET が先行必須

- `frrcfgd.py` L2875-2882 の `comm_set_handler`: `COMMUNITY_SET` / `EXTENDED_COMMUNITY_SET` のイベント処理が先に完了していないと `frrcfgd` の内部キャッシュに community list が存在しない。
- `set_community_ref` で参照先 `COMMUNITY_SET` が未作成の場合、FRR の `set community` コマンドが生成されず silent drop。
- **`COMMUNITY_SET|<name>` を先に作成してから `ROUTE_MAP` の `set_community_ref` を書き込むこと。**
- evidence: `frrcfgd.py:2875-2882`

### 4. `match_as_path` — AS_PATH_SET が先行必須

- `frrcfgd.py` L2249 で `AS_PATH_SET` テーブルを起動時に読み込み、L2998 のイベントループで動的更新。
- `match_as_path` が参照する AS_PATH_SET エントリが未作成の場合、FRR bgpd 側で `match as-path` コマンドが無効参照となり BGP ポリシーが意図どおりに動作しない。（frrcfgd 側での参照チェックはないが FRR エラーログに現れる）
- **`AS_PATH_SET|<name>` を先に作成してから `ROUTE_MAP` の `match_as_path` を書き込むことを推奨。**
- evidence: `frrcfgd.py:2249`, `frrcfgd.py:2998`

### 5. `call_route_map` — 参照先 ROUTE_MAP_SET（名前）が先行必須

- `route_map_key_map` L1942: `call_route_map` は `call {:enable-only}` として FRR に発行される。FRR は参照先 route-map が未定義の場合エラーなく受け付けるが、BGP ポリシー評価時に call 先が見つからず**黙って素通り（ポリシー未適用）**になる。
- **`call_route_map` で参照する route-map 名は FRR に事前に定義（別 ROUTE_MAP エントリ経由）してから書き込むことを推奨。**
- evidence: `frrcfgd.py:1942`

### 6. DEL 順序 — ROUTE_MAP DEL → 参照元（BGP_NEIGHBOR_AF 等）DEL

- `frrcfgd.py` L3139-3148: `del_table` 時に `route-map <name>` の `no route-map ... permit|deny ...` を FRR に発行。このとき FRR はアクティブに適用中の BGP neighbor の route-map をインラインで削除する。
- `BGP_NEIGHBOR_AF.route_map_in` / `route_map_out` が参照中の route-map を先に削除すると、FRR がエラーなく受け付けるが **BGP フィルタが消えた状態でセッションが継続**しトラフィックに影響する可能性がある。
- **推奨順序**: `BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` の `route_map_in` / `route_map_out` 参照を先に解除 → 次に `ROUTE_MAP` エントリを DEL。
- evidence: `frrcfgd.py:3139-3148`, `frrcfgd.py:1903-1904`

### 7. `route_operation` 変更（permit ↔ deny）— DEL → SET が必須

- `frrcfgd.py` L3114-3126: `route_operation` の変更は `dval.op != OP_NONE` でのみ FRR コマンドを再発行。しかし FRR は `route-map <name> permit <seq>` が存在する状態で `route-map <name> deny <seq>` を書くと**別エントリとして追加**（上書きではない）。
- `route_operation` を変更する場合は `DEL → SET` の順序が必要（古いエントリを `no route-map` で削除してから新規作成）。
- evidence: `frrcfgd.py:3113-3126`

### 8. `match_prefix_set` の PREFIX_SET DEL — ROUTE_MAP より先に DEL しない

- `frrcfgd.py` L2907-2908: PREFIX_SET の DEL イベントで `prefix_set_list` からエントリを削除。この後に ROUTE_MAP が参照していた場合、次の ROUTE_MAP 更新で AF が特定できず silent drop（依存 #2 の逆方向）。
- **PREFIX_SET を削除する場合は、先に参照する ROUTE_MAP エントリの `match_prefix_set` を除去してから PREFIX_SET を DEL すること。**
- evidence: `frrcfgd.py:2907-2908`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `route_operation` 先行書き込み → `match_*` / `set_*` 処理 | 強制先行（同一エントリ内） | route_operation なし時は全フィールド silent drop |
| 2 | `PREFIX_SET` 作成 → `ROUTE_MAP.match_prefix_set` / `match_next_hop_set` | 強制先行（AF 未解決で silent drop） | PREFIX_SET を先に作成 |
| 3 | `COMMUNITY_SET` 作成 → `ROUTE_MAP.set_community_ref` | 先行推奨（未作成で silent drop） | COMMUNITY_SET を先に作成 |
| 4 | `AS_PATH_SET` 作成 → `ROUTE_MAP.match_as_path` | 先行推奨（FRR 側で無効参照） | AS_PATH_SET を先に作成 |
| 5 | 参照先 route-map 定義 → `ROUTE_MAP.call_route_map` | 先行推奨（FRR 側で黙って素通り） | call 先 route-map を先に作成 |
| 6 | BGP_NEIGHBOR_AF 参照解除 → ROUTE_MAP DEL | 推奨（フィルタ消滅でトラフィック影響） | neighbor の route_map_in/out を先に除去 |
| 7 | route_operation 変更: DEL → SET | 必須（permit/deny 切替は上書きされない） | DEL 後に SET で新規作成 |
| 8 | ROUTE_MAP.match_prefix_set 除去 → PREFIX_SET DEL | 推奨（AF 解決不能で subsequent update が silent drop） | ROUTE_MAP 参照を先に削除 |
