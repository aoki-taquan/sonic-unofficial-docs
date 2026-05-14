# bmp — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `BMP`

### CLI
- `config bmp enable/disable`
- `config bmp table enable/disable <table>`
  - ソース: `sonic-utilities/config/main.py (bmp グループ)`

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
