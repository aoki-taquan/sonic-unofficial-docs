# BGP_AGGREGATE_ADDRESS — Phase B 書込み順依存スキャンノート

対象テーブル: `BGP_AGGREGATE_ADDRESS` / `BGP_GLOBALS_AF_AGGREGATE_ADDR`
Consumer: `bgpcfgd / AggregateAddressMgr` (`sonic-bgpcfgd/bgpcfgd/managers_aggregate_address.py`) および `frr-mgmt-framework / frrcfgd` (`sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`)
スキャン範囲: `managers_aggregate_address.py` 全 265 行精読 + `frrcfgd.py` の aggregate / local_asn / table 処理パス

---

## 検出した順序依存・タイミング依存

### 1. `BGP_GLOBALS.local_asn` 先行必須 (frrcfgd 経路)

- `frrcfgd.py:2658-2662` で VRF based table 更新時に `local_asn = self.__get_vrf_asn(vrf)` を参照。`local_asn is None` かつ更新対象が `BGP_GLOBALS` 以外 (= `BGP_GLOBALS_AF_AGGREGATE_ADDR` を含む) または `local_asn` フィールドを伴わない場合、当該 update を **`continue` でスキップ**する。
- 該当 syslog: `'ignore table {} update because local_asn for VRF {} was not configured'`。
- `BGP_GLOBALS|<vrf>` を先に書き、`local_asn` が `self.bgp_asn[vrf]` に格納 (`frrcfgd.py:2703`) されて初めて `BGP_GLOBALS_AF_AGGREGATE_ADDR|<vrf>|<af>|<prefix>` の処理が成立する。
- `local_asn` 設定成功直後に `__apply_dep_vrf_table(vrf, 'ROUTE_REDISTRIBUTE')` が呼ばれる (L2704) が、aggregate-address は再適用対象に含まれていない。**aggregate を local_asn より先に書くと黙って捨てられる**点に注意。
- evidence: `frrcfgd.py:2658-2716`

### 2. `DEVICE_METADATA.localhost.bgp_asn` 先行必須 (bgpcfgd 経路)

- `AggregateAddressMgr.__init__` のスーパー初期化時に依存宣言:
  `[("CONFIG_DB", swsscommon.CFG_DEVICE_METADATA_TABLE_NAME, "localhost/bgp_asn")]`
  (`managers_aggregate_address.py:33-40`)。
- Manager フレームワーク (`directory` / `Manager` 基底) が当該パスを満たすまで `set_handler()` は呼ばれない。
- `address_set_handler()` 冒頭 (L93) で `self.directory.get_slot(... CFG_DEVICE_METADATA_TABLE_NAME)["localhost"]["bgp_asn"]` を取得。未設定だと KeyError が上位に伝播する。
- evidence: `managers_aggregate_address.py:33-40, 93`

### 3. `BGP_BBR` テーブルの先行 (条件付き)

- `__init__` で `self.directory.subscribe([(CONFIG_DB_NAME, BGP_BBR_TABLE_NAME, BGP_BBR_STATUS_KEY)], self.on_bbr_change)` (L41) により `BGP_BBR` 変化を購読。
- `set_handler()` は `path_exist()` チェックで分岐:
  - `BGP_BBR.status` 未設定 → `bbr_status = ""` (L75-76)。
  - `bbr-required=true` かつ `bbr_status` が `enabled/disabled` のいずれでもない (=未設定) → `ADDRESS_INACTIVE_STATE` に落として FRR 投入をスキップ (L78-80)。
- **順序依存**: `bbr-required=true` の集約を書き込む場合、`BGP_BBR|all.status=enabled` を先に CONFIG_DB へ書かないと aggregate は STATE_DB 上 inactive にとどまる。後から BBR が enabled に切り替わると `on_bbr_change()` が STATE_DB を走査して FRR に再投入する (L49-56) ため最終的には収束する。
- evidence: `managers_aggregate_address.py:41, 46-63, 73-83`

### 4. `ROUTE_MAP` / `PREFIX` set 先行必須 (frrcfgd `aggr-policy` 経路)

- `frrcfgd.py:1982-1983` の `af_aggregate_key_map`:
  `'{no:no-prefix}aggregate-address {2} {3:aggr-as-set} {4:aggr-summary-only} {5:aggr-policy}'`
  — `{5:aggr-policy}` は OpenConfig BGP の `set-options/policy` を解決してルートマップ名に変換する。
- frrcfgd は `ROUTE_MAP` テーブル変化時に `prefix_set_list` から AF を引いて `ipv4` / `ipv6` を解決 (`frrcfgd.py:2669-2676`)。集約に紐づくルートマップが未登録なら FRR コマンド側で `aggregate-address ... route-map <name>` を発行しても route-map は空、結果として集約に対する属性付与が機能しない。
- **順序依存**: `aggr-policy` 経由でルートマップを使う場合、`ROUTE_MAP` および参照される `PREFIX_SET` / `PREFIX` を先に CONFIG_DB に書く。
- evidence: `frrcfgd.py:1982-1983, 2669-2676`

