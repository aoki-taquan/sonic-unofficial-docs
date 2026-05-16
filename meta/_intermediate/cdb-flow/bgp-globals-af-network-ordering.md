# BGP_GLOBALS_AF_NETWORK — Phase B 書込み順依存スキャンノート

対象テーブル: `BGP_GLOBALS_AF_NETWORK`
Consumer: `frrcfgd` (`sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`)
ハンドラ: `bgp_table_handler_common` 経由 (`table_handler_list` 内 `('BGP_GLOBALS_AF_NETWORK', self.bgp_table_handler_common)`)
スキャン範囲: `__init__`, `table_handler_list`, `bgp_message_handler` ループ (`__update_bgp`), `BGP_GLOBALS_AF_NETWORK` 専用 `elif` (frrcfgd.py:3169-3186)

---

## 検出した順序依存・タイミング依存

### 1. `BGP_GLOBALS` (local_asn) 先行必須 — VRF の BGP インスタンスがなければ即 skip

- `bgp_message_handler` のループ内 (frrcfgd.py:2656-2662)、`__vrf_based_table()` が True を返すテーブル（`BGP_GLOBALS_AF_NETWORK` を含む `vrf_tables` セット, frrcfgd.py:2136-2140）に対しては、まず `self.__get_vrf_asn(vrf)` で対象 VRF の `local_asn` を取得する。
- `local_asn` が `None` でかつ更新中テーブルが `BGP_GLOBALS` でない場合、`syslog DEBUG 'ignore table {} update because local_asn for VRF {} was not configured'` を出してそのまま `continue`（捨てる）。
- つまり `BGP_GLOBALS|<vrf>` (`local_asn` フィールド) が CONFIG_DB に存在しない状態で `BGP_GLOBALS_AF_NETWORK|<vrf>|<afi_safi>|<prefix>` を書き込むと **無視され、再試行も deferred queue もない**。後から `BGP_GLOBALS` が来ても自動再適用は走らない。
- **緩和策**: `BGP_GLOBALS.local_asn` を書く側 (`__update_bgp` 内の `BGP_GLOBALS` 分岐 frrcfgd.py:2685-2709) は `local_asn` 設定成功時に `self.__apply_dep_vrf_table(vrf, 'ROUTE_REDISTRIBUTE')` を呼ぶが、ここで呼び直されるのは `ROUTE_REDISTRIBUTE` のみで **`BGP_GLOBALS_AF_NETWORK` は再適用対象外**。
- **結果（discrepancy 候補）**: `BGP_GLOBALS_AF_NETWORK` の書き込みは `BGP_GLOBALS.local_asn` より厳密に後に来なければならない。順序を逆にすると黙って破棄される。
- evidence: `frrcfgd.py:99 (daemons map), 2136-2140 (vrf_tables), 2656-2662 (local_asn gate), 2704 (apply_dep_vrf_table — NETWORK 対象外)`

### 2. `BGP_GLOBALS_AF` 先行推奨 — address-family <afi> <safi> サブモードの暗黙生成に依存

- `BGP_GLOBALS_AF_NETWORK` 分岐 (frrcfgd.py:3169-3186) は実行する vtysh コマンドを次のように組み立てる:

```python
cmd_prefix = ['configure terminal',
              'router bgp {} vrf {}'.format(local_asn, vrf),
              'address-family {} {}'.format(af, ip_type)]
```

- `local_asn` は依存 #1 で保証されるが、`address-family <af> <ip_type>` サブモードは FRR 側で **対応する `BGP_GLOBALS_AF|<vrf>|<afi_safi>` エントリの活性化を経由しないと暗黙作成になる**。FRR `bgpd` 自体は `network` コマンドで自動的に address-family サブモードを作るが、`BGP_GLOBALS_AF` 側の `max_ebgp_paths` / `max_ibgp_paths` / `redistribute_connected` 等の AF レベル設定が**未確定の中間状態**で `network <prefix>` が先に投入される可能性がある。
- 中間状態では `network` だけが入って AF 既定値（FRR ハードコード）で動作する期間が発生する。後から `BGP_GLOBALS_AF` が来ると AF レベル属性が確定する。
- **順序依存**: 厳密な reject はないが、AF 属性 (redistribute 等) を含めた一貫した起動シーケンスでは `BGP_GLOBALS_AF` を先に書く。
- evidence: `frrcfgd.py:3179-3182`, `table_handler_list` 順序で `BGP_GLOBALS_AF` (frrcfgd.py:2297) が `BGP_GLOBALS_AF_NETWORK` (frrcfgd.py:2318) より先に登録されている → 起動時 walk では先に処理されることが保証される

