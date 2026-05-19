# Phase G 中間ファイル: VXLAN_FDB_TABLE 通信メカニズム

ソース:
- `sonic-swss/orchagent/fdborch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss-common/common/schema.h`

## 1. FdbOrch のコンストラクタ

`FdbOrch::FdbOrch()` (fdborch.cpp:27-49) は `Orch(applDbConnector, appFdbTables)` で基底クラスを初期化する。

`appFdbTables` は orchdaemon.cpp:226-230 で定義:

```cpp
vector<table_name_with_pri_t> app_fdb_tables = {
    { APP_FDB_TABLE_NAME,        FdbOrch::fdborch_pri},   // "FDB_TABLE"
    { APP_VXLAN_FDB_TABLE_NAME,  FdbOrch::fdborch_pri},   // "VXLAN_FDB_TABLE"
    { APP_MCLAG_FDB_TABLE_NAME,  FdbOrch::fdborch_pri}    // "MCLAG_FDB_TABLE"
};
```

優先度: `FdbOrch::fdborch_pri = 20` (fdborch.cpp:25)

## 2. Orch::addConsumer() の DB 種別分岐

`Orch(applDbConnector, appFdbTables)` → `addConsumer()` → DB が APPL_DB (`dbId == 0`) → **`ConsumerStateTable`** が選ばれる。

`ConsumerStateTable` は Redis の ProducerStateTable が書き込む `<TABLE_NAME>_KEY_SET` channel を購読する（keyspace 通知ではなく channel ベースの Pub/Sub）。

## 3. 追加 Executor

FdbOrch ctor は 2 つの追加 Notifier を登録する (fdborch.cpp:39-48):

### 3a. FLUSHFDBREQUEST (APPL_DB)

```cpp
m_flushNotificationsConsumer = new NotificationConsumer(applDbConnector, "FLUSHFDBREQUEST");
auto flushNotifier = new Notifier(m_flushNotificationsConsumer, this, "FLUSHFDBREQUEST");
Orch::addExecutor(flushNotifier);
```

`FLUSHFDBREQUEST` は FDB フラッシュ要求チャネル（APPL_DB）。
`doTask(NotificationConsumer&)` (fdborch.cpp:923) で処理される。

### 3b. FDB_NOTIFICATIONS (ASIC_DB)

```cpp
m_notificationsDb = make_shared<DBConnector>("ASIC_DB", 0);
m_fdbNotificationConsumer = new swss::NotificationConsumer(m_notificationsDb.get(), "NOTIFICATIONS");
auto fdbNotifier = new Notifier(m_fdbNotificationConsumer, this, "FDB_NOTIFICATIONS");
Orch::addExecutor(fdbNotifier);
```

ASIC_DB の `NOTIFICATIONS` channel で SAI からの FDB イベント通知 (`op == "fdb_event"`) を受信する。
`doTask(NotificationConsumer&)` (fdborch.cpp:1048) で処理される。
これは SAI が学習した MAC を orchagent が STATE_DB に反映するための逆方向フロー。

## 4. VXLAN_FDB_TABLE 専用の挙動

`FdbOrch::doTask(Consumer&)` (fdborch.cpp:707-919) では `table_name` で分岐する:

```cpp
// fdborch.cpp:719
if(table_name == APP_VXLAN_FDB_TABLE_NAME)
{
    origin = FDB_ORIGIN_VXLAN_ADVERTIZED;
```

APP_VXLAN_FDB_TABLE_NAME の場合のみ `origin = FDB_ORIGIN_VXLAN_ADVERTIZED` が付与される。
それ以外は `FDB_ORIGIN_PROVISIONED` (APP_FDB) または `FDB_ORIGIN_MCLAG_ADVERTIZED` (APP_MCLAG_FDB)。

## 5. バッチサイズ・TTL

- `POP_BATCH_SIZE`: `gBatchSize` (orchagent グローバル、既定 128)
- TTL: APPL_DB エントリは永続。TTL 未設定。
- key 区切り: `VXLAN_FDB_TABLE|<VlanName>:<MAC>` (セパレータ `|`)

## 証跡

- fdborch.cpp:25 — `const int FdbOrch::fdborch_pri = 20`
- fdborch.cpp:27-49 — `FdbOrch::FdbOrch()` コンストラクタ
- orchdaemon.cpp:226-235 — `app_fdb_tables` 定義と `FdbOrch` 生成
- fdborch.cpp:707-727 — `doTask(Consumer&)` の table_name 分岐
- schema.h:87 — `APP_VXLAN_FDB_TABLE_NAME = "VXLAN_FDB_TABLE"`
