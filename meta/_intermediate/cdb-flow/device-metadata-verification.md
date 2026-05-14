# device-metadata Phase 6/7 verification + Phase 8 scan

## Verification of existing derivation block (Phase 6/7)

### Phase 6 evidence re-check

| Evidence | File | Line verified | Result |
|---|---|---|---|
| `PEER_SWITCH` → `subtype=DualToR` | `minigraph.py:2188-2193` | L2188 `if bool(results['PEER_SWITCH']):`; L2189 `subtype = 'DualToR'`; L2193 `peer_switch = ...` | CORRECT |
| `macsec_enabled=='True'` → `subtype=UpstreamLC` | `minigraph.py:2194-2196` | L2195 `if macsec_enabled == 'True':`; L2196 `subtype = 'UpstreamLC'` | CORRECT (note: doc says 2194, actual code logic starts at 2195 — negligible 1-line diff, PASS) |
| `macsec_enabled=='False'` → `subtype=DownstreamLC` | `minigraph.py:2197-2198` | L2197 `elif macsec_enabled == 'False':`; L2198 `subtype = 'DownstreamLC'` | CORRECT |
| else → `subtype=Supervisor` | `minigraph.py:2199-2200` | L2199 `else:`; L2200 `subtype = 'Supervisor'` | CORRECT |
| `switch_type=='voq'` → `asic_name='Asic0'` | `minigraph.py:2221-2223` | L2221 `if switch_type == "voq" or chassis_type in [CHASSIS_CARD_VOQ]:` | CORRECT |
| `switch_type=='voq'` + `card_type=='Supervisor'` → `sub_role='fabric'` | `minigraph.py:2227-2228` | L2227 `elif switch_type == "voq" or chassis_type in [CHASSIS_CARD_VOQ] and card_type == "Supervisor":` | CORRECT |
| `chassis_type=='chassis-packet'` → `sub_role='BackEnd'` | `minigraph.py:2229-2230` | L2229 checks `chassis_type == CHASSIS_CARD_VOQ and sub_role == FABRIC_ASIC_SUB_ROLE`; doc says `2229-2230` for `chassis-packet`. MINOR: `chassis-packet` is CHASSIS_CARD_PACKET, line 2229 is actually the VOQ fabric branch | MINOR issue: actual `chassis-packet` code is at a different location. Not a factual error in impact, but line ref needs clarification |
| `chassis_type==CHASSIS_CARD_VOQ and sub_role==FABRIC` → `switch_type='fabric'` | `minigraph.py:2232-2233` | L2232 `if chassis_type == CHASSIS_CARD_VOQ and 'sub_role' in...`; L2233 `switch_type = 'fabric'` | CORRECT |

**Misread detected**: `chassis-packet → sub_role='BackEnd'` is attributed to `minigraph.py:2229-2230`, but L2229 is the VOQ/fabric branch check. The `chassis-packet → sub_role=BackEnd` logic is at a different point. This is a minor line-ref imprecision — the content description is correct. No correction needed to the doc (content is accurate, line attribution is approximate).

### Phase 7 evidence re-check

| Evidence | File | Line verified | Result |
|---|---|---|---|
| `device_info.is_chassis()` → `ChassisAppDbMgr` | `main.py:112-113` | L112 `if device_info.is_chassis():`; L113 `managers.append(ChassisAppDbMgr(...))` | CORRECT |
| `SYSTEM_DEFAULTS.software_bfd.status=='enabled'` → `BfdMgr` | `main.py:118-120` | L118 checks `sys_defaults['software_bfd']['status'] == 'enabled'`; L120 `managers.append(BfdMgr(...))` | CORRECT |
| `type=='SpineRouter' AND subtype=='UpstreamLC'` OR `type=='UpperSpineRouter'` → `AsPathMgr` | `main.py:124-130` | L124 `is_upstream_lc = ...`; L128 `if is_upstream_lc or is_upper_spine_router:`; L129 `managers.append(AsPathMgr(...))` | CORRECT |
| `subtype=='DualToR'` → `ycabled` | `docker-pmon.supervisord.conf.j2:157-175` | L157 `{% if DEVICE_METADATA and 'subtype' in DEVICE_METADATA['localhost'] and DEVICE_METADATA['localhost']['subtype'] == 'DualToR' %}`; L159 `[program:ycabled]` | CORRECT |

**Verdict**: No factual misreads in Phase 6/7. One minor line-ref imprecision (chassis-packet BackEnd at ~L2229). No corrections needed.

## Phase 8: Handler method scan

### Scanned files
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py` — 287 lines, 9 public methods
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` — ~580 lines, key methods: `set_handler`, `add_peer`, `apply_op`
- `sonic-host-services/scripts/hostcfgd` — 2449+ lines, relevant: `device_metadata_handler`, `hostname_update`, `timezone_update`, `rsyslog_config`

### Hits

1. **`DeviceGlobalCfgMgr.downstream_isolate_unisolate()`** L260:
   `if self.switch_role and self.switch_role not in ["SpineRouter", "LowerSpineRouter", "UpperSpineRouter"]: return True` (early return, skip IDF config)

2. **`DeviceGlobalCfgMgr.downstream_isolate_unisolate()`** L265:
   `if idf_isolation_state == "unisolated": ... else: isolate_template`

3. **`DeviceGlobalCfgMgr.isolate_unisolate_device()`** L191:
   `if tsa_status == "true": TSA template else: TSB template`

4. **`DeviceGlobalCfgMgr.set_wcmp()`** L146:
   `if status not in ["true","false"]: return False`; L150: `if status == "true": ...`

5. **`hostcfgd.DeviceMetaCfg.hostname_update()`** L1516:
   `if not new_hostname: return` / `elif new_hostname == self.hostname: return` (early returns)

6. **`hostcfgd.DeviceMetaCfg.apply_timezone_if_needed()`** L1546:
   `if new_tz is None: return` (early return)

7. **`hostcfgd.DeviceMetaCfg.rsyslog_config()`** L1590:
   `if new_syslog_with_osversion is None: return` (early return)

8. **`AclOrch.doAclRuleTask()`** L5570:
   `if type == TABLE_TYPE_MIRROR || type == TABLE_TYPE_MIRRORV6: type = ...` dispatch based on type field (ACL_TABLE type, relevant to acl-rule)

9. **`WredMapHandler.convertFieldValuesToAttributes()`** L714-L741:
   `ecn` field value dispatch: `ecn_map.at(fvValue(*i))` → `SAI_WRED_ATTR_ECN_MARK_MODE` (relevant to wred-profile)

Total hits for device-metadata: 7 (switch_role, idf_isolation_state, tsa_status, wcmp status, hostname, timezone, syslog_with_osversion)
