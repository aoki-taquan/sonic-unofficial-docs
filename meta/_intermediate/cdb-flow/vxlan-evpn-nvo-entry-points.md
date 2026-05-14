# vxlan-evpn-nvo — Direction A 書き込み入り口

テーブル: `VXLAN_EVPN_NVO`

## 調査ファイル

- sonic-utilities/config/vxlan.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

VXLAN_EVPN_NVO テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config vxlan evpn_nvo add/del ...` — `config/vxlan.py` が `set_entry('VXLAN_EVPN_NVO', nvo_name, fvs)` を呼ぶ (sonic-utilities/config/vxlan.py:129, 154)

### minigraph / sonic-cfggen

minigraph.py に VXLAN_EVPN_NVO 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での VXLAN_EVPN_NVO マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

