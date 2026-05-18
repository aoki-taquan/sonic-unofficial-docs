# lldp-state failure behavior (Phase D) — analysis notes

## Target page
docs/reference/config-db/lldp-state.md

## Phase added
failure (Phase D)

## Key findings

### lldp-syncd as sole writer
- LLDP_ENTRY_TABLE / LLDP_LOC_CHASSIS are APPL_DB tables written exclusively by lldp-syncd
- No CLI/REST/gNMI write path exists (read-only from consumer perspective)
- Failure modes split into: (1) lldp-syncd write failures, (2) Consumer read failures

### lldp-syncd write failures
- Process stop: supervisord autorestarts, after restart lldp-syncd does full lldpctl rescan
- TTL expiry: lldpd deletes entries via lldp-syncd DEL (hold_time = hello × multiplier, default 120s)
- Link down: lldpd notifies lldp-syncd to DEL the APPL_DB entry

### Consumer (sonic-snmpagent) read failures (ieee802_1ab.py)
- Empty lldp_rem_man_addr: early return in update_rem_if_mgmt(), Management Address MIB entry missing
- Missing lldp_rem_index/cap fields: KeyError caught, WARNING logged, entire lldpRemTable entry skipped
- lldp_table_lookup() KeyError: WARNING + return None, field absent from SNMP response
- None of these errors are recorded in STATE_DB; all are silent drops with WARNING logs

### lldp_app.go (REST/gNMI) failures
- GetTable failure → log.Info + empty neighbor list returned
- GetEntry failure → log.Info + skip entry, other entries still returned

## Evidence
- sonic-snmpagent/src/sonic_ax_impl/mibs/ieee802_1ab.py:461-463 (KeyError catch)
- sonic-snmpagent/src/sonic_ax_impl/mibs/ieee802_1ab.py:490 (lldp_table_lookup warning)
- sonic-snmpagent/src/sonic_ax_impl/mibs/ieee802_1ab.py:517-525 (man_addr early return)
- sonic-mgmt-common/translib/lldp_app.go:getLldpInfoFromDB
