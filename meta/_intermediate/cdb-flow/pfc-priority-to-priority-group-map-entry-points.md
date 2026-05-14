# pfc-priority-to-priority-group-map — Direction A 書き込み入り口

テーブル: `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP`

## 調査ファイル

- sonic-utilities/config/main.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

PFC_PRIORITY_TO_PRIORITY_GROUP_MAP テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config qos reload` — sonic-cfggen が `files/build_templates/qos_config.j2` を展開し PFC_PRIORITY_TO_PRIORITY_GROUP_MAP エントリを生成 (sonic-buildimage/files/build_templates/qos_config.j2)

### minigraph / sonic-cfggen

minigraph.py に直接生成なし — `qos_config.j2` テンプレート経由

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での PFC_PRIORITY_TO_PRIORITY_GROUP_MAP マイグレーションなし

### ビルド時デフォルト (build-time default)

各プラットフォームの `qos.json.j2` (例: device/arista/.../qos.json.j2) に値が定義され、ビルド時または `qos reload` 時に投入

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

