# VLAN_SUB_INTERFACE — 値依存挙動メモ

## admin_status: up / down
- `up` → ip link set <sub-if> up (intfmgr.cpp経由)
- `down` → ip link set <sub-if> down
- 省略時: "up" が補完 (intfmgr.cpp)

## vlan: 1..4094
- short-name 形式では vlan leaf が必須。0 または空 → "Vlan ID not configured" でリトライ待ち (intfmgr.cpp)
- YANG: uint16 1..4094

## loopback_action: drop / forward
- sonic-types.yang: pattern "drop|forward"
- drop → 同一 IF にルートバックするパケットをドロップ
- forward → 転送

## vrf_name / vnet_name
- 対応 VRF/VNET が STATE_DB に存在しない場合はリトライ待ち (intfmgr.cpp)

## mtu
- 省略時: MTU_INHERITANCE (親 IF の MTU を継承)
- 明示指定 → ip link set <sub-if> mtu <val>

Sources:
- sonic-swss/cfgmgr/intfmgr.cpp
- sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan-sub-interface.yang
