# nvgre-tunnel — Direction A 書き込み入り口

テーブル: `NVGRE_TUNNEL / NVGRE_TUNNEL_MAP`

## 調査ファイル

- sonic-utilities/config/plugins/nvgre_tunnel.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

NVGRE_TUNNEL / NVGRE_TUNNEL_MAP テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config nvgre_tunnel add/del ...` — `config/plugins/nvgre_tunnel.py` が `set_entry()` を呼ぶ (sonic-utilities/config/plugins/nvgre_tunnel.py)

### minigraph / sonic-cfggen

minigraph.py に NVGRE_TUNNEL 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での NVGRE マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

