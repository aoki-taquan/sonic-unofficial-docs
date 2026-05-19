# ip-mcast-route — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/ip-mcast-route.md` Phase C 追加分。
本ページの主題は **APP_DB の 3 テーブル**（`REPLICATION_IP_MULTICAST_TABLE` / `FIXED_IPV4_MULTICAST_TABLE` / `FIXED_IPV6_MULTICAST_TABLE`）で、いずれも `p4rt-app` (P4RT コントローラ) が**書き手 (producer only)** として書き込み、orchagent の `L3MulticastManager` / `IpMulticastManager` が消費する。
ここでの「暗黙参照」とは、これらテーブルのエントリ生成・フィールド値・SAI マッピングが依存する**入力側テーブル / Orch / プラットフォーム情報**を指す。
`sonic-swss/orchagent/p4orch/ip_multicast_manager.cpp` および `l3_multicast_manager.cpp` の Orch ロジックを精読して網羅した。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/p4orch/ip_multicast_manager.cpp` | `IpMulticastManager` — `FIXED_IPV4/IPV6_MULTICAST_TABLE` 消費 → SAI `IPMC_ENTRY` |
| `sonic-swss/orchagent/p4orch/l3_multicast_manager.cpp` | `L3MulticastManager` — `REPLICATION_IP_MULTICAST_TABLE` / `FIXED_MULTICAST_ROUTER_INTERFACE_TABLE` 消費 → SAI `IPMC_GROUP` |
| `sonic-swss/orchagent/p4orch/ip_multicast_manager.h` | `IpMulticastManager` ヘッダ、`P4IpMulticastEntry` 構造体 |
| `sonic-swss/orchagent/p4orch/l3_multicast_manager.h` | `L3MulticastManager` ヘッダ、`P4MulticastGroupEntry` 構造体 |
| `sonic-swss-common/common/schema.h` | `APP_P4RT_REPLICATION_IP_MULTICAST_TABLE_NAME` / `APP_P4RT_IPV4_MULTICAST_TABLE_NAME` / `APP_P4RT_IPV6_MULTICAST_TABLE_NAME` / `APP_P4RT_MULTICAST_ROUTER_INTERFACE_TABLE_NAME` 定義 |

## YANG leafref

3 テーブルはいずれも P4RT 専用の APP_DB テーブルであり、YANG モデル化されていない。leafref は存在せず、全依存が実装レベルの暗黙参照。

## 暗黙参照 (実装レベル)

### 1. FIXED_MULTICAST_ROUTER_INTERFACE_TABLE (replica OID 解決の必須先行)

- **参照先テーブル**: `APP_DB FIXED_MULTICAST_ROUTER_INTERFACE_TABLE`
- **参照方向**: 読み取り（`L3MulticastManager` 内部 map への照合）
- **条件**: `REPLICATION_IP_MULTICAST_TABLE` の `replicas` 配列内の各 `(port, instance)` エントリを処理するとき
- **意味**: `validateReplicas()` (`l3_multicast_manager.cpp:L1002-1008`) が各レプリカの `(multicast_replica_port, multicast_replica_instance)` キーで `L3MulticastManager` の内部 router interface map を検索する。エントリ不在の場合は即時 `SWSS_RC_NOT_FOUND` — pending retry なし。
- **evidence**: `l3_multicast_manager.cpp` L978-1057 (`validateReplicas`), L1002-1008 (router interface lookup 失敗分岐)

### 2. P4OidMapper — IPMC_GROUP OID (FIXED テーブルの multicast_group_id 解決)

- **参照先テーブル**: `APP_DB REPLICATION_IP_MULTICAST_TABLE` (L3MulticastManager が登録した P4OidMapper エントリ)
- **参照方向**: P4OidMapper `existsOID` / `getOID` 照合（読み取り）
- **条件**: `FIXED_IPV4/IPV6_MULTICAST_TABLE` の `param/multicast_group_id` フィールドを処理するとき
- **意味**: `validateSetIpMulticastEntry()` (`ip_multicast_manager.cpp:L509-514`) が `m_p4OidMapper->existsOID(SAI_OBJECT_TYPE_IPMC_GROUP, ...)` で OID の存在を確認する。`REPLICATION_IP_MULTICAST_TABLE` が先に処理されて `L3MulticastManager` が SAI `IPMC_GROUP` を作成し OID を登録していない限り、即時 `SWSS_RC_NOT_FOUND` — pending retry なし。
- **evidence**: `ip_multicast_manager.cpp` L509-514 (OID 存在確認), L748-756 (`getOID` → `SAI_IPMC_ENTRY_ATTR_OUTPUT_GROUP_ID`), L776 (`increaseRefCount` → 参照カウント管理)

### 3. VRFOrch — VRF 存在確認 (非デフォルト VRF 使用時)

- **参照先 Orch**: `VRFOrch::isVRFexists()` / `VRFOrch::getVRFid()` / `VRFOrch::increaseVrfRefCount()`
- **参照方向**: Orch 照合（読み取り + 参照カウント管理）
- **条件**: `FIXED_IPV4/IPV6_MULTICAST_TABLE` の JSON key に含まれる `match/vrf_id` が空文字列以外のとき
- **意味**: `validateIpMulticastEntry()` (`ip_multicast_manager.cpp:L477-481`) が非空 `vrf_id` を `VRFOrch::isVRFexists()` で確認する。VRF が未作成の場合は即時 `SWSS_RC_NOT_FOUND`。エントリ作成時 `increaseVrfRefCount()` (`L775`)、削除時 `decreaseVrfRefCount()` (`L886`) で参照カウントを管理する。デフォルト VRF (`vrf_id` = 空文字列) の場合は `L703` の `getVRFid("")` が `0` (SAI_NULL_OBJECT_ID) を返し VRF 確認をスキップ。
- **evidence**: `ip_multicast_manager.cpp` L477-481 (`validateIpMulticastEntry`), L703 (`getVRFid`), L775 (`increaseVrfRefCount`), L886 (`decreaseVrfRefCount`)

### 4. PortsOrch — 物理ポート存在確認 (replica port)

- **参照先 Orch**: `PortsOrch::getPort()` (内部的に `L3MulticastManager::getSaiPort()` 経由)
- **参照方向**: ポート OID 解決（読み取り）
- **条件**: `REPLICATION_IP_MULTICAST_TABLE` の `replicas` 内の各 `multicast_replica_port` を処理するとき
- **意味**: `L3MulticastManager` が各レプリカポートの SAI RIF OID を解決する (`l3_multicast_manager.cpp:L67-72`)。ポートが PortsOrch に未登録の場合は `SWSS_RC_NOT_FOUND` でエントリ作成が失敗。
- **evidence**: `l3_multicast_manager.cpp` L67-72 (`getSaiPort` → `PortsOrch::getPort`), L1002-1008 (`validateReplicas` の router interface lookup)

### 5. SAI `IPMC_GROUP` / `IPMC_ENTRY` 参照カウント (削除順ガード)

- **参照先**: P4OidMapper の `IPMC_GROUP` refcount (`increaseRefCount` / `decreaseRefCount`)
- **参照方向**: 参照カウント管理（書き込み）
- **条件**: `FIXED_IPV4/IPV6_MULTICAST_TABLE` エントリを作成・削除するとき
- **意味**: `IpMulticastManager` が `FIXED_*` エントリ作成時に `increaseRefCount(SAI_OBJECT_TYPE_IPMC_GROUP, ...)` (`L776`) を呼び、削除時に `decreaseRefCount` (`L881`) を呼ぶ。参照カウントが非ゼロの `IPMC_GROUP` を `REPLICATION_*` 経由で先に削除しようとすると SAI `remove_ipmc_group` が失敗し、`L3MulticastManager` の削除処理がロールバックされる。
- **evidence**: `ip_multicast_manager.cpp` L776 (`increaseRefCount`), L838-839 / L881 (`decreaseRefCount`), `l3_multicast_manager.cpp` の SAI group 削除パス (refcount ガード)

## 参照関係サマリ

```
APP_DB REPLICATION_IP_MULTICAST_TABLE / FIXED_IPV4/IPV6_MULTICAST_TABLE
  (書き手: p4rt-app。読み手: L3MulticastManager / IpMulticastManager)

