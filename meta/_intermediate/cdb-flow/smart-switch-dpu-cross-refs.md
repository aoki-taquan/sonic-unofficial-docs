# smart-switch-dpu — Phase C 調査証跡 (cross-table refs)

調査日: 2026-05-17

## 調査対象ファイル

- `src/sonic-yang-models/yang-models/sonic-smart-switch.yang` — YANG leafref 定義
- `src/sonic-yang-models/yang-models/sonic-vnet.yang` — VNET テーブル定義
- `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py:60-100` — dhcp_cfggen generate() の参照テーブル
- `src/sonic-dhcp-utilities/dhcp_utilities/common/utils.py:153-161` — is_smart_switch()
- `src/sonic-config-engine/config_samples.py:80-157` — SmartSwitch/DPU サンプル config 生成
- `src/sonic-config-engine/smartswitch_config.py:20-45` — platform.json から DPU/DPUS 読み込み
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:44,355,749,1143,1187,1270` — chassisd CONFIG_DB アクセス

## YANG leafref まとめ

sonic-smart-switch.yang で明示的に定義されている leafref:

| フィールド | テーブル | leafref パス |
|---|---|---|
| `DASH_HA_GLOBAL_CONFIG.global.vnet_name` (deprecated) | CONFIG_DB `VNET` | `/sonic-vnet:sonic-vnet/sonic-vnet:VNET/sonic-vnet:VNET_LIST/sonic-vnet:name` |
| `DASH_HA_GLOBAL_CONFIG.global.dpu_vnet` | CONFIG_DB `VNET` | `/sonic-vnet:sonic-vnet/sonic-vnet:VNET/sonic-vnet:VNET_LIST/sonic-vnet:name` |

その他のテーブル (`MID_PLANE_BRIDGE`, `DPUS`, `DPU`, `REMOTE_DPU`, `VDPU`) には YANG leafref なし。

## dhcp_cfggen の暗黙参照

`dhcp_cfggen.py:generate()` (L60-100) は以下テーブルをまとめて読み込む:

1. `DEVICE_METADATA|localhost` → `is_smart_switch()` で `subtype == "SmartSwitch"` を確認。`False` だと `MID_PLANE_BRIDGE` / `DPUS` を完全スキップ (L65-67,76)
2. `MID_PLANE_BRIDGE|GLOBAL` → `bridge` + `ip_prefix` 両フィールドを確認 (L84)
3. `DPUS|*` → ミッドプレーンポート一覧 (L74)
4. `DHCP_SERVER_IPV4` / `DHCP_SERVER_IPV4_PORT` → DHCP サーバー設定 (L80)

## chassisd の参照

chassisd (L355, L749, L1143, L1187) は `CHASSIS_MODULE` テーブル (CONFIG_DB) のみ読み書きし、`DPU` / `DPUS` テーブルを直接参照しない。ただし `SmartSwitchConfigManagerTask` (L1245-1270) が `PORT` テーブルを読む（DPU の dataplane state 判定）。

## config_samples.py の相互依存

`generate_t1_smartswitch_switch_sample_config()` (L80-151):
- `DEVICE_METADATA.localhost.subtype = "SmartSwitch"` を書き込む
- `platform.json` 由来の `DPUS` エントリから `DHCP_SERVER_IPV4` / `DHCP_SERVER_IPV4_PORT` を自動生成
- `FEATURE.dhcp_server.state = "enabled"` を同時設定

`generate_dpu_sample_config()` (L153-180):
- `DEVICE_METADATA.localhost.switch_type = "dpu"`, `type = "SmartSwitchDPU"`, `subtype = "SmartSwitch"` を書き込む

## まとめ

| テーブル | 参照元 | 参照方向 | YANG leafref | 必須度 |
|---|---|---|---|---|
| `DEVICE_METADATA\|localhost` (subtype) | dhcp_cfggen, config_samples | 読み取り (SmartSwitch 判定) | なし | 必須（欠如でDPU DHCP完全無効）|
| `VNET\|<name>` | YANG (sonic-smart-switch) | 読み取り (DASH_HA_GLOBAL_CONFIG.dpu_vnet / vnet_name) | あり (leafref) | 条件付き必須（DASH_HA設定時）|
| `DHCP_SERVER_IPV4` / `DHCP_SERVER_IPV4_PORT` | config_samples, dhcp_cfggen | 書き込み (DPU DHCP自動生成) | なし | 派生テーブル（自動生成）|
| `FEATURE\|dhcp_server` | config_samples | 書き込み (dhcp_server有効化) | なし | 派生テーブル（自動生成）|
| `CHASSIS_MODULE` | chassisd | 読み書き (DPU admin state) | なし | 任意（モジュール管理時）|
| `PORT` | chassisd (DPU側 SmartSwitchConfigManagerTask) | 読み取り (dataplane state判定) | なし | DPU側のみ |
