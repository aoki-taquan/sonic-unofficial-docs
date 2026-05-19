# ERSPAN pubsub phase research (Phase G)

## 調査対象
- `sonic-swss/orchagent/mirrororch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/orch.cpp`
- `sonic-swss/orchagent/aclorch.cpp`

## CONFIG_DB 購読方式

`MirrorOrch` は `Orch` 基底クラスの `addConsumer()` (orch.cpp:1186-1190) を通じて
CONFIG_DB の `MIRROR_SESSION` テーブルを購読する。

```cpp
// orch.cpp:1186-1190
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    addExecutor(new Consumer(new SubscriberStateTable(db, tableName, ..., pri), this, tableName));
}
```

内部では `SubscriberStateTable` が Redis keyspace notification を PSUBSCRIBE する:

```
PSUBSCRIBE __keyspace@4__:MIRROR_SESSION|*
```

書き込み側が `ProducerStateTable` の場合は `MIRROR_SESSION_CHANNEL@4` への PUBLISH も
同時に行われるが、MirrorOrch は PSUBSCRIBE 経由でいずれの書き込み元も受信できる。

## orchdaemon select ループ

orchdaemon.cpp:959 の主ループ:
```cpp
ret = m_select->select(&s, SELECT_TIMEOUT);  // SELECT_TIMEOUT = 1000ms
```
イベント到着 → `doTask(Consumer&)` 呼び出し (mirrororch.cpp:1566)

## doTask 内処理フロー

```
CONFIG_DB MIRROR_SESSION に SET/DEL
  → Redis: __keyspace@4__:MIRROR_SESSION|* に pmessage 発火
  → SubscriberStateTable::readData() が受信
  → orchdaemon select loop (1000ms タイムアウト)
  → MirrorOrch::doTask(Consumer&) 呼び出し
      ├─ gPortsOrch->allPortsReady() が false → 即 return (全ポート待ち)
      ├─ SET → createEntry() → m_routeOrch->attach(this, dst_ip)
      │    └─ RouteOrch callback → updateNextHop() → activateSession()
      │         → sai_mirror_api->create_mirror_session()
      │         → setSessionState() → STATE_DB MIRROR_SESSION_TABLE.set()
      │         → notify(SUBJECT_TYPE_MIRROR_SESSION_CHANGE, ...)
      └─ DEL → deleteEntry() → deactivateSession()
               → removeSessionState() → STATE_DB MIRROR_SESSION_TABLE.del()
               → notify(SUBJECT_TYPE_MIRROR_SESSION_CHANGE, ...)
```

## 内部 Observer 通知 (Redis 非介在)

`MirrorOrch::activateSession()` (mirrororch.cpp:1096) と
`MirrorOrch::deactivateSession()` (mirrororch.cpp:1111) は
`Subject::notify(SUBJECT_TYPE_MIRROR_SESSION_CHANGE, ...)` を呼ぶ。

`AclOrch` が `m_mirrorOrch->attach(this)` (aclorch.cpp:3720) で登録しており、
セッション変化時に mirror OID を即座に更新する。**これは Redis pub/sub ではなく
C++ オブジェクト内のコールバック**であり、State_DB への書き込みは伴わない。

## STATE_DB への書き込み方式

`MirrorOrch` は STATE_DB に対して `Table::set()` / `Table::del()` を直接使用する。
`ProducerStateTable` を経由しないため、STATE_DB 書き込みによる PUBLISH は orchagent
内部で処理される (syncd 経由ではなく、State_DB テーブルに直接書き込む)。

STATE_DB MIRROR_SESSION_TABLE チャンネルへの通知は `Table::set()` が
`__keyspace@6__:MIRROR_SESSION_TABLE|<name>` へ pmessage を発火するが、
このチャンネルを購読する consumer は存在しない（show mirror_session は直接 HGETALL）。

## retry 動作

`task_need_retry` (policer 未定義時) → `it++` で次回 select イベントループで再試行。
明示的な sleep/timer なし。select timeout 1000ms ごとに doTask が再呼び出しされる。
