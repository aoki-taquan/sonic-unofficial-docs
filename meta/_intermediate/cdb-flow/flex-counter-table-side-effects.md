# FLEX_COUNTER_TABLE — Phase F 副次 DB 書込 中間ファイル

調査日: 2026-05-16  
ソース: `sonic-net/sonic-swss` `orchagent/flexcounterorch.cpp` + `orchagent/saihelper.cpp` + `orchagent/portsorch.cpp` (master)  
対象ページ: `docs/reference/config-db/flex-counter-table.md`

---

## 概要

`FLEX_COUNTER_TABLE` への書込は CONFIG_DB から直接 orchagent (`FlexCounterOrch`) が購読する。  
orchagent は `FLEX_COUNTER_DB` へのグループ設定書込と、`COUNTERS_DB` への名前マップ書込という 2 種類の副次書込を行う。

---

## 1. FLEX_COUNTER_DB — グループ設定書込

### 書込経路

```
CONFIG_DB FLEX_COUNTER_TABLE SET
  └─ FlexCounterOrch::doTask() (flexcounterorch.cpp)
       ├─ setFlexCounterGroupPollInterval()  → gFlexCounterGroupTable->set(group, fv)
       ├─ setFlexCounterGroupOperation()     → gFlexCounterGroupTable->set(group, fv)
       └─ setFlexCounterGroupBulkChunkSize() → sai_switch_api (SAI Redis 経由)
```

`gFlexCounterGroupTable` は `ProducerTable(gFlexCounterDb.get(), FLEX_COUNTER_GROUP_TABLE)` として初期化される (`saihelper.cpp:325`)。  
`gTraditionalFlexCounter=true` の場合は Redis ProducerTable 書込、`false` の場合は SAI Redis 属性呼び出し (`SAI_REDIS_SWITCH_ATTR_FLEX_COUNTER_GROUP`) に切り替わる。

### 書込テーブル

| DB | テーブル | キー形式 | 書込フィールド | トリガ |
|----|---------|---------|--------------|-------|
| `FLEX_COUNTER_DB` | `FLEX_COUNTER_GROUP_TABLE` | `<group>` (例: `PORT`, `QUEUE`) | `POLL_INTERVAL` | `setFlexCounterGroupPollInterval()` — `POLL_INTERVAL` フィールド変化時 |
| `FLEX_COUNTER_DB` | `FLEX_COUNTER_GROUP_TABLE` | `<group>` | `FLEX_COUNTER_STATUS` (`enable`/`disable`) | `setFlexCounterGroupOperation()` — `FLEX_COUNTER_STATUS` フィールド変化時 |
| `FLEX_COUNTER_DB` | `FLEX_COUNTER_GROUP_TABLE` | `<group>` | `BULK_CHUNK_SIZE`, `BULK_CHUNK_SIZE_PER_PREFIX` | `setFlexCounterGroupBulkChunkSize()` — `BULK_CHUNK_SIZE*` フィールド変化時 (未設定時は `"NULL"` で書込) |

### PORT_PHY_ATTR の自動連動書込

`PORT_PHY_ATTR` グループの `FLEX_COUNTER_STATUS` を `enable`/`disable` すると、`PORT_PHY_SERDES_ATTR` グループへも自動で同じ operation が書き込まれる (`flexcounterorch.cpp:386-392`)。  
ユーザーが `FLEX_COUNTER_TABLE|PORT_PHY_SERDES_ATTR` を直接書く必要はない。

---

## 2. COUNTERS_DB — 名前マップ書込

`FLEX_COUNTER_STATUS=enable` 時に `generatePortCounterMap()` / `generateQueueMap()` / `generatePriorityGroupMap()` 等を呼ぶと、`COUNTERS_DB` の名前マップテーブルが更新される。

### 書込テーブル

| DB | テーブル | キー / フィールド | 書込タイミング |
|----|---------|----------------|--------------|
| `COUNTERS_DB` | `COUNTERS_PORT_NAME_MAP` | `<port_alias>` → OID | `PORT` グループ enable 時に `generatePortCounterMap()` → `m_counterNameMapUpdater->setCounterNameMap()` (`portsorch.cpp:4118`) |
| `COUNTERS_DB` | `COUNTERS_QUEUE_NAME_MAP` | `<port_alias>:<queue_index>` → OID | `QUEUE` / `QUEUE_WATERMARK` / `WRED_ECN_QUEUE` enable 時に `generateQueueMap()` → `m_queueCounterNameMapUpdater->setCounterNameMap()` (`portsorch.cpp:8524,8749`) |
| `COUNTERS_DB` | `COUNTERS_PG_NAME_MAP` | `<port_alias>:<pg_index>` → OID | `PG_DROP` / `PG_WATERMARK` enable 時に `generatePriorityGroupMap()` → `m_pgCounterNameMapUpdater->setCounterNameMap()` (`portsorch.cpp:8882,8937`) |