暗黙参照:
  ├─ [暗黙] FIXED_MULTICAST_ROUTER_INTERFACE_TABLE (APP_DB)
  │           replica (port, instance) → router interface OID 解決 (必須先行)
  ├─ [暗黙] P4OidMapper / REPLICATION_IP_MULTICAST_TABLE
  │           multicast_group_id → SAI IPMC_GROUP OID (必須先行)
  ├─ [暗黙] VRFOrch (非デフォルト VRF 使用時)
  │           vrf_id → VRF OID 解決 + 参照カウント管理
  ├─ [暗黙] PortsOrch
  │           replica port 名 → SAI port OID 解決
  └─ [暗黙] P4OidMapper refcount (IPMC_GROUP)
              FIXED_* 参照が残っている間は REPLICATION_* の削除が SAI レベルで失敗
```

## evidence 索引

- `ip_multicast_manager.cpp`: L477-481 (VRF ガード), L509-514 (IPMC_GROUP OID ガード), L547-550 (IPMC_ENTRY 存在確認), L703 (`getVRFid`), L748-756 (`getOID` IPMC_GROUP), L772-776 (setDummyOID + increaseRefCount), L814-841 (update 時 refcount 更新), L881-883 (eraseOID + decreaseRefCount), L886 (decreaseVrfRefCount)
- `l3_multicast_manager.cpp`: L67-72 (getSaiPort → PortsOrch), L978-1057 (validateReplicas), L1002-1008 (router interface lookup 失敗)
- `schema.h`: `APP_P4RT_MULTICAST_ROUTER_INTERFACE_TABLE_NAME`, `APP_P4RT_REPLICATION_IP_MULTICAST_TABLE_NAME`, `APP_P4RT_IPV4_MULTICAST_TABLE_NAME`, `APP_P4RT_IPV6_MULTICAST_TABLE_NAME`
