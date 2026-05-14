# vrf — Direction A 書き込み入り口

テーブル: `VRF`

## 調査ファイル

- sonic-utilities/config/main.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

VRF テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config vrf add/del <name>` — `config/main.py` が `set_entry('VRF', vrf_name, {'NULL': 'NULL'})` を呼ぶ (sonic-utilities/config/main.py:7698, 7731)
  - `config vrf add_vrf_vni_map/del_vrf_vni_map <name>` — `config/main.py` が `mod_entry('VRF', vrfname, {'vni': vni})` を呼ぶ (sonic-utilities/config/main.py:7774, 7784)

### minigraph / sonic-cfggen

**minigraph.py** が VRF エントリを生成し投入 (sonic-buildimage/src/sonic-config-engine/minigraph.py)

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での VRF マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

