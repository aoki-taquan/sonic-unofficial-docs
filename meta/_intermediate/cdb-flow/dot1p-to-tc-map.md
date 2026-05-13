# DOT1P_TO_TC_MAP — 例外条件分析

## consumer 一覧

| consumer | 用途 | ソースパス |
|---|---|---|
| orchagent / qosorch.cpp | DOT1P→TC マップの SAI オブジェクト生成・適用 | sonic-swss/orchagent/qosorch.cpp:422-426,81,83,100,102 |

## 例外条件

### orchagent: 削除時に参照中の場合 — pending remove
- qosorch.cpp:181-186 — DOT1P_TO_TC_MAP エントリを削除しようとした時に他テーブル（PORT 等）から参照中の場合、`m_pendingRemove=true` フラグを立てて `task_need_retry` を返す。参照が解放された後に削除を実行。

### orchagent: SET 時に pending remove 状態の場合
- qosorch.cpp:136-139 — 同エントリが pending remove 中に SET が来た場合、`"Entry is pending remove, need retry"` を LOG_NOTICE し `task_need_retry` を返す。

### orchagent: SAI オブジェクト生成失敗
- qosorch.cpp:162-166 — `addQosItem()` が `SAI_NULL_OBJECT_ID` を返した場合、`"Failed to create [DOT1P_TO_TC_MAP:...]"` を LOG_ERROR して `task_failed` を返す。

### orchagent: SAI オブジェクト変更失敗
- qosorch.cpp:151-155 — `modifyQosItem()` が失敗した場合、`"Failed to set [DOT1P_TO_TC_MAP:...]"` を LOG_ERROR して `task_failed` を返す。

### orchagent: DEL 対象が存在しない場合
- qosorch.cpp:176-179 — 削除対象のオブジェクトが type map に存在しない場合、`"Object with name:%s not found."` を LOG_ERROR して `task_invalid_entry` を返す。