### 5. bgpcfgd `aggregate-address-prefix-list` / `contributing-address-prefix-list` の vtysh 順序

- `address_set_handler()` は `cmd_list` に以下の順序で追記:
  1. `generate_aggregate_address_commands()` → `router bgp <asn>` / `address-family ipv4|ipv6` / `aggregate-address <prefix> [summary-only] [as-set]` / `exit-address-family` / `exit` (L241-251)
  2. `generate_prefix_list_commands(is_con=False)` → `ip|ipv6 prefix-list <name> permit <prefix>` (L114-122)
  3. `generate_prefix_list_commands(is_con=True)` → `ip|ipv6 prefix-list <name> permit <prefix> le 32|128` (L124-132)
- そして `self.cfg_mgr.push_list(cmd_list)` で一括投入 (L135)。**aggregate 本体 → prefix-list の順**であることに注意 (prefix-list を先に投入してから aggregate に紐付ける標準的な順とは逆)。これは bgpd が prefix-list の前方参照を許容するため動作するが、中間状態では aggregate が「存在しない prefix-list を参照する」状態が瞬間的に発生する。
- `del_handler` も同順 (`address_del_handler` L155-181)。
- evidence: `managers_aggregate_address.py:104-135, 155-185, 239-264`

### 6. bgpd vtysh の階層順序

- `generate_aggregate_address_commands()` (L239-252) は必ず以下の固定順を組み立てる:
  ```
  router bgp <asn>
  address-family ipv4|ipv6
  [no ]aggregate-address <prefix> [summary-only] [as-set]
  exit-address-family
  exit
  ```
- この順は bgpd の CLI モード遷移 (config → router-bgp → address-family) に従う。`router bgp <asn>` が未存在の場合、bgpd 内部で `router bgp` を作る副作用が走り、`local_asn` がフレームワーク管理外で書き込まれる。`bgpcfgd / frrcfgd` 共に **`BGP_GLOBALS.local_asn` の確定が前提**であることがここでも担保される (依存 #1, #2 と整合)。
- evidence: `managers_aggregate_address.py:239-252`

### 7. STATE_DB クリア → CONFIG_DB 購読 の起動順

- `__init__` 末尾で `self.remove_all_state_of_address()` (L44) を呼び、STATE_DB の `BGP_AGGREGATE_ADDRESS` をすべて削除してから購読を開始する。
- **意味**: bgpcfgd 再起動時、CONFIG_DB に残っている aggregate は再度 `set_handler()` を経由して STATE_DB に書き直される。再起動直後の極短時間は STATE_DB が空となるため、外部観測する場合は `bgpcfgd` のレディネスを `inactive` の有無で判定してはならない。
- evidence: `managers_aggregate_address.py:42-44, 203-207`

### 8. `BGP_GLOBALS_AF_AGGREGATE_ADDR` の frrcfgd table 列挙順

- `frrcfgd.py:2139` の table 列挙 (handler 登録順) では `BGP_GLOBALS` → `BGP_GLOBALS_AF` → `BGP_GLOBALS_AF_AGGREGATE_ADDR` → `BGP_GLOBALS_AF_NETWORK` の順で並ぶ。
- 初期スキャン (`bgp_table_handler_common` を初期化時に table 単位で順次呼ぶ経路) はこの順で処理されるため、`address-family` 宣言を伴う `BGP_GLOBALS_AF` が aggregate より先に bgpd へ投入される。逆順 (aggregate → AF) で書こうとしても、frrcfgd 側のループ順により最終的に正しい順に並ぶが、`local_asn` 未設定の VRF では continue で捨てられる (依存 #1)。
- evidence: `frrcfgd.py:2139, 2317`

---

## まとめ — 推奨書込み順

1. `DEVICE_METADATA|localhost.bgp_asn` (bgpcfgd 依存解決用)
2. `BGP_GLOBALS|<vrf>.local_asn` (frrcfgd 依存解決用)
3. `BGP_GLOBALS_AF|<vrf>|<af>` (address-family 宣言)
4. `BGP_BBR|all.status` (`bbr-required=true` を使う場合のみ)
5. `ROUTE_MAP` / `PREFIX_SET` (`aggr-policy` を使う場合のみ)
6. `BGP_AGGREGATE_ADDRESS|<prefix>` または `BGP_GLOBALS_AF_AGGREGATE_ADDR|<vrf>|<af>|<prefix>`

DEL 操作は逆順 (aggregate → policy / BBR → BGP_GLOBALS) を推奨。`bgpcfgd` 経路の DEL は STATE_DB が `inactive` の場合 FRR 削除コマンドをスキップする (`managers_aggregate_address.py:138-146`)。
