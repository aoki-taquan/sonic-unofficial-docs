# vxlan-tunnel — Direction A 書き込み入り口

テーブル: `VXLAN_TUNNEL`

## 調査ファイル

- sonic-utilities/config/vxlan.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

VXLAN_TUNNEL テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config vxlan add/del ...` — `config/vxlan.py` が `set_entry('VXLAN_TUNNEL', vxlan_name, fvs)` を呼ぶ (sonic-utilities/config/vxlan.py:49, 94)

### minigraph / sonic-cfggen

minigraph.py に VXLAN_TUNNEL 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での VXLAN_TUNNEL マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

