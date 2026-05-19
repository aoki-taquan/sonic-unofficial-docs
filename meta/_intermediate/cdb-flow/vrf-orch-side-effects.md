# vrf-orch — 副次 DB 書込 (Phase F) 調査ノート

調査日: 2026-05-19
対象ファイル:
- sonic-swss/orchagent/vrforch.cpp
- sonic-swss/orchagent/vrforch.h
- sonic-swss/orchagent/flex_counter/flowcounterrouteorch.cpp
- sonic-swss/orchagent/flex_counter/flowcounterrouteorch.h
- sonic-swss/orchagent/portsorch.cpp

## 1. STATE_DB VRF_OBJECT_TABLE 書込み

VRFOrch::addOperation が `create_virtual_router()` / `set_virtual_router_attribute()` に成功した後、
`m_stateVrfObjectTable.set(vrf_name, vfv)` で `state=ok` を書く (vrforch.cpp:120, 150)。

VRFOrch::delOperation が `remove_virtual_router()` に成功した後、
`m_stateVrfObjectTable.del(vrf_name)` でエントリを削除する (vrforch.cpp:193)。

この 2 エントリは vrfmgrd が `isVrfObjExist()` で監視し、VRF Linux デバイス削除のタイミング制御に使う。

## 2. FlowCounterRouteOrch への VR 登録通知

vrforch.cpp:110: `gFlowCounterRouteOrch->onAddVR(router_id)`
vrforch.cpp:184: `gFlowCounterRouteOrch->onRemoveVR(router_id)`

flowcounterrouteorch.cpp:401-431 の onAddVR 実装:
- `mRouteFlowCounterSupported` が false なら即 return（VS / SAI 未対応環境）
- VRF 名を `getVRFname(vrf_id)` で解決
- `mRoutePatternSet` 内に一致する vrf_name を持つパターンがあれば `createRouteFlowCounterByPattern()` を呼ぶ
- COUNTERS_DB / FLEX_COUNTER_DB にフローカウンタエントリを作成

flowcounterrouteorch.cpp:434-451 の onRemoveVR 実装:
- `mRouteFlowCounterSupported` が false なら即 return
- 一致するパターンの `removeRoutePattern()` + `vrf_id = SAI_NULL_OBJECT_ID` でリセット

## 3. PortsOrch::updateL3VniStatus — VLAN VE 状態変更

VNI 付き VRF のみ。addVrfVNIMap (vrforch.cpp:222-241) にて:
- `VxlanTunnelOrch::getVlanMappedToVni(vni)` で vlan_id を取得
- vlan_id != 0 の場合のみ `gPortsOrch->updateL3VniStatus(vlan_id, true)` を呼ぶ

portsorch.cpp:10326-10359 の updateL3VniStatus 実装:
- `m_up_member_count` のインクリメント / デクリメント
- 0→1 遷移時に `m_oper_status = SAI_PORT_OPER_STATUS_UP`
- 0 への遷移時に `m_oper_status = SAI_PORT_OPER_STATUS_DOWN`
- これはインメモリ構造体のみの変更。DB 書込みは発生しない

delVrfVNIMap (vrforch.cpp:261-269) にて同様に `updateL3VniStatus(vlan_id, false)` が呼ばれる。
戻り値 (bool) は無視される。

## 4. その他 — APPL_DB / CONFIG_DB / COUNTERS_DB への直接書込みなし

VRFOrch は `ProducerStateTable` / `NotificationProducer` を保持しない。
APPL_DB / CONFIG_DB への直接書込みは一切ない。
COUNTERS_DB への直接書込みも VRFOrch 自身では行わない（FlowCounterRouteOrch 経由のみ）。
