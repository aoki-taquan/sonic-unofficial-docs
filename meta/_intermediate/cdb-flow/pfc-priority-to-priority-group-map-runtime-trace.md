# pfc-priority-to-priority-group-map — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`PFC_PRIORITY_TO_PRIORITY_GROUP_MAP`

## 段階 1: Consumer 登録

- **orchagent / QosOrch** (`sonic-swss/orchagent/qosorch.cpp`): `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` を `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- QosOrch がマップエントリを解析し SAI priority group map として作成。
- APP_DB への書き込みなし (orchagent → SAI 直接)。

## 段階 3: APPL → SAI

- QosOrch が `sai_qos_map_api->create_qos_map()` を呼び出して `SAI_QOS_MAP_TYPE_PFC_PRIORITY_TO_PRIORITY_GROUP` マップを作成。
- その後 PORT テーブルのマップ参照が解決されたときにポートに適用。

## 段階 4: タイミング + 副作用

- マップ作成後、PORT_QOS_MAP での参照が更新されると即時ポートに適用される。
- 副作用: PFC しきい値設定 (BUFFER_PG) と組み合わせて動作するため、両方の設定が揃う必要がある。
