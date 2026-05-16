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

---

## G-6. orchagent 起動時一括読み込み → ASIC_DB SAI switch 操作

`SwitchOrch` / `orchagent` は `DEVICE_METADATA` を **subscribe しない**。起動時に `hget` で一括取得し SAI API 経由で ASIC_DB に反映する。

### 起動時読み込みフィールドと SAI 変換

| フィールド | 読み込み関数 | SAI 属性 / グローバル変数 | evidence |
|---|---|---|---|
| `switch_type` | `getCfgSwitchType()` | `SAI_SWITCH_ATTR_TYPE` (voq→`VOQ`, fabric→`FABRIC`) | `main.cpp:242-276` |
| `subtype` | `getCfgSwitchType()` | `gMySwitchSubType` (SmartSwitch 判定) | `main.cpp:269` |
| `switch_id` (VOQ) | `getSystemPortConfigList()` | `SAI_SWITCH_ATTR_SWITCH_ID` | `main.cpp:305-313` |
| `max_cores` (VOQ) | `getSystemPortConfigList()` | `SAI_SWITCH_ATTR_MAX_SYSTEM_CORES` | `main.cpp:321-335` |
| `hostname` (VOQ) | `getSystemPortConfigList()` | `gMyHostName` | `main.cpp:337-349` |
| `asic_name` (VOQ) | `getSystemPortConfigList()` | `gMyAsicName` | `main.cpp:351-363` |
| `switch_id` (fabric) | 直接 `hget` | `SAI_SWITCH_ATTR_SWITCH_ID` | `main.cpp:746-769` |

### SAI create_switch 呼び出しフロー

```
DEVICE_METADATA|localhost.switch_type (hget)
  → getCfgSwitchType() → gMySwitchType / gMySwitchSubType
  → attrs[] に SAI_SWITCH_ATTR_TYPE / SAI_SWITCH_ATTR_SWITCH_ID / SAI_SWITCH_ATTR_MAX_SYSTEM_CORES 等を追加
  → sai_switch_api->create_switch(gSwitchId, attrs)
  → sairedis → ASIC_DB (ASIC_STATE:SAI_OBJECT_TYPE_SWITCH)
```

### orchagent 内コンポーネント間共有経路 (gDirectory)

| 共有経路 | 方向 | 内容 |
|---|---|---|
| `gDirectory.set(gSwitchOrch)` → `gDirectory.get<SwitchOrch*>()` | SwitchOrch → 依存 Orch | PFC DLR init 状態、restart ready フラグ |
| `gDirectory.set(flexCounterOrch)` | FlexCounterOrch → 依存 Orch | `create_only_config_db_buffers` フラグ (DEVICE_METADATA 由来) |
| `gSwitchOrch->checkPfcDlrInitEnable()` | OrchDaemon → SwitchOrch | バッファ設定タイミング制御 |
| `gSwitchOrch->checkRestartReady()` | OrchDaemon ループ → SwitchOrch | warmboot/fastboot 再起動チェック |

> `SwitchOrch` 自体は `APP_SWITCH_TABLE`・`CFG_ASIC_SENSORS`・`CFG_SWITCH_HASH` 等を subscribe するが、`DEVICE_METADATA` を直接 subscribe しない。runtime の `DEVICE_METADATA` 変更を ASIC_DB に反映するには orchagent 再起動が必要。  
> evidence: `sonic-swss/orchagent/main.cpp:242,292,658,746`; `orchdaemon.cpp:213,500,766`; `switchorch.cpp:148-175,1493-1527`

---

## 注記

- **orchagent main (起動時のみ)**: `main.cpp:244,292,658,746` で `switch_type`、`subtype`、`switch_id`、`max_cores`、`hostname`、`asic_name` を `hget` で一括取得 (subscribe なし)。runtime 変更は反映されない
- **SwitchOrch と DEVICE_METADATA**: SwitchOrch は DEVICE_METADATA を subscribe しない。DEVICE_METADATA 値は orchagent 起動時の SAI create_switch attrs に組み込まれ ASIC_DB へ反映される
- **bgpcfgd の Directory 機構**: `SubscriberStateTable` イベントを `BGPDataBaseMgr.set_handler` → `Directory.put()` → `Directory.subscribe()` で登録されたサブコールバックへと伝播させる独自の pub-sub 実装。Redis native pub/sub とは別レイヤー
- **Python ConfigDBConnector**: `swsscommon.ConfigDBConnector.subscribe()` は内部で `swsscommon.SubscriberStateTable` を生成し Redis keyspace notification を購読する
- **fpmsyncd の条件付き addSelectable**: suppress-fib-pending を `enabled` にした場合のみ `NotificationConsumer` (APPL_STATE_DB のルート応答チャネル) が追加登録される動的な subscribe 拡張がある点が特徴的
