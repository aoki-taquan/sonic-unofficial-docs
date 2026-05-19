# DPU カウンタ Phase G — 通信メカニズム (Redis PUBSUB / keyspace notification)

Generated: 2026-05-19
Target doc: docs/reference/config-db/dpu-counter.md

対象テーブル: `FLEX_COUNTER_TABLE|ENI` / `FLEX_COUNTER_TABLE|DASH_METER`
Consumer: `orchagent` — `FlexCounterOrch::doTask()` + `DashOrch::handleFCStatusUpdate()` / `handleMeterFCStatusUpdate()`
スキャン範囲:
  - `sonic-swss/orchagent/orchdaemon.cpp:620-628,1350-1352`
  - `sonic-swss/orchagent/flexcounterorch.cpp:60-93,127-167,299-305`
  - `sonic-swss/orchagent/orch.cpp:1186-1196`
  - `sonic-swss-common/common/subscriberstatetable.cpp:17-44,95-165`
  - `sonic-swss/orchagent/saihelper.cpp:117-118,324-325,868-885,918-962`

---

## 概要

`FLEX_COUNTER_TABLE|ENI` / `FLEX_COUNTER_TABLE|DASH_METER` は CONFIG_DB (db 4) に保持される。
購読者は **orchagent の `FlexCounterOrch`** 単体で、`SubscriberStateTable` (Redis keyspace PSUBSCRIBE) で変更通知を受け取る。
受信後は内部で `DashOrch` の `handleFCStatusUpdate()` / `handleMeterFCStatusUpdate()` を呼び出し、副次的に FLEX_COUNTER_DB へ書き込む。

---

## 購読者: orchagent `FlexCounterOrch`

### 生成 (orchdaemon.cpp:620-628)

```cpp
vector<string> flex_counter_tables = {
    CFG_FLEX_COUNTER_TABLE_NAME,      // "FLEX_COUNTER_TABLE"
    CFG_DEVICE_METADATA_TABLE_NAME    // "DEVICE_METADATA"
};
auto* flexCounterOrch = new FlexCounterOrch(m_configDb, flex_counter_tables);
```

`m_configDb` は CONFIG_DB (dbId=4) DBConnector。`Orch::addConsumer()` 経由で各テーブルに対して
**SubscriberStateTable** が生成される (orch.cpp:1186-1196)。

### PSUBSCRIBE パターン

`SubscriberStateTable` ctor は以下のパターンで PSUBSCRIBE を発行 (subscriberstatetable.cpp:17-24):

| テーブル | PSUBSCRIBE パターン |
|---|---|
| `FLEX_COUNTER_TABLE` | `__keyspace@4__:FLEX_COUNTER_TABLE\|*` |
| `DEVICE_METADATA` | `__keyspace@4__:DEVICE_METADATA\|*` |

`ENI` / `DASH_METER` サブキーを含む全書き込みがこのパターンで捕捉される。

### 起動時スナップショット

`SubscriberStateTable` ctor は PSUBSCRIBE 直後に `m_table.getKeys()` で既存全エントリを HGETALL し、
`SET_COMMAND` として `m_buffer` に積む (subscriberstatetable.cpp:26-44)。
orchagent 起動時に CONFIG_DB に `FLEX_COUNTER_TABLE|ENI` / `FLEX_COUNTER_TABLE|DASH_METER` が
既に存在する場合は、**PSUBSCRIBE 待ちなしで即時 doTask に流れる**。

ただし `m_delayTimerExpired = false` (warm-start 時) または `!gPortsOrch->allPortsReady()` の場合は
`doTask()` 先頭で即 return されるため、実際の処理は条件満了後になる。

### doTask の ENI / DASH_METER 分岐 (flexcounterorch.cpp:299-305)

```cpp
DashOrch* dash_orch = gDirectory.get<DashOrch*>();

if (dash_orch && (key == ENI_KEY))
{
    dash_orch->handleFCStatusUpdate((value == "enable"));
}
if (dash_orch && (key == DASH_METER_KEY))
{
    dash_orch->handleMeterFCStatusUpdate((value == "enable"));
}
```

- `ENI_KEY = "ENI"`, `DASH_METER_KEY = "DASH_METER"` (flexcounterorch.cpp:60-61)
- `dash_orch` が `nullptr` の場合はスキップ (DASH 機能なしビルド時)
- `FLEX_COUNTER_STATUS` フィールドのみがこの分岐を通る。`POLL_INTERVAL` は `setFlexCounterGroupPollInterval()` 経路で処理される

---

## 書き込み元 (Publisher 側)

CONFIG_DB に対する書き込みはすべて直接 HSET ベース (`ProducerStateTable` ではない):

