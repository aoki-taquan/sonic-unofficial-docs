# telemetry-client — Direction A 書き込み入り口

テーブル: `TELEMETRY_CLIENT`

## 調査ファイル

- sonic-utilities/config/hft.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

TELEMETRY_CLIENT テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config hft target/session ...` — `config/hft.py` が TELEMETRY_CLIENT を書き込む (sonic-utilities/config/hft.py)

### minigraph / sonic-cfggen

**minigraph.py** が `<TelemetryInfo>` タグから TELEMETRY_CLIENT エントリを生成 (sonic-buildimage/src/sonic-config-engine/minigraph.py)

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

**db_migrator.py** が TELEMETRY_CLIENT のマイグレーション処理を実装 (sonic-utilities/scripts/db_migrator.py)

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

