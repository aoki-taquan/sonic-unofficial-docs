# APPL_DB FIXED_MIRROR_SESSION_TABLE — pub/sub mechanism (Phase G)

## Scope

Page: `docs/reference/config-db/appl-mirror.md` covers `APPL_DB FIXED_MIRROR_SESSION_TABLE`
written by P4RT. This file documents how the orchagent side subscribes to / receives
updates for that table.

## Subscription path

`FIXED_MIRROR_SESSION_TABLE` is **NOT** consumed via the conventional redis
`ConsumerStateTable` / keyspace-notification path that most `*Orch` (incl. `MirrorOrch`
for CONFIG_DB MIRROR_SESSION) use. P4RT tables are dispatched through a dedicated
**ZMQ** channel.

### Class hierarchy

- `P4Orch : public ZmqOrch` — single Orch instance that owns all P4RT table managers
  including `p4orch::MirrorSessionManager`.
  - file: `orchagent/p4orch/p4orch.h:46`
- Constructor wiring:
  - `P4Orch(swss::DBConnector* db, std::vector<std::string> tableNames, ZmqServer* zmqServer, ...)`
  - `: ZmqOrch(db, tableNames, zmqServer, /*orderedQueue=*/true, /*dbPersistence=*/false)`
  - file: `orchagent/p4orch/p4orch.cpp:36-43`
- Dispatcher entry point:
  - `void P4Orch::doTask(ConsumerBase &consumer)` — receives `KeyOpFieldsValuesTuple`
    batches from the ZMQ-backed ConsumerBase, validates `table_name == APP_P4RT_TABLE_NAME`,
    and routes each entry to the manager registered in `m_p4TableToManagerMap` keyed by
    `APP_P4RT_MIRROR_SESSION_TABLE_NAME` (= `"FIXED_MIRROR_SESSION_TABLE"`).
  - file: `orchagent/p4orch/p4orch.cpp:126-200`
- Manager registration:
  - `m_p4TableToManagerMap[APP_P4RT_MIRROR_SESSION_TABLE_NAME] = m_mirrorSessionManager.get();`
  - file: `orchagent/p4orch/p4orch.cpp:80`

### ZmqServer creation (publisher side endpoint)

- `m_p4OrchZmqServer = new swss::ZmqServer(m_p4OrchZmqServerEp, "", false, true);`
- `gP4Orch = new P4Orch(m_applDb, p4rt_tables, m_p4OrchZmqServer, vrf_orch, gCoppOrch);`
- file: `orchagent/orchdaemon.cpp:848-849`

### Why ZMQ (not redis ConsumerStateTable / keyspace notifications)

`ZmqOrch` is a transport variant where the producer (P4RT client) sends batches over a
ZMQ socket to the orchagent's `ZmqServer`. The orchagent enqueues them on a
`ConsumerBase`-compatible queue that `P4Orch::doTask` drains synchronously per swsscommon
Select loop iteration. This bypasses the redis SET / SUBSCRIBE pipeline used by
conventional `Consumer` / `ConsumerStateTable` consumers (e.g. `MirrorOrch` reading
CONFIG_DB `MIRROR_SESSION`). It still mirrors writes into APPL_DB through
`m_publisher = ResponsePublisher("APPL_DB", buffered=true, db_write_thread=true, zmqServer)`
so that downstream readers can observe state, but the *trigger* for orchagent processing
is the ZMQ frame, not a redis keyspace event.

### Response / status publication back to P4RT

- `MirrorSessionManager` uses `m_publisher->publish(APP_P4RT_TABLE_NAME, key, fvs, ...)`
  to send per-key status back over the same ZmqServer.
- files:
  - `orchagent/p4orch/mirror_session_manager.cpp:82`
  - `orchagent/p4orch/mirror_session_manager.cpp:111`

## Comparison: CONFIG_DB MIRROR_SESSION path (for contrast)

- `MirrorOrch : public Orch` — constructed from a `TableConnector(confDbConnector)` and
  uses the conventional Orch / ConsumerStateTable path (no ZMQ).
  - file: `orchagent/mirrororch.cpp:79-110`
- This is the path referenced from `docs/reference/config-db/mirror-session.md`, not
  from `appl-mirror.md`.

## Conclusion for `<!-- pubsub -->` block in appl-mirror.md

- Transport: **ZMQ (swss::ZmqServer / ZmqOrch)** — dedicated socket
  (`m_p4OrchZmqServerEp`), not redis keyspace.
- Orch class: `P4Orch` (subclass of `ZmqOrch`), single shared consumer for all P4RT
  tables.
- Manager: `p4orch::MirrorSessionManager`, dispatched by table name
  `FIXED_MIRROR_SESSION_TABLE` (constant `APP_P4RT_MIRROR_SESSION_TABLE_NAME`).
- Dispatch entry: `P4Orch::doTask(ConsumerBase&)`
  (`orchagent/p4orch/p4orch.cpp:126`).
- Status publication: `ResponsePublisher("APPL_DB", buffered=true, ..., zmqServer)`
  (`orchagent/p4orch/p4orch.cpp:41-42`).
- ConfigDB MirrorOrch (`mirrororch.cpp`) is a **separate** path and irrelevant to this
  table — confirmed by `MirrorOrch` constructor taking `confDbConnector` only.
