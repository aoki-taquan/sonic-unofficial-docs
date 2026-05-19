# gnmi-state cross-refs (Phase C) — intermediate research notes

## Page
`docs/reference/config-db/gnmi-state.md` — TELEMETRY_CONNECTIONS (STATE_DB)

## Source examined
- `sonic-net/sonic-gnmi` @ eb635b7679b260c3fd0786a6d0734fc8e82c9a22
  - `gnmi_server/connection_manager.go`
  - `gnmi_server/client_subscribe.go`
  - `gnmi_server/server.go`
  - `gnmi_server/server_test.go`
  - `gnmi_server/clientCertAuth.go`
  - `sonic_db_config/db_config.go`
  - `telemetry/telemetry.go`

## Summary

`TELEMETRY_CONNECTIONS` is written exclusively by the `telemetry` daemon.
No orchagent or translib pipeline touches this table.
Implicit references that influence the table's content:

## Implicit cross-references found

### 1. database_config.json (STATE_DB address/port resolution)

`connection_manager.go:33-43` — `PrepareRedis()` calls:
```go
ns, _ := sdcfg.GetDbDefaultNamespace()
addr, err := sdcfg.GetDbTcpAddr("STATE_DB", ns)
db, err := sdcfg.GetDbId("STATE_DB", ns)
```
These delegate to `sonic_db_config/db_config.go` which reads
`/var/run/redis/sonic-db/database_config.json` via swsscommon.

If the file is absent or STATE_DB is not listed, `rclient` stays nil
and all HSet/HDel become silent no-ops.

### 2. CONFIG_DB GNMI|gnmi threshold (entry count cap)

`telemetry.go:187` sets CLI flag `--threshold` default = 100.
`server.go:866` passes it via `c.setConnectionManager(s.config.Threshold)`.
`connection_manager.go:65` checks:
```go
if len(cm.connections) >= cm.threshold && cm.threshold != 0 {
    return "", false  // no STATE_DB write
}
```
So GNMI threshold indirectly caps the number of active entries in TELEMETRY_CONNECTIONS.

### 3. Server.clients in-memory map (conceptual mirror)

`server.go:877` — `s.clients[clientKey] = c` (memory registration)
followed by `Add()` → `storeKeyRedis()` (STATE_DB write).
`server.go:872-876` — duplicate client: `oc.Close()` + `delete(s.clients, clientKey)`,
which triggers `Remove()` → `deleteKeyRedis()`.

The STATE_DB table is a best-effort mirror of the in-memory `Server.clients` map.

## Consumers (read-side)

Only two known readers of TELEMETRY_CONNECTIONS:
1. `show gnmi` CLI (sonic-utilities side, not cached in .cache/ — confirmed by grep across all cached repos returning 0 hits)
2. `gnmi_server/server_test.go:5176,5182` — test-only HGetAll for assertion

No orchagent, translib, or any other repo in the 15-repo cache references TELEMETRY_CONNECTIONS.

## No CONFIG_DB write-back

TELEMETRY_CONNECTIONS does not feed back into CONFIG_DB.
It is a runtime visibility table only.
