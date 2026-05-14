# buffer-pool — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `BUFFER_POOL`

### CLI
- `config buffer pool add/del <name> ...`
  - ソース: `sonic-utilities/config/main.py (buffer グループ)`

### minigraph / sonic-cfggen
- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `buffers_config.j2` テンプレートからプラットフォーム別プールが生成

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- Dynamic buffer model では `buffermgrd` がプールサイズを自動調整
