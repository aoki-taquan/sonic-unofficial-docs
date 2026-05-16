# VRF 副次 DB 書込 詳細分析 (Phase F)

> 調査日: 2026-05-16
> ソース: `sonic-swss/orchagent/vrforch.cpp`, `sonic-swss/cfgmgr/vrfmgr.cpp`

## 概要

`VRF` テーブルへの SET/DEL が CONFIG_DB 外へ引き起こす書込みを、処理プロセスごとに整理する。

---

## 1. vrfmgrd (cfgmgr/vrfmgr.cpp)

CONFIG_DB `VRF` を購読し、Linux VRF デバイス作成と下流 DB への書込みを担当する。

### 1-1. SET 時副次書込み

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_stateVrfTable.set(vrfName, [{state:"ok"}])` | STATE_DB / `VRF_TABLE` | `<name>` field=`state` | Linux netdev 作成成功後 (vrfmgr.cpp:289) |
| `m_appVrfTableProducer.set(vrfName, fields)` | APPL_DB / `VRF_TABLE` | `<name>` | VRF_TABLE または MGMT_VRF_CONFIG 経由 (vrfmgr.cpp:303) |
| `m_appVxlanVrfTableProducer.set(key, [{vni,vrf}])` | APPL_DB / `VXLAN_VRF_TABLE` | `<tunnel>:evpn_map_<vni>_<vrf>` | `vni` 非ゼロ かつ EVPN NVO トンネル設定済み (vrfmgr.cpp:521) |
| `m_appVnetTableProducer.set(vrfName, fields)` | APPL_DB / `VNET_TABLE` | `<name>` | VNET テーブル経由 SET の場合のみ (vrfmgr.cpp 別分岐) |

カーネル副作用 (DB 外):
- `ip link add <name> type vrf table <id>` — VRF デバイス作成（mgmt VRF はスキップ）
- `ip link set <name> up` — VRF デバイス UP

### 1-2. DEL 時副次書込み

| 操作 | 対象 DB / テーブル | キー | 条件 |
|------|------------------|------|------|
| `m_appVrfTableProducer.del(vrfName)` | APPL_DB / `VRF_TABLE` | `<name>` | STATE_DB に該当エントリが存在する場合 (vrfmgr.cpp:338) |
| `m_stateVrfTable.del(vrfName)` | STATE_DB / `VRF_TABLE` | `<name>` | 同上 (vrfmgr.cpp:339) |
| `m_appVxlanVrfTableProducer.del(key)` | APPL_DB / `VXLAN_VRF_TABLE` | `<tunnel>:evpn_map_<vni>_<vrf>` | `vni` マッピングが存在する場合 (vrfmgr.cpp:524) |

カーネル副作用: `ip link del <name>`（mgmt VRF は `recycleTable()` のみ）。

DEL 遅延条件: orchagent が `STATE_DB.VRF_OBJECT_TABLE|<name>` を保持する間、`isVrfObjExist()` で DEL をブロックし無制限待機 (vrfmgr.cpp:331–345)。

---

## 2. VRFOrch (orchagent/vrforch.cpp)

APPL_DB `VRF_TABLE` を購読し、SAI 呼び出しと STATE_DB 書込み、orchagent 内部副次操作を行う。

### 2-1. addOperation — VRF 新規作成 / 更新

**STATE_DB 書込み:**

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_stateVrfObjectTable.hset(vrf_name, "state", "ok")` | STATE_DB / `VRF_OBJECT_TABLE` | `<name>` field=`state` | SAI create_virtual_router 成功後、新規 (vrforch.cpp:120) |
| `m_stateVrfObjectTable.hset(vrf_name, "state", "ok")` | STATE_DB / `VRF_OBJECT_TABLE` | `<name>` field=`state` | SAI set 成功後、更新 (vrforch.cpp:150) |

**SAI 副作用 (ASIC_DB 経由):**
- `sai_virtual_router_api->create_virtual_router(...)` — VR OID 新規生成 (vrforch.cpp:93)
- `sai_virtual_router_api->set_virtual_router_attribute(...)` — 属性更新 (vrforch.cpp:131)

