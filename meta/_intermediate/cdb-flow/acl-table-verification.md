# acl-table Phase 8 scan (no existing derivation block to re-verify)

## Phase 8: Handler method scan

### Scanned files
- `sonic-swss/orchagent/aclorch.cpp` — key: `doAclTableTask()` (L5346), `AclTable::validateAddType()`, `processAclTableType()`, `processAclTableStage()`

### Hits in doAclTableTask (L5346-5520)

1. **`AclOrch::doAclTableTask()` L5380-5388**: 
   `if (attr_name == ACL_TABLE_TYPE)` → `processAclTableType(attr_value, tableTypeName)` — type string dispatch: empty string rejected; everything else passed through as custom or built-in type.

2. **`AclOrch::doAclTableTask()` L5400-5408**: 
   `else if (attr_name == ACL_TABLE_STAGE)` → `processAclTableStage(attr_value, newTable.stage)` — INGRESS/EGRESS parsed; invalid stage → `bAllAttributesOk=false`

3. **`AclOrch::doAclTableTask()` L5410-5413**: 
   `else if (attr_name == ACL_TABLE_SERVICES) { continue; }` — services field is silently ignored (continue) for non-CTRLPLANE tables

4. **`AclOrch::addAclTable()` / `updateAclTable()` L4675+**: 
   Inside table creation: `type=CTRLPLANE` branch — `if stage == ACL_STAGE_UNKNOWN` → error; `if !isAclL3V4V6TableSupported(stage)` for L3V4V6 type; `if type==MIRROR/MIRRORV6` → ASIC capability check

5. **`AclOrch` L4444 `addEgrSetDscpTable()`**:
   `type=EGR_SET_DSCP` → internally uses `TABLE_TYPE_MARK_META` / `TABLE_TYPE_MARK_METAV6` for SAI; stage forced to EGRESS

### Verdict: 5 handler dispatch patterns found. No existing derivation block to re-verify.
