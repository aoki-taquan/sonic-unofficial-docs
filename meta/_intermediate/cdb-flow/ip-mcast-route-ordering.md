# ip-mcast-route — Phase B (ordering) スキャンノート

## ソース

- `sonic-net/sonic-swss` `orchagent/p4orch/ip_multicast_manager.cpp` HEAD
- `sonic-net/sonic-swss` `orchagent/p4orch/l3_multicast_manager.cpp` HEAD

## 検出した順序依存

### 依存 1: FIXED_IPV4/IPV6_MULTICAST_TABLE → REPLICATION_IP_MULTICAST_TABLE

`validateSetIpMulticastEntry()` (`ip_multicast_manager.cpp:L509-514`):

```cpp
if (!m_p4OidMapper->existsOID(SAI_OBJECT_TYPE_IPMC_GROUP,
                              ip_multicast_entry.multicast_group_id)) {
  return ReturnCode(StatusCode::SWSS_RC_NOT_FOUND)
         << "No multicast group ID found for "
         << QuotedVar(ip_multicast_entry.multicast_group_id);
}
```

`FIXED_IPV4_MULTICAST_TABLE` / `FIXED_IPV6_MULTICAST_TABLE` の `param/multicast_group_id` で参照するグループが
P4OidMapper に未登録の場合、即座に `SWSS_RC_NOT_FOUND` で失敗する。
**pending キューや自動 retry はない。**

`REPLICATION_IP_MULTICAST_TABLE` を先に書き込み、`L3MulticastManager` が SAI `IPMC_GROUP` を作成して
P4OidMapper に OID を登録してから `FIXED_*_MULTICAST_TABLE` を書き込む必要がある。

### 依存 2: REPLICATION_IP_MULTICAST_TABLE → MULTICAST_ROUTER_INTERFACE_TABLE

`validateReplicas()` (`l3_multicast_manager.cpp:L1002-1008`):

```cpp
if (router_interface_entry_ptr == nullptr) {
  return ReturnCode(StatusCode::SWSS_RC_NOT_FOUND)
         << "No corresponding "
         << APP_P4RT_MULTICAST_ROUTER_INTERFACE_TABLE_NAME
         << " entry found for multicast group ...";
}
```

`replicas` 内の各 `(port, instance)` に対応する `MULTICAST_ROUTER_INTERFACE_TABLE` エントリが
`L3MulticastManager` の内部 map に未登録の場合、即座に `SWSS_RC_NOT_FOUND` で失敗する。
**pending キューや自動 retry はない。**

### 依存 3: FIXED_IPV4/IPV6_MULTICAST_TABLE → VRF (VrfOrch)

`validateIpMulticastEntry()` (`ip_multicast_manager.cpp:L477-481`):

```cpp
if (!ip_multicast_entry.vrf_id.empty() &&
    !m_vrfOrch->isVRFexists(ip_multicast_entry.vrf_id)) {
  LOG_ERROR_AND_RETURN(ReturnCode(StatusCode::SWSS_RC_NOT_FOUND)
                       << "No VRF found with name " << ...);
}
```

非空の `vrf_id` で VrfOrch が未登録の場合、即座に `SWSS_RC_NOT_FOUND` で失敗する。
**pending キューや自動 retry はない。**

## 結論

すべての順序違反は P4RT フレームワークの即時エラー返却で終わり、自動回復機能はない。
コントローラ (p4rt-app) が依存順に書き込む必要がある。
