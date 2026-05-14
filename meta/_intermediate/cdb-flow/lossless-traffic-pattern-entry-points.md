# lossless-traffic-pattern — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `LOSSLESS_TRAFFIC_PATTERN`

### CLI
- `config buffer lossless-traffic-pattern <mtu> <small_packet_percentage>`
  - ソース: `sonic-utilities/config/main.py (buffer グループ)`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `buffers_config.j2` からデフォルト MTU / small_packet_percentage が生成される場合あり

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- `buffermgrd` がこのテーブルを読み取り Lossless バッファプロファイルを動的に算出
