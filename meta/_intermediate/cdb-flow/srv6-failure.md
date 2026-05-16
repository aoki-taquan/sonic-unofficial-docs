# Phase D — SRv6 Failure / 失敗挙動 (証拠ファイル)

ソース: `sonic-swss/orchagent/srv6orch.cpp`
revision: 4305596156d70e9797e8a881b3d19b46de0bce0d

---

## 1. SRV6_SID_LIST_TABLE — 失敗ケース

### 1-1. `path` が空（セグメントリスト 0 件）
- 行 1052-1055: `segment_list.count == 0` → `SWSS_LOG_ERROR("segment list count is zero, skip")` → `return true`（呼び出し元は成功扱いだが SAI 呼び出しは発生しない）
- 実際の SID リストは SAI に登録されず、nexthop 作成で後続エラーとなる

### 1-2. SAI create 失敗
- 行 1092-1095: `sai_srv6_api->create_srv6_sidlist()` が `SAI_STATUS_SUCCESS` 以外 → `SWSS_LOG_ERROR("Failed to create srv6 sidlist object, rv %d", status)` → `return false`
- `doTaskSidTable` が `task_failed` を返す（行 1168-1169）

### 1-3. SAI set（update）失敗
- 行 1109-1112: `set_srv6_sidlist_attribute()` が `SAI_STATUS_SUCCESS` 以外 → `SWSS_LOG_ERROR("Failed to set srv6 sidlist object with new segments, rv %d", status)` → `return false`

### 1-4. DEL 時：存在しない seg_name
- 行 1123-1126: `sid_table_.find(sid_name) == sid_table_.end()` → `SWSS_LOG_ERROR("segment name %s doesn't exist", sid_name.c_str())` → `task_failed`

### 1-5. DEL 時：nexthop 参照中（refcount > 0）
- 行 1129-1133: `sid_table_[sid_name].nexthops.size() > 0` → `SWSS_LOG_NOTICE("segment object %s referenced by other nexthops: count %zu, not deleting")` → `task_need_retry`（再キューイング）

### 1-6. SAI remove 失敗
- 行 1137-1140: `remove_srv6_sidlist()` が失敗 → `SWSS_LOG_ERROR("Failed to delete SRV6 sidlist object for %s")` → `task_failed`

---

## 2. SRV6_MY_SID_TABLE — 失敗ケース

### 2-1. 不正な `action` 値
- 行 1473-1476: `sidEntryEndpointBehavior(end_action, ...)` が `false` を返す場合 → `SWSS_LOG_ERROR("Invalid my_sid action %s", end_action.c_str())` → `return false`
- `doTaskMySidTable` で `SWSS_LOG_ERROR("Failed to create/update my_sid entry for sid %s")` (行 1247)

### 2-2. VRF が存在しない（DT 系 action）
- 行 1498-1501: `m_vrfOrch->isVRFexists(dt_vrf)` が false → `SWSS_LOG_ERROR("VRF %s doesn't exist in DB", dt_vrf.c_str())` → `return false`
- 行 1492-1495: VRF が DB に存在するが SAI OID が null → `SWSS_LOG_ERROR("VRF object not created for DT VRF %s")` → `return false`

### 2-3. ECMP adjacency（複数 adj）未サポート
- 行 1516-1519: `adjv.size() > 1` → `SWSS_LOG_ERROR("Failed to create my_sid entry %s adj %s: ECMP adjacency not yet supported")` → `return false`（即時失敗、リトライなし）

### 2-4. Nexthop（adj）未解決 → pending キュー
- 行 1528-1534: nexthop OID が null → `m_pendingSRv6MySIDEntries[nexthop].insert(...)` → `return false`（SAI 未登録）
- 行 1539-1542: nexthop が NeighOrch に存在しない → 同様に pending → `return false`
- NeighOrch から neighbor ADD イベントが届いた時点で `updateNeighbor()` が再インストールを試みる（行 1236-1248）
- neighbor ADD でも `createUpdateMysidEntry()` が再度失敗した場合はエントリを pending に残したまま `continue`（行 1247-1249）

### 2-5. IPinIP トンネル作成失敗（`un` / `udt46` + DSCP mode 設定時）
- 行 1554-1557: `createMySidIpInIpTunnel()` 失敗 → `return false`
- 行 1561-1565: `createMySidIpInIpTunnelTermEntry()` 失敗 → `removeMySidIpInIpTunnel()` を呼んでロールバック → `return false`
- 行 508-509: `sai_router_intfs_api->create_router_interface()` 失敗 → `SWSS_LOG_ERROR("Failed to create overlay router interface for MySID IPinIP tunnel: %d")`
- 行 541-542: `sai_tunnel_api->create_tunnel()` 失敗 → `SWSS_LOG_ERROR("Failed to create MySID IPinIP tunnel: %d")`
- 行 652-653: `create_tunnel_term_table_entry()` 失敗 → `SWSS_LOG_ERROR("Failed to create tunnel termination entry for MySID - %d")`

