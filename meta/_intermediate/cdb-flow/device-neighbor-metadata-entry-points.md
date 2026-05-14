# device-neighbor-metadata — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `DEVICE_NEIGHBOR_METADATA`

### CLI
- なし (CLI 書き込みパスなし)

### minigraph / sonic-cfggen
- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `sonic-cfggen -m` で minigraph.xml を処理して生成。`device_metadata.py` の `parse_device_desc_xml()` が各NeighborDevice のメタを読み出す

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
