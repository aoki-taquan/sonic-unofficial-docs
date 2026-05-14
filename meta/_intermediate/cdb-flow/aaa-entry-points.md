# aaa — Direction A 書き込み入り口

## 書き込み入り口 (Direction A)

対象テーブル: `AAA`

### CLI
- `config aaa authentication login <method>`
- `config aaa authentication failthrough <enable|disable>`
- `config aaa authentication fallback <enable|disable>`
- `config aaa authorization login <method>`
- `config aaa accounting login <method>`
  - ソース: `sonic-utilities/config/aaa.py`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- あり: `migrate_aaa_table_field_sync()` で `authentication`/`accounting`/`authorization` エントリを再生成 (db_migrator.py:879,886,895)

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
