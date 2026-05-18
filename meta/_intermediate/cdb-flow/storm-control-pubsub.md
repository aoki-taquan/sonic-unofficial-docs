# PORT_STORM_CONTROL テーブル — Phase G 通信メカニズム スキャンノート

対象テーブル: `CONFIG_DB PORT_STORM_CONTROL`
Consumer: `PolicerOrch::doTask()` (`sonic-swss/orchagent/policerorch.cpp`)
スキャン範囲: `orchdaemon.cpp:395-402` + `policerorch.cpp:374-404` + swsscommon `Orch` 基底クラス

---

## 購読メカニズム

### orchdaemon での登録

`orchdaemon.cpp:395-402`:

```cpp
vector<TableConnector> policer_tables = {
    TableConnector(m_configDb, CFG_POLICER_TABLE_NAME),
    TableConnector(m_configDb, CFG_PORT_STORM_CONTROL_TABLE_NAME)
};
gPolicerOrch = new PolicerOrch(policer_tables, gPortsOrch);
```

`TableConnector` は `swsscommon::SubscriberStateTable` を内部生成し、CONFIG_DB の
`PORT_STORM_CONTROL` テーブルへの変更通知を Redis keyspace 通知 (PSUBSCRIBE) で受け取る。
`Orch` 基底クラスが `select()`/`read()` ループを駆動し、イベント発生時に `doTask()` を呼ぶ。

### 購読テーブル一覧

| 購読者 | 購読 DB | 購読テーブル | 購読 API |
|--------|---------|------------|---------|
| `PolicerOrch` (`gPolicerOrch`) | CONFIG_DB | `CFG_PORT_STORM_CONTROL_TABLE_NAME` (`PORT_STORM_CONTROL`) | `SubscriberStateTable` (swsscommon `TableConnector` 経由) |
| `PolicerOrch` (`gPolicerOrch`) | CONFIG_DB | `CFG_POLICER_TABLE_NAME` (`POLICER`) | 同上 |

### 通知フロー

```
CLI: config interface storm-control ...
  ↓ HSET "PORT_STORM_CONTROL|Ethernet0|broadcast" kbps 1000
Redis keyspace PUBLISH "__keyspace@4__:PORT_STORM_CONTROL|Ethernet0|broadcast" "hset"
  ↓ SubscriberStateTable が通知受信 (swsscommon select loop)
Orch::execute() → consumer.m_toSync にエントリを積む
  ↓
PolicerOrch::doTask(consumer)
  allPortsReady() チェック（false なら即 return）
  ↓
handlePortStormControlTable(tuple)
  ↓
SAI create_policer / set_port_attribute
```

### 通知ペイロードと再取得

`SubscriberStateTable` は通知を受け取ると `HGETALL "PORT_STORM_CONTROL|<key>"` でフィールド値を再取得する。
通知ペイロード自体にはフィールド値は含まれず、keyspace 通知のキー名と操作種別 (`hset`/`hdel`) のみ。

### 起動時スナップショット

`Orch` 基底クラスは SELECT ループ開始前に `getContent()` によって既存エントリをスナップショット取得し `m_toSync` に積む。
`allPortsReady()` が false の場合は `doTask()` が即 return するため、スナップショット分は ready 後に一括処理される。

### 購読者の一意性

`gPolicerOrch` 以外に `PORT_STORM_CONTROL` を直接購読するプロセスは **存在しない**。

| プロセス | `PORT_STORM_CONTROL` 購読 |
|---------|--------------------------|
| `orchagent` (PolicerOrch) | あり |
| `hostcfgd` | なし |
| `sonic-utilities` (CLI/show) | なし（CONFIG_DB を直接 HGET して表示） |

---

## 通知サマリ

| フロー | 方向 | 仕組み |
|--------|------|-------|
| CLI → CONFIG_DB | HSET/HDEL | `ConfigDBConnector.set_entry()` |
| CONFIG_DB → PolicerOrch | SubscriberStateTable (keyspace 通知) | `TableConnector` + Orch select ループ |
| PolicerOrch → ASIC_DB | SAI API (sai_policer_api / sai_port_api) | syncd 経由 |
