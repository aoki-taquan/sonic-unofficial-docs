# state-flex-counter Phase G — Redis 通知メカニズム調査メモ

## 調査対象

- `sonic-sairedis/syncd/Syncd.cpp`
- `sonic-sairedis/syncd/FlexCounter.cpp`
- `sonic-swss/orchagent/flexcounterorch.cpp`
- `sonic-swss-common/common/consumertable.cpp`
- `sonic-swss-common/common/producertable.cpp`
- `sonic-swss-common/common/table.h`

## 主要発見

### orchagent → FLEX_COUNTER_DB 書き込みメカニズム

`FlexCounterOrch` および各 Orch は `ProducerTable` 経由で FLEX_COUNTER_DB に書き込む。
`producertable.cpp:38` の Lua スクリプトが `LPUSH` + `PUBLISH` をアトミックに実行。

チャネル名は `table.h:85-96` の `getChannelName(int tag)` で生成:
```
FLEX_COUNTER_TABLE_CHANNEL@5
FLEX_COUNTER_GROUP_TABLE_CHANNEL@5
```
（5 = FLEX_COUNTER_DB の DB インデックス）

### syncd の ConsumerTable 購読

`Syncd.cpp:209-210`:
```cpp
m_flexCounter = std::make_shared<swss::ConsumerTable>(m_dbFlexCounter.get(), FLEX_COUNTER_TABLE);
m_flexCounterGroup = std::make_shared<swss::ConsumerTable>(m_dbFlexCounter.get(), FLEX_COUNTER_GROUP_TABLE);
```

`consumertable.cpp:31`:
```cpp
subscribe(m_db, getChannelName(m_db->getDbId()));
```
→ `SUBSCRIBE FLEX_COUNTER_TABLE_CHANNEL@5` / `SUBSCRIBE FLEX_COUNTER_GROUP_TABLE_CHANNEL@5`

### syncd 主ループ

`Syncd.cpp:5832-5856`:
```cpp
s->addSelectable(m_flexCounter.get());
s->addSelectable(m_flexCounterGroup.get());
```
タイムアウトなし（永続ブロック）。イベント到着時に `processFlexCounterEvent` / `processFlexCounterGroupEvent` を呼ぶ。

### FlexCounter ポーリングスレッド内部 wakeup

`FlexCounter.cpp` の条件変数 `m_cvSleep` を使用:
- `setPollInterval()`: `m_cvSleep.notify_all()` (行 3068)
- `setStatus()`: `m_cvSleep.notify_all()` (行 3089)
- `setStatsMode()`: `m_cvSleep.notify_all()` (行 3110)
- `endFlexCounterThread()`: `m_cvSleep.notify_all()` (行 3597)
- 条件未充足時: `waitPoll()` (行 3902) でブロック

外部 Redis SUBSCRIBE は使わず、内部スレッド間条件変数のみで制御。

## 結論

FLEX_COUNTER_DB は ProducerTable/ConsumerTable ペアによる Redis pub/sub で
orchagent → syncd への通知を行う標準的な swss パターン。
ポーリングスレッドへの設定変更伝搬は内部条件変数（`m_cvSleep`）のみ。
