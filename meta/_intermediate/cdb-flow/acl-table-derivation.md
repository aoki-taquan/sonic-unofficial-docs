# ACL_TABLE — Phase 6/7 derivation grep 証跡

## Phase 6: 自動派生 (assignment scan)

### 1. minigraph.py での `type` / `stage` 自動決定

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:1100-1250`

```python
# stage の派生 (line 1103-1107)
if aclintf.find(QName(ns, "InAcl")) is not None:
    stage = "ingress"
elif aclintf.find(QName(ns, "OutAcl")) is not None:
    stage = "egress"

# type の派生 (line 1215-1228)
if is_mirror: acls[aclname]['type'] = 'MIRROR'
elif is_mirror_v6: acls[aclname]['type'] = 'MIRRORV6'
elif is_mirror_dscp: acls[aclname]['type'] = 'MIRROR_DSCP'
elif is_bmc_data: acls[aclname]['type'] = 'BMCDATA'
elif is_bmc_data_v6: acls[aclname]['type'] = 'BMCDATAV6'
else: acls[aclname]['type'] = 'L3V6' if 'v6' in aclname.lower() else 'L3'
```

| 派生元条件 | 派生値 |
|---|---|
| XML `InAcl` タグ | `stage=ingress` |
| XML `OutAcl` タグ | `stage=egress` |
| AttachTo に erspan prefix | `type=MIRROR` |
| AttachTo に erspanv6 prefix | `type=MIRRORV6` |
| AttachTo に erspan_dscp prefix | `type=MIRROR_DSCP` |
| `Type=BMCDATA` + 名前に `v6` | `type=BMCDATAV6` |
| `Type=BMCDATA` + 名前に `v6` なし | `type=BMCDATA` |
| ports なし | `type=CTRLPLANE` |
| 上記以外 + 名前に `v6` | `type=L3V6` |
| 上記以外 | `type=L3` |

### 2. `UNDERLAY_SET_DSCP` → `MARK_META` への内部変換

**ソース**: `sonic-swss/orchagent/aclorch.cpp` `acltable.h:41-42`

```
TABLE_TYPE_UNDERLAY_SET_DSCP  → 内部で TABLE_TYPE_MARK_META に変換して SAI 投入
TABLE_TYPE_UNDERLAY_SET_DSCPV6 → 内部で TABLE_TYPE_MARK_METAV6 に変換
```

- orchdaemon.cpp で is_chassis() → ports の自動展開が異なる

### 3. `EGR_SET_DSCP` → EGRESS stage 固定

**ソース**: `sonic-swss/orchagent/aclorch.cpp:489`

```
type=EGR_SET_DSCP の場合、ユーザ指定の stage を無視して EGRESS stage 固定で SAI 投入
```

---

## Phase 7: 条件付き登録

### AclOrch の ASIC capability 条件チェック

**ソース**: `sonic-swss/orchagent/aclorch.cpp:3500-3684`

1. **MIRROR capability**: 起動時に `sai_query_attribute_enum_values_capability()` でプラットフォーム MIRROR 能力照会 → `m_mirrorTableCapabilities` に格納。`type=MIRROR` or `MIRRORV6` の ACL_TABLE 作成時にチェック。
2. **L3V4V6 support**: `isAclL3V4V6TableSupported(stage)` — ASIC が dual stack ACL をサポートしていない場合 reject。
3. **META_DATA capability**: `SAI_ACL_ENTRY_ATTR_FIELD_ACL_USER_META` / `SAI_ACL_ENTRY_ATTR_ACTION_SET_ACL_META_DATA` を `sai_query_attribute_capability()` で照会後に有効化。
4. **DTelOrch**: `orchdaemon.cpp:502-530` — `platform == BFN || VS` でのみ生成。DTelOrch なしでは DTEL 系 ACL rule action が機能しない。

### orchdaemon.cpp 登録条件 (非条件)

```
AclOrch は常時登録 (orchdaemon.cpp:533,569)
platform 依存なし
```
