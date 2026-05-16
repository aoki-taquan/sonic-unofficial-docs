# BGP_GLOBALS_AF_NETWORK — 暗黙参照スキャン (Task F Phase C)

ソース: `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## 検出した暗黙参照

### 1. BGP_GLOBALS

- **種別**: 必須先行依存
- **参照箇所**: `frrcfgd.py:2659`, `frrcfgd.py:2685-2703`, `frrcfgd.py:2175-2179`
- **内容**: `BGP_GLOBALS.local_asn` が未設定の場合、ハンドラは `syslog LOG_DEBUG 'ignore table ... because local_asn for VRF ... was not configured'` を出して `continue`（silent drop）する。`frrcfgd` 起動時に `get_table('BGP_GLOBALS')` で全 VRF の ASN をキャッシュする (`bgp_asn` dict)。
- **方向**: BGP_GLOBALS → BGP_GLOBALS_AF_NETWORK（BGP_GLOBALS が先行必須）

### 2. BGP_GLOBALS_AF

- **種別**: 推奨先行依存
- **参照箇所**: `frrcfgd.py:2107`, `frrcfgd.py:2297`, `frrcfgd.py:2771-2774`
- **内容**: `BGP_GLOBALS_AF` は `table_handler_list` で `BGP_GLOBALS_AF_NETWORK` より先に登録される（`frrcfgd.py:2297 vs 2318`）。AF レベル属性（`max_ebgp_routes` 等）が本テーブルより先にハンドラへ投入されることを意図した設計。runtime では投入順は保証されないが、AF コンテキストが FRR 側で先に存在していると `address-family` ブロックへの `network` コマンドが確実に受理される。
- **方向**: BGP_GLOBALS_AF → BGP_GLOBALS_AF_NETWORK（推奨順序）

### 3. ROUTE_MAP

- **種別**: オプション先行依存（`policy` フィールド使用時）
- **参照箇所**: `frrcfgd.py:2113`, `frrcfgd.py:2669-2676`, `frrcfgd.py:922-924`
- **内容**: `BGP_GLOBALS_AF_NETWORK.policy` フィールドが route-map 名を参照する。frrcfgd は参照先の存在を検証せず、`network <prefix> route-map <name>` を即時発行する。未定義 route-map を FRR は permit-any として扱い**全プレフィックスを広告**する（意図しない広告漏洩リスク）。`ROUTE_MAP` 変更は `bgp_table_handler_common` 経由で FRR へも反映される。
- **方向**: ROUTE_MAP → BGP_GLOBALS_AF_NETWORK（推奨順序。policy 参照時は先行推奨）

### 4. DEVICE_METADATA

- **種別**: グローバル制御フラグ参照
- **参照箇所**: `frrcfgd.py:2162-2168`
- **内容**: `frrcfgd` 初期化時に `DEVICE_METADATA|localhost` から `frr_mgmt_framework_config` フラグと `docker_routing_config_mode` を読み取る。`frr_mgmt_framework_config = true` の場合のみ `frrcfgd` 全体が有効化される（このフラグが false の環境では BGP_GLOBALS_AF_NETWORK ハンドラ自体が起動しない）。
- **方向**: DEVICE_METADATA → BGP_GLOBALS_AF_NETWORK（前提フラグ）

## まとめ

| 参照先テーブル | 必須度 | 参照用途 |
|---|---|---|
| BGP_GLOBALS | 必須 | local_asn 取得（不在で silent drop） |
| BGP_GLOBALS_AF | 推奨 | AF コンテキスト事前確立 |
| ROUTE_MAP | 推奨（policy 使用時） | network route-map 名の実体 |
| DEVICE_METADATA | 前提フラグ | frr_mgmt_framework_config 有効確認 |
