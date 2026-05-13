# PORTCHANNEL_INTERFACE フィールド値分析

## enum フィールド

### `loopback_action` (stypes:loopback_action)
- `drop`: 同一 IF に ingress→routed されたパケットを破棄
- `forward`: 同一 IF に ingress→routed されたパケットを通過

### `mpls`
- `enable`: MPLS routing 有効化
- `disable`: 無効化

### `ipv6_use_link_local_only` (stypes:mode-status)
- `enable`: IPv6 link-local のみ設定
- `disable` (デフォルト): 通常 IPv6 動作

## 数値範囲フィールド

### `nat_zone` (uint8, 0..3)
- `0` (デフォルト): NAT ゾーン 0
- `1`..`3`: 対応 NAT ゾーン
- > 3: YANG range 違反: `Invalid nat zone for the portchannel interface.` → reject

## leafref フィールド
- `vrf_name` → VRF.name (存在しない VRF は YANG validate で reject)
- `name` (key) → PORTCHANNEL.name

## ソース
- sonic-portchannel.yang (sonic-buildimage sha 9ea932ec)
- intfmgrd / orchagent/intfsorch.cpp (sonic-swss)
