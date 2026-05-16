# state-flex-counter — Phase A: コード由来デフォルト調査メモ

## 対象ページ

`docs/reference/config-db/state-flex-counter.md`

## 調査対象ファイル

- `sonic-sairedis/syncd/FlexCounter.cpp`
- `sonic-sairedis/syncd/FlexCounter.h`
- `sonic-sairedis/syncd/FlexCounterManager.cpp`
- `sonic-swss/orchagent/flexcounterorch.cpp`
- `sonic-swss/orchagent/flexcounterorch.h`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-buildimage/files/build_templates/init_cfg.json.j2`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-flex_counter.yang`
- `sonic-utilities/counterpoll/main.py`
- `sonic-utilities/scripts/db_migrator.py`
- `sonic-swss-common/common/schema.h`

## FLEX_COUNTER_DB 概要

`schema.h` より: `FLEX_COUNTER_DB = 5`（CONFIG_DB=4, STATE_DB=6 とは別の独立 DB）

syncd の `Syncd.cpp` が `FLEX_COUNTER_DB` と `FLEX_COUNTER_GROUP_TABLE` を購読し、
orchagent の `FlexCounterOrch` が CONFIG_DB `FLEX_COUNTER_TABLE` を消費→ FLEX_COUNTER_DB へ転送する形。

COUNTERS_DB（DB 2）が SAI から収集した実カウンタの書き込み先。

## FlexCounter.cpp コンストラクタデフォルト

`FlexCounter::FlexCounter(...)` (line 3031-3051):

```cpp
m_readyToPoll(false),
m_pollInterval(0),
m_enable = false;
m_isDiscarded = false;
```

- `m_pollInterval = 0` → 起動直後はポーリングしない
- `m_enable = false` → `FLEX_COUNTER_STATUS = enable` が届くまで無効

## FlexCounter.cpp: setStatus() のデフォルト

```cpp
const auto &cit = statusMap.find(status);
if (cit == statusMap.cend())
{
    SWSS_LOG_WARN("Input value %s is not supported ...", status.c_str());
    return;
}
```

- `enable` / `disable` 以外の値は `SWSS_LOG_WARN` でスキップ→ `m_enable` は変更されない
- 未設定時は `m_enable = false`（ポーリングなし）

## portsorch.cpp ハードコード初期ポーリング間隔

`portsorch.cpp:87-93`:

```cpp
#define PORT_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS     1000
#define PORT_BUFFER_DROP_STAT_POLLING_INTERVAL_MS     60000
#define PORT_PHY_ATTR_FLEX_COUNTER_POLLING_INTERVAL_MS 10000
#define QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS   10000
#define QUEUE_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS   60000
#define PG_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS   60000
#define PG_DROP_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS   10000
```

これらが `FlexCounterManager` コンストラクタ呼び出し時に初期値として FLEX_COUNTER_DB に書き込まれる。
CONFIG_DB の `POLL_INTERVAL` フィールドで後から上書き可能。

## FlexCounterOrch: m_* フラグ初期値

`flexcounterorch.cpp:433-478` の各 `get*State()` メソッドは、対応する
`m_port_counter_enabled`, `m_queue_enabled`, ... を返す。

コンストラクタで明示初期化なし（デフォルト `false`）。
`FLEX_COUNTER_STATUS = enable` を受信するまで全グループ disabled 状態。

## init_cfg.json.j2 ビルド時デフォルト

`init_cfg.json.j2:24-58` より、以下グループが `FLEX_COUNTER_STATUS: enable` で初期化される:

| グループ | POLL_INTERVAL |
|---------|--------------|
| ACL | 10000 ms（明示） |
| PORT | なし（portsorch 側 1000ms） |
| PORT_PHY_ATTR | なし（portsorch 側 10000ms） |
| RIF | なし |
| QUEUE | なし（portsorch 側 10000ms） |
| PFCWD | なし |
| PG_WATERMARK | なし（portsorch 側 60000ms） |
| PG_DROP | なし（portsorch 側 10000ms） |
| QUEUE_WATERMARK | なし（portsorch 側 60000ms） |
| BUFFER_POOL_WATERMARK | なし |
| PORT_BUFFER_DROP | なし（portsorch 側 60000ms） |

## FLEX_COUNTER_GROUP_TABLE の STATS_MODE フィールド

`FlexCounter::setStatsMode()` が FLEX_COUNTER_DB の `STATS_MODE_FIELD` を処理:
- `STATS_MODE_READ`: カウンタを読み込むのみ（デフォルト）
- `STATS_MODE_READ_AND_CLEAR`: 読み取り後にクリア（watermark 系で使用）

`QUEUE_WATERMARK` と `PG_WATERMARK` グループは `STATS_MODE_READ_AND_CLEAR` で portsorch から設定される。

## FlexCounter.cpp ポーリング実行条件

`FlexCounter.cpp:3538`:
```cpp
if (m_enable && !allIdsEmpty() && (m_pollInterval > 0))
```

3 条件が全て true にならないとポーリングしない:
1. `m_enable = true` (`FLEX_COUNTER_STATUS = enable`)
2. `allIdsEmpty() = false`（COUNTER_ID_LIST が 1 件以上ある）
3. `m_pollInterval > 0`（polling interval が設定されている）

## WARM_RESTART との関係

`Syncd.cpp:5824`: `WarmRestartTable warmRestartTable("STATE_DB")` — syncd が warm-reboot 後の状態を STATE_DB に書き込む。
FLEX_COUNTER は warm-reboot 時に一定期間ポーリングを遅延する（`FLEX_COUNTER_DELAY_STATUS` フィールド）。

`db_migrator.py:801-824`:
- fast-reboot 前: `FLEX_COUNTER_DELAY_STATUS` を全エントリで `true` に強制上書き
- cross-branch upgrade 時: `FLEX_COUNTER_DELAY_STATUS` フィールドを削除する migration

## COUNTERS_DB（実カウンタ書き込み先）

syncd の `FlexCounter` は `m_dbCounters`（`COUNTERS_DB`）に SAI stats を書き込む。
`FLEX_COUNTER_DB:FLEX_COUNTER_TABLE|<group>|<oid>` が入力、
`COUNTERS_DB:COUNTERS:<oid>` が出力（実カウンタ値）。

## まとめ

STATE_DB には FLEX_COUNTER 専用の独立テーブルはない。
warm-reboot ステータスのみ `STATE_DB:WARM_RESTART_TABLE` 経由で管理される。
FLEX_COUNTER 専用 DB は `FLEX_COUNTER_DB`（DB 5）。
実カウンタ書き込み先は `COUNTERS_DB`（DB 2）。
