# buffer-pg — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `BUFFER_PG`

### CLI
- `config interface buffer priority-group set <port> <pg-range> <profile>`
- `config interface buffer priority-group remove <port> <pg-range>`
  - ソース: `sonic-utilities/config/main.py (buffer グループ)`

### minigraph / sonic-cfggen
- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `sonic-cfggen` が `buffers_config.j2` テンプレートから初期バッファ PG マッピングを生成

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- Dynamic buffer model: `buffermgrd` が LOSSLESS_TRAFFIC_PATTERN を参照してポートごとに自動再計算・書き込み
