# copp-trap — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `COPP_TRAP`

### CLI
- `config copp trap add/del <trap-name> ...`
  - ソース: `sonic-utilities/config/main.py (copp グループ)`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `copp_cfg.j2` が `sonic-cfggen` 経由でデフォルトトラップセットを生成

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
