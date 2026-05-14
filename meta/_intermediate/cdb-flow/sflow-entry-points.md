# sflow — Direction A 書き込み入り口

テーブル: `SFLOW / SFLOW_SESSION / SFLOW_COLLECTOR`

## 調査ファイル

- sonic-utilities/config/main.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

SFLOW / SFLOW_SESSION / SFLOW_COLLECTOR テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config sflow enable/disable/polling-interval/...` — `config/main.py` が `mod_entry('SFLOW', 'global', ...)` を呼ぶ (sonic-utilities/config/main.py:9066–9260)
  - `config sflow interface enable/disable ...` — `config/main.py` が `mod_entry('SFLOW_SESSION', ifname, ...)` を呼ぶ (sonic-utilities/config/main.py:9192–9260)

### minigraph / sonic-cfggen

minigraph.py に sFlow テーブル生成なし

### REST / gNMI

**sonic-mgmt-common** `translib/transformer/xfmr_sflow.go` が REST/gNMI 経由で SFLOW テーブルを書き込む (sonic-mgmt-common/translib/transformer/xfmr_sflow.go)

### db_migrator

**db_migrator.py** が SFLOW のマイグレーション処理を実装 (sonic-utilities/scripts/db_migrator.py)

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

