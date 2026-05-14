# snmp-agent-address-config — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`SNMP_AGENT_ADDRESS_CONFIG`

## 段階 1: Consumer 登録

- **hostcfgd**: `SNMP_AGENT_ADDRESS_CONFIG` テーブルを `ConfigDBConnector` で購読。

## 段階 2: CFG → APPL 翻訳

- hostcfgd が SNMP エージェント (`snmpd`) のリッスンアドレス設定を `/etc/snmp/snmpd.conf` に書き込み再起動。
- APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- SAI 経由なし。snmpd がデータプレーン統計を直接 SAI/kernel から読み取る。

## 段階 4: タイミング + 副作用

- snmpd 再起動まで数秒。既存 SNMP セッションは切断される。
- 副作用: リッスンアドレス変更中に SNMP モニタリングが一時停止。
