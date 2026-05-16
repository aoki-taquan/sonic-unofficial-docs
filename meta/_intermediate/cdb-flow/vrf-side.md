# VRF SET/DEL 副次 DB 書込 分析 (Phase F)

ソース: `sonic-swss/cfgmgr/vrfmgr.cpp`, `sonic-swss/orchagent/vrforch.cpp`, `sonic-swss-common/common/schema.h`

## vrfmgrd (cfgmgr/vrfmgr.cpp)

CONFIG_DB `VRF` テーブルを購読し、Linux VRF デバイス作成と下流 DB への書込みを行う。

### SET — VRF|<name>

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_stateVrfTable.set(vrfName, [{state:"ok"}])` | STATE_DB / `VRF_TABLE` | `<name>` field=`state` | Linux netdev 作成後、常時 (vrfmgr.cpp:289) |
| `m_appVrfTableProducer.set(vrfName, kfvFieldsValues(t))` | APPL_DB / `VRF_TABLE` | `<name>` | CFG_VRF_TABLE_NAME または CFG_MGMT_VRF_CONFIG_TABLE_NAME からの SET (vrfmgr.cpp:303) |
| `m_appVxlanVrfTableProducer.set(key, [{vni,vrf}])` | APPL_DB / `VXLAN_VRF_TABLE` | `<tunnel>:evpn_map_<vni>_<vrf>` | `vni` フィールドが非ゼロ かつ EVPN NVO トンネルが設定済み (vrfmgr.cpp:521) |

カーネル変更 (副次 DB 書込ではなく Linux コマンド):
- `ip link add <name> type vrf table <id>` — VRF デバイス作成 (mgmt VRF の場合はスキップ)
- `ip link set <name> up` — VRF デバイス UP

### SET — VRF|mgmt (MGMT_VRF_CONFIG 経由)

`mgmtVrfEnabled=true` かつ `in_band_mgmt_enabled=true` の場合、`vrfName="mgmt"` として上記 SET と同等の処理。
mgmt VRF は `ip link add` をスキップし固定テーブル ID `6000` を使用。

### SET — VRF VNET テーブル経由

`CFG_VRF_TABLE_NAME` 以外のテーブルからの SET (VNET 系) の場合:
- `m_appVnetTableProducer.set(vrfName, kfvFieldsValues(t))` → APPL_DB / `VNET_TABLE`

### DEL — VRF|<name>

| 操作 | 対象 DB / テーブル | キー | 条件 |
|------|------------------|------|------|
| `m_appVrfTableProducer.del(vrfName)` | APPL_DB / `VRF_TABLE` | `<name>` | STATE_DB `VRF_TABLE` にエントリが存在する場合 (vrfmgr.cpp:338) |
| `m_stateVrfTable.del(vrfName)` | STATE_DB / `VRF_TABLE` | `<name>` | 同上 (vrfmgr.cpp:339) |
| `m_appVxlanVrfTableProducer.del(key)` | APPL_DB / `VXLAN_VRF_TABLE` | `<tunnel>:evpn_map_<vni>_<vrf>` | `vni` マッピングが存在する場合 (vrfmgr.cpp:524) |

カーネル変更: `ip link del <name>` — VRF デバイス削除 (mgmt VRF は `recycleTable()` のみ)

**DEL の遅延条件**: `isVrfObjExist()` が true (= orchagent が STATE_DB `VRF_OBJECT_TABLE` にエントリを持つ) の間は DEL をスキップしてキューに残す。orchagent が SAI VR を削除してから `m_stateVrfObjectTable.del()` が呼ばれるまで無制限に待機 (vrfmgr.cpp:331-345)。

---

## VRFOrch (orchagent/vrforch.cpp)

APPL_DB の `VRF_TABLE` を購読し、SAI 呼び出しと STATE_DB 書込みを行う。

### addOperation (APPL_DB VRF_TABLE SET)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_stateVrfObjectTable.hset(vrf_name, "state", "ok")` | STATE_DB / `VRF_OBJECT_TABLE` | `<name>` field=`state` | SAI create_virtual_router 成功後、新規作成時 (vrforch.cpp:120) |
| `m_stateVrfObjectTable.hset(vrf_name, "state", "ok")` | STATE_DB / `VRF_OBJECT_TABLE` | `<name>` field=`state` | SAI set 成功後、更新時 (vrforch.cpp:150) |

SAI 呼び出し (ASIC_DB へ反映):
- `sai_virtual_router_api->create_virtual_router(...)` — VR OID 新規生成
- `sai_virtual_router_api->set_virtual_router_attribute(...)` — 属性更新 (`v4`, `v6`, `src_mac`, `ttl_action`, `ip_opt_action`, `l3_mc_action`)
- `updateVrfVNIMap()` — VNI マッピング処理 (VxlanTunnelOrch 経由で ASIC_DB に反映)
- `gFlowCounterRouteOrch->onAddVR(router_id)` — フローカウンター登録

### delOperation (APPL_DB VRF_TABLE DEL)

| 操作 | 対象 DB / テーブル | キー | 条件 |
|------|------------------|------|------|
| `m_stateVrfObjectTable.del(vrf_name)` | STATE_DB / `VRF_OBJECT_TABLE` | `<name>` | SAI remove_virtual_router 成功後 (vrforch.cpp:193) |

SAI 呼び出し:
- `sai_virtual_router_api->remove_virtual_router(...)` — VR OID 削除
- `delVrfVNIMap()` — VNI マッピング解除
- `gFlowCounterRouteOrch->onRemoveVR(router_id)` — フローカウンター解除

**DEL ブロック条件**: `vrf_table_[vrf_name].ref_count > 0` の場合 `return false` → Consumer キューに残留。所属インタフェース・ルートが先に削除されて ref_count が 0 になるまで待機 (vrforch.cpp:169)。

---

## STATE_DB / APPL_DB スキーマまとめ

| 論理役割 | DB | テーブル名定数 | 実テーブル名 | スキーマ定義箇所 |
|---------|-----|--------------|------------|----------------|
| VRF readiness sentinel | STATE_DB | `STATE_VRF_TABLE_NAME` | `VRF_TABLE` | `schema.h:429` |
| SAI VR object sentinel | STATE_DB | `STATE_VRF_OBJECT_TABLE_NAME` | `VRF_OBJECT_TABLE` | `schema.h:430` |
| APPL VRF エントリ | APPL_DB | `APP_VRF_TABLE_NAME` | `VRF_TABLE` | `schema.h:80` |
| APPL VXLAN-VRF マップ | APPL_DB | `APP_VXLAN_VRF_TABLE_NAME` | `VXLAN_VRF_TABLE` | `schema.h:84` |
| APPL VNET エントリ | APPL_DB | `APP_VNET_TABLE_NAME` | `VNET_TABLE` | `schema.h:81` |

確認コマンド:
```bash
sonic-db-cli STATE_DB hgetall 'VRF_TABLE|VrfRed'
sonic-db-cli STATE_DB hgetall 'VRF_OBJECT_TABLE|VrfRed'
sonic-db-cli APPL_DB hgetall 'VRF_TABLE:VrfRed'
sonic-db-cli APPL_DB hgetall 'VXLAN_VRF_TABLE:vtep1:evpn_map_10001_VrfRed'
```
