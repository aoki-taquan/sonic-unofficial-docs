# DOT1P_TO_TC_MAP — Phase F 副作用調査メモ

## 調査方針

`QosOrch` が `DOT1P_TO_TC_MAP` の SET/DEL を処理する際に発生する副作用を調査する。
対象: APPL_DB / STATE_DB / COUNTERS_DB / 他 CONFIG_DB テーブルへの書込み、PUBLISH 通知、in-memory 状態変化。

## 主な知見

### SAI 直結・中継 DB なし

`QosOrch` は CONFIG_DB を直接購読して SAI に反映する（`SubscriberStateTable` 経由）。APPL_DB 中継なし。

### STATE_DB 書込みなし

`qosorch.cpp` には `stateDb` / `STATE_DB` / `setStateDBOperStatus` / `setAclTableStatus` に相当する呼び出しが存在しない。SET/DEL 時の STATE_DB エントリ変化はゼロ。

### PUBLISH 通知なし

`qosorch.cpp` に `Notification` / `NotificationProducer` / `channel` PUBLISH の使用はない。

### in-memory 副作用

- `m_qos_maps["DOT1P_TO_TC_MAP"][name]` に SAI object_id が登録/削除される（SET 時追加、DEL 時削除）。
- `PORT_QOS_MAP` の `handlePortQosMapTable()` が `resolveFieldRefValue()` でこの in-memory マップを参照するため、SET 後は pending な `PORT_QOS_MAP` エントリがアンブロックされる可能性がある。

### DEL 時の参照ロック

`PORT_QOS_MAP` から参照中の場合は `m_pendingRemove=true` がセットされ、参照解除まで DEL が保留される（他テーブルへの書込みは発生しない）。

### ポート QoS 分類への間接影響

マップの内容変更 (SET) は SAI に即時反映され、`PORT_QOS_MAP.dot1p_to_tc_map` で当該マップを参照しているすべてのポートの 802.1p → TC マッピングが即座に変化する。これは ASIC ハードウェアレベルでのトラフィック分類挙動に影響する。

## Evidence

- `sonic-swss/orchagent/qosorch.cpp:124-201` (QosMapHandler::processWorkItem)
- `sonic-swss/orchagent/qosorch.cpp:2046-2134` (handlePortQosMapTable / resolveFieldRefValue)
- `sonic-swss/orchagent/qosorch.cpp:399-415` (Dot1pToTcMapHandler::convertFieldValuesToAttributes / addQosItem)
