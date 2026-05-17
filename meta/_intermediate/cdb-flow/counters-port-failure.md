# COUNTERS_DB PORT カウンタ — Phase D 失敗挙動スキャンノート

対象: `COUNTERS_DB COUNTERS:<oid>` / flex counter ポーリング経路
Consumer: `flexcounterorch` + `portsorch` (sonic-swss/orchagent/)
スキャン範囲: flexcounterorch.cpp 全行、portsorch.cpp の counter 登録経路精読

---

## 検出した失敗パターン

### 1. 不正 flex counter グループキー — 即エントリ削除・retry なし

`FlexCounterOrch::doTask()` は `flexCounterGroupMap` に存在しないキーを受信した場合、
`SWSS_LOG_NOTICE "Invalid flex counter group input, <key>"` を出力し、エントリを即削除する
(flexcounterorch.cpp:183-188)。

```cpp
if (!flexCounterGroupMap.count(key))
{
    SWSS_LOG_NOTICE("Invalid flex counter group input, %s", key.c_str());
    consumer.m_toSync.erase(it++);
    continue;
}
```

**影響**: `FLEX_COUNTER_TABLE|PORT` 以外の未知キー（例: タイポ）は silent に破棄される。PORT カウンタ自体は影響なし。

### 2. 未サポートフィールド — SWSS_LOG_NOTICE で silent skip

SET_COMMAND 処理で `POLL_INTERVAL_FIELD` / `FLEX_COUNTER_STATUS_FIELD` / `STATS_MODE_FIELD` /
`BULK_CHUNK_SIZE_FIELD` / `BULK_CHUNK_SIZE_PER_PREFIX_FIELD` 以外のフィールドを受信した場合、
`SWSS_LOG_NOTICE "Unsupported field <field>"` を出力してスキップする (flexcounterorch.cpp:396-398)。

**影響**: フィールドは無視されるが、エントリは削除されない（他フィールドの処理は継続）。

### 3. allPortsReady() が false の間は全処理保留

`FlexCounterOrch::doTask()` は `gPortsOrch->allPortsReady()` が `false` の間、即 return する
(flexcounterorch.cpp:164-166)。これはエラーではなく設計上の保留。

- `m_toSync` のエントリは保持されたまま
- 次の `doTask()` 呼び出し（Consumer tick）で再試行される
- `allPortsReady()` は `m_initDone && m_pendingPortSet.empty()` (portsorch.cpp:1685-1687)

**影響**: 起動シーケンスが正常であれば PortInitDone 後に自動解除される。PortInitDone が永遠に来ない場合（portsyncd 異常終了等）、flex counter は永遠に enable されない。

### 4. Warm Start 時の 60 秒遅延タイマー

Warm Start 時、`FlexCounterOrch` ctor が `m_delayTimerExpired = false` でタイマーを起動し、
タイマー満了（60 秒）まで `doTask()` が全リターンする (flexcounterorch.cpp:127-136, 155-158)。

```cpp
// flexcounterorch.cpp:127-137 (概略)
if (WarmStart::isWarmStart())
{
    // start 60s timer, set m_delayTimerExpired = false
}
else
{
    m_delayTimerExpired = true; // 通常起動時は即解除
}
```

**影響**: Warm Start 環境では PortInitDone 後も 60 秒間は `FLEX_COUNTER_TABLE` への書き込みが処理されない。再起動後 60 秒間は PORT カウンタが更新されない。

### 5. setCounterIdList() の失敗は orchagent クラッシュ

`port_stat_manager.setCounterIdList()` / `gb_port_stat_manager.setCounterIdList()` は Redis への
書き込み操作（`FLEX_COUNTER_DB` への `hset`）で、通常は失敗しないが、Redis 接続断等の場合は
`RedisReply` の例外が throw され orchagent プロセス全体がクラッシュする。明示的な catch はない。

**影響**: Redis 障害時は orchagent がクラッシュし、supervisor が再起動するまで全カウンタ収集停止。

### 6. SAI カウンタ取得失敗 — syncd 側の処理（portstat 表示への影響）

SAI が特定の counter stat を返せない場合（ASIC 非サポート等）、syncd の flex counter polling が
当該フィールドを書き込まない。`portstat.py` の `get_counters()` は Redis から値を取得できない場合
`STATUS_NA` ('N/A') を返す (portstat.py:297-329)。

| ケース | portstat 表示 | COUNTERS_DB 状態 |
|--------|-------------|-----------------|
| ASIC サポートあり | 数値 | 値あり |
| ASIC 非サポート (WRED 等) | N/A | フィールド不在 or 0 |
| counterpoll disable | 前回値（stale）| 最後の値が残る |

### 7. DEL 時（counterpoll disable）—COUNTERS_DB は削除されない

`FLEX_COUNTER_TABLE|PORT` に `FLEX_COUNTER_STATUS=disable` が書かれた場合、syncd はポーリングを停止するが
`COUNTERS_DB:COUNTERS:<oid>` のハッシュは**削除されない**。最後の値がそのまま残る。

ポート削除時は `m_counterNameMapUpdater->delCounterNameMap(alias)` で `COUNTERS_PORT_NAME_MAP` から
当該エントリが削除される (portsorch.cpp:4312)。`COUNTERS:<oid>` ハッシュ自体は portsorch 側からは
削除されない（syncd が管理）。

---

## 失敗挙動サマリ

| # | トリガー | 挙動 | retry |
|---|----------|------|-------|
| 1 | 不正グループキー | エントリ即削除・NOTICE ログ | なし |
| 2 | 未サポートフィールド | silent skip・NOTICE ログ | なし（他フィールドは継続） |
| 3 | allPortsReady() = false | doTask 全リターン・m_toSync 保留 | 自動（次 tick） |
| 4 | Warm Start 60 秒タイマー | doTask 全リターン・m_toSync 保留 | 自動（タイマー満了後） |
| 5 | Redis 接続断 | orchagent クラッシュ | supervisor 再起動 |
| 6 | SAI counter 非サポート | N/A 表示・フィールド不在 | なし（設計上の省略） |
| 7 | counterpoll disable | ポーリング停止・COUNTERS_DB 値残留 | なし（DEL は noop） |
