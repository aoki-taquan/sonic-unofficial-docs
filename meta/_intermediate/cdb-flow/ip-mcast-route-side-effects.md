# ip-mcast-route — Phase F side-effects 調査メモ

## 調査対象ソース

- `sonic-swss/orchagent/p4orch/ip_multicast_manager.cpp`
- `sonic-swss/orchagent/p4orch/l3_multicast_manager.cpp`

## 副作用一覧

### IpMulticastManager が FIXED_IPV4/IPV6_MULTICAST_TABLE を処理する際の副作用

**IPMC エントリ作成時 (`createIpMulticastEntries`, `ip_multicast_manager.cpp:L741-778`)**:

1. SAI `create_ipmc_entry` を呼び出す → ASIC_DB 経由で syncd が ASIC を更新
2. `m_p4OidMapper->setDummyOID(SAI_OBJECT_TYPE_IPMC_ENTRY, ...)` — P4OidMapper 内部状態を更新
3. `gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_IPMC_ENTRY)` — CRM_DB の IPMC_ENTRY 使用量カウンタをインクリメント
4. `m_vrfOrch->increaseVrfRefCount(ip_multicast_entry.vrf_id)` — VrfOrch 内部の参照カウントをインクリメント
5. `m_p4OidMapper->increaseRefCount(SAI_OBJECT_TYPE_IPMC_GROUP, ...)` — IPMC_GROUP の参照カウントをインクリメント

**IPMC エントリ削除時 (`deleteIpMulticastEntries`, `ip_multicast_manager.cpp:L862-897`)**:

1. SAI `remove_ipmc_entry` を呼び出す → ASIC_DB 経由で syncd が ASIC を更新
2. `m_p4OidMapper->decreaseRefCount(SAI_OBJECT_TYPE_IPMC_GROUP, ...)` — IPMC_GROUP 参照カウント減少
3. `m_p4OidMapper->eraseOID(SAI_OBJECT_TYPE_IPMC_ENTRY, ...)` — P4OidMapper から OID 削除
4. `gCrmOrch->decCrmResUsedCounter(CrmResourceType::CRM_IPMC_ENTRY)` — CRM カウンタをデクリメント
5. `m_vrfOrch->decreaseVrfRefCount(ip_multicast_entry.vrf_id)` — VRF 参照カウント減少
6. `m_ipMulticastTable.size() == 0` → `deleteDefaultRpfGroup()` 呼び出し — 最後のエントリ削除時に RPF group も削除

### L3MulticastManager が REPLICATION_IP_MULTICAST_TABLE を処理する際の副作用

**IPMC グループ作成時 (`addIpMulticastGroupEntry`, `l3_multicast_manager.cpp:L2187-2305`)**:

1. SAI `create_ipmc_group` を呼び出す → ASIC_DB 経由で syncd が ASIC を更新
2. `m_p4OidMapper->setOID(SAI_OBJECT_TYPE_IPMC_GROUP, ...)` — P4OidMapper にグループ OID を登録
3. SAI `create_ipmc_group_member` を各レプリカに対して呼び出す
4. `m_p4OidMapper->setOID(SAI_OBJECT_TYPE_IPMC_GROUP_MEMBER, ...)` — 各メンバーの OID を登録
5. `m_p4OidMapper->increaseRefCount(SAI_OBJECT_TYPE_ROUTER_INTERFACE, router_interface_key)` — 参照先 MULTICAST_ROUTER_INTERFACE エントリの参照カウントをインクリメント

**`addL3MulticastRouterInterfaceEntry` (`l3_multicast_manager.cpp:L1795-1848`)**:

1. SAI `create_router_interface` を呼び出す
2. SAI `create_next_hop` を呼び出す (L2 以外)
3. `gPortsOrch->increasePortRefCount(entry.multicast_replica_port)` — PortsOrch 内部の port 参照カウントをインクリメント
4. `m_p4OidMapper->setOID(SAI_OBJECT_TYPE_ROUTER_INTERFACE, ...)` および `SAI_OBJECT_TYPE_NEXT_HOP` への OID 書き込み

**`addL2MulticastRouterInterfaceEntry` (`l3_multicast_manager.cpp:L1850-1880`)**:

1. `gPortsOrch->addBridgePort(port)` — PortsOrch が bridge port を作成 (SAI 呼び出しを含む)
2. `gPortsOrch->increaseBridgePortRefCount(port)` — bridge port 参照カウントをインクリメント
3. `m_p4OidMapper->setOID(SAI_OBJECT_TYPE_BRIDGE_PORT, ...)` — bridge port OID を登録

### APP_P4RT_TABLE へのステータス書き戻し

処理成否に関わらず、各バッチエントリの結果が `m_publisher->publish(APP_P4RT_TABLE_NAME, ...)` で APP_DB の `P4RT` テーブルに書き戻される。これがコントローラ (p4rt-app) への通知経路となる。

### CRM (Critical Resource Manager) カウンタへの影響

`gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_IPMC_ENTRY)` / `decCrmResUsedCounter` が呼ばれると、CrmOrch は `COUNTERS_DB` の `CRM:Stats` テーブルにある `crm_stats_ipmc_entry_used` フィールドを更新する (crmorch.cpp)。CRM 閾値に達した場合は syslog 警告も発生する。

### STATE_DB への書き込みなし

両マネージャとも STATE_DB への直接書き込みは行わない。

### CONFIG_DB への書き込みなし

両マネージャとも CONFIG_DB への書き込みは行わない。
