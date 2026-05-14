# restapi — Direction A 書き込み入り口

テーブル: `RESTAPI`

## 調査ファイル



## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

RESTAPI テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - 専用 CLI なし

### minigraph / sonic-cfggen

**minigraph.py** が `results['RESTAPI']` に REST API 設定を投入 (sonic-buildimage/src/sonic-config-engine/minigraph.py:2689)

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

**db_migrator.py** が RESTAPI のマイグレーション処理 (`config` / `certs` サブキー) を実装 (sonic-utilities/scripts/db_migrator.py:609–619)

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

