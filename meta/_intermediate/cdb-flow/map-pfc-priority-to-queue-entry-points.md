# map-pfc-priority-to-queue — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `MAP_PFC_PRIORITY_TO_QUEUE`

### CLI
- `config qos map pfc-priority-queue add/del <map-name> <pfc> <queue>`
  - ソース: `sonic-utilities/config/main.py (qos グループ)`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `qos_config.j2` から platform 別 PFC→Queue マップが生成

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
