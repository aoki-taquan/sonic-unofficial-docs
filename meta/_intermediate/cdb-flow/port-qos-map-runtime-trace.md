# port-qos-map — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`PORT_QOS_MAP`

## 段階 1: Consumer 登録

- **orchagent / QosOrch** (`sonic-swss/orchagent/qosorch.cpp`): `PORT_QOS_MAP` テーブルを `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- QosOrch が各フィールド (`dscp_to_tc_map`, `tc_to_queue_map`, `pfc_to_pg_map` 等) を解析し、参照される QoS マップ OID を解決。
- APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- QosOrch が `sai_port_api->set_port_attribute()` を呼び出して各 QoS マップをポートに適用。
- 例: `SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP`, `SAI_PORT_ATTR_QOS_TC_TO_QUEUE_MAP` 等。

## 段階 4: タイミング + 副作用

- 参照する QoS マップが未作成の場合は `task_need_retry`。マップ作成後に自動再処理。
- 副作用: 既存トラフィックへの影響が即座に発生するため、メンテナンス時間帯での変更を推奨。
