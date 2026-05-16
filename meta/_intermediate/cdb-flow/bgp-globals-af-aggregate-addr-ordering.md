# BGP_GLOBALS_AF_AGGREGATE_ADDR — Phase B 書込み順依存スキャンノート

対象テーブル: `BGP_GLOBALS_AF_AGGREGATE_ADDR`
Consumer: `frrcfgd` / `BGPConfigDaemon` (`sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`)
スキャン範囲: `__init__()` 初期 snapshot ロード、`table_handler_list` 登録順、`bgp_table_handler_common()` 経路、`hdl_af_aggregate()`、`AggregateAddr` クラス、`af_aggregate_key_map`、vtysh `aggregate-address` コマンドの順序要件。

---

## 検出した順序依存・タイミング依存

### 1. `BGP_GLOBALS` 先行必須 — bgp_asn が無いと aggregate コマンドが組み立てられない

- `bgp_table_handler_common()` 内の `BGP_GLOBALS_AF_AGGREGATE_ADDR` 分岐 (L3169) では、対象 VRF の `local_asn` を `self.bgp_asn[vrf]` から取得し、`cmd_prefix = ['configure terminal', 'router bgp {local_asn} vrf {vrf}', 'address-family {af} {ip_type}']` を組み立てる (L3179-3182)。
- `bgp_asn[vrf]` は `BGP_GLOBALS` ハンドラ (`bgp_global_handler`) が `local_asn` を読み込んだ時点で初めて登録される。
- **順序依存**: 対応 VRF の `BGP_GLOBALS|<vrf>` (`local_asn` 設定) が CONFIG_DB に**先に**存在しないと、`router bgp <as>` プレフィクスが組み立てられず、aggregate-address コマンドが FRR に流れない。
- `table_handler_list` (L2296-2317) では `BGP_GLOBALS` が 3 番目、`BGP_GLOBALS_AF_AGGREGATE_ADDR` が 23 番目に登録されているため、`load()` フェーズでは同 daemon インスタンス内で必ず `BGP_GLOBALS` が先処理される。runtime subscribe では到着順依存となるが、`KeyError` 例外で握り潰され続けるため、後追いで `BGP_GLOBALS` が届いても aggregate は自動再投入されない（再 SET が必要）。
- evidence: `frrcfgd.py:3169-3186, 2296-2317`

### 2. `BGP_GLOBALS_AF` 先行推奨 — address-family コンテキスト

- aggregate-address は FRR で `router bgp <as>` → `address-family <afi> <safi>` → `aggregate-address <prefix>` の階層下に置かれる (L3180-3182)。
- vtysh は `address-family` コンテキスト未確立でも該当行を受け付け FRR 側で自動的に AF を生やすが、`BGP_GLOBALS_AF` で AF レベル設定 (`multipath`, `route-distance`, `advertise-all-vni` 等) を後から書くと、その時点で AF コンテキストが再構成され、既に投入された aggregate-address はそのまま保持される。順序が逆になっても致命ではないが、AF の派生属性 (例 `max-paths`) は AF 設定到着まで非反映。
- **順序依存（中間状態最小化）**: `BGP_GLOBALS_AF|<vrf>|<afi_safi>` を先に書いてから aggregate を投入することで、AF 属性と aggregate が同一適用ウィンドウで揃う。
- `table_handler_list` では `BGP_GLOBALS_AF` (4 番目) が `BGP_GLOBALS_AF_AGGREGATE_ADDR` (23 番目) より先に処理されるため load フェーズでは自動保証。
- evidence: `frrcfgd.py:2297, 2317`, `frrcfgd.py:3169-3186`

### 3. `__init__` snapshot 段階 — `BGP_GLOBALS` snapshot が `af_aggr_list` 構築前に必要

- `BGPConfigDaemon.__init__()` (L2257-2266) は CONFIG_DB から `BGP_GLOBALS_AF_AGGREGATE_ADDR` テーブルを一括取得し `self.af_aggr_list[vrf][prefix] = AggregateAddr()` を構築する。
- ただしこのループは `bgp_asn[vrf]` を参照しない（純粋にキャッシュ構築のみ）。`bgp_asn` の初期化は同 `__init__` のより前段 (`glb_table = self.config_db.get_table('BGP_GLOBALS')` L2207-2213) で行われる。
- **順序依存（コード内）**: `__init__` の固定順序により、daemon 起動時のスナップショットでは `BGP_GLOBALS` → `BGP_GLOBALS_AF_AGGREGATE_ADDR` の順で読まれることがコードレベルで保証される。CONFIG_DB に aggregate が存在しても `BGP_GLOBALS` が無い場合、`af_aggr_list` はキャッシュされるが、後段の `table_handler_list` 駆動の SET イベントで `bgp_asn[vrf]` 不在となり vtysh 投入は失敗する。
- evidence: `frrcfgd.py:2207-2213, 2257-2266`

### 4. `frrcfgd` 起動順序 — `bgpd` が ready でないと vtysh が失敗する

