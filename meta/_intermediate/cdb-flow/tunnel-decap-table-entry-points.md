# tunnel-decap-table — Direction A 書き込み入り口

テーブル: `TUNNEL_DECAP_TABLE`

## 調査ファイル



## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

TUNNEL_DECAP_TABLE テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - 専用 CLI なし — `config load` または minigraph 経由

### minigraph / sonic-cfggen

minigraph.py に TUNNEL_DECAP_TABLE 直接生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

**db_migrator.py** が TUNNEL_DECAP_TABLE のマイグレーション処理を実装 (sonic-utilities/scripts/db_migrator.py)

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