各マップは **一度生成されると `m_is*Generated` フラグで以降の再生成をスキップ**する (idempotent)。  
ポート削除・キュー削除時には対応するエントリを `delCounterNameMap()` で削除する。

---

## 3. FLEX_COUNTER_DB — COUNTER_ID_LIST 書込（generate*Map の内部動作）

`generatePortCounterMap()` / `addQueueFlexCounters()` 等は、ポートごとの `COUNTER_ID_LIST` を `FLEX_COUNTER_DB` に書き込む（syncd の FlexCounter モジュールが参照してポーリングを実行する）。

| DB | テーブル | キー形式 | 書込フィールド |
|----|---------|---------|--------------|
| `FLEX_COUNTER_DB` | `FLEX_COUNTER_TABLE` | `PORT:<OID>` 等 | `COUNTER_ID_LIST` — ポーリング対象の SAI stats ID リスト |

この書込は orchagent が直接 CONFIG_DB を読んで `FlexCounterTable`（`gFlexCounterTable`）へ push する経路。SAI stats 実収集は syncd 側の FlexCounter が担う。

---

## 書込タイミングまとめ

```
FLEX_COUNTER_TABLE SET (CONFIG_DB)
  └─ FlexCounterOrch::doTask() (直接 CONFIG_DB Subscribe)
       ├─ POLL_INTERVAL 変化
       │    └─ setFlexCounterGroupPollInterval()
       │         └─ FLEX_COUNTER_DB FLEX_COUNTER_GROUP_TABLE SET (<group>, POLL_INTERVAL=<ms>)
       ├─ FLEX_COUNTER_STATUS=enable
       │    ├─ setFlexCounterGroupOperation()
       │    │    └─ FLEX_COUNTER_DB FLEX_COUNTER_GROUP_TABLE SET (<group>, FLEX_COUNTER_STATUS=enable)
       │    ├─ generate*CounterMap() / add*FlexCounters()
       │    │    ├─ FLEX_COUNTER_DB FLEX_COUNTER_TABLE SET (<OID>, COUNTER_ID_LIST=...)
       │    │    └─ COUNTERS_DB COUNTERS_*_NAME_MAP HSET (<name>=<OID>)
       │    └─ PORT_PHY_ATTR のみ: PORT_PHY_SERDES_ATTR にも自動連動書込
       └─ BULK_CHUNK_SIZE* 変化
            └─ setFlexCounterGroupBulkChunkSize()
                 └─ FLEX_COUNTER_DB FLEX_COUNTER_GROUP_TABLE SET (<group>, BULK_CHUNK_SIZE=<n>)
```

---

## 証跡サマリ

| 副次書込先 | テーブル | 書込経路 | evidence |
|-----------|---------|---------|---------|
| `FLEX_COUNTER_DB` | `FLEX_COUNTER_GROUP_TABLE` | `setFlexCounterGroupOperation()` | `saihelper.cpp:918`, `flexcounterorch.cpp:380` |
| `FLEX_COUNTER_DB` | `FLEX_COUNTER_GROUP_TABLE` | `setFlexCounterGroupPollInterval()` | `saihelper.cpp:941`, `flexcounterorch.cpp:202` |
| `FLEX_COUNTER_DB` | `FLEX_COUNTER_GROUP_TABLE` | `setFlexCounterGroupBulkChunkSize()` | `saihelper.cpp:987`, `flexcounterorch.cpp:404` |
| `FLEX_COUNTER_DB` | `FLEX_COUNTER_TABLE` | `gFlexCounterTable->set(<OID>, COUNTER_ID_LIST)` | `saihelper.cpp:324`, `portsorch.cpp` |
| `COUNTERS_DB` | `COUNTERS_PORT_NAME_MAP` | `m_counterNameMapUpdater->setCounterNameMap()` | `portsorch.cpp:4118` |
| `COUNTERS_DB` | `COUNTERS_QUEUE_NAME_MAP` | `m_queueCounterNameMapUpdater->setCounterNameMap()` | `portsorch.cpp:8524` |
| `COUNTERS_DB` | `COUNTERS_PG_NAME_MAP` | `m_pgCounterNameMapUpdater->setCounterNameMap()` | `portsorch.cpp:8882` |
