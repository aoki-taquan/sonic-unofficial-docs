# nhg cross-refs (Phase C) — intermediate evidence

Generated: 2026-05-19
Source: orchagent/nhgorch.cpp, orchagent/routeorch.cpp, orchagent/orchdaemon.cpp

## Key cross-reference dependencies identified

### APPL_DB tables
- `NEXTHOP_GROUP_TABLE` — primary consumer. `fpmsyncd` (routesync.cpp) writes SET/DEL.
- `ROUTE_TABLE` — reverse reference: holds `nexthop_group` field pointing to NHG keys. ref_count tracking in routeorch.cpp L1368-1391.
- `CLASS_BASED_NEXT_HOP_GROUP_TABLE` — CBF NHG uses this table's entries as members.
- `FC_TO_NHG_INDEX_MAP_TABLE` — used by CbfNhgOrch selection_map, indirect dep.

### External orchs / guards
- `PortsOrch::allPortsReady()` — startup guard. nhgorch.cpp L41-44.
- `NeighOrch` — ARP/NDP state. getNhId() calls gNeighOrch->hasNextHop/getNextHopId. nhgorch.cpp L544-585.
- `RouteOrch` — ECMP count limits: getNhgCount()/getMaxNhgCount(). nhgorch.cpp L252, routeorch.cpp L86-90.
- `CrmOrch` — resource counter. incCrmResUsedCounter(CRM_NEXTHOP_GROUP). nhgorch.cpp L795.

### SAI attributes
- `SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS` — queried at RouteOrch init. Fallback: DEFAULT_NUMBER_OF_ECMP_GROUPS=128 (routeorch.cpp L37).

### Independent paths (no direct dep)
- `FG_NHG` CONFIG_DB / `FgNhgOrch` — separate implementation, no direct dependency on NEXTHOP_GROUP_TABLE.
