# fg-nhg — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `FG_NHG`

### CLI
- `config fg-nhg add/del <nhg-name> --bucket-size <n> --match-mode <mode>`
  - ソース: `sonic-utilities/config/plugins/sonic-fine-grained-ecmp_yang.py`

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
