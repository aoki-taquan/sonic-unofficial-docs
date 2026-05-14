# peer-switch — Direction A 書き込み入り口

テーブル: `PEER_SWITCH`

## 調査ファイル



## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

PEER_SWITCH テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - 専用 CLI なし — minigraph または手動 JSON 投入

### minigraph / sonic-cfggen

**minigraph.py** が `results['PEER_SWITCH']` にデュアルトール構成のピア情報を投入 (sonic-buildimage/src/sonic-config-engine/minigraph.py)

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での PEER_SWITCH マイグレーションなし

### ビルド時デフォルト (build-time default)

`src/sonic-config-engine/config_samples.py` にサンプルエントリあり

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

