# subnet-decap — Direction A 書き込み入り口

テーブル: `SUBNET_DECAP`

## 調査ファイル



## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

SUBNET_DECAP テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - 専用 CLI なし

### minigraph / sonic-cfggen

minigraph.py に SUBNET_DECAP 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での SUBNET_DECAP マイグレーションなし

### ビルド時デフォルト (build-time default)

**`dockers/docker-orchagent/ipinip.json.j2`** が SUBNET_DECAP テーブルのデフォルト値をビルド時に生成 (sonic-buildimage/dockers/docker-orchagent/ipinip.json.j2)

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