### 3. `bgpd` デーモン起動順 — 未起動の bgpd への vtysh は失敗

- `BGP_TABLE_NAME_MAP` (frrcfgd.py:99) で `BGP_GLOBALS_AF_NETWORK` は `['bgpd']` 依存とマークされている。
- 投入される vtysh コマンドは最終的に `bgpd` の running-config へ反映される必要があるため、`bgpd` プロセスが起動していなければ `__run_command()` が失敗し `syslog ERR 'failed running BGP IP prefix AF config command'` で `continue`（frrcfgd.py:3184-3186）。
- **順序依存**: `frrcfgd` 自身は systemd の `frr.service` (`bgpd` を含む) より後に起動する想定だが、`bgpd` の SIGHUP 中 / restart 中に書き込みが届くと取りこぼす。frrcfgd は再試行・deferred キューを持たないので、その期間に書かれた `BGP_GLOBALS_AF_NETWORK` エントリは reapply トリガが来るまで FRR に反映されない。
- **緩和策**: 起動シーケンス側で `frr-bgpd` の `wait_till_system_init_done` 相当を確認してから書き込む。runtime 中は `vtyshconnector` の reconnect で自動回復するが、その間の書き込み欠落はある。
- evidence: `frrcfgd.py:85-99 (BGP_TABLE_NAME_MAP daemons), 3184-3186 (__run_command 失敗時 continue, リトライなし)`

### 4. `ROUTE_MAP_SET` (`policy` leafref) 先行推奨 — 未存在 route-map での `network ... route-map` 投入

- `policy` フィールドは `ROUTE_MAP_SET.name` への leafref（YANG `sonic-bgp-global.yang`）。`af_network_key_map` (frrcfgd.py:1985) では `++policy` (opt_idx_list) として処理され、値がある場合 `network <prefix> route-map <name>` が生成される。
- `frrcfgd` 側では `policy` 値の route-map 実在チェックは **行わない**（`network-policy` フォーマッタは単純に文字列を埋めるだけ, frrcfgd.py:922-924）。
- **FRR 側挙動**: `bgpd` は未定義の route-map を参照する `network <prefix> route-map <name>` を受理する（"permit any" として動作 → 全 permit になる）。後から `route-map <name> permit/deny` を入れると即時反映される。
- **順序依存**: 厳密な reject はないが、route-map による prefix 属性加工を意図した運用では `ROUTE_MAP` / `ROUTE_MAP_SET` 投入を先行させること。逆順だと route-map が空の期間中は意図しない全許可で広告される。
- evidence: `frrcfgd.py:1985 (af_network_key_map), 922-924 (network-policy formatter), 86 (ROUTE_MAP daemons: zebra/bgpd/ospfd)`

### 5. `VRF` テーブル先行必須（default 以外の VRF）

- `vrf_tables` (frrcfgd.py:2136-2140) には `BGP_GLOBALS_AF_NETWORK` が含まれ、key 第1要素は VRF 名として解釈される。`__get_vrf_asn(vrf)` が `self.bgp_asn[vrf]` を参照するが、これは `BGP_GLOBALS` 経由で投入される。
- ただし VRF 自体（`zebra` 配下の `vrf <name>`）が未生成だと `router bgp <asn> vrf <name>` が `bgpd` で失敗する可能性。`VRF` テーブルは `vrf_handler` 経由で `zebra` に投入される（frrcfgd.py:2294 で `table_handler_list` 先頭付近、`BGP_GLOBALS` より前）。
- **順序依存**: `default` VRF 以外を使う場合、`VRF|<name>` → `BGP_GLOBALS|<name>` → `BGP_GLOBALS_AF|<name>|<afi_safi>` → `BGP_GLOBALS_AF_NETWORK|<name>|<afi_safi>|<prefix>` の順を守ること。逆順は依存 #1 と同じく silent drop。
- evidence: `frrcfgd.py:2294 (VRF handler 最先頭), 100 (VRF daemons: zebra), 2136-2140`

