# dscp-to-tc-map — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `DSCP_TO_TC_MAP`

### CLI
- `config qos map dscp-tc add/del <map-name> <dscp> <tc>`
  - ソース: `sonic-utilities/config/main.py (qos グループ)`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `qos_config.j2` から platform 別 DSCP→TC マップが生成される場合あり

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
