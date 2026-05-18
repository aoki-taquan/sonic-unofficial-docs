# VXLAN_TUNNEL_MAP — Phase F 副作用スキャンノート

対象テーブル: `VXLAN_TUNNEL_MAP`
Consumer: `vxlanmgrd` (VxlanMgr) → `orchagent` (VxlanTunnelMapOrch)
スキャン範囲: `sonic-swss/cfgmgr/vxlanmgr.cpp`, `sonic-swss/orchagent/vxlanorch.cpp`

---

## 検出した副作用

### SET 時の副作用

#### 1. カーネル VXLAN net device 生成 (vxlanmgrd)

`doVxlanTunnelMapCreateTask()` → `createVxlanNetdevice()` が以下のカーネルオブジェクトを順番に作成する:

1. `ip link add <tunnel>-<vlan_id> type vxlan id <vni> local <src_ip> nolearning dstport 4789`
2. `ip link set <tunnel>-<vlan_id> master Bridge`
3. `bridge vlan add vid <vlan_id> dev <tunnel>-<vlan_id>`
4. `bridge vlan add vid <vlan_id> untagged pvid dev <tunnel>-<vlan_id>`
5. （vlan_id != 1 の場合）`bridge vlan del vid 1 dev <tunnel>-<vlan_id>`
6. （EVPN NVO 存在時）`bridge link set dev <tunnel>-<vlan_id> learning off`
7. `ip link set <tunnel>-<vlan_id> up`

evidence: `vxlanmgr.cpp:1003-1051`

#### 2. STATE_DB NEIGH_SUPPRESS_VLAN_TABLE への書き込み (vxlanmgrd)

VXLAN MAP 作成成功後、`Vlan<id>` key に `netdev=<tunnel>-<vlan_id>` を書き込む。
vlanmgrd が ARP/ND Suppression フラグを更新するためのシグナル。

evidence: `vxlanmgr.cpp:613-618`

#### 3. APP_DB VXLAN_TUNNEL_MAP への書き込み (vxlanmgrd → orchagent)

`createAppDBTunnelMapTable(t)` でエントリが APP_DB に転記される (vxlanmgr.cpp:592)。
orchagent の VxlanTunnelMapOrch が APP_DB を購読し、SAI 操作を実行する。

evidence: `vxlanmgr.cpp:592`, `orchdaemon.cpp:352`

#### 4. SAI トンネルオブジェクト一括生成（初回 MAP エントリ時のみ）(orchagent)

`VxlanTunnelMapOrch::addOperation()` は `tunnel_obj->isActive()` が false の場合に `createTunnelHw(TUNNEL_MAP_USE_DEDICATED_ENCAP_DECAP)` を呼ぶ:
- `create_tunnel_map()` — encap/decap 各マッパー (vxlanorch.cpp:759-776)
- `create_tunnel()` — SAI トンネルオブジェクト
- `create_tunnel_term_table_entry()` — トンネル終端エントリ
- `gPortsOrch->addTunnel()` + `addBridgePort()` — トンネルポートのカーネルポート/SAI ブリッジポート登録

**2 枚目以降の MAP エントリ追加では SAI トンネル再作成は発生しない。**

evidence: `vxlanorch.cpp:2063-2087`

#### 5. `vxlan_vni_vlan_map_table_` 内部状態更新 (orchagent)

`tunnel_orch->addVlanMappedToVni(vni_id, vlan_id)` により orchagent 内部の VNI→VLAN マップが更新される。
EVPN remote 動的 DIP トンネル処理時にこのマップが参照される。

evidence: `vxlanorch.cpp:2120`, `vxlanorch.h:354-357`

---

### DEL 時の副作用

#### 1. カーネル VXLAN net device 削除 (vxlanmgrd)

`ip link set dev <tunnel>-<vlan_id> down` → `ip link del dev <tunnel>-<vlan_id>`

evidence: `vxlanmgr.cpp:655-656`, `vxlanmgr.cpp:1056-1069`

#### 2. STATE_DB NEIGH_SUPPRESS_VLAN_TABLE エントリ削除 (vxlanmgrd)

`m_stateNeighSuppressVlanTable.del("Vlan<id>")` により ARP/ND suppression 設定が解除される。

evidence: `vxlanmgr.cpp:668`

#### 3. 最終 MAP 削除時: SAI トンネルオブジェクト削除 (orchagent)

`vlan_vrf_vni_count == 0` になった時点で `deleteTunnelHw()` が呼ばれ、SAI マッパー・トンネル・トンネル終端が削除される。
DIP トンネルが残存している場合は `del_tnl_hw_pending = true` で削除が遅延し、MAP 追加がブロックされる。

evidence: `vxlanorch.cpp:2180-2226`

#### 4. EVPN MAC/IP ルート連動削除

VXLAN MAP が削除されると、対応する EVPN type-2/3 経路と紐付いた MAC/IP エントリが自動削除される（`VxlanTunnelMapOrch` → EVPN ルート管理経由）。

evidence: `vxlanorch.cpp` runtime-trace 段階 4 の記述

---

## 副作用マトリクスサマリ

| 副作用 | 対象 | SET | DEL |
|--------|------|-----|-----|
| カーネル VXLAN net device (`<tunnel>-<vlan_id>`) | Linux kernel | 作成・UP | DOWN → 削除 |
| `STATE_DB NEIGH_SUPPRESS_VLAN_TABLE.<Vlan>` | STATE_DB | `netdev=<dev>` 書込み | エントリ削除 |
| `APP_DB APP_VXLAN_TUNNEL_MAP_TABLE` | APP_DB | エントリ書込み | エントリ削除 |
| SAI tunnel-map + tunnel + tunnel-term | SAI/HW | 初回 SET 時のみ作成 | 最終 DEL 時のみ削除 |
| orchagent 内部 `vxlan_vni_vlan_map_table_` | orchagent memory | VNI→VLAN 登録 | 削除 |
| EVPN MAC/IP ルート | FDB/ルートテーブル | なし | 連動削除 |

source: `sonic-swss/cfgmgr/vxlanmgr.cpp`, `sonic-swss/orchagent/vxlanorch.cpp`
