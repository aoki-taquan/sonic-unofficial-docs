# lldp-port — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `LLDP_PORT`

### CLI
- `config lldp <port> enable/disable`
- `config lldp portdesc <port> <description>`
- `config lldp portid-subtype <port> <subtype>`
  - ソース: `sonic-utilities/config/main.py (lldp グループ)`

### minigraph / sonic-cfggen
- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる

### REST / gNMI (sonic-mgmt-common)
- sonic-mgmt-common lldp_app.go 経由 (OpenConfig LLDP)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