**orchagent 内部副次操作 (DB 外):**
- `gFlowCounterRouteOrch->onAddVR(router_id)` — フローカウンターへの VR 登録 (vrforch.cpp:110)
- `gPortsOrch->updateL3VniStatus(vlan_id, true)` — VLAN VE インタフェース UP。VNI に対応する VLAN マッピングが存在する場合のみ (vrforch.cpp:239、`updateVrfVNIMap` 内)

**VNI マッピング処理 (`updateVrfVNIMap`):**
- `vrf_vni_map_table_[vrf_name] = vni` — orchagent 内部マップ更新
- `l3vni_table_[vni].{vlan_id, l3_vni}` — L3 VNI テーブル更新
- `evpn_orch->getEVPNVtep()` — EVPN VTEP 存在確認（未設定なら `return false`）(vrforch.cpp:225–230)

### 2-2. delOperation — VRF 削除

**STATE_DB 書込み:**

| 操作 | 対象 DB / テーブル | キー | 条件 |
|------|------------------|------|------|
| `m_stateVrfObjectTable.del(vrf_name)` | STATE_DB / `VRF_OBJECT_TABLE` | `<name>` | SAI remove_virtual_router 成功後 (vrforch.cpp:193) |

**SAI 副作用 (ASIC_DB 経由):**
- `sai_virtual_router_api->remove_virtual_router(router_id)` — VR OID 削除 (vrforch.cpp:173)

**orchagent 内部副次操作 (DB 外):**
- `gFlowCounterRouteOrch->onRemoveVR(router_id)` — フローカウンターから VR 解除 (vrforch.cpp:184)
- `gPortsOrch->updateL3VniStatus(vlan_id, false)` — VLAN VE インタフェース DOWN。VNI に対応する VLAN マッピングが存在する場合のみ (vrforch.cpp:267、`delVrfVNIMap` 内)
- `l3vni_table_.erase(vni)` / `vrf_vni_map_table_.erase(vrf_name)` — orchagent 内部マップ削除

DEL ブロック条件: `vrf_table_[vrf_name].ref_count > 0` → `return false` → Consumer キューに残留。ref_count がゼロになるまで無制限待機 (vrforch.cpp:169–170)。

---

## 3. STATE_DB / APPL_DB スキーマまとめ

| 論理役割 | DB | テーブル名定数 | 実テーブル名 | 書込みプロセス |
|---------|-----|--------------|------------|--------------|
| VRF readiness sentinel | STATE_DB | `STATE_VRF_TABLE_NAME` | `VRF_TABLE` | vrfmgrd |
| SAI VR object sentinel | STATE_DB | `STATE_VRF_OBJECT_TABLE_NAME` | `VRF_OBJECT_TABLE` | VRFOrch |
| APPL VRF エントリ | APPL_DB | `APP_VRF_TABLE_NAME` | `VRF_TABLE` | vrfmgrd |
| APPL VXLAN-VRF マップ | APPL_DB | `APP_VXLAN_VRF_TABLE_NAME` | `VXLAN_VRF_TABLE` | vrfmgrd |
| APPL VNET エントリ | APPL_DB | `APP_VNET_TABLE_NAME` | `VNET_TABLE` | vrfmgrd |

スキーマ定義: `sonic-swss-common/common/schema.h:429-430` (STATE_DB) / `schema.h:80-84` (APPL_DB)

---

## 4. APPL_STATE_DB

VRF テーブルに対する直接的な APPL_STATE_DB 書込みは存在しない。`vrfmgrd` は APPL_DB（db_id=0）の `VRF_TABLE` に書き込み、STATE_DB（db_id=6）の `VRF_TABLE` / `VRF_OBJECT_TABLE` に書き込む。APPL_STATE_DB（db_id=14）は VRF 経路では使用されない。

---

## 5. 確認コマンド

```bash
# STATE_DB VRF readiness sentinel
sonic-db-cli STATE_DB hgetall 'VRF_TABLE|VrfRed'

# STATE_DB SAI VR object sentinel
sonic-db-cli STATE_DB hgetall 'VRF_OBJECT_TABLE|VrfRed'

# APPL_DB VRF エントリ
sonic-db-cli APPL_DB hgetall 'VRF_TABLE:VrfRed'

# APPL_DB VXLAN VRF マップ
sonic-db-cli APPL_DB hgetall 'VXLAN_VRF_TABLE:vtep1:evpn_map_10001_VrfRed'
```
