# DSCP_TO_TC_MAP — 例外条件分析

## consumer 一覧

| consumer | 用途 | ソースパス |
|---|---|---|
| orchagent / qosorch.cpp | DSCP→TC マップの SAI オブジェクト生成・適用 | sonic-swss/orchagent/qosorch.cpp:298-303,61,81,100,1329 |
| orchagent / tunneldecaporch.cpp | トンネル decap 時の DSCP→TC マップ適用 | sonic-swss/orchagent/tunneldecaporch.cpp:831-834,1084 |

## 例外条件

### orchagent (qosorch): 削除時に参照中の場合 — pending remove
- qosorch.cpp:181-186 — DSCP_TO_TC_MAP エントリ削除時に PORT や TUNNEL から参照中の場合、`m_pendingRemove=true` を立てて `task_need_retry` を返す。DOT1P_TO_TC_MAP と同一の QosMapHandler を使用。

### orchagent: スイッチレベル DSCP map 適用時の capability 確認
- qosorch.cpp:1956 — スイッチに DSCP→TC マップを適用する前に `querySwitchCapability(SAI_OBJECT_TYPE_SWITCH, SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP)` で capability を確認。未対応の場合は適用をスキップ。

### orchagent: スイッチレベル適用で null (解除) 時
- qosorch.cpp:1993 — `applyDscpToTcMapToSwitch(SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP, SAI_NULL_OBJECT_ID)` でスイッチ全体から DSCP マップを解除可能。

### orchagent: SAI 生成・変更・削除失敗
- qosorch.cpp:162-166, 151-155, 188-191 — DOT1P_TO_TC_MAP と同様に SAI 操作失敗時は `task_failed` を返す。
