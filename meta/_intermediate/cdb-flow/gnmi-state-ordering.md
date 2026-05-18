# gnmi-state ordering (Phase B) — intermediate research notes

## Page
`docs/reference/config-db/gnmi-state.md` — TELEMETRY_CONNECTIONS (STATE_DB)

## Source examined
- `sonic-net/sonic-gnmi` @ eb635b7679b260c3fd0786a6d0734fc8e82c9a22
  - `gnmi_server/connection_manager.go`
  - `gnmi_server/client_subscribe.go`

## Ordering findings

### PrepareRedis → HSet (startup)
`PrepareRedis()` at L32-61 performs HGetAll → full HDel before any new HSet.
This enforces a strict clear-before-write ordering at daemon startup.

### setConnectionManager re-init (threshold change)
`client_subscribe.go:73-85` — if threshold changes between Subscribe RPCs,
a new ConnectionManager is instantiated and PrepareRedis() is called again,
wiping all STATE_DB entries.

### Memory-before-Redis write order
In Add() (L63-78): threshold check → memory map update → storeKeyRedis
In Remove() (L80-92): memory delete → deleteKeyRedis
So STATE_DB always trails memory state by a small window.
