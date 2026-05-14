# breakout-cfg — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `BREAKOUT_CFG`

### CLI
- `config interface breakout <port> <mode>`
  - ソース: `sonic-utilities/config/main.py (interface グループ)`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- プラットフォーム提供の `platform.json` / `port_config.ini` から `sonic-cfggen` が初期値を注入

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
