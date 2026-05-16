# QUEUE SET/DEL 副次 DB 書込 分析 (Phase F)

ソース調査ファイル:
- `sonic-swss/orchagent/qosorch.cpp` — QosOrch::doQueueTask() / handleQueueTable() / applySchedulerToQueueSchedulerGroup() / applyWredProfileToQueue()
- `sonic-swss/orchagent/portsorch.cpp` — addQueueFlexCountersPerPortPerQueueIndex() / generateQueueMapPerPort() / initCounterCapabilities()
- `sonic-swss/orchagent/portsorch.h` — FlexCounter グループ名定数
- `sonic-swss/orchagent/flexcounterorch.cpp` — getQueueConfigurations() / FlexCounterQueueStates
- `sonic-swss-common/common/schema.h` — COUNTERS_QUEUE_NAME_MAP / COUNTERS_QUEUE_PORT_MAP / COUNTERS_QUEUE_INDEX_MAP / COUNTERS_QUEUE_TYPE_MAP / STATE_QUEUE_COUNTER_CAPABILITIES_NAME

---

## QUEUE SET 操作 (qosorch.cpp)

### 1. SAI 呼び出し → ASIC_DB

QUEUE エントリの SET 時、QosOrch は `handleQueueTable()` を経由して以下の SAI 呼び出しを行う:

| 条件 | SAI API / 属性 | ASIC_DB 反映 |
|------|--------------|-------------|
| `scheduler` フィールドあり | `sai_scheduler_api->set_scheduler_group_attribute(SAI_SCHEDULER_GROUP_ATTR_SCHEDULER_PROFILE_ID)` | `ASIC_STATE:SAI_OBJECT_TYPE_SCHEDULER_GROUP` 属性更新 |
| `wred_profile` フィールドあり | `sai_queue_api->set_queue_attribute(SAI_QUEUE_ATTR_WRED_PROFILE_ID)` | `ASIC_STATE:SAI_OBJECT_TYPE_QUEUE` 属性更新 |
| `scheduler` フィールド削除 | `sai_scheduler_api->set_scheduler_group_attribute(SAI_SCHEDULER_GROUP_ATTR_SCHEDULER_PROFILE_ID, OID_NULL)` | スケジューラ解除 |
| `wred_profile` フィールド削除 | `sai_queue_api->set_queue_attribute(SAI_QUEUE_ATTR_WRED_PROFILE_ID, OID_NULL)` | WRED 解除 |

QosOrch は APPL_DB / STATE_DB への書き込みを一切行わない。副次 DB 書込は全て ASIC_DB (syncd 経由 SAI) のみ。

---

## PortsOrch ポート作成時の QUEUE 関連 DB 書込

QUEUE テーブルの SET ではなく、**ポート作成時** (APPL_DB `PORT_TABLE` の処理) に PortsOrch が QUEUE OID を SAI から取得し、以下を書き込む。これは QUEUE テーブル設定の前提条件を形成する。

### 2. COUNTERS_DB — Queue マップ群

`generateQueueMapPerPort()` (portsorch.cpp:8446-8530) が呼ばれるタイミング:

| テーブル | Redis キー形式 | 書込内容 | コードロケーション |
|---------|--------------|---------|-----------------|
| `COUNTERS_QUEUE_NAME_MAP` | `""` field=`<alias>:<qindex>` | value = queue SAI OID (sai_serialize) | portsorch.cpp:8527 (`m_queueCounterNameMapUpdater->setCounterNameMap`) |
| `COUNTERS_QUEUE_PORT_MAP` | `""` field=`<queue_oid>` | value = port SAI OID | portsorch.cpp:8527 (`m_queuePortTable->set`) |
| `COUNTERS_QUEUE_INDEX_MAP` | `""` field=`<queue_oid>` | value = queue real index (uint8_t→string) | portsorch.cpp:8528 (`m_queueIndexTable->set`) |
| `COUNTERS_QUEUE_TYPE_MAP` | `""` field=`<queue_oid>` | value = `SAI_QUEUE_TYPE_UNICAST` / `SAI_QUEUE_TYPE_MULTICAST` / `SAI_QUEUE_TYPE_ALL` など | portsorch.cpp:8529 (`m_queueTypeTable->set`) |

