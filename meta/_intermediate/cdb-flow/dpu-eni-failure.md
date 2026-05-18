# dpu-eni failure behavior (Phase D)

source: sonic-swss/orchagent/dash/dashenifwdorch.cpp, dashenifwdinfo.cpp

## Summary

DashEniFwdOrch uses an internal rule_state_t state machine (UNINSTALLED / PENDING / INSTALLED / FAILED) rather than the standard orchagent task_need_retry / task_failed mechanism. addOperation() / delOperation() always return true, so tasks are immediately erased from m_toSync. Retry for PENDING cases relies on external events (Neighbor Up) or re-SET from the APPL_DB producer.

## Failure patterns

| pattern | trigger | behavior | state | recovery |
|---------|---------|----------|-------|----------|
| vdpu_ids / primary_vdpu missing | EniInfo::create() mandatory field absent | SWSS_LOG_ERROR, create() returns false, no ACL rules | — | DEL + SET re-injection |
| primary_vdpu not in DpuRegistry | EniAclRule::processUpdate() dpu_info.getType() fails | SWSS_LOG_ERROR("No primary id ... in DPU Table"), INVALID → FAILED | FAILED | orchagent restart + DPU table fix |
| LOCAL DPU Neighbor unresolved | LocalEniNH::resolve() isNeighborResolved() false | no ACL rule written, PENDING; resolveNeighbor() request sent | PENDING | auto-recovery via handleNeighUpdate() on Neighbor Up |
| CLUSTER ENI VNET tunnel not registered | RemoteEniNH::resolve() findVnetTunnel() false | SWSS_LOG_ERROR, UNRESOLVED → PENDING | PENDING | re-SET after VNET registration (no auto-recovery) |
| CLUSTER ENI VNI not registered | RemoteEniNH::resolve() findVnetVni() false | SWSS_LOG_ERROR, UNRESOLVED → PENDING | PENDING | re-SET after VNET registration (no auto-recovery) |
| VIP_TABLE empty (CLUSTER ENI) | getVip() called during ACL rule fire | SWSS_LOG_THROW aborts orchagent | — | VIP_TABLE must be pre-populated before any ENI entry |
| Neighbor DEL (LOCAL ENI) | NeighborUpdate.add == false | ignored (comment: "not supported yet"), stale ACL rule remains | INSTALLED (stale) | orchagent restart |
| ENI UPDATE missing primary_vdpu | EniInfo::update(Request) itr_primary_id not found | throw logic_error, orchagent crash | — | HaMgrd must always include primary_vdpu |
| TUNNEL_TERM rule, no local EP | EniAclRule::processUpdate() findLocalEp() false | SWSS_LOG_ERROR, INVALID → FAILED | FAILED | change VDPU to one with LOCAL DPU, re-SET |

## Key design notes

- addOperation() / delOperation() always return true → no m_toSync requeueing
- EniAclRule::PENDING waits for external event (Neighbor Up via handleNeighUpdate)
- CLUSTER type with unregistered VNET does NOT auto-recover; requires re-SET
- VIP_TABLE empty is the only SWSS_LOG_THROW path; all others leave ENI in PENDING or FAILED state
- lazyInit() runs once only; DPU table changes after first ENI ADD are not reflected without restart
