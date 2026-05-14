# buffer-queue — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `BUFFER_QUEUE`

### CLI
- `config interface buffer queue set <port> <q-range> <profile>`
- `config interface buffer queue remove <port> <q-range>`
  - ソース: `sonic-utilities/config/main.py (buffer グループ)`

### minigraph / sonic-cfggen
- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `qos_config.j2` から QoS マッピングと共に生成

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
