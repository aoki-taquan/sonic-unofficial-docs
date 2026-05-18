# scheduler-orch — Phase C cross-refs 調査ノート

## 調査対象

- `sonic-swss/orchagent/qosorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/qosorch.h` (同上)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-queue.yang`

## 主要発見

### SCHEDULER は「被参照専用」テーブル

SCHEDULER エントリ自体は他の CONFIG_DB テーブルへの leafref を持たない。
依存の方向は常に「外部テーブル → SCHEDULER」。

### QUEUE → SCHEDULER 参照 (SET 方向)

`handleQueueTable()` (qosorch.cpp:1822-1852) が `resolveFieldRefValue()` を呼び
SCHEDULER SAI オブジェクトを解決する。未解決 (`not_resolved`) は `task_need_retry`。
YANG `sonic-queue.yang:84-87` でも leafref として宣言。

### SCHEDULER DEL ガード (DEL 方向)

`handleSchedulerTable()` DEL パス (qosorch.cpp:1483-1491) で `isObjectBeingReferenced()`
を確認。QUEUE から参照中は `m_pendingRemove = true` + `task_need_retry`。

### PortsOrch 起動ガード

`doTask(Consumer&)` 冒頭 (qosorch.cpp:2258-2261) で `gPortsOrch->allPortsReady()` が
偽の間は全 QoS タスク処理を skip。PortsOrch 完了まで SAI 送信なし。

### doTask() での処理順序

`QosOrch::doTask()` (qosorch.cpp:2231-2252):
1. CFG_PORT_QOS_MAP 以外の全 Consumer を先に drain
2. CFG_PORT_QOS_MAP を drain
3. CFG_QUEUE_TABLE を drain
→ SCHEDULER は最初のフェーズで処理されるため、QUEUE より先に SAI 登録される。

### SCHEDULER_GROUP (SAI 管理、DB テーブルなし)

QUEUE に SCHEDULER を紐付ける際、`getSchedulerGroup()` (qosorch.cpp:1512-1626) で
キュー → スケジューラグループ ID を検索し SAI_SCHEDULER_GROUP_ATTR_SCHEDULER_PROFILE_ID
をセット。SAI 内部のスケジューラグループツリーに依存（CONFIG_DB テーブルなし）。
