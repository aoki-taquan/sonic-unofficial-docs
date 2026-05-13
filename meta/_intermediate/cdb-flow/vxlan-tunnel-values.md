# VXLAN_TUNNEL — 値依存挙動メモ

## ttl_mode: uniform / pipe
- YANG: pattern "uniform|pipe"
- uniform → decap 時に outer TTL を inner TTL にコピー
- pipe → decap 時に inner TTL を保持（outer TTL は無視）
- 実装: vxlanmgr が netdev に渡す（現在 kernel vxlan では ttl オプションとして渡す）

## src_ip (ip-address)
- VTEP 自身の IP。Loopback0 を推奨（物理 IF だとリンクダウンで VTEP 消失）
- EVPN 用途: 必須 (VTEP の源泉)

## dst_ip (ip-address)
- P2P トンネル用。省略すると multipoint (EVPN 動的学習モード)
- EVPN 構成での dst_ip 静的指定は type-3 と競合するため避ける
- vxlanmgr.cpp: dst_ip 空の場合 remote オプションなしで ip link add

## max-elements 2
- YANG による制約。通常 EVPN 用 1 + 静的 P2P 用 1 を想定

Sources:
- sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vxlan.yang
- sonic-swss/cfgmgr/vxlanmgr.cpp
