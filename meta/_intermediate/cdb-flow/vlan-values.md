# VLAN — 値依存挙動メモ

## admin_status: up / down
- `up` → ip link set Vlan<id> up (vlanmgr.cpp:163-176)
- `down` → ip link set Vlan<id> down
- 省略時: "up" が自動補完 (vlanmgr.cpp:424)

## mtu: 1..9216
- 省略時: DEFAULT_MTU_STR (通常 9100) (vlanmgr.cpp:96)
- 注意: ホスト VLAN MTU 設定は TODO 扱い。vlanmgr は受け取るが netdev MTU を変更しない (vlanmgr.cpp:402-406)

## vlanid: 2..4094
- YANG must: substring-after(../name, 'Vlan') = current()
- name 末尾と不一致の場合 YANG バリデーションが reject

## dhcp_servers / dhcpv6_servers (leaf-list)
- dhcprelayd がリストを読み出して relay agent を構成
- 単一文字列で入れると dhcprelayd が relay を起動しない（leaf-list として入力）

## mac: mac-address
- 省略時: gMacAddress (スイッチ MAC) が自動補完 (vlanmgr.cpp)

Sources:
- sonic-swss/cfgmgr/vlanmgr.cpp
- sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang
