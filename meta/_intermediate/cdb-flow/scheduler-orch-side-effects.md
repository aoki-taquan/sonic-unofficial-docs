# SCHEDULER-ORCH — Phase F 副次 DB 書込 中間ファイル

生成日: 2026-05-19
ソース: `sonic-swss/orchagent/qosorch.cpp` (`QosOrch::handleSchedulerTable`, `QosOrch::applySchedulerToQueueSchedulerGroup`)

---

## 概要

`QosOrch::handleSchedulerTable()` の SET/DEL は APPL_DB / STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB への直接書き込みを一切行わない。
副次書き込みは SAI API 経由の **ASIC_DB のみ** である。

| DB | 書き込み内容 | トリガ | 証跡 |
|----|------------|-------|------|
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_SCHEDULER:<oid>` 新規作成 | `sai_scheduler_api->create_scheduler()` | `qosorch.cpp:1460` |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_SCHEDULER:<oid>` 属性更新 | `sai_scheduler_api->set_scheduler_attribute()` | `qosorch.cpp:1446` |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_SCHEDULER:<oid>` 削除 | `sai_scheduler_api->remove_scheduler()` | `qosorch.cpp:1490` |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_SCHEDULER_GROUP:<group_oid>` 属性更新 | QUEUE が当該 SCHEDULER を参照するとき `applySchedulerToQueueSchedulerGroup()` 経由 | `qosorch.cpp:1690-1695` |
| APPL_DB | なし | — | — |
| STATE_DB | なし | — | — |
| COUNTERS_DB | なし | — | — |
| FLEX_COUNTER_DB | なし | — | — |

---

## 詳細

### SET（新規作成）→ ASIC_DB scheduler object 作成

```cpp
// qosorch.cpp:1460
sai_status = sai_scheduler_api->create_scheduler(&sai_object, gSwitchId,
    (uint32_t)sai_attr_list.size(), sai_attr_list.data());
// 成功後
(*(m_qos_maps[qos_map_type_name]))[qos_object_name].m_saiObjectId = sai_object;
```

syncd が `ASIC_STATE:SAI_OBJECT_TYPE_SCHEDULER:<new_oid>` を ASIC_DB に新規書き込み。

### SET（既存更新）→ ASIC_DB scheduler object 属性更新

```cpp
// qosorch.cpp:1446
sai_status = sai_scheduler_api->set_scheduler_attribute(sai_object, &attr);
```

変更されたフィールドの属性のみを個別に `set_scheduler_attribute()` で送信。ASIC_DB の既存エントリが更新される。

### DEL → ASIC_DB scheduler object 削除

```cpp
// qosorch.cpp:1490
sai_status = sai_scheduler_api->remove_scheduler(sai_object);
```

QUEUE から参照されている間は `isObjectBeingReferenced()` が `true` を返すため SAI 削除は延期（`m_pendingRemove = true`）。参照解除後に `remove_scheduler()` が呼ばれ、ASIC_DB の該当エントリが削除される。

### QUEUE バインド → ASIC_DB scheduler_group 属性更新（副次書込）

SCHEDULER 作成後、QUEUE テーブルの `scheduler` フィールドが当該 SCHEDULER 名を参照すると `handleQueueTable()` から `applySchedulerToQueueSchedulerGroup()` が呼ばれる:

```cpp
// qosorch.cpp:1688-1695
attr.id = SAI_SCHEDULER_GROUP_ATTR_SCHEDULER_PROFILE_ID;
attr.value.oid = scheduler_profile_id;
sai_status = sai_scheduler_group_api->set_scheduler_group_attribute(group_id, &attr);
```

syncd が `ASIC_STATE:SAI_OBJECT_TYPE_SCHEDULER_GROUP:<group_oid>` の `SAI_SCHEDULER_GROUP_ATTR_SCHEDULER_PROFILE_ID` を更新。QUEUE DEL 時は `scheduler_profile_id = SAI_NULL_OBJECT_ID` を渡してバインドを解除。
