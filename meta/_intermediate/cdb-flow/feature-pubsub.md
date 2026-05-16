# FEATURE — Phase G 通信メカニズム (Redis PUBSUB / keyspace notification)

対象ページ: `docs/reference/config-db/feature.md`
調査日: 2026-05-15
Evidence:
- `sonic-host-services/scripts/featured:600-692`
- `sonic-swss-common/common/subscriberstatetable.cpp:17-175`
- `sonic-buildimage/src/sonic-containercfgd/containercfgd/containercfgd.py:38-62`
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/common/dhcp_db_monitor.py:15-411`
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py:200-207`
- `sonic-utilities/scripts/route_check.py:720-729`

---

## 概要

`FEATURE` テーブルは主に **2 系統の購読メカニズム** で消費される。

| 購読者 | 方式 | Redis primitive |
|--------|------|-----------------|
| `featured` (`FeatureDaemon`) | **SubscriberStateTable** | PSUBSCRIBE (keyspace 通知) |
| `containercfgd` | **ConfigDBConnector.listen()** | PSUBSCRIBE (keyspace 通知) — SYSLOG_CONFIG_FEATURE 経由 |
| `dhcprelayd` (`DhcpServerFeatureStateChecker`) | **SubscriberStateTable** | PSUBSCRIBE (keyspace 通知) |
| `route_check.py` | **get_table (hgetall)** | 購読なし — 起動時一括読み取りのみ |

`ConsumerStateTable` (channel ベース PUBLISH/SUBSCRIBE) は FEATURE テーブルでは**使用しない**。

---

## 購読者 G-1: featured (FeatureDaemon)

### 初期化 (featured:600-648)

```
FeatureDaemon.__init__()
  └─ DBConnector(CFG_DB, 0)                    ← CONFIG_DB 接続
  └─ DBConnector(STATE_DB, 0)
  └─ DBConnector(APPL_DB, 0)
  └─ swsscommon.Select()                        ← 統合イベントループ
  └─ FeatureHandler(...)                        ← 実処理クラス初期化

FeatureDaemon.register_callbacks()
  └─ subscribe(cfg_db_conn, FEATURE_TBL,
               callback=feature_handler.handler,
               pri=HOSTCFGD_MAX_PRI=10)
       └─ SubscriberStateTable(cfg_db_conn, "FEATURE",
                               DEFAULT_POP_BATCH_SIZE, pri=10)
            ← 内部で PSUBSCRIBE "__keyspace@<dbId>__:FEATURE|*"
       └─ selector.addSelectable(subscriber)
       └─ subscriber_map[subscriber.getFd()] = (subscriber, "FEATURE")

  └─ subscribe(appl_db_conn, PORT_TBL,
               callback=feature_handler.port_listener,
               pri=HOSTCFGD_MAX_PRI-1=9)
       └─ SubscriberStateTable(appl_db_conn, "PORT", ...)
            ← delayed 機能の PortInitDone 待ち用
```

**PSUBSCRIBE パターン**: `__keyspace@<CONFIG_DB_ID>__:FEATURE|*`
(SubscriberStateTable.cpp:20-24 で `m_keyspace = "__keyspace@" + dbId + "__:" + tableName + "|*"` と組み立て)

### Select ループ (featured:654-678)

```
FeatureDaemon.start(init_time)
  while True:
    state, sel = selector.select(DEFAULT_SELECT_TIMEOUT=1000ms)

    if TIMEOUT:
      if elapsed > PORT_INIT_TIMEOUT_SEC(180s):
        feature_handler.handle_port_table_timeout()  ← delayed 強制起動
      continue

    if ERROR:
      continue

    fd = sel.getFd()
    subscriber, table = subscriber_map[fd]
    key, op, fvs = subscriber.pop()     ← SubscriberStateTable.pops() → HGETALL
    callback(table, key, op, dict(fvs)) ← feature_handler.handler(key, op, data)
```

### SubscriberStateTable.pops() の動作 (subscriberstatetable.cpp:95-165)

```
pops(vkco)
  for each keyspace_event in m_keyspace_event_buffer:
    pattern = message.pattern   ← "__keyspace@<dbId>__:FEATURE|*"
    msg = message.channel       ← "set" / "hset" / "del" 等の操作名
    key = message.message       ← "bgp" 等の feature 名 ("FEATURE|bgp" の "|bgp" 部分)
    if msg == "del":
      op = DEL_COMMAND
      fvs = {}
    else:
      op = SET_COMMAND
      fvs = HGETALL("FEATURE|" + key)  ← 本体ハッシュから全フィールド取得
    vkco.append((key, op, fvs))
```

