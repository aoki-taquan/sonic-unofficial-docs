# ACL_RULE — Phase 6/7 derivation grep 証跡

## Phase 6: 自動派生 (assignment scan)

### 1. `MATCH_TCP_FLAGS` → `IP_PROTOCOL=6` 自動付与

**ソース**: `sonic-swss/orchagent/aclorch.cpp:5632-5660`

```
grep: MATCH_TCP_FLAGS + bHasTCPFlag + IP_PROTOCOL_NUM = 6
```

- ルールに `MATCH_TCP_FLAGS` があり `IP_PROTOCOL` (または `NEXT_HEADER`) が未設定の場合、`AclOrch` が自動で `IP_PROTOCOL=6` を付与する。
- IPv6 テーブル (`L3V6`, `MIRRORV6`) の場合は `NEXT_HEADER=6` を付与。
- `SWSS_LOG_INFO("Automatically added match attribute '%s : %s'", ...)` でログ出力。

### 2. `stage` → `INGRESS`/`EGRESS` の ACL_TABLE 継承

ACL_RULE 自体に `stage` フィールドはなく、所属 `ACL_TABLE` の `stage` を継承する。

**ソース**: `sonic-swss/orchagent/aclorch.cpp:166-167,263-272`

```
grep: aclStageLookUp, SAI_ACL_STAGE_INGRESS, SAI_ACL_STAGE_EGRESS
```

| ACL_TABLE.stage | 使用可能 MIRROR action |
|---|---|
| `INGRESS` | `MIRROR_INGRESS_ACTION` 有効 |
| `EGRESS` | `MIRROR_EGRESS_ACTION` のみ有効 |

### 3. minigraph.py での `type` 自動決定

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:1218-1228`

```python
# line 1228
acls[aclname]['type'] = 'L3V6' if 'v6' in aclname.lower() else 'L3'
```

- `AclInterface` が erspan 系 → `type=MIRROR` / `MIRRORV6` / `MIRROR_DSCP` を自動設定
- `AclInterface` が BMC data → `type=BMCDATA` / `BMCDATAV6` を自動設定
- それ以外: ACL 名称に `v6` を含む → `type=L3V6`、含まない → `type=L3`

```python
# line 1104-1107 (stage derive from InAcl/OutAcl)
if aclintf.find(QName(ns, "InAcl")) is not None:
    stage = "ingress"
elif aclintf.find(QName(ns, "OutAcl")) is not None:
    stage = "egress"
```

- XML の `InAcl` タグ → `stage=ingress`
- XML の `OutAcl` タグ → `stage=egress`

---

## Phase 7: 条件付き登録

### AclOrch の ASIC capability 条件チェック

**ソース**: `sonic-swss/orchagent/aclorch.cpp:3500-3541,5198-5227`

1. **MIRROR テーブル**: 起動時 `sai_query_attribute_enum_values_capability()` で `m_mirrorTableCapabilities[MIRROR]` / `[MIRRORV6]` を設定。capability がなければ `type=MIRROR` の ACL_TABLE 作成を reject。
2. **L3V4V6 テーブル**: `isAclL3V4V6TableSupported(stage)` を確認。未サポート ASIC では `aclorch.cpp:2739` で reject。
3. **DTelOrch**: `orchdaemon.cpp:502-530` — `platform == BFN || VS` かつ `capability.create_implemented` の場合のみ `DTelOrch` を生成し `AclOrch` に渡す。DTEL 系 action (`FLOW_OP` 等) は DTelOrch なしでは機能しない。
4. **META_DATA 系 capability**: `sai_query_attribute_capability()` で `SAI_ACL_ENTRY_ATTR_FIELD_ACL_USER_META` / `SAI_ACL_ENTRY_ATTR_ACTION_SET_ACL_META_DATA` を確認後に有効化 (`aclorch.cpp:3590-3659`)。

### orchdaemon.cpp 登録条件

```
AclOrch は常時登録 (orchdaemon.cpp:533,569)
DTelOrch は条件付き: BFN or VS platform でのみ生成 (orchdaemon.cpp:527-530)
```