| 書き込み元 | 書き込み手段 |
|---|---|
| `counterpoll eni enable/disable/interval` | `swsssdk.ConfigDBConnector.mod_entry()` → Redis HSET |
| `counterpoll dash-meter enable/disable/interval` | 同上 |
| `enable_counters.py` | `ConfigDBConnector.set_entry()` → Redis HSET (DPU 起動時自動) |
| `sonic-cfggen` / `config_db.json` 一括投入 | sonic-cfggen による HSET |

HSET が走ると Redis サーバが keyspace 通知 `__keyspace@4__:FLEX_COUNTER_TABLE|<key>` を
`notify-keyspace-events` 設定に従って PUBLISH し、`SubscriberStateTable` がこれを拾う。

---

## orchagent → FLEX_COUNTER_DB 書き込み方式

`FlexCounterManager` が per-OID カウンタ ID リストを FLEX_COUNTER_DB へ書き込む経路は
起動オプション `--traditional-flexcounter` の有無で 2 系統に分かれる:

| モード | 書き込み API | 通知方式 |
|--------|------------|---------|
| Traditional (`gTraditionalFlexCounter = true`) | `ProducerTable::set()` (`saihelper.cpp:1047`) | `FLEX_COUNTER_TABLE_CHANNEL` で syncd が起床 |
| 非 Traditional (デフォルト) | `SAI_REDIS_SWITCH_ATTR_FLEX_COUNTER` 属性経由 (`saihelper.cpp:1055-1063`) | ASIC チャンネル経由。FLEX_COUNTER_DB への直接 PUBLISH は行わない |

---

## Producer / Consumer ペアサマリ

| 区間 | 方式 | チャンネル |
|------|------|-----------|
| CLI / enable_counters.py → CONFIG_DB | `ConfigDBConnector.mod_entry()` (直接 HSET) | keyspace `__keyspace@4__:FLEX_COUNTER_TABLE\|*` |
| CONFIG_DB → FlexCounterOrch | `SubscriberStateTable` (PSUBSCRIBE) | keyspace notification |
| FlexCounterOrch → DashOrch | 関数呼び出し (`handleFCStatusUpdate`) | — (同プロセス内) |
| FlexCounterOrch → FLEX_COUNTER_DB (traditional) | `ProducerTable` | `FLEX_COUNTER_TABLE_CHANNEL` |
| FlexCounterOrch → syncd (非 traditional) | SAI Redis Attribute / ASIC channel | — |
| syncd FlexCounter → COUNTERS_DB | `swss::Table::set()` (plain HSET) | **なし (PUBLISH 非発行)** |

---

## 重要な特性

| 特性 | 内容 |
|------|------|
| 通知種別 | Redis PSUBSCRIBE (keyspace notification) |
| PSUBSCRIBE パターン | `__keyspace@4__:FLEX_COUNTER_TABLE\|*` |
| keyspace イベント名 | `hset` / `del` 等の Redis 操作名 |
| フィールド値取得 | 通知後に HGETALL で別途取得 |
| SWSS abstraction | `swss::SubscriberStateTable` + `swss::Select` (Orch::addConsumer 経由) |
| ConsumerStateTable | **不使用** (CONFIG_DB は ProducerStateTable 経路を持たないため) |
| NotificationConsumer | **不使用** |
| 起動時スナップショット | `SubscriberStateTable` ctor が getKeys()+HGETALL で既存全エントリを SET_COMMAND として buffer 充填 |
| Warm restart 遅延 | FlexCounterOrch のみ 60 秒、その間 doTask は no-op (m_toSync に蓄積) |
| COUNTERS_DB への push 通知 | **なし** (syncd が plain HSET で書くため PUBLISH 非発行) |

---

## 証拠リンク

- `sonic-swss/orchagent/orchdaemon.cpp:620-628` — FlexCounterOrch 生成
- `sonic-swss/orchagent/orchdaemon.cpp:1350-1352` — DashOrch 生成 (DPU パス)
- `sonic-swss/orchagent/orch.cpp:1186-1196` — addConsumer の CONFIG_DB → SubscriberStateTable 分岐
- `sonic-swss/orchagent/flexcounterorch.cpp:60-61` — ENI_KEY / DASH_METER_KEY 定数
- `sonic-swss/orchagent/flexcounterorch.cpp:92-93` — flexCounterGroupMap の ENI / DASH_METER 登録
- `sonic-swss/orchagent/flexcounterorch.cpp:127-167` — doTask 冒頭ガード (warm-start タイマー / allPortsReady)
- `sonic-swss/orchagent/flexcounterorch.cpp:299-305` — ENI / DASH_METER フィールド処理 → DashOrch 呼び出し
- `sonic-swss-common/common/subscriberstatetable.cpp:17-44` — ctor: PSUBSCRIBE + 初回スナップショット
- `sonic-swss-common/common/subscriberstatetable.cpp:95-165` — pops(): keyspace イベント → HGETALL
- `sonic-swss/orchagent/saihelper.cpp:918-962` — setFlexCounterGroupOperation: SAI redis 直書き or ProducerTable 分岐