- keyspace 通知ペイロードは操作名 (`hset`/`set`/`del` 等) のみ。フィールド値は HGETALL で別途取得する。
- **競合**: keyspace 通知受信 → HGETALL の間に別プロセスが書き込んだ場合、最新値が読まれる (lost-update 耐性あり)。

### コールバック (feature_handler.handler) の処理フロー

```
handler(key=feature_name, op="SET"/"DEL", data={...})
  └─ Feature(feature_name, data, device_config)  ← Feature オブジェクト生成
  └─ update_feature_state(feature)               ← state フィールド処理
       └─ auto_restart → update_systemd_config()
       └─ state → enable_feature() or disable_feature()
       └─ 失敗時 → set_feature_state(FAILED) + resync_feature_state()
  └─ sync_feature_scope(feature)                 ← scope フィールド処理
```

---

## 購読者 G-2: containercfgd (コンテナ内)

`containercfgd` は **SYSLOG_CONFIG_FEATURE** テーブルを購読し、そのハンドラ内で FEATURE テーブルの `support_syslog_rate_limit` フィールドを間接的に参照する形になっている。FEATURE テーブルを直接購読はしない。

```
ContainerConfigDaemon.run()
  └─ ConfigDBConnector.connect()
  └─ for table_name, handler in handlers.items():
       config_db.subscribe(table_name, handler.handle_config)
         ← SYSLOG_CONFIG_FEATURE テーブルのみ購読
  └─ config_db.listen(init_data_handler=init_data_handler)
       ← 内部で PSUBSCRIBE "__keyspace@<dbId>__:SYSLOG_CONFIG_FEATURE|*"
```

**FEATURE テーブルは `init_data_handler` 経由でも直接処理されない**。
containercfgd は自身のサービス名 (`service_name`) に対応する `SYSLOG_CONFIG_FEATURE` エントリを処理する。

---

## 購読者 G-3: dhcprelayd (DhcpServerFeatureStateChecker)

```
DhcpServerFeatureStateChecker(sel, db)
  └─ table_name = "FEATURE"
  └─ ConfigDbEventChecker.enable()
       └─ SubscriberStateTable(db, "FEATURE")
            ← PSUBSCRIBE "__keyspace@<CONFIG_DB_ID>__:FEATURE|*"
       └─ sel.addSelectable(subscriber_state_table)

checker._process_check(key, op, entry, dhcp_server_feature_enabled)
  ← key == "dhcp_server" のときのみ処理
  ← "state" フィールドの enabled/disabled 変化を検出
  ← 変化あり → DhcpRelayd がリレープロセス制御を切り替え
```

- dhcprelayd は `dhcp_server` キーの `state` フィールドのみを監視する。他の feature は無視。
- 初期状態は `_is_dhcp_server_enabled()` が `config_db.get_config_db_table("FEATURE")` (HGETALL) で同期読み取り。

---

## 購読者 G-4: route_check.py (非購読・スナップショット)

```
is_feature_bgp_enabled(namespace)
  └─ cfg_db.get_table("FEATURE")   ← HGETALL スキャン（全エントリ）
  └─ feature_table['bgp']['state'] == 'enabled' を確認
```

Subscribe は行わず、実行時に一度だけ CONFIG_DB から読み取るスナップショット方式。常駐デーモンではなく cron / systemd サービス呼び出し。

---

## フィールド × Consumer 購読マトリクス

| フィールド | featured | containercfgd | dhcprelayd | route_check |
|---|:---:|:---:|:---:|:---:|
| `state` | ✓ (全 feature) | ✗ | ✓ (dhcp_server のみ) | ✓ (bgp のみ) |
| `auto_restart` | ✓ | ✗ | ✗ | ✗ |
| `delayed` | ✓ | ✗ | ✗ | ✗ |
| `has_global_scope` | ✓ | ✗ | ✗ | ✗ |
| `has_per_asic_scope` | ✓ | ✗ | ✗ | ✗ |
| `has_per_dpu_scope` | ✓ | ✗ | ✗ | ✗ |
| `set_owner` | ✓ | ✗ | ✗ | ✗ |
| `check_up_status` | ✓ | ✗ | ✗ | ✗ |
| `support_syslog_rate_limit` | ✓ | ✗ (間接) | ✗ | ✗ |

