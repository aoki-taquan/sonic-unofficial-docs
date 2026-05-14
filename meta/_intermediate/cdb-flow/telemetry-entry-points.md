# telemetry — Direction A 書き込み入り口

テーブル: `TELEMETRY`

## 調査ファイル



## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

TELEMETRY テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - 専用 CLI なし — minigraph または手動 `config load` 経由

### minigraph / sonic-cfggen

**minigraph.py** が TELEMETRY エントリを生成 (sonic-buildimage/src/sonic-config-engine/minigraph.py)

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での TELEMETRY マイグレーションなし

### ビルド時デフォルト (build-time default)

**`dockers/docker-sonic-telemetry/telemetry_vars.j2`** が TELEMETRY テーブルを参照して設定を生成 (読み取り側)

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

