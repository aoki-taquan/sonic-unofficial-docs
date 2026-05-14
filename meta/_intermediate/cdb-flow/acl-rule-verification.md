# acl-rule Phase 8 scan (no existing derivation block to re-verify)

## Phase 8: Handler method scan

### Scanned files
- `sonic-swss/orchagent/aclorch.cpp` — 6222 lines, key: `doAclRuleTask()` (L5520), `AclRule::validateAddAction()`, `convertFieldValuesToAttributes()`

### Hits in doAclRuleTask (L5520-5700)

1. **`AclOrch::doAclRuleTask()` L5536-5540**: Early return / skip when `table_id.empty()` → WARN + erase (key precondition guard)

2. **`AclOrch::doAclRuleTask()` L5552-5566**: 
   - `if table_oid == SAI_NULL_OBJECT_ID` AND `m_ctrlAclTables.find(table_id) != m_ctrlAclTables.end()` → skip (control plane rule)
   - `if table_oid == SAI_NULL_OBJECT_ID` AND table not yet created → `it++` (wait)

3. **`AclOrch::doAclRuleTask()` L5570-5573**: 
   `auto type = m_AclTables[table_oid].type.getName();`
   `if (type == TABLE_TYPE_MIRROR || type == TABLE_TYPE_MIRRORV6)` → dispatch to determine which mirror table OID to use

4. **`AclOrch::doAclRuleTask()` L5633-5654**: 
   TCP_FLAGS auto-IP_PROTOCOL: `if (bHasTCPFlag && !bHasIPProtocol)` → if `type == TABLE_TYPE_MIRRORV6 || type == TABLE_TYPE_L3V6` use `MATCH_NEXT_HEADER` else use `MATCH_IP_PROTOCOL`

5. **`AclOrch::doAclRuleTask()` L5656-5663**:
   `if (bHasIPV4 && bHasIPV6)` AND `type == TABLE_TYPE_L3V4V6` → error, INACTIVE

### Note on ACL_RULE fields
`stage` and `type` are inherited from ACL_TABLE, not direct fields of ACL_RULE. The handler dispatches on these inherited values. The existing `<!-- value-behavior -->` block correctly captures this.

### Verdict: 5 handler dispatch patterns found, no existing derivation block to re-verify.
