# device-metadata pubsub (Phase G — 通信メカニズム / subscribe 経路)

生成日: 2026-05-15
対象: `DEVICE_METADATA|localhost` テーブル (CONFIG_DB)
手法: sonic-swss / sonic-buildimage / sonic-host-services ソース全行精読

---

## 概要

`DEVICE_METADATA` テーブルへの subscribe は **4 種類の低レベルメカニズム** で実装されている:

1. **`SubscriberStateTable` (C++ swss)** — Redis keyspace notification をポーリングする swss の基本購読クラス。`Select::addSelectable()` でイベントループに登録し、`pops()` でイベントキューを取り出す
2. **`ConsumerStateTable` 経由の `Orch` フレームワーク (C++ swss)** — `Orch(db, tableNames)` コンストラクタが各テーブル名に対して内部で `ConsumerStateTable` を生成し、`doTask(Consumer&)` にディスパッチする
3. **`ConfigDBConnector.subscribe()` (Python swsscommon)** — Python daemon が Redis keyspace 変更を購読するラッパー。swsscommon の `SubscriberStateTable` を内部で生成し、コールバック関数に変更イベントを渡す
4. **`Directory.subscribe()` (bgpcfgd 内部)** — bgpcfgd の `Directory` オブジェクトが `CONFIG_DB / DEVICE_METADATA` のパスを監視し、依存 Manager にコールバックを届ける

---

## Consumer 一覧

### G-1. fpmsyncd — `SubscriberStateTable` (直接)

| 項目 | 詳細 |
|------|------|
| デーモン | `docker-fpm-frr` 内 `fpmsyncd` プロセス |
| 購読 API | `SubscriberStateTable deviceMetadataTableSubscriber(&cfgDb, CFG_DEVICE_METADATA_TABLE_NAME)` |
| Select 登録 | `s.addSelectable(&deviceMetadataTableSubscriber)` (FPM 接続確立後に登録) |
| イベント取り出し | `deviceMetadataTableSubscriber.pops(keyOpFvsQueue)` |
| 監視フィールド | `suppress-fib-pending` のみ。key = `localhost`、op = `SET_COMMAND` のみ処理 |
| 効果 | `enabled` → `routeResponseChannel` (NotificationConsumer) を新規作成し `s.addSelectable()` で追加; `disabled` → `sync.markRoutesOffloaded(db)` を呼んだ後 `removeSelectable` して reset |
| evidence | `sonic-swss/fpmsyncd/fpmsyncd.cpp:82-83,145,252-315` |

### G-2. BufferMgr — `Orch` フレームワーク経由 ConsumerStateTable

| 項目 | 詳細 |
|------|------|
| デーモン | `docker-swss` 内 `buffermgrd` プロセス (traditional buffer model 時のみ起動) |
| 購読 API | `new BufferMgr(&cfgDb, &applDb, pg_lookup_file, cfg_buffer_tables)` — `cfg_buffer_tables` に `CFG_DEVICE_METADATA_TABLE_NAME` を含む |
| Select 登録 | `s.addSelectables(o->getSelectables())` でループ内一括登録 |
| コールバック | `BufferMgr::doTask(Consumer &consumer)` → `table_name == CFG_DEVICE_METADATA_TABLE_NAME` のとき `doBufferMetaTask(consumer)` |
| 監視フィールド | `buffer_model` |
| 効果 | `dynamic` → `dynamic_buffer_model = true` フラグを立て APPL_DB 書き込みをスキップ; それ以外 → APPL_DB への BUFFER_POOL/PROFILE 転写を継続 |
| evidence | `sonic-swss/cfgmgr/buffermgrd.cpp:200,216; cfgmgr/buffermgr.cpp:464-499` |

### G-3. FlexCounterOrch (orchagent) — `Orch` フレームワーク経由 ConsumerStateTable

| 項目 | 詳細 |
|------|------|
| デーモン | `docker-swss` 内 `orchagent` プロセス |
| 購読 API | `new FlexCounterOrch(m_configDb, flex_counter_tables)` — `flex_counter_tables` に `CFG_DEVICE_METADATA_TABLE_NAME` を含む (orchdaemon.cpp:621-626) |
| コールバック | `FlexCounterOrch::doTask(Consumer &consumer)` → `consumer.getTableName() == CFG_DEVICE_METADATA_TABLE_NAME` のとき `handleDeviceMetadataTable(consumer)` |
| 監視フィールド | `create_only_config_db_buffers` |
| 効果 | `m_createOnlyConfigDbBuffers` フラグ更新 → `getQueueConfigurations()` のカウンタ設定分岐を制御 |
| evidence | `sonic-swss/orchagent/orchdaemon.cpp:620-627; orchagent/flexcounterorch.cpp:106,149-152,488-521` |

### G-4. hostcfgd (DeviceMetaCfg) — `ConfigDBConnector.subscribe()` (Python)

