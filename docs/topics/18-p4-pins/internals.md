---
title: 内部実装
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/internals/p4-orchagent.md
  - docs/management/p4rt-read-cache-hld.md
  - docs/management/p4rt-application-hld.md
---

# 内部実装

PINS の中身を読むときに、まず押さえるのは **P4Orch の Manager 群と P4OidMapper**、次に **entity_cache_ の Write 連動更新**、最後に **APPL_STATE_DB を介した同期応答** の 3 点です。HLD 当初の設計から実装が拡張されているところがあるため、現行 master の構造に沿って整理します。

## P4Orch の Manager 群

P4Orch は `sonic-swss/orchagent/p4orch/` に置かれ、`p4orch.cpp` / `p4orch.h` が本体です。各 Manager が独立した SAI オブジェクト種別を担当します:

- `router_interface_manager`
- `neighbor_manager`
- `next_hop_manager`
- `wcmp_manager`
- `route_manager`
- `acl_table_manager`
- `acl_rule_manager`
- `mirror_session_manager`
- `l3_admit_manager`
- `gre_tunnel_manager`
- `tunnel_decap_group_manager`
- `ext_tables_manager`
- `tables_definition_manager`
- `ip_multicast_manager`
- `l3_multicast_manager`

HLD 当初は 7 Manager の構成でしたが、現行 master ではこれらにさらに拡張されています。詳細は [P4Orch HLD](../../internals/p4-orchagent.md) を参照してください。

## ObjectManagerInterface の抽象

各 Manager は `object_manager_interface.h` の `enqueue` / `drain` / `drainWithNotExecuted` を実装します。`enqueue` で APPL_DB から取り出した entry を蓄え、`drain` で SAI 呼び出しを実行し、`drainWithNotExecuted` でエラーケースのリカバリを記述するという 3 つの責務分離です。

## P4OidMapper

`p4oidmapper.h` の `P4OidMapper` は `(sai_object_type_t, key) → (oid, ref_count)` の対応を保持します。`getRefCount` を public 公開しており、複数 Manager から参照される共有オブジェクト（next_hop が wcmp / route から参照される等）の生存管理に使います。

## entity_cache_ の Write 連動更新

`sonic-pins/p4rt_app/p4runtime/p4runtime_impl.cc` の `UpdateCacheAndUtilizationState` が次を担当します:

- INSERT / MODIFY: PI 形式の Entity をキャッシュへ書き込み、利用率カウンタを更新
- DELETE: キャッシュから `erase`

型は HLD 記載の `table_entry_cache_` から **`entity_cache_`（`absl::flat_hash_map<pdpi::EntityKey, p4::v1::Entity>`）** へ汎化されており、TableEntry に加え PacketReplicationEngineEntry も保持します。Read は `p4runtime_read.cc` の `AppendTableEntryReads` が `entity_cache_` を走査して AppDb をスキップします。詳細は [Read キャッシュ HLD](../../management/p4rt-read-cache-hld.md) を参照してください。

## 同期書き込みと APPL_STATE_DB

通常の orchagent は SAI を非同期に呼びますが、P4Orch は **SAI 応答を待ち、結果を APPL_STATE_DB に書き戻す** ことで P4RT App が controller に成否を返せるようにします。`APPL_STATE_DB=14` は `sonic-swss-common/common/schema.h` で定義されており、PINS のために追加されたものです（SmartSwitch 向けに `DPU_APPL_STATE_DB=16` も別途追加）。

## warm boot とキャッシュの整合

`warm_boot_state_adapter_` が warm boot 時のキャッシュ復元基盤を提供しており、HLD で挙げられていた事前充填案を踏まえた骨組みになっています。整合は `P4RuntimeImpl::VerifyState()` が `VerifyP4rtTableWithCacheEntities` で確認します。
