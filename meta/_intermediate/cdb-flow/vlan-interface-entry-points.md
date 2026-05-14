# vlan-interface — Direction A 書き込み入り口

テーブル: `VLAN_INTERFACE`

## 調査ファイル

- sonic-utilities/config/main.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

VLAN_INTERFACE テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config interface ip add/remove <Vlan...> ...` — `config/main.py` が `set_entry('VLAN_INTERFACE', ...)` を呼ぶ (sonic-utilities/config/main.py)

### minigraph / sonic-cfggen

**minigraph.py** が VLAN_INTERFACE に IP アドレスを投入 (sonic-buildimage/src/sonic-config-engine/minigraph.py)

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での VLAN_INTERFACE マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

