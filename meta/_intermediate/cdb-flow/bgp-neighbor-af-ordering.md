# BGP_NEIGHBOR_AF — Phase B 書込み順依存スキャンノート

対象テーブル: `BGP_NEIGHBOR_AF`
Consumer: `frrcfgd` (`BGPConfigDaemon`) + `bgpcfgd` (`BGPPeerMgr`)
スキャン範囲: `frrcfgd.py` `__update_bgp()`, `bgp_table_handler_common()`, `__apply_dep_vrf_table()`, `table_handler_list` 全行精読; `bgpcfgd/managers_bgp.py` `add_peer()`, `post_dependencies_init()` 精読

---

## 検出した順序依存・タイミング依存

### 1. BGP_GLOBALS (local_asn) が先行必須

- `frrcfgd.py:2658-2662` の `__update_bgp()` 内で、VRF ベーステーブルへの変更処理開始時に `__get_vrf_asn(vrf)` を呼び、`local_asn` が未設定なら LOG_DEBUG を出して **silent skip** する。
- `BGP_NEIGHBOR_AF` は `__vrf_based_table(table)` が True を返すため必ずこのチェックに掛かる。
- **順序依存**: `BGP_GLOBALS|<vrf>.local_asn` を CONFIG_DB に書いてから `BGP_NEIGHBOR_AF` を書かないと、AF 設定は FRR に反映されず、ログにも目立たないメッセージ（DEBUG レベル）しか残らない。
- FRR コマンド上も `router bgp <asn> vrf <vrf>` がない状態では `address-family` ブロックに入れない（vtysh 側で拒否）。
- evidence: `frrcfgd.py:2658-2662`, `frrcfgd.py:2865-2873`

### 2. BGP_NEIGHBOR が先行必須（対象 peer の存在）

- `frrcfgd.py:2865-2874`: `BGP_NEIGHBOR_AF` 処理では `cmd_prefix` に `address-family <af> <ip_type>` を追加し、`key_map.run_command(self, table, data, cmd_prefix, nbr)` で `neighbor <nbr> ...` コマンド群を FRR に投入する。
- FRR `bgpd` では `address-family` ブロック内の `neighbor <addr> activate` 等は、**事前に `router bgp` ブロックで `neighbor <addr> remote-as` が定義されていなければ失敗**する（bgpd が `% Unknown command.` または `% No such neighbor` を返す）。
- `BGP_NEIGHBOR` の `bgp_neighbor_handler` が L2851-2853 で `BGP_NEIGHBOR` SET 成功後に `__apply_dep_vrf_table(vrf, 'BGP_NEIGHBOR_AF', key, af)` を呼び出すことで、先に `BGP_NEIGHBOR_AF` が到着していた場合でも後追い適用する仕組みが存在する。ただしこの後追い適用は `BGP_NEIGHBOR` の SET 完了が条件であり、`BGP_NEIGHBOR` が未定義のまま `BGP_NEIGHBOR_AF` のみが CONFIG_DB に書かれても直接は反映されない。
- `table_handler_list` (frrcfgd.py:2293-2318) でも登録順は `BGP_NEIGHBOR`（L2304）→ `BGP_NEIGHBOR_AF`（L2306）となっており、初期ロード時も BGP_NEIGHBOR が先に処理される。
- evidence: `frrcfgd.py:2851-2853`, `frrcfgd.py:2293-2318`, `frrcfgd.py:2865-2874`

### 3. BGP_GLOBALS_AF が先行推奨（address-family ブロック開通）

- `frrcfgd.py:2771-2813`: `BGP_GLOBALS_AF` ハンドラ (`bgp_af_handler`) は `address-family <af> <ip_type>` ブロックを FRR 上で開通させ、完了後に `__apply_dep_vrf_table(vrf, 'BGP_NEIGHBOR_AF', key, af)` (L2853) で待機中の `BGP_NEIGHBOR_AF` エントリを再適用する。
- `table_handler_list` の順序: `BGP_GLOBALS_AF`（L2297）→ `BGP_NEIGHBOR_AF`（L2306）。初期ロード時は `BGP_GLOBALS_AF` が先に処理される。
- FRR では `address-family` ブロック自体は neighbor コマンドの際に暗黙開通する場合もあるが、`max-paths`・`aggregate-address` 等の global AF 設定が先行していないと AF 全体の動作が不完全になる。
- **推奨順序**: `BGP_GLOBALS_AF` を書いてから `BGP_NEIGHBOR_AF` を書く（強制ではないが後追い再適用が保証される）。
- evidence: `frrcfgd.py:2297` (table_handler_list 登録順), `frrcfgd.py:2847-2853`

### 4. ROUTE_MAP / PREFIX_LIST / FILTER_LIST が先行推奨（FRR 名前空間解決）

