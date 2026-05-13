# NVGRE_TUNNEL / NVGRE_TUNNEL_MAP フィールド値分析

## enum フィールド

なし — src_ip は inet:ip-address 型、vlan_id は uint16 (1..4094)、vsid は uint32 (0..16777214)。

## 数値範囲フィールド

### `vlan_id` (NVGRE_TUNNEL_MAP)
- 有効範囲: 1..4094
- 範囲外: nvgreorch が `VLAN ID doesn't exist: %d` → WARN ログ後スキップ

### `vsid` (NVGRE_TUNNEL_MAP)
- 有効範囲: 0..16777214 (24bit)
- 範囲外: `VSID is invalid: %d` → WARN ログ後スキップ

## leafref フィールド

### `tunnel_name` (NVGRE_TUNNEL_MAP key)
- 存在する NVGRE_TUNNEL を参照: 正常
- 存在しない親トンネル: `NVGRE tunnel '%s' doesn't exist` → WARN

## ソース
- sonic-nvgre-tunnel.yang (sonic-buildimage sha 9ea932ec)
- orchagent/nvgreorch.cpp (sonic-swss)
