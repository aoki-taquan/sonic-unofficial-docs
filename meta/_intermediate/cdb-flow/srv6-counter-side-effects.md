# FLEX_COUNTER_TABLE|SRV6 — Phase F 副次 DB 書込 中間ファイル

生成日: 2026-05-17
ソース: `sonic-swss/orchagent/srv6orch.cpp` / `flexcounterorch.cpp` / `saihelper.cpp`
主要関数: `FlexCounterOrch::doTask`, `Srv6Orch::setCountersState`, `Srv6Orch::addMySidCounter`, `Srv6Orch::removeMySidCounter`, `setFlexCounterGroupPollInterval`

---

## 概要

`FLEX_COUNTER_TABLE|SRV6` への書込みは orchagent の `FlexCounterOrch` が受け取り、各フィールドに応じて下記の副次 DB 書込みを引き起こす。CONFIG_DB そのものへの書き戻しはない。

---

## 1. `FLEX_COUNTER_STATUS` フィールド変更

`flexcounterorch.cpp:337-340` が `gSrv6Orch->setCountersState(enable)` を呼び出す。

### enable 時 (`"enable"`)

`Srv6Orch::setCountersState(true)` は全既存 MY_SID エントリに対して以下を実行:

| 副次 DB / API | キー / 操作 | ソース |
|-------------|-----------|--------|
| COUNTERS_DB / `COUNTERS_SRV6_NAME_MAP` | `hset("", sid_prefix, counter_oid)` — MySID ごとのカウンタ OID を登録 | `srv6orch.cpp:196-199` |
| `m_pending_counters` (in-memory) | counter_oid を追加 → 1 秒タイマー起動 | `srv6orch.cpp:201-206` |
| ASIC_DB / `VIDTORID` | `hget` 読取のみ（VID→RID 解決確認）| `srv6orch.cpp:294` |
| FLEX_COUNTER_DB / `SRV6_STAT_COUNTER:<oid>` | `setCounterIdList` — VIDTORID 確認後に登録 | `srv6orch.cpp:300` |
| SAI / `sai_srv6_api` | `set_my_sid_entry_attribute(SAI_MY_SID_ENTRY_ATTR_COUNTER_ID, counter_oid)` — ASIC にカウンタ紐付け | `srv6orch.cpp:276, 244` |

プラットフォームが SAI_MY_SID_ENTRY_ATTR_COUNTER_ID を非サポートの場合は `setCountersState` が early-return し、副次書込みは一切発生しない (`srv6orch.cpp:256-260`)。

### disable 時 (`"disable"`)

| 副次 DB / API | キー / 操作 | ソース |
|-------------|-----------|--------|
| SAI / `sai_srv6_api` | `set_my_sid_entry_attribute(SAI_MY_SID_ENTRY_ATTR_COUNTER_ID, SAI_NULL_OBJECT_ID)` — ASIC からカウンタ切離し | `srv6orch.cpp:278, 244` |
| COUNTERS_DB / `COUNTERS_SRV6_NAME_MAP` | `hdel("", sid_prefix)` — 名前マップエントリ削除 | `srv6orch.cpp:223` |
| FLEX_COUNTER_DB / `SRV6_STAT_COUNTER:<oid>` | `clearCounterIdList` — FLEX_COUNTER_DB エントリ削除 | `srv6orch.cpp:229` |
| `m_pending_counters` (in-memory) | counter_oid を除去（ pending 中であればタイマー停止） | `srv6orch.cpp:225-231` |

### enable → disable → enable の再有効化

`m_mysid_counters_enabled` フラグで冪等性を保証 (`srv6orch.cpp:261-263`)。同一値の連続書込みは no-op。

---

## 2. `POLL_INTERVAL` フィールド変更

`flexcounterorch.cpp:200-203` が `setFlexCounterGroupPollInterval(SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP, value)` を呼び出す。

| モード | 副次 DB / API | 操作 | ソース |
|-------|-------------|------|--------|
| `gTraditionalFlexCounter=true` | FLEX_COUNTER_DB / `SRV6_STAT_COUNTER` group | `POLL_INTERVAL` フィールドを更新 | `saihelper.cpp:946-948` |
| `gTraditionalFlexCounter=false` | SAI Redis 通知 (`notifySyncdCounterOperation`) | `SAI_REDIS_SWITCH_ATTR_FLEX_COUNTER_GROUP` 経由で syncd に伝達 | `saihelper.cpp:956-963` |

COUNTERS_DB / STATE_DB への書込みは発生しない。

---

## 3. `FLEX_COUNTER_DELAY_STATUS` フィールド変更

`FlexCounterOrch::doTask` (`flexcounterorch.cpp`) が FLEX_COUNTER_DB の group エントリの delay フィールドを更新する（`setFlexCounterGroupOperation` 呼び出し）。SRV6 固有の追加副作用はない。

---

## フロー概要

```
CONFIG_DB FLEX_COUNTER_TABLE|SRV6
  └─► FlexCounterOrch::doTask (flexcounterorch.cpp:337-340)
        ├─ FLEX_COUNTER_STATUS: Srv6Orch::setCountersState(enable)
        │    ├─ [enable] addMySidCounter() x (全 MY_SID 数)
        │    │    ├─ COUNTERS_DB COUNTERS_SRV6_NAME_MAP hset(sid_prefix, counter_oid)
        │    │    └─ m_pending_counters へ追加 → 1秒タイマー
        │    │         └─ doTask(timer): VIDTORID 確認後
        │    │              ├─ FLEX_COUNTER_DB SRV6_STAT_COUNTER:<oid> set
        │    │              └─ SAI set_my_sid_entry_attribute(COUNTER_ID, oid)
        │    └─ [disable] removeMySidCounter() x (全 MY_SID 数)
        │         ├─ SAI set_my_sid_entry_attribute(COUNTER_ID, NULL)
        │         ├─ COUNTERS_DB COUNTERS_SRV6_NAME_MAP hdel(sid_prefix)
        │         └─ FLEX_COUNTER_DB SRV6_STAT_COUNTER:<oid> del
        └─ POLL_INTERVAL: setFlexCounterGroupPollInterval(SRV6_STAT_COUNTER, value)
             └─ FLEX_COUNTER_DB or SAI Redis 通知 (gTraditionalFlexCounter に依存)
```

---

## 注記

- COUNTERS_DB / FLEX_COUNTER_DB 書込みは `getMySidCountersSupported()` が true の場合のみ。
- `m_pending_counters` が空の場合、タイマーは起動しない（`srv6orch.cpp:201-206`）。
- STATE_DB / APPL_DB / CONFIG_DB への書き戻しはいずれのケースでも発生しない。
