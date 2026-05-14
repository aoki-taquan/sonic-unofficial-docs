# port-qos-map — Direction A 書き込み入り口

テーブル: `PORT_QOS_MAP`

## 調査ファイル

- sonic-utilities/config/main.py
- sonic-utilities/pfc/main.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

PORT_QOS_MAP テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config qos reload` — sonic-cfggen が `files/build_templates/qos_config.j2` を展開し PORT_QOS_MAP エントリを生成 (sonic-buildimage/files/build_templates/qos_config.j2)
  - `pfc ...` / `pfcwd ...` コマンドが間接的に PORT_QOS_MAP を参照 (sonic-utilities/pfc/main.py, pfcwd/main.py)

### minigraph / sonic-cfggen

minigraph.py に直接生成なし — `qos_config.j2` テンプレート経由

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

**db_migrator.py** が PORT_QOS_MAP に対してマイグレーション処理を実装 (sonic-utilities/scripts/db_migrator.py)

### ビルド時デフォルト (build-time default)

各プラットフォームの `qos.json.j2` に PORT_QOS_MAP エントリが定義され、ビルド時に投入

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

