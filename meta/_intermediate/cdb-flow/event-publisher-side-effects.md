# event-publisher — Phase F side-effects 調査メモ

slug: event-publisher  
phase: F (side-effects)  
date: 2026-05-18  

## 対象

`init_cfg.json` `"events"` 設定を読み込む `eventd` (`sonic-buildimage/src/sonic-eventd/src/eventd.cpp`)
および `events_common` (`sonic-swss-common/common/events_common.cpp`) の副次 DB 書込みを調査。

## 調査結果

### COUNTERS_DB への書込 — 確認済み

- `stats_collector::start()` (`eventd.cpp:172`) が `DBConnector("COUNTERS_DB", ...)` を作成
- `swss::Table(m_counters_db.get(), COUNTERS_EVENTS_TABLE)` で `COUNTERS_EVENTS` テーブルを開く
- `run_writer()` スレッドが `m_updated` フラグを確認し 10ms ループで `m_stats_table->set(counter_keys[i], fv)` を呼ぶ (`eventd.cpp:198-221`)
- 書込みキー: `COUNTERS_EVENTS|published` / `COUNTERS_EVENTS|missed_to_cache` + 内部カウンタ
  - `counter_keys[]` = `{ COUNTERS_EVENTS_PUBLISHED, COUNTERS_EVENTS_MISSED_CACHE }` (`eventd.cpp:50-52`)
  - `COUNTERS_EVENTS_PUBLISHED = "published"` / `COUNTERS_EVENTS_MISSED_CACHE = "missed_to_cache"` (`schema.h:275,278`)

### CONFIG_DB / APPL_DB / STATE_DB / ASIC_DB — 書込なし

- `eventd.cpp` 全行確認。`CONFIG_DB` / `APPL_DB` / `STATE_DB` / `ASIC_DB` / `FLEX_COUNTER_DB` への書込みは 0 件。
- `init_cfg.json` はファイル読みのみ (`read_init_config()` in `events_common.cpp:38-72`)。

### ZMQ ハートビート副次作用

- `stats_collector::run_collector()` が `events_init_publisher("sonic-events-eventd")` でハートビートパブリッシャーを作成
- `event_publish(pub_handle, "heartbeat")` でハートビートを ZMQ XPUB (:5571) に配信 (`eventd.cpp:291-296`)
- DB への直接書込みではなく ZMQ メッセージブロードキャスト

## evidence

- `eventd.cpp` L172-225 (`stats_collector::start`, `run_writer`)
- `eventd.cpp` L230-311 (`run_collector`, heartbeat publish)
- `eventd.cpp` L46-52 (定数定義: `EVENTD_PUBLISHER_SOURCE`, `EVENTD_HEARTBEAT_TAG`, `counter_keys`)
- `schema.h` L266,275,278 (`COUNTERS_EVENTS_TABLE`, `COUNTERS_EVENTS_PUBLISHED`, `COUNTERS_EVENTS_MISSED_CACHE`)