- aggregate-address コマンドは `vtysh -c 'configure terminal' -c 'router bgp ...'` 経由で `bgpd` に投入される (L3180)。
- `bgpd` が socket 受付前 (`/var/run/frr/bgpd.vty` 未生成) に vtysh を実行すると `Exiting: failed to connect to any daemon` で失敗、`run_command()` が False を返して syslog ERR (L3185-3186)。frrcfgd 内部キャッシュは更新されるが FRR には反映されない。
- **順序依存**: docker-fpm-frr コンテナ内では `supervisord` が `bgpd` → `frrcfgd` の順に起動するよう設定されているが、再起動レース時は frrcfgd 側の subscribe が先行し得る。frrcfgd は `run_command` 失敗時に再試行しないため、bgpd 復活後に CONFIG_DB へ再 SET （`hset` で同値書き直し）するか、`/usr/bin/frrcfg.sh restart` で再 replay する必要がある。
- evidence: `frrcfgd.py:3179-3186` (key_map.run_command 戻り値ハンドリング)

### 5. bgpd CLI 順 — `no aggregate-address` を先行発行する mutation 戦略

- `hdl_af_aggregate()` (L1313-1326) は UPDATE 操作 (`op != OP_DELETE`) のとき、既存 entry が `self.af_aggr_list[vrf]` に存在するなら **先に `no aggregate-address <prefix>` を生成**し (`cmd_list.append(cmd_str.format(... no=False))`)、その後 `get_command_cmn()` で実 SET コマンドを追加する。
- これにより既存の `as_set` / `summary_only` / `policy` を一旦剥がしてから再投入する、Update = (Delete + Add) の振る舞いになる。
- **順序依存（FRR 内部）**: bgpd は同一 prefix に対する `aggregate-address` の重複設定をマージせず最後の指定で上書きするが、`as-set` / `summary-only` / `route-map` の **欠落フィールドは引き継がず**消える。frrcfgd が `no` を先行発行するのはこの仕様の事故防止策で、CLI として `no aggregate-address` → `aggregate-address <new>` の順序は逆転できない。
- 同一 vtysh セッション内でこの 2 行が連続投入されるため、外部から見た中間状態 (aggregate 一時消失) は短時間だが、`summary-only` 利用時はその瞬間に more-specific ルートが一瞬広告される副作用に注意。
- evidence: `frrcfgd.py:1313-1326`

### 6. DEL 時の cache 更新順

- DEL 操作で `bgp_table_handler_common` の AGGREGATE_ADDR 分岐 (L3187-3197) は、`key_map.run_command` で `no aggregate-address` を投入後に `self.af_aggr_list[vrf].pop(norm_ip_prefix, None)` を呼ぶ (L3194-3197)。
- **順序依存なし**（pop は `None` デフォルトで KeyError 発生せず）。ただし FRR 投入失敗時もキャッシュは pop されないため、次回 UPDATE 時の `no` 先行発行に使われ続ける（リソースリークではない）。
- evidence: `frrcfgd.py:3187-3197`

### 7. `normalize_ip_prefix` 失敗時の早期 continue

- key 内の `ip_prefix` が `inet:ip-prefix` 形式として不正な場合 `MatchPrefix.normalize_ip_prefix()` が None を返し、`continue` で当該エントリの処理がスキップされる (L3172-3175)。
- **順序依存なし**だが、後続エントリの処理は継続するため、不正キーがあっても他 prefix の aggregate は通常通り適用される。
- evidence: `frrcfgd.py:3172-3175`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `BGP_GLOBALS|<vrf>.local_asn` → `BGP_GLOBALS_AF_AGGREGATE_ADDR` | 先行必須（bgp_asn 不在で vtysh コマンド組立失敗） | load フェーズ内は table_handler_list 順序で自動保証。runtime 追加は事後再 SET が必要 |
| 2 | `BGP_GLOBALS_AF|<vrf>|<afi_safi>` → `BGP_GLOBALS_AF_AGGREGATE_ADDR` | 推奨先行（AF 属性と aggregate 同期適用） | load 内は自動保証、runtime は順序逆でも aggregate は反映 |
| 3 | `__init__` 内 `BGP_GLOBALS` snapshot → `af_aggr_list` 構築 | コード固定順で保証 | — |
| 4 | `bgpd` 起動完了 → frrcfgd の vtysh 発行 | 強制（vtysh socket 必要） | bgpd 復活後の再 SET、または `frrcfg.sh restart` で replay |
| 5 | UPDATE 時 `no aggregate-address` 先行 → `aggregate-address <new>` | コード固定（hdl_af_aggregate） | 中間 1 瞬の more-specific 漏れに注意（summary-only 利用時） |
| 6 | DEL 時 vtysh `no` 投入 → `af_aggr_list.pop` | コード固定（順序逆でも KeyError なし） | — |
| 7 | 不正 `ip_prefix` キー → 当該 entry skip | 即時 continue | 他エントリは正常処理 |
