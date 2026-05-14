# bgp-device-global — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `BGP_DEVICE_GLOBAL`

### CLI
- `config bgp device-global tsa enable/disable`
- `config bgp device-global w-ecmp enable/disable`
  - ソース: `sonic-utilities/config/main.py (bgp グループ)`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `init_cfg.json.j2` に `BGP_DEVICE_GLOBAL` セクションが存在し `tsa_enabled: false` 等のデフォルト値が注入される

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
