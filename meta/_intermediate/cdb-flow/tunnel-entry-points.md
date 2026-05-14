# tunnel — Direction A 書き込み入り口

テーブル: `TUNNEL`

## 調査ファイル



## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

TUNNEL テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - 専用 CLI なし — NVGRE トンネルは `config nvgre_tunnel`、VxLAN は `config vxlan` コマンド経由で別テーブルに投入

### minigraph / sonic-cfggen

minigraph.py に TUNNEL 直接生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

**db_migrator.py** が TUNNEL テーブルのマイグレーション処理を実装 (sonic-utilities/scripts/db_migrator.py)

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

TUNNEL テーブルはレガシー汎用トンネルテーブル; 現行は VXLAN_TUNNEL / NVGRE_TUNNEL が使用される
<!-- /entry-points -->

