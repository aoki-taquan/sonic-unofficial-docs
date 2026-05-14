# tacplus-server — Direction A 書き込み入り口

テーブル: `TACPLUS_SERVER / TACPLUS`

## 調査ファイル

- sonic-utilities/config/aaa.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

TACPLUS_SERVER / TACPLUS テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config tacacs add/delete/set ...` — `config/aaa.py` が TACPLUS_SERVER を書き込む (sonic-utilities/config/aaa.py)

### minigraph / sonic-cfggen

minigraph.py に TACPLUS_SERVER 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

**db_migrator.py** が TACPLUS のマイグレーション処理を実装 (sonic-utilities/scripts/db_migrator.py)

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

