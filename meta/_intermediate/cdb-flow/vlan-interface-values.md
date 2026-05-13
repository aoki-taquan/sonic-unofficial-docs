# VLAN_INTERFACE — 値依存挙動メモ

## mpls: enable / disable
- `enable` → `sysctl -w net.mpls.conf.<alias>.input=1` (intfmgr.cpp:176)
- `disable` または空 → `sysctl -w net.mpls.conf.<alias>.input=0` (intfmgr.cpp:178)

## proxy_arp: enabled / disabled
- `enabled` → `/proc/sys/net/ipv4/conf/<alias>/proxy_arp_pvlan` に `1`、`proxy_arp` に `1` (intfmgr.cpp:636,642)
- `disabled` → 同ファイルに `0` (intfmgr.cpp:628)
- その他の値 → SWSS_LOG_ERROR("Proxy ARP state is invalid") で中断

## grat_arp: enabled / disabled
- `enabled` → `/proc/sys/net/ipv4/conf/<alias>/arp_accept` に `1` (intfmgr.cpp:580,584)
- `disabled` → 同ファイルに `0` (intfmgr.cpp:584)
- その他の値 → SWSS_LOG_ERROR("GARP state is invalid") で中断

## ipv6_use_link_local_only: enable / disable
- `enable` → IPv6 link-local アドレスのみ付与（グローバルアドレス不可）(intfmgr.cpp:915)
- `disable` → 通常の IPv6 アドレス割当 (intfmgr.cpp:920)
- YANG default: `disable`

## loopback_action: drop / forward
- `drop` → 同一 IF に戻るパケットをドロップ
- `forward` → 同一 IF に戻るパケットを転送
- sonic-types.yang: pattern "drop|forward"

## nat_zone: 0..3
- YANG default: 0
- 0 = NAT zone なし（デフォルト）

## vrf_name
- 変更禁止: intfmgr の isIntfChangeVrf() が検出するとエラー、再設定するには一旦削除が必要

Sources:
- sonic-swss/cfgmgr/intfmgr.cpp
- sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang
- sonic-buildimage/src/sonic-yang-models/yang-templates/sonic-types.yang.j2
