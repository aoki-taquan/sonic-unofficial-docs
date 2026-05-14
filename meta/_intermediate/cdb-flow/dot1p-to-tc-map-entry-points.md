# dot1p-to-tc-map — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `DOT1P_TO_TC_MAP`

### CLI
- `config qos map dot1p-tc add/del <map-name> <dot1p> <tc>`
  - ソース: `sonic-utilities/config/main.py (qos グループ)`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `qos_config.j2` から platform 別 QoS マップが生成される場合あり

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
