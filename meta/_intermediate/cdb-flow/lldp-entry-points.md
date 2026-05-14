# lldp — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `LLDP`

### CLI
- `config lldp global txinterval <n>`
- `config lldp global sysdescr <desc>`
- `config lldp global sysdescr-type <type>`
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