VoQ モードでは `m_voqTable->set("", queueVector)` が別途 `COUNTERS_QUEUE_NAME_MAP` (VoQ 用) にも書き込む。

### 3. FLEX_COUNTER_DB — Queue Counter エントリ登録

`addQueueFlexCountersPerPortPerQueueIndex()` (portsorch.cpp:8592-8614):

| FlexCounter グループ | FLEX_COUNTER_DB キー | ポーリング間隔 | 有効化条件 | StatsMode |
|--------------------|-------------------|-------------|---------|-----------|
| `QUEUE_STAT_COUNTER` | `QUEUE_STAT_COUNTER:<queue_oid>` | 10,000 ms (コードデフォルト) | `m_queue_enabled = true` (FlexCounterOrch) | READ |
| `QUEUE_WATERMARK_STAT_COUNTER` | `QUEUE_WATERMARK_STAT_COUNTER:<queue_oid>` | 60,000 ms (コードデフォルト) | `m_queue_watermark_enabled = true` | READ_AND_CLEAR |
| `WRED_ECN_QUEUE_STAT_COUNTER` | `WRED_ECN_QUEUE_STAT_COUNTER:<queue_oid>` | 10,000 ms | `m_wred_queue_counter_enabled = true` | READ |

各グループに登録されるカウンタフィールドセット:

**QUEUE_STAT_COUNTER** (queue_stat_ids, portsorch.cpp:389-398):
- `SAI_QUEUE_STAT_PACKETS`, `SAI_QUEUE_STAT_BYTES`
- `SAI_QUEUE_STAT_DROPPED_PACKETS`, `SAI_QUEUE_STAT_DROPPED_BYTES`
- `SAI_QUEUE_STAT_TRIM_PACKETS`, `SAI_QUEUE_STAT_DROPPED_TRIM_PACKETS`, `SAI_QUEUE_STAT_TX_TRIM_PACKETS`
- VoQ 追加: `SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS` (voq_stat_ids, portsorch.cpp:399-402)

**QUEUE_WATERMARK_STAT_COUNTER** (queueWatermarkStatIds, portsorch.cpp:405-408):
- `SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES`

**WRED_ECN_QUEUE_STAT_COUNTER** (wred_queue_stat_ids, portsorch.cpp:429-435):
- `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS`, `SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES`
- `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS`, `SAI_QUEUE_STAT_WRED_DROPPED_BYTES`

---

## orchagent 起動時の STATE_DB 書込

`initCounterCapabilities()` (portsorch.cpp:1850-1918) が起動時に 1 回だけ実行される:

### 4. STATE_DB — QUEUE_COUNTER_CAPABILITIES

| Redis キー | フィールド | デフォルト | SAI 成功時 |
|-----------|---------|---------|-----------|
| `QUEUE_COUNTER_CAPABILITIES\|WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER` | `isSupported` | `"false"` | `"true"` (SAI が `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` を返した場合) |
| `QUEUE_COUNTER_CAPABILITIES\|WRED_ECN_QUEUE_ECN_MARKED_BYTE_COUNTER` | `isSupported` | `"false"` | `"true"` (SAI が `SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES` を返した場合) |
| `QUEUE_COUNTER_CAPABILITIES\|WRED_ECN_QUEUE_WRED_DROPPED_PKT_COUNTER` | `isSupported` | `"false"` | `"true"` (SAI が `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS` を返した場合) |
| `QUEUE_COUNTER_CAPABILITIES\|WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER` | `isSupported` | `"false"` | `"true"` (SAI が `SAI_QUEUE_STAT_WRED_DROPPED_BYTES` を返した場合) |

スキーマ定数: `STATE_QUEUE_COUNTER_CAPABILITIES_NAME "QUEUE_COUNTER_CAPABILITIES"` (schema.h:528)。

---

## QUEUE DEL 操作

### 5. SAI 呼び出し → ASIC_DB (del_handler)

