# srv6-my-sids — Phase C: Cross-references

Generated: 2026-05-17
Source: sonic-swss orchagent/srv6orch.cpp, sonic-buildimage src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py, sonic-srv6.yang

## 読込み元テーブル（SRV6_MY_SIDS が依存するテーブル）

### CONFIG_DB: SRV6_MY_LOCATORS
- YANG leafref: `sonic-srv6.yang:108-110` — `locator_name` フィールドは `/SRV6_MY_LOCATORS/SRV6_MY_LOCATORS_LIST/locator_name` へのリファレンス
- bgpcfgd runtime check: `managers_srv6.py:62-68` — `directory.path_exist("SRV6_MY_LOCATORS", locator_name)` が false の場合、依存を登録して `return False`
- bgpcfgd uses locator object: `managers_srv6.py:71-74` — `directory.get("SRV6_MY_LOCATORS", locator_name)` でロケータオブジェクトを取得し `prefix` を検証
- Srv6Orch: `srv6orch.cpp:331-350` — `getLocatorCfgFromDb()` で `m_locatorCfgTable`（CFG_DB SRV6_MY_LOCATORS）を直接読み、block_len/node_len/func_len/arg_len を取得して MY_SID エントリのロケータビット長を決定

### CONFIG_DB: VRF
- YANG leafref: `sonic-srv6.yang:123-125` — `decap_vrf` フィールドは `/VRF/VRF_LIST/name` へのリファレンス
- Srv6Orch runtime check: `srv6orch.cpp:1488` — `m_vrfOrch->isVRFexists(dt_vrf)` が false の場合 `return false`（エラーログ出力、自動再試行なし）
- VRF "default": `srv6orch.cpp:1484-1486` — `dt_vrf == "default"` の場合は `gVirtualRouterId` に直接解決（VRF テーブル参照不要）

### APP_DB: NEIGH_TABLE / NeighOrch（隣接ノード）
- 条件依存: `end.x` / `ua` 等 `mySidNextHopRequired()` が true の action に限定
- `srv6orch.cpp:1524` — `m_neighOrch->hasNextHop(nexthop)` / `getNextHopId(nexthop)` で隣接解決
- 未解決時: `srv6orch.cpp:1532-1534` — `m_pendingSRv6MySIDEntries` にエントリを保留、隣接 ADD イベント受信時に `updateNeighbor()` が自動再インストール（設定消失なし）

## 書込み先テーブル（SRV6_MY_SIDS が更新するテーブル）

### APP_DB: SRV6_MY_SID_TABLE
- bgpcfgd は CONFIG_DB を直接書かず FRR に push するため、orch 経路では Srv6Orch が `m_mysidTable`（APP_DB `APP_SRV6_MY_SID_TABLE_NAME`）から読む
- `srv6orch.cpp:104` — `m_mysidTable(applDb, APP_SRV6_MY_SID_TABLE_NAME)` で初期化; `doTask()` で APP_DB → SAI 方向を処理

### COUNTERS_DB: COUNTERS_SRV6_NAME_MAP
- `srv6orch.cpp:131,199,223` — MySID エントリ作成・削除時に `m_mysid_counters_table->set()` / `hdel()` で SID アドレス → counter OID のマッピングを記録
- 条件付き: `getMySidCountersSupported() && getMySidCountersEnabled()` が true の場合のみ（`srv6orch.cpp:1593`）

### SAI: SAI_OBJECT_TYPE_MY_SID_ENTRY
- `srv6orch.cpp:1606` — `sai_srv6_api->create_my_sid_entry()` で ASIC に投入
- CRM: `srv6orch.cpp:1612` — `gCrmOrch->incCrmResUsedCounter(CRM_SRV6_MY_SID_ENTRY)` で CRM リソースカウントをインクリメント

### SAI: SAI_OBJECT_TYPE_TUNNEL / TUNNEL_TERM_TABLE_ENTRY（uDT46 等のデカプセル動作）
- `srv6orch.cpp:1551-1576` — `mySidTunnelRequired()` が true の場合（uDT46 等）、`createMySidIpInIpTunnel()` および `createMySidIpInIpTunnelTermEntry()` で IPinIP トンネルと term entry を生成

## 逆参照（他テーブルが SRV6_MY_SIDS を参照）

なし（SRV6_MY_SIDS は末端テーブルであり他のテーブルから leafref 参照されない）

## FRR（vtysh）反映
- `managers_srv6.py:88-94` — bgpcfgd が `cfg_mgr.push_list()` で FRR に `segment-routing srv6 static-sids sid <prefix> locator <name> behavior <action> [vrf <vrf>]` コマンドを送信
- DEL: `managers_srv6.py:127-131` — `no sid <prefix> locator <name> behavior <action>` で FRR から削除

## VRF refcount 管理
- SET: `srv6orch.cpp:1639` — `m_vrfOrch->increaseVrfRefCount(dt_vrf)`
- DEL: `srv6orch.cpp:1683` — `m_vrfOrch->decreaseVrfRefCount(endVrfString)`
- VRF 削除はこの refcount が 0 になるまでブロックされる（VRFOrch 側の制御）

## NeighOrch refcount 管理
- SET: `srv6orch.cpp:1644` — `m_neighOrch->increaseNextHopRefCount(nexthop, 1)`
- DEL: `srv6orch.cpp:1689` — `m_neighOrch->decreaseNextHopRefCount(nexthop, 1)`
