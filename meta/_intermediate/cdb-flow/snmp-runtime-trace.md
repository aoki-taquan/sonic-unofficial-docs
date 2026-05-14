# snmp — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`SNMP / SNMP_COMMUNITY`

## 段階 1: Consumer 登録

- **hostcfgd**: `SNMP` / `SNMP_COMMUNITY` テーブルを `ConfigDBConnector` で購読。

## 段階 2: CFG → APPL 翻訳

- hostcfgd が snmpd の community string / v3 ユーザ設定を `/etc/snmp/snmpd.conf` に書き込み再起動。

## 段階 3: APPL → SAI

- SAI 経由なし。snmpd が MIB ツリーを通じてスイッチ統計を提供。

## 段階 4: タイミング + 副作用

- 設定変更後 snmpd 再起動まで数秒。community 変更は即時有効 (再起動後)。
- 副作用: 旧 community string での SNMP ポーリングが失敗するため、NMS 側の設定変更も必要。
