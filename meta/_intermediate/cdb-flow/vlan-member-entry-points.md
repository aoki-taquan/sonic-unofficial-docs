# vlan-member — Direction A 書き込み入り口

テーブル: `VLAN_MEMBER`

## 調査ファイル

- sonic-utilities/config/vlan.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

VLAN_MEMBER テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config vlan member add/del ...` — `config/vlan.py` が `set_entry('VLAN_MEMBER', (vlan, port), {'tagging_mode': ...})` を呼ぶ (sonic-utilities/config/vlan.py:407, 451)

### minigraph / sonic-cfggen

**minigraph.py** が VLAN_MEMBER を生成し投入 (sonic-buildimage/src/sonic-config-engine/minigraph.py)

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での VLAN_MEMBER マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

