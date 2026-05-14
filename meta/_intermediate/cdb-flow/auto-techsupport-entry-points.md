# auto-techsupport — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `AUTO_TECHSUPPORT`

### CLI
- `config auto-techsupport global enable/disable`
- `config auto-techsupport global max-techsupport-limit <pct>`
- `config auto-techsupport global rate-limit-interval <secs>`
  - ソース: `sonic-utilities/config/plugins/auto_techsupport.py`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