### 6. `network_import_check` (RIB 存在チェック) との非同期性

- これは厳密には CONFIG_DB の書込み順依存ではないが、`BGP_GLOBALS.network_import_check` (FRR デフォルト `true`) が有効な場合、`network <prefix>` で広告するためにはそのプレフィックスが既に **RIB に存在**している必要がある。RIB に乗るためには `STATIC_ROUTE` / `INTERFACE`（直結） / `ROUTE_REDISTRIBUTE` 等の経路がある。
- `frrcfgd` は CONFIG_DB への書き込みを成功させ、FRR にも投入するが、**実際の BGP UPDATE 注入は遅延または発生しない**。
- **タイミング依存**: 静的経路や IGP 経路の収束を待ってから `BGP_GLOBALS_AF_NETWORK` を書く運用ではないと、書込み後に広告されない期間が発生する。再試行は FRR 側で内部的に発生する。
- evidence: `BGP_GLOBALS.network_import_check` フィールド (`sonic-bgp-global.yang`), FRR `bgpd` `network` コマンド仕様（一般知識・bgpd ドキュメント）

### 7. DEL 操作の挙動 — 内部キャッシュなし、即時 `no network` 発行

- `BGP_GLOBALS_AF_NETWORK` 分岐は `BGP_GLOBALS_AF_AGGREGATE_ADDR` と違って `self.af_aggr_list` のような内部キャッシュ更新を**持たない**（frrcfgd.py:3187-3196 の if は AGGREGATE_ADDR 限定）。
- DEL 時は `op = OP_DELETE` で `key_map.run_command` に渡され、`{no:no-prefix}` フォーマッタが `no network <prefix> ...` を生成。
- **順序依存なし**（DEL は即時で待機ループや前提依存なし）。ただし `local_asn` が `None` になっている VRF への DEL は依存 #1 で同様に silent drop される。
- evidence: `frrcfgd.py:3169-3186 (NETWORK 分岐), 3187-3196 (AGGREGATE_ADDR 限定の内部キャッシュ更新)`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `BGP_GLOBALS.local_asn` → `BGP_GLOBALS_AF_NETWORK` | 先行必須（silent drop、再試行なし） | `BGP_GLOBALS` を必ず先に書く（`__apply_dep_vrf_table` は NETWORK 対象外） |
| 2 | `BGP_GLOBALS_AF` → `BGP_GLOBALS_AF_NETWORK` | 推奨先行 | `table_handler_list` 順序で起動時 walk は保証、runtime は中間状態あり |
| 3 | `bgpd` プロセス起動 → 書込み | 先行必須（未起動時 vtysh 失敗・再試行なし） | systemd 順序、SIGHUP/restart 期間は書込み欠落許容 |
| 4 | `ROUTE_MAP_SET[policy]` → `BGP_GLOBALS_AF_NETWORK[policy=name]` | 推奨先行 | frrcfgd・FRR とも未存在 route-map を受理（permit-any 期間あり） |
| 5 | `VRF|<name>` → `BGP_GLOBALS|<name>` → `BGP_GLOBALS_AF_NETWORK` | 先行必須（default 以外） | `table_handler_list` で VRF が最先頭 |
| 6 | RIB 上に prefix 存在 → 実際の BGP UPDATE 注入 | タイミング依存（書込みは成功） | `network_import_check=false` で回避、または IGP 収束待ち |
| 7 | DEL 操作 | 即時、内部キャッシュなし | `local_asn=None` の VRF への DEL は silent drop |
