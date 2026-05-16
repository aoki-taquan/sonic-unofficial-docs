# BGP_GLOBALS_AF_AGGREGATE_ADDR — 暗黙参照スキャン (Phase C)

対象テーブル: `BGP_GLOBALS_AF_AGGREGATE_ADDR`
対象ソース: `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## 概要

`BGP_GLOBALS_AF_AGGREGATE_ADDR` の YANG (`sonic-bgp-global.yang`) は `vrf_name` を `BGP_GLOBALS.vrf_name` への leafref、`policy` を `ROUTE_MAP_SET.name` への leafref として宣言する。実装側 (`frrcfgd.py`) では、これらに加え `BGP_GLOBALS` の `local_asn` を vtysh コマンド組み立てに使うこと、`BGP_GLOBALS_AF` の AF コンテキストが先に bgpd 上に存在する前提でコマンドを投入すること、`DEVICE_METADATA.frr_mgmt_framework_config = true` が daemon 起動の前提条件となることが暗黙参照として読み取れる。

## 検出した暗黙参照

### 1. `BGP_GLOBALS|<vrf>` (local_asn)

- **参照方向**: 読み取り (vtysh コマンドプレフィクス組み立て)
- **条件**: 常時 (UPDATE / DELETE 共通)
- **evidence**: `frrcfgd.py` L3162, L3180
  - `cmd_prefix = ['configure terminal', 'router bgp {} vrf {}'.format(local_asn, vrf), 'address-family {} {}'.format(af, ip_type)]`
- `local_asn` は `self.bgp_asn[vrf]` から取得され、`BGP_GLOBALS|<vrf>` の `local_asn` を `BGPConfigDaemon.__init__` および `BGP_GLOBALS` ハンドラで構築する (L2207-2213)。
- 不在時: `KeyError` が `bgp_table_handler_common()` 内で握り潰され、aggregate は FRR に投入されない。

### 2. `BGP_GLOBALS_AF|<vrf>|<afi_safi>` (AF コンテキスト)

- **参照方向**: 暗黙の先行依存 (FRR コマンド階層上の親コンテキスト)
- **条件**: aggregate-address は `router bgp <as>` → `address-family <afi> <safi>` 配下のコマンドのため、AF コンテキスト自身は frrcfgd 側で常に生成する (`cmd_prefix` 第 3 要素) が、AF レベル属性 (`multipath`、route distance、L2VPN advertise-all-vni 等) は `BGP_GLOBALS_AF` ハンドラ経由で別途投入される。
- **evidence**: `frrcfgd.py` L3163, L3181 (`address-family {} {}`), L2297 (`table_handler_list` で `BGP_GLOBALS_AF` を aggregate より先に登録)
- 不在でも aggregate コマンド自体は動くが、AF 属性は別 SET 到着まで反映されない。

### 3. `ROUTE_MAP` / `ROUTE_MAP_SET.name` (policy フィールド)

- **参照方向**: 読み取り (`policy` フィールド値 → vtysh `route-map <name>` 引数)
- **条件**: `policy` フィールドが非空のとき
- **evidence**: `frrcfgd.py` L1982-1983 (`af_aggregate_key_map` の `+policy`、`{5:aggr-policy}` フォーマット指定)、L928-930 (`format == 'aggr-policy'` 分岐で `'route-map %s'` に変換)
- YANG (`sonic-bgp-global.yang`) は `policy` を `ROUTE_MAP_SET.name` への leafref として宣言。frrcfgd は値の存在を確認するのみで route-map の実在性は FRR (`bgpd`) 側で検証される。
- ROUTE_MAP テーブル自体も `table_handler_list` (L2302) に登録され、`bgp_table_handler_common` 経由で FRR に投入される。

### 4. `DEVICE_METADATA|localhost.frr_mgmt_framework_config`

- **参照方向**: 起動時前提条件 (経路選択フラグ)
- **条件**: `true` でないと frrcfgd 経路全体が無効化される (bgpcfgd テンプレ経路が代わりに動作)
- **evidence**: `frrcfgd.py` L80 (`'DEVICE_METADATA': ['bgpd']` の依存宣言)、L2162 (`db_entry = self.config_db.get_entry('DEVICE_METADATA', 'localhost')`)、L2164-2170 (`bgp_asn` / `docker_routing_config_mode` の取得)
- `frr_mgmt_framework_config != true` の環境では `bgpcfgd` (テンプレート経路) が `BGP_AGGREGATE_ADDRESS` テーブル (本テーブルとは別) を使う。本テーブルは frrcfgd 経路でのみ有効。

## 参照しないテーブル (確認済み)

`frrcfgd.py` の `BGP_GLOBALS_AF_AGGREGATE_ADDR` 分岐 (L3169-3197) および `hdl_af_aggregate()` (L1313-) を全文走査した結果、以下のテーブルは **直接参照しない**:

- `VRF` — vrf 名は CONFIG_DB key にそのまま含まれ、`BGP_GLOBALS.vrf_name` の leafref として担保される。frrcfgd は VRF テーブル本体を読まない。
- `PORT` / `INTERFACE` / `LOOPBACK_INTERFACE` — aggregate-address は L3 prefix ベースのため interface 参照なし。
- `NEXTHOP` / `ROUTE_TABLE` — aggregate 計算は bgpd 内部 RIB に基づき、CONFIG_DB 経路情報は使わない。

## 参照元 evidence サマリ

| 参照先 | 種別 | L# (frrcfgd.py) |
|--------|-----|-----------------|
| `BGP_GLOBALS.local_asn` | 暗黙 (vtysh プレフィクス) | 3162, 3180, 2207-2213 |
| `BGP_GLOBALS_AF` (AF コンテキスト) | 暗黙 (コマンド階層) | 3163, 3181, 2297 |
| `ROUTE_MAP_SET.name` (`policy`) | YANG leafref + 実装 | 1982-1983, 928-930 |
| `DEVICE_METADATA.frr_mgmt_framework_config` | 起動経路選択 | 80, 2162-2170 |
