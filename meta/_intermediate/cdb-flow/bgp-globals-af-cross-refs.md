# BGP_GLOBALS_AF — 暗黙参照スキャン (Task F Phase C)

ソース: `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## 検出した暗黙参照

### 1. BGP_GLOBALS

- **種別**: 必須先行依存
- **参照箇所**: `frrcfgd.py:2659`, `frrcfgd.py:2685-2703`, `frrcfgd.py:2175-2179`
- **内容**: `BGP_GLOBALS.local_asn` が未設定の場合、`__update_bgp()` は `syslog LOG_DEBUG 'ignore table ... because local_asn for VRF ... was not configured'` を出して `continue`（silent drop）する。frrcfgd 起動時に `get_table('BGP_GLOBALS')` で全 VRF の ASN をキャッシュする。
- **方向**: BGP_GLOBALS → BGP_GLOBALS_AF（BGP_GLOBALS が先行必須）

### 2. ROUTE_MAP

- **種別**: オプション先行依存（`import_vrf_route_map` / `route_download_filter` 使用時）
- **参照箇所**: `frrcfgd.py:2113`, `frrcfgd.py:2669-2676`, `frrcfgd.py:922-924`
- **内容**: `BGP_GLOBALS_AF.import_vrf_route_map` および `route_download_filter` フィールドが route-map 名を参照する（YANG leafref `ROUTE_MAP_SET.name`）。frrcfgd は参照先の存在を検証せず即時 FRR コマンドを発行する。`ROUTE_MAP` 自体は `bgp_table_handler_common` 経由で別途 FRR へ反映される。
- **方向**: ROUTE_MAP → BGP_GLOBALS_AF（推奨順序。route-map 参照フィールド使用時は先行推奨）

### 3. BGP_GLOBALS_AF_AGGREGATE_ADDR / BGP_GLOBALS_AF_NETWORK

- **種別**: 従属テーブル（BGP_GLOBALS_AF が先行前提）
- **参照箇所**: `frrcfgd.py:2107-2119`, `frrcfgd.py:2136-2140`, `frrcfgd.py:2317-2318`
- **内容**: `BGP_GLOBALS_AF_AGGREGATE_ADDR` / `BGP_GLOBALS_AF_NETWORK` は `vrf_tables` セットに含まれ、同一 VRF の `local_asn` チェックを共有する。`table_handler_list` では `BGP_GLOBALS_AF` が先に登録される（L2297 vs L2317-2318）。AF コンテキストが FRR 側で先に確立されないと `aggregate-address` / `network` コマンドが `address-family` ブロック外で発行される恐れがある。
- **方向**: BGP_GLOBALS_AF → BGP_GLOBALS_AF_AGGREGATE_ADDR / BGP_GLOBALS_AF_NETWORK（推奨順序）

### 4. DEVICE_METADATA

- **種別**: グローバル制御フラグ参照
- **参照箇所**: `frrcfgd.py:2162-2168`
- **内容**: frrcfgd 初期化時に `DEVICE_METADATA|localhost` から `frr_mgmt_framework_config` フラグと `docker_routing_config_mode` を読み取る。`frr_mgmt_framework_config = true` の場合のみ frrcfgd 全体が有効化される（このフラグが false の環境では BGP_GLOBALS_AF ハンドラ自体が起動しない）。
- **方向**: DEVICE_METADATA → BGP_GLOBALS_AF（前提フラグ）

## まとめ

| 参照先テーブル | 必須度 | 参照用途 |
|---|---|---|
| BGP_GLOBALS | 必須 | local_asn 取得（不在で silent drop） |
| ROUTE_MAP | 推奨（route-map フィールド使用時） | import_vrf_route_map / route_download_filter の実体 |
| BGP_GLOBALS_AF_AGGREGATE_ADDR | 従属（BGP_GLOBALS_AF が先行） | aggregate-address コンテキスト |
| BGP_GLOBALS_AF_NETWORK | 従属（BGP_GLOBALS_AF が先行） | network statement コンテキスト |
| DEVICE_METADATA | 前提フラグ | frr_mgmt_framework_config 有効確認 |
