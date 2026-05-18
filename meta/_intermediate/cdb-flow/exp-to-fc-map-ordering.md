# EXP_TO_FC_MAP — Phase B 書込み順依存調査

## 調査対象
- `orchagent/qosorch.cpp` (sonic-swss@4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/cbf/nhgmaporch.cpp`

## 発見された順序依存

### 1. EXP_TO_FC_MAP → PORT_QOS_MAP 強制先行

`handlePortQosMapTable` は `resolveFieldRefValue` で `CFG_EXP_TO_FC_MAP_TABLE_NAME`
の SAI oid を解決する。マップが未登録（`m_qos_maps` にない）場合は
`task_need_retry` を返してイベントを再キューする。

Evidence: `qosorch.cpp:2120-2131`

### 2. DEL 時のリファレンス保護（pendingRemove）

DEL パスで `isObjectBeingReferenced` が真の場合、
`m_pendingRemove = true` を立てて `task_need_retry` を返す。
PORT_QOS_MAP で参照が外れると、次回ループで再試行・削除成功。

Evidence: `qosorch.cpp:181-186`

### 3. pendingRemove 中の SET は defer

同名エントリを DEL 中（pendingRemove=true）に SET すると
`task_need_retry` が返り、削除完了まで defer される。

Evidence: `qosorch.cpp:136-139`