| 条件 | SAI API / 属性 | ASIC_DB 反映 |
|------|--------------|-------------|
| `wred_profile` フィールドがあった場合 | `sai_queue_api->set_queue_attribute(SAI_QUEUE_ATTR_WRED_PROFILE_ID, OID_NULL)` | WRED プロファイル解除 |
| `scheduler` フィールドがあった場合 | `sai_scheduler_api->set_scheduler_group_attribute(SAI_SCHEDULER_GROUP_ATTR_SCHEDULER_PROFILE_ID, OID_NULL)` | スケジューラ解除 |

### 6. COUNTERS_DB / FLEX_COUNTER_DB クリーンアップ

ポート削除時 (PORT DEL) に `deletePortBufferQueueCounters()` が呼ばれ:

| テーブル | 操作 | コードロケーション |
|---------|------|-----------------|
| `COUNTERS_QUEUE_NAME_MAP` | `hdel("", alias:qindex)` | portsorch.cpp:8790 (`m_queuePortTable->hdel`) |
| `COUNTERS_QUEUE_PORT_MAP` | `hdel("", queue_oid)` | portsorch.cpp:8790 |
| `COUNTERS_QUEUE_INDEX_MAP` | `hdel("", queue_oid)` | portsorch.cpp:8797 |
| `COUNTERS_QUEUE_TYPE_MAP` | `hdel("", queue_oid)` | portsorch.cpp:8796 |
| FLEX_COUNTER_DB (`QUEUE_STAT_COUNTER:<oid>`) | `clearCounterIdList(queue_oid)` | portsorch.cpp:8804 (`queue_stat_manager.clearCounterIdList`) |
| FLEX_COUNTER_DB (`WRED_ECN_QUEUE_STAT_COUNTER:<oid>`) | `clearCounterIdList(queue_oid)` | portsorch.cpp:8815 (`wred_queue_stat_manager.clearCounterIdList`) |

---

## 副次書込サマリ

| DB | テーブル | 操作 | 契機 | evidence |
|----|---------|------|------|---------|
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_QUEUE` | SET scheduler_profile / wred_profile 属性 | QUEUE SET | qosorch.cpp |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_SCHEDULER_GROUP` | SET scheduler_profile 属性 / NULL クリア | QUEUE SET/DEL | qosorch.cpp |
| COUNTERS_DB | `COUNTERS_QUEUE_NAME_MAP` | SET (ポート作成時) / DEL (ポート削除時) | PORT SET/DEL | portsorch.cpp:8527,8790 |
| COUNTERS_DB | `COUNTERS_QUEUE_PORT_MAP` | SET / DEL | PORT SET/DEL | portsorch.cpp:8527,8790 |
| COUNTERS_DB | `COUNTERS_QUEUE_INDEX_MAP` | SET / DEL | PORT SET/DEL | portsorch.cpp:8528,8797 |
| COUNTERS_DB | `COUNTERS_QUEUE_TYPE_MAP` | SET / DEL | PORT SET/DEL | portsorch.cpp:8529,8796 |
| FLEX_COUNTER_DB | `QUEUE_STAT_COUNTER:<oid>` | SET (エントリ登録) / DEL (クリア) | PORT SET/DEL かつ QUEUE カウンタ有効 | portsorch.cpp:8614,8804 |
| FLEX_COUNTER_DB | `QUEUE_WATERMARK_STAT_COUNTER:<oid>` | SET / DEL | PORT SET/DEL かつ QUEUE Watermark 有効 | portsorch.cpp:8635,8810 |
| FLEX_COUNTER_DB | `WRED_ECN_QUEUE_STAT_COUNTER:<oid>` | SET / DEL | PORT SET/DEL かつ WRED_ECN カウンタ有効 | portsorch.cpp:9592,8815 |
| STATE_DB | `QUEUE_COUNTER_CAPABILITIES` | SET (4 キー, isSupported=true/false) | orchagent 起動時 1 回 | portsorch.cpp:1850-1918 |

> **重要**: QUEUE テーブル自体の SET/DEL は APPL_DB / STATE_DB に直接書き込みを行わない。
> COUNTERS_DB / FLEX_COUNTER_DB への書込みは **PORT 作成・削除** のタイミングに紐付いており、QUEUE テーブルの個別エントリ操作とは独立している。
> STATE_DB `QUEUE_COUNTER_CAPABILITIES` への書込みは orchagent 起動時 1 回のみ (SAI 能力クエリ結果)。
