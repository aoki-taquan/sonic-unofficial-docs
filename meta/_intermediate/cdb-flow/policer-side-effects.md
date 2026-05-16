# POLICER — Phase F 副次 DB 書込調査

source: `sonic-swss/orchagent/policerorch.cpp`  
調査日: 2026-05-16

---

## 1. ASIC_DB 書込

| 操作 | SAI API | ASIC_DB キー (syncd 経由) | 発生条件 |
|------|---------|--------------------------|---------|
| SAI policer 作成 | `sai_policer_api->create_policer()` | `ASIC_STATE:SAI_OBJECT_TYPE_POLICER:<oid>` | POLICER SET (新規) / PORT_STORM_CONTROL SET (新規) |
| SAI policer 属性更新 | `sai_policer_api->set_policer_attribute()` | 同上 | POLICER SET (update) — CIR/CBS/PIR/PBS のみ |
| SAI policer 削除 | `sai_policer_api->remove_policer()` | 同上 (DEL) | POLICER DEL / PORT_STORM_CONTROL DEL |
| SAI port 属性 (storm-control) | `sai_port_api->set_port_attribute()` | `ASIC_STATE:SAI_OBJECT_TYPE_PORT:<port_oid>` | PORT_STORM_CONTROL SET/DEL で broadcast/unicast/multicast policer OID をポートへ attach/detach |

### storm-control 経由の port 属性 ID

| storm_type | SAI_PORT 属性 |
|-----------|--------------|
| `broadcast` | `SAI_PORT_ATTR_BROADCAST_STORM_CONTROL_POLICER_ID` |
| `unknown-unicast` | `SAI_PORT_ATTR_FLOOD_STORM_CONTROL_POLICER_ID` |
| `unknown-multicast` | `SAI_PORT_ATTR_MULTICAST_STORM_CONTROL_POLICER_ID` |

evidence: `policerorch.cpp:204-215`, `policerorch.cpp:322-340`

---

## 2. COUNTERS_DB 書込

`policerorch.cpp` 自体は COUNTERS_DB へ書き込まない。

policer の統計（`SAI_POLICER_STAT_GREEN/YELLOW/RED_PACKETS/BYTES`）は
**P4 ACL ルールに紐付いた policer のみ** P4 ACL rule manager が取得し、COUNTERS_DB へ書き込む。

| 書込主体 | ファイル | COUNTERS_DB キー | 条件 |
|---------|---------|-----------------|------|
| `AclRuleManager` (P4 orch) | `p4orch/acl_rule_manager.cpp:804` | `COUNTERS:<acl_rule.db_key>` | P4 ACL rule に meter (policer) が設定されており、flex-counter が有効な場合 |

標準 `policerorch` が管理する `POLICER` テーブル由来の SAI policer について、
COUNTERS_DB への統計書込は存在しない。

evidence: `p4orch/acl_rule_manager.cpp:762-804`

---

## 3. CRM カウンタ

`crmorch.cpp` に `POLICER` / `SAI_OBJECT_TYPE_POLICER` の参照はゼロ件。

PolicerOrch は `gCrmOrch->incCrmResUsedCounter()` / `decCrmResUsedCounter()` を呼び出さない。

**結論: CRM は policer オブジェクトをトラッキングしない。**

evidence: `crmorch.cpp` — POLICER ヒット 0 件確認済み

---

## 4. その他の副次効果

- **m_syncdPolicers** (orchagent メモリ): policer 名 → SAI OID のマップ。ASIC_DB ではなくメモリ上の状態管理。
- **m_policerRefCounts** (orchagent メモリ): 参照カウント。MirrorOrch / p4 orch が `increaseRefCount()` / `decreaseRefCount()` を呼ぶ。DB 書込なし。
- **MirrorOrch からの参照**: MIRROR_SESSION SET 時に `policerExists()` → `getPolicerOid()` → `increaseRefCount()` を呼び、SAI mirror session に policer OID を attach。副次的に SAI MIRROR SESSION オブジェクト (`ASIC_STATE:SAI_OBJECT_TYPE_MIRROR_SESSION`) が更新される。
  evidence: `mirrororch.cpp:432-441`