| 項目 | 詳細 |
|------|------|
| デーモン | ホスト上の `hostcfgd` Python スクリプト |
| 購読 API | `self.config_db.subscribe(swsscommon.CFG_DEVICE_METADATA_TABLE_NAME, make_callback(self.device_metadata_handler))` |
| 内部実装 | `ConfigDBConnector.subscribe()` が内部で `SubscriberStateTable` を生成し `swsscommon.Select` に登録。変更発生時に `device_metadata_handler()` を呼ぶ |
| コールバック先 | `device_metadata_handler()` → `hostname_update()` / `apply_timezone_if_needed()` / `rsyslog_config()` に委譲 |
| 監視フィールド | `hostname`、`timezone`、`syslog_with_osversion`、`syslog_counter` |
| 効果 | hostname 変更 → `service hostname-config restart` + `monit reload`; timezone 変更 → `timedatectl set-timezone` + `systemctl restart rsyslog`; syslog 変更 → `rsyslog-config.sh` 再実行 |
| evidence | `sonic-host-services/scripts/hostcfgd:2492-2494,1485-1600` |

### G-5. BGPDataBaseMgr (bgpcfgd) — `SubscriberStateTable` (bgpcfgd Runner 経由)

| 項目 | 詳細 |
|------|------|
| デーモン | `docker-fpm-frr` 内 `bgpcfgd` プロセス |
| 購読 API | `BGPDataBaseMgr(common_objs, "CONFIG_DB", swsscommon.CFG_DEVICE_METADATA_TABLE_NAME)` として Runner に登録; `Runner.add_manager()` が `swsscommon.SubscriberStateTable(conn, table_name)` を生成し `swsscommon.Select.addSelectable()` で登録 |
| コールバック | `BGPDataBaseMgr.set_handler(key, data)` → `self.directory.put("CONFIG_DB", "DEVICE_METADATA", key, data)` — Directory オブジェクトにデータを格納し、依存 Manager のコールバックを発火 |
| 依存 Manager コールバック | |
| &emsp;• BgpPeerMgr | `directory.subscribe(["CONFIG_DB/DEVICE_METADATA/localhost/bgp_asn", "CONFIG_DB/DEVICE_METADATA/localhost/type", ...])` → `set_handler()` でピア設定を FRR に push |
| &emsp;• DeviceGlobalCfgMgr | `directory.subscribe(["CONFIG_DB/DEVICE_METADATA/localhost/type"])` → `handle_type_update()` で `self.switch_role` を更新し TSA/IDF isolation 判定に利用 |
| &emsp;• AsPathMgr | `set_handler()` で `t2_group_asns` フィールドを読み FRR AS-path set を更新 |
| &emsp;• AdvertiseRouteMgr | `directory.subscribe(["CONFIG_DB/DEVICE_METADATA/localhost/bgp_asn"])` → `on_bgp_asn_change()` で BGP route 広告設定を再構成 |
| 監視フィールド | `bgp_asn`、`type`、`t2_group_asns`、`frr_mgmt_framework_config`、`docker_routing_config_mode`、`bgp_router_id`、`suppress-fib-pending`、`bgp_adv_lo_prefix_as_128` |
| evidence | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py:75; runner.py:29,49-55; managers_db.py:4-24; managers_bgp.py:119-143; managers_device_global.py:33; managers_as_path.py; managers_advertise_rt.py:26` |

---

## フィールド × consumer マトリクス

| フィールド | fpmsyncd | BufferMgr | FlexCounterOrch | hostcfgd | bgpcfgd |
|---|:---:|:---:|:---:|:---:|:---:|
| `suppress-fib-pending` | ✓ | | | | ✓ |
| `buffer_model` | | ✓ | | | |
| `create_only_config_db_buffers` | | | ✓ | | |
| `hostname` | | | | ✓ | |
| `timezone` | | | | ✓ | |
| `syslog_with_osversion` / `syslog_counter` | | | | ✓ | |
| `bgp_asn` | | | | | ✓ |
| `type` | | | | | ✓ |
| `t2_group_asns` | | | | | ✓ |
| `bgp_router_id` | | | | | ✓ |
| `frr_mgmt_framework_config` | | | | | ✓ |
| `bgp_adv_lo_prefix_as_128` | | | | | ✓ |

---

## 注記

- **orchagent main (起動時のみ)**: `main.cpp:244,292,658` で `switch_type`、`subtype`、`switch_id` を `hget` で一度だけ取得 (subscribe なし)。runtime 変更は反映されない
- **bgpcfgd の Directory 機構**: `SubscriberStateTable` イベントを `BGPDataBaseMgr.set_handler` → `Directory.put()` → `Directory.subscribe()` で登録されたサブコールバックへと伝播させる独自の pub-sub 実装。Redis native pub/sub とは別レイヤー
- **Python ConfigDBConnector**: `swsscommon.ConfigDBConnector.subscribe()` は内部で `swsscommon.SubscriberStateTable` を生成し Redis keyspace notification を購読する
- **fpmsyncd の条件付き addSelectable**: suppress-fib-pending を `enabled` にした場合のみ `NotificationConsumer` (APPL_STATE_DB のルート応答チャネル) が追加登録される動的な subscribe 拡張がある点が特徴的
