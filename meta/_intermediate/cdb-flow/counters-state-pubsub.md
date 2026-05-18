# counters-state Phase G — 通信メカニズム スキャンノート

Generated: 2026-05-18
Target doc: docs/reference/config-db/counters-state.md

対象テーブル: `STATE_DB` の `PORT_COUNTER_CAPABILITIES` / `QUEUE_COUNTER_CAPABILITIES` / `DEBUG_COUNTER_CAPABILITIES`
書き込み元: `orchagent` — `PortsOrch::initCounterCapabilities()` / `DebugCounterOrch::publishDropCounterCapabilities()`
スキャン範囲: `portsorch.cpp` initCounterCapabilities, `debugcounterorch.cpp` publishDropCounterCapabilities,
              `sonic-utilities/utilities_common/portstat.py`, `sonic-utilities/scripts/dropconfig`

---

## 通信方式の分類

これらのテーブルは CONFIG_DB テーブルと根本的に異なる通信パターンを持つ。

### 書き込み側 — Table::set() によるスナップショット書き込み

`PortsOrch` は `m_portCounterCapabilitiesTable` / `m_queueCounterCapabilitiesTable` を
`unique_ptr<Table>(new Table(m_state_db.get(), STATE_PORT_COUNTER_CAPABILITIES_NAME))` として保持する
(portsorch.cpp:793-794)。`initCounterCapabilities()` は `Table::set()` を呼ぶことで Redis `HSET` を実行する。
これは **一方向・一回限りの書き込み** であり、購読・通知のプロデューサー側パターン
(`ProducerStateTable` / `NotificationProducer`) は一切使用しない。

`DebugCounterOrch` も同様に `Table(stateDb, STATE_DEBUG_COUNTER_CAPABILITIES_NAME)` への `set()` で書き込む
(debugcounterorch.cpp:315-363)。

### 読み取り側 — HGET/HGETALL によるポーリング取得 (非購読型)

読み取り側は `SubscriberStateTable` や keyspace 通知を **使わない**。CLI ツールが実行時に
直接 `db.get()` / `db.get_all()` で現在値をスナップショット取得する方式を採る。

| 読み取り元 | 対象テーブル | Redis 操作 | コード |
|-----------|------------|-----------|--------|
| `portstat.py` | `PORT_COUNTER_CAPABILITIES\|<key>` | `db.get(STATE_DB, key, "isSupported")` | portstat.py:299-311 |
| `dropconfig` | `DEBUG_COUNTER_CAPABILITIES\|*` | `db.keys(STATE_DB, 'DEBUG_COUNTER_CAPABILITIES\|*')` + `db.get_all()` | dropconfig:423-431 |
| `dropconfig` (個別 capability) | `DEBUG_COUNTER_CAPABILITIES\|<counter_type>` | `db.get_all(STATE_DB, key)` | dropconfig:444-455 |

QUEUE_COUNTER_CAPABILITIES を直接参照するコンシューマーはソース内に確認できない（ポーリング実装なし）。
queuestat 等のツールが利用する可能性はあるが、portstat.py が参照するのは PORT_COUNTER_CAPABILITIES のみ。

---

## Redis 通知設定の不使用

STATE_DB には keyspace 通知 (`notify-keyspace-events`) が有効化されている環境もあるが、
これら 3 テーブルを `SubscriberStateTable` / `ConsumerStateTable` で購読するプロセスは
SONiC ソース内に存在しない。テーブル内容が変化するのは orchagent 起動時の 1 回のみ
（hot-reload / オンライン変更はサポートされない）であるため、keyspace 通知に乗る設計上の必要がない。

---

## データフロー図

```
SAI / ASIC
  ↓ sai_query_stats_capability()
  ↓ sai_query_attribute_enum_values_capability()
orchagent (PortsOrch::initCounterCapabilities / DebugCounterOrch::publishDropCounterCapabilities)
  ↓ Table::set() → Redis HSET (起動時 1 回)
STATE_DB
  ├── PORT_COUNTER_CAPABILITIES|<key>  {isSupported: "true"/"false"}
  ├── QUEUE_COUNTER_CAPABILITIES|<key> {isSupported: "true"/"false"}
  └── DEBUG_COUNTER_CAPABILITIES|<counter_type> {count: "<N>", reasons: "[...]"}

読み取り経路 (on-demand polling):
  portstat.py  → db.get(STATE_DB, "PORT_COUNTER_CAPABILITIES|...", "isSupported")
  dropconfig   → db.get_all(STATE_DB, "DEBUG_COUNTER_CAPABILITIES|...")
  (keyspace 通知 / SubscriberStateTable は不使用)
```

---

## 検出した特性

1. **ProducerStateTable 不使用**: 書き込みは `Table::set()` (= 生 HSET) のみ。APPL_DB への変換・中継なし。
2. **keyspace 購読者なし**: 変更通知を受け取る SubscriberStateTable 実装はソース内に存在しない。
3. **QUEUE_COUNTER_CAPABILITIES の読者不在**: portstat.py は PORT_COUNTER_CAPABILITIES のみ参照。
   QUEUE_COUNTER_CAPABILITIES は orchagent が書くが、SONiC ユーティリティ側に直接参照コードがない。
4. **一方向・一回限り**: orchagent 起動時のみ書き込み。オンライン更新・DEL はサポートしない。
   再設定には orchagent の再起動が必要。
