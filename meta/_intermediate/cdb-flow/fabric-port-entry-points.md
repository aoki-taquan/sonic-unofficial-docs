# fabric-port — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `FABRIC_PORT`

### CLI
- `config fabric port status enable/disable <port>`
  - ソース: `sonic-utilities/config/main.py (fabric グループ)`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- プラットフォーム `platform.json` から fabric ポート一覧が `sonic-cfggen` 経由で生成

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
