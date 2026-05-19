# VXLAN_FDB_TABLE — 通信メカニズム (Phase G) 解析メモ

対象: `APP_DB` の `VXLAN_FDB_TABLE` テーブル。
ソース: `sonic-swss/fdbsyncd/fdbsync.h`, `fdbsync.cpp`, `sonic-swss/orchagent/fdborch.cpp`, `orchdaemon.cpp`, `sonic-swss/orchagent/orch.cpp`。

## 1. 書き込み側 (fdbsyncd) — ProducerStateTable

`fdbsyncd` の `FdbSync` クラスが `APP_DB` に `ProducerStateTable` 経由で書き込む。

```cpp
// fdbsync.h:88
ProducerStateTable m_fdbTable;

// fdbsync.cpp:24-25
FdbSync::FdbSync(RedisPipeline *pipelineAppDB, ...) :
    m_fdbTable(pipelineAppDB, APP_VXLAN_FDB_TABLE_NAME),
```

`m_fdbTable.set(key, fvVector)` (`fdbsync.cpp:676`) が呼ばれると、Redis パイプライン経由で以下の 2 操作がアトミックに実行される:

1. `HSET APPL_DB:VXLAN_FDB_TABLE|<key>` — フィールド値を書き込む
2. `PUBLISH VXLAN_FDB_TABLE_CHANNEL@0 <key>` — orchagent の ConsumerStateTable にイベントを通知

削除時は `m_fdbTable.del(key)` (`fdbsync.cpp:645`) で `DEL` + `PUBLISH` が発行される。

### warm-restart 中のバッファリング

warm-restart タイマー (120 秒) 中は `m_fdbTable` への直接書き込みを抑制し、`AppRestartAssist::insertToMap()` でメモリキャッシュに蓄積する (`fdbsync.cpp:641,672`)。reconcile フェーズ完了後に差分のみを `ProducerStateTable` 経由で一括フラッシュする。

## 2. 読み取り側 (orchagent/FdbOrch) — ConsumerStateTable

`FdbOrch` は `Orch(applDbConnector, appFdbTables)` 基底コンストラクタ経由で `addConsumer()` を呼ぶ (`fdborch.cpp:29`)。`applDbConnector` は APP_DB (dbId=0) であり `CONFIG_DB / STATE_DB` ではないため、`Orch::addConsumer()` (`orch.cpp:1186-1196`) は **ConsumerStateTable** ブランチを選択する:

```cpp
// orch.cpp:1193-1195
else
{
    addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
}
```

| パラメータ | 値 | 根拠 |
|-----------|-----|------|
| テーブル名 | `APP_VXLAN_FDB_TABLE_NAME` = `"VXLAN_FDB_TABLE"` | `orchdaemon.cpp:228` |
| 優先度 | `FdbOrch::fdborch_pri` = `20` | `fdborch.cpp:25` |
| バッチサイズ | `gBatchSize` (デフォルト `0` → 実効値 30000) | `orch.cpp:17,913` |
| SELECT_TIMEOUT | 1000 ms | `orchdaemon.cpp:23` |
| 購読チャネル | `VXLAN_FDB_TABLE_CHANNEL@0` | `table.h:85,94` |

orchagent のメインループは `m_select->select(&s, SELECT_TIMEOUT)` で `1000ms` タイムアウト付きブロッキング待機し (`orchdaemon.cpp:959`)、`VXLAN_FDB_TABLE_CHANNEL@0` に PUBLISH が来ると即座に `FdbOrch::doTask(Consumer&)` が呼び出される。

## 3. ASIC_DB 逆方向通知 — FDB_NOTIFICATIONS

FdbOrch は SAI から ASIC 上の FDB 学習イベントも受け取る。コンストラクタで `NotificationConsumer` を ASIC_DB の `NOTIFICATIONS` チャネルに登録し、`"FDB_NOTIFICATIONS"` エグゼキュータとして処理する:

```cpp
// fdborch.cpp:46-49
m_notificationsDb = make_shared<DBConnector>("ASIC_DB", 0);
m_fdbNotificationConsumer = new swss::NotificationConsumer(m_notificationsDb.get(), "NOTIFICATIONS");
auto fdbNotifier = new Notifier(m_fdbNotificationConsumer, this, "FDB_NOTIFICATIONS");
Orch::addExecutor(fdbNotifier);
```

このパスはローカル MAC 学習・エージング通知であり `VXLAN_FDB_TABLE` への書き込みとは逆方向（ASIC → orchagent）である。

## 4. FLUSHFDBREQUEST 通知 — NotificationConsumer

FdbOrch は `app flush` コマンド受信用に APP_DB の `FLUSHFDBREQUEST` チャネルも購読する:

```cpp
// fdborch.cpp:41-43
m_flushNotificationsConsumer = new NotificationConsumer(applDbConnector, "FLUSHFDBREQUEST");
auto flushNotifier = new Notifier(m_flushNotificationsConsumer, this, "FLUSHFDBREQUEST");
Orch::addExecutor(flushNotifier);
```

## 5. 全 Producer/Consumer ペア

| 区間 | 方向 | API | チャネル / テーブル | 根拠 |
|------|-----|-----|------------------|------|
| fdbsyncd → APP_DB | 書き込み | `ProducerStateTable` | `VXLAN_FDB_TABLE_CHANNEL@0` | `fdbsync.h:88, fdbsync.cpp:25,645,676` |
| APP_DB → orchagent | 読み取り | `ConsumerStateTable` | `VXLAN_FDB_TABLE_CHANNEL@0` | `orchdaemon.cpp:228, orch.cpp:1194` |
| ASIC_DB → orchagent | 逆通知 | `NotificationConsumer` | `NOTIFICATIONS` (ASIC_DB) | `fdborch.cpp:46-49` |
| CLI → orchagent | フラッシュ指示 | `NotificationConsumer` | `FLUSHFDBREQUEST` (APP_DB) | `fdborch.cpp:41-43` |

## 6. 参考行番号

- `sonic-swss/fdbsyncd/fdbsync.h:88-90`: `ProducerStateTable m_fdbTable` 宣言
- `sonic-swss/fdbsyncd/fdbsync.cpp:24-34`: FdbSync コンストラクタ — `pipelineAppDB` / `APP_VXLAN_FDB_TABLE_NAME` 登録
- `sonic-swss/fdbsyncd/fdbsync.cpp:641,672`: warm-restart 中の `insertToMap()` vs 通常の `m_fdbTable.set()`
- `sonic-swss/fdbsyncd/fdbsync.cpp:645`: `m_fdbTable.del(key)` — DEL 書き込み
- `sonic-swss/orchagent/fdborch.cpp:25`: `fdborch_pri = 20`
- `sonic-swss/orchagent/fdborch.cpp:27-49`: FdbOrch コンストラクタ
- `sonic-swss/orchagent/orchdaemon.cpp:227-229`: `app_fdb_tables` 定義 — `APP_VXLAN_FDB_TABLE_NAME` 含む
- `sonic-swss/orchagent/orchdaemon.cpp:23,959`: `SELECT_TIMEOUT = 1000`, メインループ
- `sonic-swss/orchagent/orch.cpp:17,913,1186-1196`: `gBatchSize`, `addConsumer()` 分岐ロジック
- `sonic-swss-common/common/table.h:85,94`: `getChannelName()` — チャネル名生成ロジック
