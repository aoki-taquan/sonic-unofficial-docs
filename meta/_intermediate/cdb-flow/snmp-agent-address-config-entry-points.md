# snmp-agent-address-config — Direction A 書き込み入り口

テーブル: `SNMP_AGENT_ADDRESS_CONFIG`

## 調査ファイル

- sonic-utilities/config/main.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

SNMP_AGENT_ADDRESS_CONFIG テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config snmp agentaddress add/del ...` — `config/main.py` が `set_entry('SNMP_AGENT_ADDRESS_CONFIG', key, {})` を呼ぶ (sonic-utilities/config/main.py:4142–4186)

### minigraph / sonic-cfggen

minigraph.py に SNMP_AGENT_ADDRESS_CONFIG 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での SNMP_AGENT_ADDRESS_CONFIG マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

