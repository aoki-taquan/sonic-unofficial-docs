# vxlan-tunnel-map — Direction A 書き込み入り口

テーブル: `VXLAN_TUNNEL_MAP`

## 調査ファイル

- sonic-utilities/config/vxlan.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

VXLAN_TUNNEL_MAP テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config vxlan map add/del ...` / `config vxlan map_range add/del ...` — `config/vxlan.py` が `set_entry('VXLAN_TUNNEL_MAP', mapname, fvs)` を呼ぶ (sonic-utilities/config/vxlan.py:206, 248, 315, 359)

### minigraph / sonic-cfggen

minigraph.py に VXLAN_TUNNEL_MAP 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

**db_migrator.py** が VXLAN_TUNNEL_MAP のマイグレーション処理を実装 (sonic-utilities/scripts/db_migrator.py)

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

