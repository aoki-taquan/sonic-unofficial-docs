# extended-monitor — Phase C: 暗黙参照 (cross-table refs)

調査日: 2026-05-18
対象: eventd が読み書きする関連 DB・ファイル

## 調査対象ソース

- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp` — `stats_collector::run_writer()`, `run_eventd_service()`
- `sonic-buildimage/src/sonic-eventd/src/eventd.h` — `EVENTS_STATS_FIELD_NAME`, `STATS_HEARTBEAT_MIN`
- `sonic-swss-common/common/schema.h` — `COUNTERS_EVENTS_TABLE`, `COUNTERS_EVENTS_PUBLISHED`, `COUNTERS_EVENTS_MISSED_CACHE`, `EVENT_DB`
- `sonic-swss-common/common/events_common.h` — `INIT_CFG_PATH`, `XSUB_END_KEY`, `XPUB_END_KEY`, `CAPTURE_END_KEY`, `CACHE_MAX_CNT`
- `sonic-buildimage/dockers/docker-eventd/supervisord.conf`
- `SONiC/doc/event-alarm-framework/event-alarm-framework.md` — section 3.1.2, 3.1.3, 3.1.8

---

## 1. ファイル参照

| ファイルパス | 読み/書き | タイミング | 内容 |
|------------|---------|-----------|------|
| `/etc/sonic/init_cfg.json` | 読み | 起動時 1 回 | ZMQ エンドポイント (`xsub_path`, `xpub_path`, `capture_path`) と `cache_max_cnt` を取得。不在時はデフォルト値にフォールバック |
| `/etc/evprofile/default.json` | 読み | 起動時 1 回 | イベントプロファイルを読み込み `static_event_map` を構築 |
| `/etc/eventd.json` | 読み (HLD 設計) | 起動時 (未確認) | EVENT テーブル保持上限 (`no-of-records` / `no-of-days`) |

## 2. Redis DB 参照

| DB | テーブル | 読み/書き | 根拠 |
|----|---------|---------|------|
| `COUNTERS_DB` | `COUNTERS_EVENTS` | 書き | stats_collector が `published` と `missed_to_cache` を定期書き込み (`eventd.cpp:186-210`) |
| `EVENT_DB` (index 19) | `EVENT` / `ALARM` | 書き | event consumer が受信イベントを EVENT テーブルへ追記 (HLD section 3.1.2) |
| `EVENT_DB` (index 19) | `EVENT_STATS` / `ALARM_STATS` | 書き | severity 別カウンタを更新 |
| `EVENT_DB` (index 19) | `ALARM_STATS` | 読み (pmon) | pmon が購読してシステム LED 制御 (HLD section 3.1.3) |

## 3. ZMQ エンドポイント参照

| エンドポイント | キー | デフォルト | 役割 |
|--------------|-----|---------|------|
| XSUB | `xsub_path` | `tcp://127.0.0.1:5570` | event producer が publish する入口 |
| XPUB | `xpub_path` | `tcp://127.0.0.1:5571` | subscriber が受信する出口 |
| capture PUB | `capture_path` | `tcp://127.0.0.1:5573` | capture_service がキャッシュする専用チャネル |

## 4. 暗黙的なコンポーネント依存

- **telemetry (gnmi_server)**: `EVENT_CACHE_INIT` → `EVENT_CACHE_START` → `EVENT_CACHE_STOP` → `EVENT_CACHE_READ` シーケンスを eventd に送信。telemetry 起動前はキャッシュ drain 不可
- **rsyslogd**: supervisord で `dependent_startup_wait_for=start:exited` により eventd は rsyslogd + start.sh 完了後に起動
- **pmon**: ALARM_STATS を購読して LED 制御 (Critical/Major → Red、Minor/Warning → Amber、なし → Green)

## 5. COUNTERS_EVENTS テーブル詳細

```
COUNTERS_EVENTS|published      → {value: <uint64>}  # 発行済みイベント総数
COUNTERS_EVENTS|missed_to_cache → {value: <uint64>}  # キャッシュ溢れによる欠損数
```

`schema.h:266` で `COUNTERS_EVENTS_TABLE = "COUNTERS_EVENTS"` と定義。
`schema.h:275,278` で `COUNTERS_EVENTS_PUBLISHED = "published"`, `COUNTERS_EVENTS_MISSED_CACHE = "missed_to_cache"` と定義。
`eventd.h:23` で `EVENTS_STATS_FIELD_NAME = "value"` と定義。
