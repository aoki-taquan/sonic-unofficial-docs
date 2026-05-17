# counters-port Phase G — 通信メカニズム (pubsub)

Generated: 2026-05-17
Target doc: docs/reference/config-db/counters-port.md

## 調査対象

- `sonic-swss/orchagent/flexcounterorch.cpp`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-utilities/utilities_common/portstat.py`

## Producer/Consumer ペア

PORT カウンタの制御経路は **CONFIG_DB → FlexCounterOrch → syncd** という 3 段構成をとる。
APPL_DB 中継なし。

| 区間 | 方式 | 詳細 |
|------|------|------|
| CONFIG_DB → FlexCounterOrch | `SubscriberStateTable` | `CFG_FLEX_COUNTER_TABLE_NAME` (`FLEX_COUNTER_TABLE|PORT` 等) を購読。keyspace notification で変化を検出 |
| FlexCounterOrch → portsorch | 直接関数呼び出し | `gPortsOrch->generatePortCounterMap()` / `setCounterIdList()` |
| portsorch → syncd | `FlexCounterTaggedCachedManager` (FLEX_COUNTER_DB) | `PORT_STAT_COUNTER_FLEX_COUNTER_GROUP` グループに COUNTER_ID_LIST を書き込む |
| syncd → ASIC | SAI flex counter ポーリング | 1000 ms 間隔で SAI stat API をポーリング |
| syncd → COUNTERS_DB | 直接書き込み | `COUNTERS:<oid>` Hash に各 SAI フィールドの値をアトミック更新 |
| COUNTERS_DB → portstat | `Table::get()` 直接読み出し | `COUNTERS_PORT_NAME_MAP` で名前→OID 解決後、`COUNTERS:<oid>` を読む |

## FlexCounterOrch の起動シーケンスと遅延タイマー

`FlexCounterOrch` は `orchdaemon.cpp:625` で生成される。

```
orchdaemon init
  ↓ new FlexCounterOrch(m_configDb, {CFG_FLEX_COUNTER_TABLE_NAME, ...})
  ↓   cold-start: m_delayTimerExpired = true → 即処理可能
  ↓   warm-start:  SelectableTimer(60s) 起動 → 60s 間 doTask 全ブロック
                   (flexcounterorch.cpp:127-137)
```

warm-start 時は `FLEX_COUNTER_DELAY_SEC = 60` 秒間、`doTask(Consumer&)` 冒頭の
`if (!m_delayTimerExpired) return;` (flexcounterorch.cpp:156-159) により
全 FLEX_COUNTER_TABLE 更新が保留される。これは syncd 再起動完了まで
SAI ポーリング設定を遅延させるための設計意図。

## SubscriberStateTable の動作

`FlexCounterOrch` は `Orch(db, tableNames)` 基底クラス経由で
`CFG_FLEX_COUNTER_TABLE_NAME` に対する `SubscriberStateTable` を保持する。
Redis keyspace notification (`PSUBSCRIBE __keyspace@{cfg_db_id}__:FLEX_COUNTER_TABLE|*`)
でエントリの変化を検出し、`orchdaemon` の `select()` ループが wake-up する。

## select() ループとの関係

```
orchdaemon: Select::select(timeout=1000ms)
  ↓ FLEX_COUNTER_TABLE|PORT が変化
  ↓ Consumer::drain() → FlexCounterOrch::doTask(Consumer&)
      [m_delayTimerExpired チェック]
      [gPortsOrch->allPortsReady() チェック]
      FLEX_COUNTER_STATUS=enable → gPortsOrch->generatePortCounterMap()
                                 → port_stat_manager.setCounterIdList()
                                   (FLEX_COUNTER_DB への書き込み)
      setFlexCounterGroupOperation() → FLEX_COUNTER_DB グループ enable
  ↓
syncd FlexCounter スレッド
  ↓ ポーリング間隔 (1000ms) ごとに SAI stat API 呼び出し
  ↓ COUNTERS_DB / COUNTERS:<oid> を更新
```

## FLEX_COUNTER_DB への書き込みキー

| FLEX_COUNTER_DB キー | 内容 |
|----------------------|------|
| `FLEX_COUNTER_GROUP_TABLE\|PORT` | `POLL_INTERVAL`, `FLEX_COUNTER_STATUS`, `STATS_MODE` |
| `FLEX_COUNTER_TABLE\|<port_oid>:COUNTER_ID_LIST` | ポーリング対象 SAI カウンタ ID のカンマ区切りリスト |

portsorch の `port_stat_manager` (`FlexCounterTaggedCachedManager`) が
`setCounterIdList()` を呼ぶと、上記 `FLEX_COUNTER_TABLE|<oid>` エントリが書かれる。
syncd はこの DB を購読しており、エントリが書かれ次第 SAI ポーリングを開始する。

## portstat.py の読み出しパス

```python
# portstat.py (utilities_common/portstat.py)
counter_port_name_map = self.db.get_all(COUNTERS_DB, COUNTERS_PORT_NAME_MAP)
# → {Ethernet0: oid:0x..., ...}

counter_data = self.db.get(COUNTERS_DB, f"COUNTERS:{oid}", field_name)
# → "12345678"  (uint64 文字列)
```

`portstat` は COUNTERS_DB を **直接読み取る**。pub/sub 購読は行わず、
コマンド実行時点の最新値をポーリング取得する（push 型ではなく pull 型）。

## 通知消費者なし

COUNTERS_DB の `COUNTERS:<oid>` 更新は syncd → Redis 書き込みのみ。
`portstat` / `show interface counters` は読み取り専用クライアント。
`NotificationConsumer` / `NotificationProducer` はこの経路では使用されない。
（ポート状態変化通知 `port_state_change` は別チャンネル `NOTIFICATIONS` を使うが、
カウンタ値の配信には無関係）

## データフロー図まとめ

```
CONFIG_DB[FLEX_COUNTER_TABLE|PORT]
  ↓ SubscriberStateTable (keyspace notification)
orchdaemon select() loop (SELECT_TIMEOUT=1000ms)
  ↓ FlexCounterOrch::doTask()
      allPortsReady() + delayTimerExpired チェック
      generatePortCounterMap() → port_stat_manager.setCounterIdList()
FLEX_COUNTER_DB[FLEX_COUNTER_TABLE|<port_oid>:COUNTER_ID_LIST]
  ↓ syncd FlexCounter スレッド (1000ms ポーリング)
      sai_port_api->get_port_stats()
COUNTERS_DB[COUNTERS:<oid>] ← SAI 統計値 (uint64 文字列)
  ↓ portstat / show interface counters (pull 型 direct read)

APPL_DB 書き込み: なし
STATE_DB 書き込み: なし（PORT_COUNTER_CAPABILITIES は SAI capability 由来で別途書かれる）
NotificationConsumer: なし（カウンタ配信に使用せず）
```
