# ALARM テーブル 副次 DB 書込 分析 (Phase F)

生成日: 2026-05-15

## スコープ注記

`docs/reference/config-db/alarm-table.md` は **EVENT_DB (DB index 6) の ALARM テーブル** を扱う。
SONiC Event/Alarm Framework において、ALARM テーブル自身への書き込みは「主たる書込」であって副次ではない。
本 Phase F では「ALARM 系処理に付随して、ALARM テーブル以外の DB / テーブルへ書かれる事象」を対象とする。

ソース確認範囲:

- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp` — eventd メインプロセス・stats_collector
- `sonic-buildimage/src/sonic-eventd/src/eventd.h` — クラス定義・定数
- `sonic-swss-common/common/schema.h` — テーブル名定数
- `sonic-buildimage/src/system-health/health_checker/` — タスク仕様で指定されたディレクトリ (後述: ALARM テーブル無関係)

---

## 1. COUNTERS_DB / `COUNTERS_EVENTS` (eventd stats_collector)

eventd プロセスは内部 `stats_collector` クラスを保持し、イベント / アラームのパブリッシュ統計を周期的に **COUNTERS_DB** へ書き込む。
ALARM テーブル更新トリガそのものではなく、`event_publish()` 経路全体 (ALARM 発生時も含む) に対する累計カウンタである。

| 操作 | 対象 DB / テーブル | キー | フィールド | 値 | 条件 |
|------|-----------------|------|-----------|-----|------|
| `m_stats_table->set(counter_keys[i], fv)` | COUNTERS_DB / `COUNTERS_EVENTS` | `counter_keys[i]` (例: `published`, `missed_internal`, `missed_to_cache`, `missed_by_slow_receiver`, `latency_in_ms`) | `value` | `to_string(m_lst_counters[i])` (uint64) | `stats_collector::run_writer()` が 10ms 周期で `m_updated` フラグを確認し、更新があれば書き込み |

コード証跡:

- `sonic-eventd/src/eventd.cpp:178` — `m_counters_db = make_shared<swss::DBConnector>("COUNTERS_DB", 0, false);`
- `sonic-eventd/src/eventd.cpp:186-187` — `m_stats_table = make_shared<swss::Table>(m_counters_db.get(), COUNTERS_EVENTS_TABLE);`
- `sonic-eventd/src/eventd.cpp:205-210` — `for (int i = 0; i < COUNTERS_EVENTS_TOTAL; ++i) { ... m_stats_table->set(counter_keys[i], fv); }`
- `sonic-eventd/src/eventd.h:23` — `#define EVENTS_STATS_FIELD_NAME "value"`
- `sonic-swss-common/common/schema.h:266` — `#define COUNTERS_EVENTS_TABLE "COUNTERS_EVENTS"`

備考:

- ALARM の RAISE/CLEAR/ACK 個別の副次書込ではなく、eventd の **publish パス全体** のサマリ統計。
- `RAISE_ALARM` action の event が `event_publish()` 経由で流れる際にこのカウンタが更新される (ALARM 固有のフィールドは未分離)。

---

## 2. STATE_DB への副次書込

ALARM テーブル処理 (eventd → ALARM テーブル更新) からの STATE_DB への副次書込は **`sonic-buildimage/src/sonic-eventd/src/`** 内のソースには検出されない。

確認内容:

- `grep -rn "STATE_DB" .cache/sonic-sources/sonic-buildimage/src/sonic-eventd/src/` → ヒット 0 件 (test 配下の DB 設定 JSON を除く)
- eventd は EVENT_DB (ALARM / EVENT / ALARM_STATS / EVENT_STATS) と COUNTERS_DB (`COUNTERS_EVENTS`) のみを扱う

**結論: ALARM テーブル処理に伴う STATE_DB への副次書込は「なし」**。

### タスク指定の `src/system-health/` について

タスク仕様は `sonic-buildimage/src/system-health/` を確認対象に挙げているが、当該ディレクトリのコード (`hardware_checker.py`, `sysmonitor.py` 他) は SONiC の **System Health Monitoring** サブシステムであり、STATE_DB の `FAN_INFO` / `PSU_INFO` / `ALL_SERVICE_STATUS` / `SYSTEM_READY` / `CHASSIS_INFO|chassis 1` (`led_status`) 等を扱う。
これは pmon の `LED` 連動・サービス起動監視であり、Event/Alarm Framework の **ALARM テーブル (EVENT_DB) とは別系統**である。

代表的に検出された STATE_DB 書込 (system-health 由来、ALARM テーブル非依存):

- `sysmonitor.py:142` — `state_db.set(state_db.STATE_DB, "SYSTEM_READY|SYSTEM_STATE", "Status", state)`
- `sysmonitor.py:306` — `state_db.hmset(state_db.STATE_DB, key, statusvalue)` (`ALL_SERVICE_STATUS|<service>`)
- `manager.py:77` — `chassis.set_status_led(...)` (`ALARM_STATS` の集計結果に依存しない独立 LED 経路)

これらは ALARM テーブルとは独立した System Health monitor 由来の書込であり、本 Phase F の副次書込対象には含めない。

---

## 3. EVENT_DB 内の付随テーブル (参考)

ALARM テーブルと同一 DB (EVENT_DB) 内の `EVENT` / `ALARM_STATS` / `EVENT_STATS` は HLD (Section 3.1.2, 3.1.7) において Alarm Consumer が同時更新すると規定されているが、現行の `sonic-buildimage/src/sonic-eventd/src/` では Alarm Consumer 本体の実装は未マージ (buildimage submodule 内の eventd は publisher / stats_collector / cache_service のみ)。
そのため、これらは「将来の主たる書込先」であり、副次ではない。本ページ上部の概要・関連テーブル表が既に網羅している。

---

## まとめ

| 副次書込先 | 有無 | 根拠 |
|-----------|-----|------|
| **COUNTERS_DB** (`COUNTERS_EVENTS`) | あり | `eventd.cpp:178-210` の `stats_collector` |
| **STATE_DB** | なし | eventd src 配下 grep 0 件 / system-health 書込は ALARM テーブル無関係 |
| FLEX_COUNTER_DB | なし | 該当コード未検出 |
| APPL_DB | なし | 該当コード未検出 |
| ASIC_DB | なし | 該当コード未検出 |