### 2-6. 不正な DSCP mode 文字列（CONFIG_DB `SRV6_MY_SIDS.decap_dscp_mode`）
- 行 388-392: `mySidDscpModeToSai(*cfg, ...)` が false → `SWSS_LOG_ERROR("Invalid MySID %s DSCP mode: %s")` → 早期 return（キャッシュ未登録）

### 2-7. ロケータが CONFIG_DB に存在しない
- 行 337-338: `m_locatorCfgTable.get(locator, fvs)` が false → `SWSS_LOG_ERROR("Failed to get the SRv6 locator %s - not present in the CONFIG_DB")` → `return false`
- 行 468-469: 複数ロケータ候補から一致するものが見つからない → `SWSS_LOG_ERROR("Cannot find a locator in the CONFIG DB for MySID Entry %s")` → `return false`

### 2-8. SAI create_my_sid_entry 失敗
- 行 1607-1610: `sai_srv6_api->create_my_sid_entry()` が失敗 → `SWSS_LOG_ERROR("Failed to create my_sid entry %s, rv %d")` → `return false`

### 2-9. DEL 時：エントリが存在しない
- 行 1662-1663: `srv6_my_sid_table_.find(my_sid_string) == end()` → `SWSS_LOG_ERROR("My_sid_entry doesn't exist for %s")` → `return false`

### 2-10. カウンタ作成失敗
- 行 190-191: `sai_counter_api->create_counter()` 失敗 → `SWSS_LOG_ERROR("Failed to create SAI counter for SRv6 MySID entry")` → `return false`（SID エントリ全体の作成を中断）

---

## 3. PIC_CONTEXT_TABLE — 失敗ケース

### 3-1. SET（update）試行 → task_duplicated
- 行 2280-2283: `it != srv6_pic_context_table_.end()`（既存エントリへの SET）→ `SWSS_LOG_ERROR("update is not allowed for pic context table")` → `task_duplicated`（PIC コンテキストは不変；update 不可）

### 3-2. nexthop と vpn_sid の数が不一致
- 行 2298-2302: `pci.nexthops.size() != pci.sids.size()` → `SWSS_LOG_ERROR("inconsistent number of endpoints(%zu) and vpn sids(%zu)")` → `task_failed`（再試行なし）

### 3-3. VPN 作成失敗 → task_need_retry
- 行 2305-2308: `createSrv6Vpns()` が false → `SWSS_LOG_ERROR("Failed to create SRv6 VPNs for context id %s")` → `task_need_retry`（次のイベントループで再試行）
- p2p トンネル未作成時（エンドポイントとの P2P トンネルが未確立）がこのケースの主因（行 2083: `SWSS_LOG_ERROR("Tunnel map for endpoint %s does not exist")`）

### 3-4. DEL 時：ref_count > 0（routeorch から参照中）
- 行 2321-2328: `it->second.ref_count != 0` → `addToRetry()` でリトライキューに追加 → `task_need_retry`
- ref_count は `decreasePicContextIdRefCount()` で 0 になった時点で DEL が再実行される

### 3-5. DEL 時：VPN 削除失敗
- 行 2330-2333: `deleteSrv6Vpns()` が false → `SWSS_LOG_ERROR("Failed to delete SRv6 VPNs for context id %s")` → `task_need_retry`

### 3-6. 予期しない refcount 操作
- 行 1819: `SWSS_LOG_ERROR("Unexpected refcount increase for context id %s")` — routeorch が存在しないコンテキスト ID を参照しようとした場合
- 行 1828: `SWSS_LOG_ERROR("Unexpected refcount decrease for context id %s")`

---

## 4. task_process_status マッピング

| status | 意味 | doTask() の処理 |
|--------|------|----------------|
| `task_success` | 成功 | エントリを m_toSync から削除 |
| `task_failed` | 非リトライ失敗 | エントリを m_toSync から削除（ログのみ） |
| `task_need_retry` | 一時的失敗 | `it++` して次回イベントループで再試行 |
| `task_duplicated` | 重複 SET | エントリを m_toSync から削除（警告） |
| `task_ignore` | 無視 | エントリを m_toSync から削除（何もしない） |

根拠: `srv6orch.cpp:2352-2394`（`doTask()` のメインループ）

---

## 5. SAI エラー伝播パターン

- `sai_srv6_api->*` の戻り値（`sai_status_t`）を直接チェックし、`SAI_STATUS_SUCCESS` 以外は `SWSS_LOG_ERROR` + `return false`
- `false` は呼び出し元で `task_failed` または `task_need_retry` にマップされる
- カウンタ / トンネル / RIF の部分的作成で失敗した場合、作成済みオブジェクトのロールバックは限定的（`createMySidIpInIpTunnelTermEntry` 失敗時のみ `removeMySidIpInIpTunnel` を呼ぶ、行 1564）
