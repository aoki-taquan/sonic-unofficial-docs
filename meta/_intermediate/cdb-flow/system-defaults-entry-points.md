# system-defaults — Direction A 書き込み入り口

テーブル: `SYSTEM_DEFAULTS`

## 調査ファイル



## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

SYSTEM_DEFAULTS テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - 専用 CLI なし

### minigraph / sonic-cfggen

minigraph.py に SYSTEM_DEFAULTS 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での SYSTEM_DEFAULTS マイグレーションなし

### ビルド時デフォルト (build-time default)

**`files/build_templates/init_cfg.json.j2`** に SYSTEM_DEFAULTS エントリ (IPv6 forwarding 等) がビルド時に投入 (sonic-buildimage/files/build_templates/init_cfg.json.j2); **`files/build_templates/qos_config.j2`** と **`files/build_templates/buffers_config.j2`** も参照

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