- `frrcfgd.py:2302`: `ROUTE_MAP` も `bgp_table_handler_common` 経由で処理される。`table_handler_list` 登録順は `ROUTE_MAP`（L2302）→ `BGP_NEIGHBOR_AF`（L2306）であり、初期ロード時は ROUTE_MAP が先。
- `BGP_NEIGHBOR_AF` の `route_map_in` / `route_map_out` / `default_rmap` / `unsuppress_map_name` は FRR コマンドに文字列名でそのまま展開される（`frrcfgd.py:1899-1906` `nbr_af_key_map`）。
- FRR `bgpd` では `neighbor <addr> route-map <name> in` のように存在しない route-map 名を指定した場合、コマンドが成功しても経路フィルタは機能しない（bgpd は未定義 route-map を permit-all として扱う場合がある）。一方 `prefix-list` / `filter-list` 未定義名は bgpd 側でエラーになる場合がある。
- `frrcfgd.py:2669-2676`: `ROUTE_MAP` 処理時に `match_prefix_set` で `prefix_set_list` を参照しており、`PREFIX_SET` / `PREFIX` も先行が推奨される。
- **推奨順序**: `ROUTE_MAP` → `PREFIX_LIST` → `BGP_NEIGHBOR_AF`（FRR 名前空間で参照解決できない場合、コマンドは受け付けられるが意図した動作にならない）。
- evidence: `frrcfgd.py:2302` (table_handler_list), `frrcfgd.py:1899-1906`, `frrcfgd.py:2669-2676`

### 5. bgpcfgd パス: BGP_NEIGHBOR (bgp_asn) が先行必須

- `bgpcfgd/managers_bgp.py:192`: `add_peer()` は `DEVICE_METADATA.bgp_asn` を使ってテンプレートを展開し、`apply_op(cmd, vrf)` で vtysh に投入する。BGP_NEIGHBOR が未登録の peer に対して `BGP_NEIGHBOR_AF` 相当の設定を Jinja2 テンプレート経由で渡すことはない（AF 設定は neighbor テンプレ内に埋め込まれている）。
- `post_dependencies_init()` (managers_bgp.py:245-246) は `add_peer()` 初回呼び出し時に一度だけ実行される。`BGP_NEIGHBOR` の SET タイミングで全 AF テンプレが展開されるため、**bgpcfgd パスでは BGP_NEIGHBOR より前に BGP_NEIGHBOR_AF 単独を書いても無視される**。
- evidence: `bgpcfgd/managers_bgp.py:181-182`, `bgpcfgd/managers_bgp.py:245-246`

### 6. bgpd address-family CLI 投入順（FRR vtysh レベル）

- `frrcfgd.py:2869-2871`: FRR に投入するコマンド列は `configure terminal` → `router bgp <asn> vrf <vrf>` → `address-family <af> <ip_type>` の順に構成される。
- この順序は vtysh の CLI 階層に従った強制順序であり、前段コマンドが存在しない状態では後続コマンドが失敗する。
- `address-family` ブロック内で発行される `neighbor <addr> activate` / `route-map` / `max-prefix` 等のコマンドはすべてこの階層下でのみ有効。
- **FRR 内部順序**: `router bgp <asn>` → `neighbor <addr> remote-as` → `address-family <af>` → `neighbor <addr> activate` の順が正規 CLI 投入順。
- evidence: `frrcfgd.py:2869-2874`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 強制 / 推奨 | 緩和策 |
|---|----------|------|------------|--------|
| 1 | `BGP_GLOBALS.local_asn` → `BGP_NEIGHBOR_AF` | 先行必須 | 強制 | local_asn 未設定時は `__update_bgp` 内で silent skip (LOG_DEBUG)。`BGP_GLOBALS` SET 後に自動再適用なし（手動 or 再起動が必要） |
| 2 | `BGP_NEIGHBOR` (remote-as 定義) → `BGP_NEIGHBOR_AF` | 先行必須 | 強制 | `BGP_NEIGHBOR` SET 完了後に `__apply_dep_vrf_table` が `BGP_NEIGHBOR_AF` を後追い適用するため、順序逆でも最終的に収束する |
| 3 | `BGP_GLOBALS_AF` → `BGP_NEIGHBOR_AF` | 先行推奨 | 推奨 | `bgp_af_handler` が `BGP_GLOBALS_AF` SET 完了後に `BGP_NEIGHBOR_AF` を後追い再適用。初期ロード時は `table_handler_list` 順序で自動保証 |
| 4 | `ROUTE_MAP` / `PREFIX_LIST` → `BGP_NEIGHBOR_AF` | 先行推奨 | 推奨 | FRR 名前空間で未解決でも vtysh コマンドは通るが期待動作にならない。初期ロード時は `table_handler_list` 順序で自動保証 |
| 5 | (bgpcfgd パス) `BGP_NEIGHBOR` → AF 設定 | 先行必須 | 強制 | bgpcfgd は BGP_NEIGHBOR 単位でテンプレート展開するため AF 単独書き込みは無効 |
| 6 | (FRR vtysh) `router bgp` → `neighbor remote-as` → `address-family` → neighbor AF コマンド | 先行必須 | 強制 (CLI 階層) | frrcfgd が cmd_prefix でこの順序を保証して投入 |
