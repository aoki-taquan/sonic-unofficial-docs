# vrf-orch — Phase C 暗黙参照テーブル (cross-refs) 調査メモ

調査日: 2026-05-19
対象ファイル:
- sonic-swss/orchagent/vrforch.cpp (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- sonic-swss/orchagent/vrforch.h  (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- sonic-swss/cfgmgr/vrfmgr.cpp   (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 参照関係まとめ

### CONFIG_DB 入力側

| テーブル | 参照元 | 参照内容 | evidence |
|---------|--------|---------|---------|
| `CONFIG_DB VRF\|<vrf_name>` | vrfmgrd `doTask(Consumer&)` | SET/DEL トリガ。kfvFieldsValues をそのまま APPL_DB VRF_TABLE へ転写 | vrfmgr.cpp:273-310 |
| `CONFIG_DB MGMT_VRF_CONFIG\|vrf_global` | vrfmgrd `doTask(Consumer&)` | `mgmtVrfEnabled` / `in_band_mgmt_enabled` を解釈して mgmt VRF の SET/DEL を決定。VRF 名は "mgmt" に固定 | vrfmgr.cpp:229-270 |
| `CONFIG_DB VXLAN_EVPN_NVO\|<nvo_name>` | vrfmgrd `doVrfEvpnNvoAddTask()` | EVPN VTEP tunnel 名を `m_evpnVxlanTunnel` にキャッシュ。VNI 付き VRF の APPL_DB VXLAN_VRF_TABLE 書込みに必要 | vrfmgr.cpp:373-396 |

### orchagent 内部参照（暗黙依存 Orch）

| 依存先 | 参照方向 | 条件 | evidence |
|--------|---------|------|---------|
| `EvpnNvoOrch::getEVPNVtep()` (via `gDirectory`) | VNI 付き VRF の EVPN VTEP 解決 | `addOperation` で `vni != 0` のとき。VTEP が null なら `false` 返却 → doTask 再試行 | vrforch.cpp:205, 225-229 |
| `VxlanTunnelOrch::getVlanMappedToVni(vni)` (via `gDirectory`) | VNI → VLAN ID 解決 | `updateVrfVNIMap()` 内。VLAN 0 なら `updateL3VniStatus` は呼ばれない | vrforch.cpp:207, 233-241 |
| `gPortsOrch->updateL3VniStatus(vlan_id, true/false)` | L3 VNI VLAN の VE インターフェイス UP/DOWN | VLAN ID が解決済みの場合のみ（vlan_id != 0）。VRF add/del/vni 変更時 | vrforch.cpp:239, 267, 285 |
| `gFlowCounterRouteOrch->onAddVR(router_id)` | フローカウンタへの VR 登録 | VRF create 成功後、SAI VR OID を引数に通知 | vrforch.cpp:110 |
| `gFlowCounterRouteOrch->onRemoveVR(router_id)` | フローカウンタへの VR 削除通知 | VRF remove 成功後 | vrforch.cpp:184 |

### STATE_DB 書込み（自己書込みと vrfmgrd 書込み）

| テーブル | 書込元 | タイミング | evidence |
|---------|--------|---------|---------|
| `STATE_DB VRF_TABLE\|<vrf_name>` state=ok | vrfmgrd | SET 受信直後、APPL_DB 書込み前 | vrfmgr.cpp:289 |
| `STATE_DB VRF_TABLE\|<vrf_name>` DEL | vrfmgrd | DEL 時、VRF_OBJECT_TABLE が消えた後 | vrfmgr.cpp:339 |
| `STATE_DB VRF_OBJECT_TABLE\|<vrf_name>` state=ok | VRFOrch | `addOperation`/`set_virtual_router` 成功後 | vrforch.cpp:120, 150 |
| `STATE_DB VRF_OBJECT_TABLE\|<vrf_name>` DEL | VRFOrch | `delOperation`/`remove_virtual_router` 成功後 | vrforch.cpp:193 |

### APPL_DB 書込み（vrfmgrd の副次書込み）

| テーブル | 書込元 | タイミング | evidence |
|---------|--------|---------|---------|
| `APPL_DB VXLAN_VRF_TABLE\|<nvo>:evpn_map_<vni>_<vrf>` | vrfmgrd `doVrfVxlanTableUpdate()` | VNI 付き VRF の SET/DEL 時、EVPN NVO 設定済みの場合 | vrfmgr.cpp:510-528 |
