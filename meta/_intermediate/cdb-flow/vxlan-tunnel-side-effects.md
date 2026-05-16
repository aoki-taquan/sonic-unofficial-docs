# VXLAN_TUNNEL — 副次 DB 書込 (Phase F)

ソース: `sonic-swss/orchagent/vxlanorch.cpp`, `sonic-swss/cfgmgr/vxlanmgr.cpp`

---

## 1. APPL_DB — APP_VXLAN_TUNNEL_TABLE

| 操作 | トリガ | 書込経路 |
|------|-------|---------|
| SET | CONFIG_DB に `VXLAN_TUNNEL` エントリが作成される | `vxlanmgrd` の `doVxlanTunnelCreateTask()` が `m_appVxlanTunnelTable.set(name, fvs)` を呼ぶ (`vxlanmgr.cpp:432`) |
| DEL | CONFIG_DB から `VXLAN_TUNNEL` エントリが削除され、NVO / MAP 参照がゼロになる | `doVxlanTunnelDeleteTask()` が `m_appVxlanTunnelTable.del(name)` を呼ぶ (`vxlanmgr.cpp:463`) |

書き込まれるフィールド: CONFIG_DB のフィールドをそのまま転送 (`kfvFieldsValues(t)` をそのまま渡す)。

---

## 2. STATE_DB — STATE_VXLAN_TUNNEL_TABLE

| 操作 | トリガ | 書込経路 | 書込フィールド |
|------|-------|---------|--------------|
| SET (初回登録) | `VxlanTunnelOrch` が SAI トンネルを生成した直後 (`addRemoveStateTableEntry(…, add=true)`) | `m_stateVxlanTable.set(tunnel_name, fvVector)` (`vxlanorch.cpp:1943`) | `src_ip`, `dst_ip`, `tnl_src`(`CLI`\|`EVPN`), `operstatus`=`down` |
| SET (oper 更新) | SAI port oper status 変化イベント (`updateDbTunnelOperStatus()`) | `m_stateVxlanTable.set(tunnel_name, fvVector)` (`vxlanorch.cpp:1910`) | `operstatus`=`up`\|`down` |
| DEL | `addRemoveStateTableEntry(…, add=false)` — トンネル削除時 | `m_stateVxlanTable.del(tunnel_name)` (`vxlanorch.cpp:1953`) | — |

ウォームブート時の例外: `WarmStart::INITIALIZED` 状態かつ既に STATE_DB にエントリがある場合は SET をスキップし既存エントリを保持 (`vxlanorch.cpp:1927-1948`)。

---

## 3. ASIC_DB — SAI tunnel オブジェクト

orchagent は直接 ASIC_DB に書くのではなく SAI API 経由で syncd が書く。  
該当する SAI 呼び出しと生成されるオブジェクト:

| SAI API 呼び出し | オブジェクト種別 | トリガ |
|----------------|--------------|-------|
| `sai_tunnel_api->create_tunnel()` | `SAI_OBJECT_TYPE_TUNNEL` (VXLAN) | `VxlanTunnel::createTunnel()` (`vxlanorch.cpp:397`) |
| `sai_tunnel_api->create_tunnel_term_table_entry()` | `SAI_OBJECT_TYPE_TUNNEL_TERM_TABLE_ENTRY` | `VxlanTunnel::createTunnelTermEntry()` (`vxlanorch.cpp:482`) |
| `sai_tunnel_api->create_tunnel_map()` | `SAI_OBJECT_TYPE_TUNNEL_MAP` (VNI↔VLAN 等) | `createTunnelMapperHw()` (`vxlanorch.cpp:141`) |
| `sai_tunnel_api->create_tunnel_map_entry()` | `SAI_OBJECT_TYPE_TUNNEL_MAP_ENTRY` | `createTunnelMapperEntryHw()` (`vxlanorch.cpp:211`) |
| `sai_tunnel_api->remove_tunnel()` 他 | 各 SAI オブジェクト削除 | tunnel / map 削除パス |

主な SAI 属性:
- `SAI_TUNNEL_ATTR_TYPE` = `SAI_TUNNEL_TYPE_VXLAN`
- `SAI_TUNNEL_ATTR_PEER_MODE` = `P2P`(dst_ip 指定時) / `P2MP`(省略時)
- `SAI_TUNNEL_ATTR_ENCAP_SRC_IP` = src_ip
- `SAI_TUNNEL_ATTR_DECAP_TTL_MODE` = `PIPE` / `UNIFORM` (ttl_mode 指定時のみ)

---

## 4. カーネル netlink — VXLAN netdevice

`vxlanmgrd` は SAI 経由ではなく `ip` / `bridge` / `brctl` コマンドでカーネル netlink を直接操作する。

| netlink 操作 | コマンド | トリガ |
|-------------|---------|-------|
| VXLAN netdevice 作成 | `ip link add <name> type vxlan id <vni> local <src_ip> dstport 4789 nolearning` | `createVxlanNetdevice()` (`vxlanmgr.cpp:56-73`) |
| netdevice UP | `ip link set dev <name> up` | `createVxlanNetdevice()` (`vxlanmgr.cpp:73`) |
| bridge デバイス作成 | `ip link add <bridge> type bridge` | `createBridgeNetdevice()` (`vxlanmgr.cpp:83`) |
| bridge に MAC 設定 | `ip link set dev <bridge> address <mac>` | `createBridgeNetdevice()` (`vxlanmgr.cpp:103`) |
| bridge への enslaving | `ip link set dev <vxlan> master <bridge>` | `createBridgeNetdevice()` (`vxlanmgr.cpp:114`) |
| FDB learning 無効化 | `bridge link set dev <vxlan> learning off` | EVPN NVO 登録後 (`vxlanmgr.cpp:146`) |
| VXLAN netdevice 削除 | `ip link del dev <name>` | `deleteVxlanNetdevice()` (`vxlanmgr.cpp:135`) |
| bridge 削除 | `ip link del <bridge>` | `deleteBridgeNetdevice()` (`vxlanmgr.cpp:164`) |

ハードコード値: `dstport 4789`、`nolearning` フラグは設定フィールドなしで常に付与される。

---

## 5. COUNTERS_DB — COUNTERS_TUNNEL_NAME_MAP / COUNTERS_TUNNEL_TYPE_MAP

| 操作 | 書込先 | トリガ |
|------|-------|-------|
| SET | `COUNTERS_TUNNEL_NAME_MAP` / `COUNTERS_TUNNEL_TYPE_MAP` | `VxlanTunnelOrch::doTask(timer)` — SAI OID が VIDTORID に登録された後 Flex Counter に登録 (`vxlanorch.cpp:1328-1329`) |
| DEL | 同上 | トンネル削除時 `hdel()` (`vxlanorch.cpp:1365-1366`) |

---

## 書込タイミングまとめ

```
CONFIG_DB SET
  └─ vxlanmgrd
       ├─ APPL_DB APP_VXLAN_TUNNEL_TABLE SET  (即時)
       └─ kernel netlink: ip link add (VNI MAP 追加時)
            └─ orchagent (APP_DB consumer)
                 ├─ SAI create_tunnel → syncd → ASIC_DB
                 ├─ STATE_DB VXLAN_TUNNEL_TABLE SET (src_ip, dst_ip, tnl_src, operstatus=down)
                 └─ COUNTERS_DB COUNTERS_TUNNEL_NAME_MAP (非同期, FlexCounter timer)
                      └─ operstatus UP: SAI port event → STATE_DB SET operstatus=up
```