---

## 重要な特性

| 特性 | 内容 |
|------|------|
| 通知種別 | Redis PSUBSCRIBE (keyspace notification) |
| PSUBSCRIBE パターン | `__keyspace@<dbId>__:FEATURE\|*` |
| keyspace イベント | `hset` / `set` / `del` 等の Redis 操作名 |
| フィールド値取得 | 通知後に HGETALL で別途取得 |
| SWSS abstraction | `swss::SubscriberStateTable` + `swss::Select` (Python: `swsscommon.SubscriberStateTable`) |
| ConsumerStateTable | **不使用** (FEATURE は CONFIG_DB 直接書き込みのため ProducerStateTable 経路なし) |
| NotificationConsumer | **不使用** |
| TTL / keyevent expire | **不使用** |
| タイムアウト | 1000ms (`DEFAULT_SELECT_TIMEOUT`, featured:23) |
| PORT_TBL 同時購読 | `featured` は `APPL_DB` の `PORT` テーブルも同一 Selector に登録し `delayed` 機能の PortInitDone 待ちに使用 |
| 起動時スナップショット | `render_all_feature_states()` が `config_db.get_table(FEATURE_TBL)` で全エントリを一括取得後、Subscribe ループ開始 |
| 優先度 | FEATURE 購読 pri=10 (`HOSTCFGD_MAX_PRI`)、PORT 購読 pri=9 |
| batch サイズ | `DEFAULT_POP_BATCH_SIZE` (swsscommon デフォルト) |

---

## シーケンス図 (テキスト形式)

```
CLI / init_cfg
  │
  │  HSET "FEATURE|bgp" state enabled   (CONFIG_DB)
  │
  ▼
Redis CONFIG_DB
  │
  │  keyspace PUBLISH "__keyspace@<dbId>__:FEATURE|bgp"  "hset"
  │
  ├─► featured (SubscriberStateTable.pops)
  │     └─ HGETALL "FEATURE|bgp"
  │     └─ handler(key="bgp", op=SET, data={state:enabled,...})
  │          └─ enable_feature(bgp)
  │          └─ systemctl start bgp.service
  │          └─ STATE_DB HSET "FEATURE|bgp" state enabled
  │
  └─► dhcprelayd (DhcpServerFeatureStateChecker.pops)
        └─ key == "bgp" → skip (dhcp_server のみ処理)
```

---

## 参照コード

| ファイル | 行 | 内容 |
|---|---|---|
| `sonic-host-services/scripts/featured` | 20 | `FEATURE_TBL = swsscommon.CFG_FEATURE_TABLE_NAME` |
| `sonic-host-services/scripts/featured` | 22-23 | `HOSTCFGD_MAX_PRI = 10`, `DEFAULT_SELECT_TIMEOUT = 1000` |
| `sonic-host-services/scripts/featured` | 600-648 | `FeatureDaemon.__init__` + `register_callbacks` |
| `sonic-host-services/scripts/featured` | 626-636 | `subscribe()` — SubscriberStateTable 生成 + Selector 登録 |
| `sonic-host-services/scripts/featured` | 644-648 | FEATURE_TBL + PORT_TBL の subscribe 呼び出し |
| `sonic-host-services/scripts/featured` | 654-678 | `start()` — メインイベントループ |
| `sonic-swss-common/common/subscriberstatetable.cpp` | 17-24 | ctor — PSUBSCRIBE パターン組み立て |
| `sonic-swss-common/common/subscriberstatetable.cpp` | 95-165 | `pops()` — keyspace イベント → HGETALL |
| `sonic-buildimage/src/sonic-containercfgd/containercfgd/containercfgd.py` | 44-62 | `run()` — SYSLOG_CONFIG_FEATURE のみ subscribe |
| `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/common/dhcp_db_monitor.py` | 388-411 | `DhcpServerFeatureStateChecker` |
| `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py` | 200-207 | `_is_dhcp_server_enabled()` |
| `sonic-utilities/scripts/route_check.py` | 720-729 | `is_feature_bgp_enabled()` |
