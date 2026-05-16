# DOT1P_TO_TC_MAP — Phase A defaults derivation notes

Source files read (post-grep, full-line):
- `sonic-swss/orchagent/qosorch.cpp` (lines 360-420, 124-201, 1326-1345)
- `sonic-swss/orchagent/qosorch.h` (lines 1-225)
- `sonic-swss/orchagent/orchdaemon.cpp` (lines 365-394)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dot1p-tc-map.yang`
- `sonic-buildimage/src/sonic-yang-models/yang-templates/sonic-types.yang.j2` (lines 338-346)
- `sonic-buildimage/files/build_templates/qos_config.j2` (lines 235-265)
- `sonic-swss/tests/mock_tests/qosorch_ut.cpp` (lines 430-576)
- `sonic-buildimage/src/sonic-yang-models/tests/yang_model_tests/tests_config/qosmaps.json`
- `sonic-buildimage/src/sonic-config-engine/tests/sample_output/py3/qos-arista7050-t0-storage-backend.json`
- `sonic-swss/tests/test_qos_map.py`

---

## Field enumeration

### 1. `name` (key of outer list DOT1P_TO_TC_MAP_LIST)

- YANG: `string`, pattern `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})`, length 1..32
- No `default` statement in YANG.
- No fallback in qosorch — if key is missing it simply doesn't exist.
- **Hardcoded platform default**: `qos_config.j2` generates map named `"AZURE"` on storage-backend platforms.
- **Case sensitivity**: pattern allows mixed case; Redis key is case-sensitive. `AZURE` and `Azure` are distinct entries.

### 2. `dot1p` (key of inner list DOT1P_TO_TC_MAP)

- YANG: `string`, pattern `[0-7]?`
  - **YANG-implementation discrepancy**: pattern `[0-7]?` means 0 or 1 character from `[0-7]`. An **empty string `""`** matches this pattern and passes YANG validation. qosorch uses `stoi(fvField(fv))` which will throw `std::invalid_argument` on empty string.
  - **Silent drop on parse error**: `convertFieldValuesToAttributes()` catches `std::invalid_argument` and `std::out_of_range`, logs `SWSS_LOG_ERROR`, and `continue`s — the offending entry is **silently dropped** from the SAI list. `return true` is still returned even with 0 valid entries.
  - qosorch passes the value through `stoi()` → `static_cast<sai_uint8_t>`. No range check beyond stoi throwing for non-numeric; values 8-255 are NOT rejected by qosorch (only by YANG at write time).
  - **No YANG default** on `dot1p` field.

### 3. `tc` (leaf in inner list)

- YANG type: `stypes:tc_type` = `uint8 range 0..15` (sonic-types.yang.j2 line 338-346)
- **YANG-documentation discrepancy**: existing page says `tc` is 0..7; YANG actually allows 0..15.
- Test config `qosmaps.json` uses `"tc": "8"` as valid and `"tc": "16"` as invalid — confirms 0..15 range.
- qosorch: `static_cast<sai_cos_t>(stoi(fvValue(fv)))`. `sai_cos_t` is typically `uint8_t`. No upper-bound check in qosorch; ASIC SAI may or may not accept TC > 7 depending on hardware.
- **No YANG default** on `tc` field.
- **Silent drop on parse error**: same error-continue pattern as `dot1p`.

---

## Detected implicit defaults / behaviors

### A. Silent drop + substitution (CRITICAL)

**Location**: `qosorch.cpp` lines 375-384, 386-388

If any `dot1p` or `tc` value fails `stoi()` (invalid_argument or out_of_range), that entry is silently skipped. The function still returns `true` and the SAI map is created with fewer entries than specified. No explicit `task_invalid_entry` is returned. This means a partial map can be pushed to SAI without error indication to the caller.

### B. YANG range vs. SAI discrepancy for `tc`

YANG allows `tc` 0..15. qosorch passes value directly to SAI as `sai_cos_t`. Most hardware ASICs support only TC 0..7. Entries with TC 8..15 will pass YANG validation and qosorch processing, but SAI/ASIC may reject them silently or with a logged error. This is a **platform-dependent behavior**.

### C. Platform-conditional default map injection

`qos_config.j2` injects `DOT1P_TO_TC_MAP|AZURE` only on storage-backend platforms (`type in backend_device_types AND storage_device == 'true'`). The mapping is:
```
"0":"1", "1":"0", "2":"2", "3":"3", "4":"4", "5":"5", "6":"6", "7":"7"
```
On non-storage-backend platforms, **no DOT1P_TO_TC_MAP is injected by default**.

### D. Dead consumer without PORT_QOS_MAP reference

The map exists in CONFIG_DB and a SAI QoS map object is created. However, it has **no effect on traffic** until referenced by `PORT_QOS_MAP.dot1p_to_tc_map`. Creation of the SAI object is unconditional on whether any port references it. This is a "dead consumer" pattern for unattached maps.

### E. Pending remove + SET retry

If a map is referenced by a port and a DEL arrives, `m_pendingRemove = true` is set and `task_need_retry` is returned. If a SET arrives while pending remove, qosorch logs NOTICE and returns `task_need_retry` — the SET is **deferred**, not applied. This is a write-order dependency.

### F. YANG `dot1p` pattern allows empty string

`[0-7]?` — the `?` makes the entire character optional, so `""` is valid YANG but causes `stoi("")` exception in qosorch → silent drop. This is a **YANG-implementation discrepancy**.

### G. No APPL_DB stage

Unlike many other SONiC tables, `DOT1P_TO_TC_MAP` has **no APPL_DB fanout**. QosOrch subscribes directly to CONFIG_DB. There is no cfgmgr/portmgr relay. Changes apply directly to SAI without buffering.

### H. Modify path vs create path

If a map entry already exists in `m_qos_maps`, qosorch calls `modifyQosItem()` → `sai_qos_map_api->set_qos_map_attribute()`. If new, it calls `addQosItem()` → `sai_qos_map_api->create_qos_map()`. The entire map list is replaced on each SET (no per-entry patching). Removing a single dot1p entry requires re-sending the full map without that entry.

---

## Summary table for `<!-- defaults -->` block

| Field | YANG default | Fallback/implicit | Silent drop | Platform dep |
|-------|-------------|-------------------|-------------|--------------|
| `name` | none | "AZURE" via j2 on storage-backend only | N/A | Yes (storage-backend) |
| `dot1p` | none | none; invalid → entry silently skipped | Yes | No |
| `tc` | none | none; invalid → entry silently skipped; range 0..15 YANG but ASIC may cap at 7 | Yes | Yes (ASIC TC limit) |
