# SCHEDULER — Phase F 副次 DB 書込 中間ファイル

生成日: 2026-05-16
ソース: `sonic-swss/orchagent/qosorch.cpp` (`QosOrch::handleSchedulerTable`, `QosOrch::applySchedulerToQueueSchedulerGroup`, `QosOrch::handleQueueTable`)

---

## 概要

`SCHEDULER` テーブルへの SET/DEL 処理時、`QosOrch` は APPL_DB / STATE_DB / COUNTERS_DB への直接書き込みを行わない。
ただし **ASIC_DB への SAI scheduler オブジェクト書き込み** と、そのオブジェクト ID を参照する **QUEUE への副次バインド** の 2 段階が発生する。

| DB | 書き込み内容 | トリガ | evidence |
|----|------------|-------|---------|
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_SCHEDULER:<oid>` | `sai_scheduler_api->create_scheduler()` / `set_scheduler_attribute()` / `remove_scheduler()` | `qosorch.cpp:1460,1446,1490` |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_SCHEDULER_GROUP:<group_oid>` (`SAI_SCHEDULER_GROUP_ATTR_SCHEDULER_PROFILE_ID`) | QUEUE が当該 SCHEDULER を参照するとき `applySchedulerToQueueSchedulerGroup()` が呼出 | `qosorch.cpp:1690-1695` |
| APPL_DB | なし | — | — |
| STATE_DB | なし | — | — |
| COUNTERS_DB | なし | — | — |
| FLEX_COUNTER_DB | なし | — | — |

---

## 1. ASIC_DB / `ASIC_STATE:SAI_OBJECT_TYPE_SCHEDULER`

### SET ハンドラ（既存オブジェクトあり）

`handleSchedulerTable()` SET パスのうち、すでに SAI オブジェクトが存在する場合:

```cpp
// qosorch.cpp:1446
sai_status = sai_scheduler_api->set_scheduler_attribute(sai_object, &attr);
```

syncd がこれを受けて `ASIC_DB` の `ASIC_STATE:SAI_OBJECT_TYPE_SCHEDULER:<oid>` を更新する。

### SET ハンドラ（新規作成）

```cpp
// qosorch.cpp:1460
sai_status = sai_scheduler_api->create_scheduler(&sai_object, gSwitchId, ...);
// 成功後:
(*(m_qos_maps[qos_map_type_name]))[qos_object_name].m_saiObjectId = sai_object;
```

syncd が `ASIC_DB` に `ASIC_STATE:SAI_OBJECT_TYPE_SCHEDULER:<new_oid>` エントリを作成。

### DEL ハンドラ

```cpp
// qosorch.cpp:1490
sai_status = sai_scheduler_api->remove_scheduler(sai_object);
```

syncd が当該 OID の `ASIC_STATE:SAI_OBJECT_TYPE_SCHEDULER:<oid>` を削除。QUEUE から参照されている間は `isObjectBeingReferenced` が `true` となり `m_pendingRemove = true` / `task_need_retry` が返され、SAI 削除は延期される。

---

## 2. ASIC_DB / `ASIC_STATE:SAI_OBJECT_TYPE_SCHEDULER_GROUP`（QUEUE 経由副次書込）

SCHEDULER が作成された後、`QUEUE` テーブルの `scheduler` フィールドが当該 SCHEDULER 名を参照すると `handleQueueTable()` から `applySchedulerToQueueSchedulerGroup()` が呼ばれる。

```cpp
// qosorch.cpp:1688-1695
attr.id = SAI_SCHEDULER_GROUP_ATTR_SCHEDULER_PROFILE_ID;
attr.value.oid = scheduler_profile_id;
sai_status = sai_scheduler_group_api->set_scheduler_group_attribute(group_id, &attr);
```

これにより syncd が `ASIC_STATE:SAI_OBJECT_TYPE_SCHEDULER_GROUP:<group_oid>` の `SAI_SCHEDULER_GROUP_ATTR_SCHEDULER_PROFILE_ID` 属性を更新する。

- **`group_id` の決定**: `getSchedulerGroup()` が `SAI_PORT_ATTR_QOS_SCHEDULER_GROUP_LIST` を取得し、対象キュー (`queue_id`) の親グループ (`SAI_SCHEDULER_GROUP_ATTR_CHILD_LIST`) を探索して特定する。
- **voq モード**: `gMySwitchType == "voq"` かつシステムポートタイプが `SAI_SYSTEM_PORT_TYPE_REMOTE` の場合はスキップ（return true で早期終了）。
- **QUEUE DEL 時**: `sai_scheduler_profile = SAI_NULL_OBJECT_ID` を渡すことでスケジューラバインドを解除。

---

## 3. APPL_DB / STATE_DB / COUNTERS_DB — 書き込みなし

`handleSchedulerTable()` の SET/DEL パスで swsscommon の `ProducerStateTable`・`Table::set()`・`hset()` 呼出は一切存在しない。副作用は SAI API 経由の ASIC_DB 書き込みのみ。

---

## 結論サマリ

| 検証項目 | 結果 |
|---------|------|
| `handleSchedulerTable` 内の APPL_DB 書込 | なし |
| `handleSchedulerTable` 内の STATE_DB 書込 | なし |
| `handleSchedulerTable` 内の COUNTERS_DB 書込 | なし |
| `handleSchedulerTable` → SAI → ASIC_DB scheduler object | あり（create/set/remove） |
| QUEUE 参照時の ASIC_DB scheduler_group 属性更新 | あり（`applySchedulerToQueueSchedulerGroup`） |

`<!-- side-effects -->` ブロックとして docs/reference/config-db/scheduler.md に追記済み。
