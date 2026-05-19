# ip-mcast-route — Phase C: 暗黙参照 (cross-refs)

## 調査日: 2026-05-19

## 調査対象ソース

- `sonic-net/sonic-swss` `orchagent/p4orch/ip_multicast_manager.cpp` HEAD
- `sonic-net/sonic-swss` `orchagent/p4orch/l3_multicast_manager.cpp` HEAD
- `sonic-net/sonic-swss` `orchagent/p4orch/ip_multicast_manager.h` HEAD
- `sonic-net/sonic-swss` `orchagent/vrforch.h` HEAD
- `sonic-net/sonic-swss` `orchagent/orchdaemon.cpp` L283
- `sonic-net/sonic-swss-common` `common/schema.h` L59-80

## 検出された暗黙参照

### 1. VRF_TABLE (APP_DB) への暗黙参照

`IpMulticastManager::validateIpMulticastEntry()` (`ip_multicast_manager.cpp:L477-481`) が VRFOrch 経由で APP_DB の `VRF_TABLE` に存在確認を行う。`vrf_id` が非空の場合のみチェックが発動する。

- 参照先: `APP_DB:VRF_TABLE:<vrf_name>` (APP_VRF_TABLE_NAME = "VRF_TABLE")
- 参照方法: `m_vrfOrch->isVRFexists(vrf_id)`
- 未存在時: `SWSS_RC_NOT_FOUND` を即返却

またエントリ作成時 (`ip_multicast_manager.cpp:L775`) は `m_vrfOrch->increaseVrfRefCount(vrf_id)` で参照カウントを増加し、削除時 (`L886`) に `decreaseVrfRefCount` で解放する。これにより VRF が削除されるとカウント不整合が起きる可能性がある。

### 2. FIXED_MULTICAST_ROUTER_INTERFACE_TABLE (APP_DB) への暗黙参照

`L3MulticastManager::validateReplicas()` が `REPLICATION_IP_MULTICAST_TABLE` エントリの各 replica について `FIXED_MULTICAST_ROUTER_INTERFACE_TABLE` エントリの存在を内部マップで確認する (`l3_multicast_manager.cpp:L1002-1008`)。

- 参照先: `APP_DB:P4RT:FIXED_MULTICAST_ROUTER_INTERFACE_TABLE:<port>:<instance>`
- 参照方法: `L3MulticastManager` 内部キャッシュ（APP_DB の同テーブルを subscribe して管理）
- 未存在時: `SWSS_RC_NOT_FOUND`

### 3. P4OidMapper 内 IPMC_GROUP への暗黙参照

`FIXED_IPV4/IPV6_MULTICAST_TABLE` 書き込み時に `P4OidMapper::existsOID(SAI_OBJECT_TYPE_IPMC_GROUP, multicast_group_id)` で REPLICATION グループの登録状態を確認する (`ip_multicast_manager.cpp:L509-514`)。

- 参照先: P4OidMapper 内部マップ (REPLICATION_IP_MULTICAST_TABLE が先行してセットしたもの)
- 参照方法: `m_p4OidMapper->existsOID(SAI_OBJECT_TYPE_IPMC_GROUP, ...)`
- 未存在時: `SWSS_RC_NOT_FOUND`

### CONFIG_DB への直接参照

`ip_multicast_manager.cpp` / `l3_multicast_manager.cpp` の双方とも CONFIG_DB への直接 subscribe / get は行わない (grep "CONFIG_DB" で 0 ヒット)。CONFIG_DB 依存は VRFOrch および P4Orch 上位レイヤが間接的に処理する。

## YANG leafref 相当

これらは APP_DB テーブル同士の実行時参照であり、YANG leafref としては定義されていない (P4RT テーブルは YANG スキーマ管理外)。
