# device-runtime-metadata — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `DEVICE_RUNTIME_METADATA`

### CLI
- なし (CLI 書き込みパスなし)

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- 起動時に `sonic-cfggen` や `platform_env.conf` スクリプトが実行環境情報 (platform name, HW SKU 等) を注入する。YANG モデルなし・スキーマレス
