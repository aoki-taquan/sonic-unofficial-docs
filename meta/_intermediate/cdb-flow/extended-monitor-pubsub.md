# extended-monitor — pubsub 調査メモ

## 対象ページ
`docs/reference/config-db/extended-monitor.md`

## 概要
extended-monitor は CONFIG_DB テーブルではなくファイルベース設定 (`/etc/eventd.json`, `/etc/evprofile/default.json`) を扱う。
そのため Redis keyspace 通知の購読機構を持たない。代わりに eventd 自体が ZMQ ブローカとして動作する。

## 通信メカニズムの特性

- `eventd` は起動時にファイルを直接読み込む（SubscriberStateTable / ConsumerStateTable なし）
- ZMQ XSUB/XPUB proxy が全コンテナ間のイベント配信を担う
- pmon が EVENT_DB の ALARM_STATS を購読してシステム LED を制御する
- telemetry (gnmi_server) が ZMQ REQ/REP でキャッシュ制御コマンドを送る

## ソース参照
- `eventd.cpp:656-704` — run_eventd_service() 起動シーケンス
- `eventd.cpp:172-225` — stats_collector::start()
- `eventd.h:43` — HEARTBEAT_INTERVAL_SECS
- HLD section 3.1.2, 3.1.3, 3.1.8
