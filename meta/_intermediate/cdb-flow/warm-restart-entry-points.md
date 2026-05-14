# warm-restart — Direction A 書き込み入り口

テーブル: `WARM_RESTART`

## 調査ファイル

- sonic-utilities/config/main.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

WARM_RESTART テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config warm_restart enable/disable/neighsyncd_timer/bgp_timer/teamsyncd_timer ...` — `config/main.py` が `mod_entry('WARM_RESTART', 'swss'/'bgp'/'teamd', ...)` を呼ぶ (sonic-utilities/config/main.py:4032–4094)

### minigraph / sonic-cfggen

minigraph.py に WARM_RESTART 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

**db_migrator.py** が WARM_RESTART のマイグレーション処理を実装 (sonic-utilities/scripts/db_migrator.py)

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

