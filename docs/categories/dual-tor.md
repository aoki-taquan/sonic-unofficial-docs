---
title: Dual-ToR 関連
area: categories
verification: meta
last_verified: 2026-05-10
---

# Dual-ToR 関連

## 概要

Dual-ToR の active-active / active-standby、MUX cable、linkmgrd、Y-cable、経路制御、トンネル処理を横断して追う入口です。

主要キーワード: `Dual-ToR`, `active-active`, `active-standby`, `MUX`, `linkmgrd`, `Y-cable`

## 関連ページ

- [DHCPv6 Relay Agent（Option 79 / dual ToR loopback）](../architecture/dhcpv6-relay-agent.md) (area: `architecture`, verification: `code-verified`)
- [gRPC client（active-active DualToR / ycabled ↔ SoC 連携）](../management/design-doc.md) (area: `management`, verification: `code-verified`)
- [Active-Active Dual ToR（gRPC ベース cable control + prefix-based neighbor）](../overlay/active-active-dual-tor.md) (area: `overlay`, verification: `code-verified`)
- [Active-Standby Dual ToR（y-cable + linkmgrd state machine + IPinIP tunnel）](../overlay/active-standby-dual-tor.md) (area: `overlay`, verification: `code-verified`)
- [トンネルトラフィックの DSCP / TC リマップ（Dual-ToR PFC デッドロック回避）](../overlay/dscp-remapping-for-tunnel-traffic.md) (area: `overlay`, verification: `discrepancy-found`)
- [ICMP Hardware Offload（DualToR link prober の NPU 化）](../platform/icmp-hardware-offload.md) (area: `platform`, verification: `code-verified`)
- [config muxcable サブコマンド](../reference/cli/config-muxcable.md) (area: `reference`, verification: `code-verified`)
- [show muxcable サブコマンド](../reference/cli/show-muxcable.md) (area: `reference`, verification: `code-verified`)
- [MUX_CABLE テーブル](../reference/config-db/mux-cable.md) (area: `reference`, verification: `code-verified`)
- [linkmgrd のデフォルトルート連動（DualToR mux 制御）](../routing/default-route.md) (area: `routing`, verification: `hld-only`)
- [dual-tor mux 跨ぎの multi-nexthop route ループ回避（MuxOrch::updateRoute）](../routing/multiple-nexthop-route-hld.md) (area: `routing`, verification: `code-verified`)
- [プレフィックスルート方式の Mux ネイバ（Dual-ToR の状態遷移最適化）](../routing/prefix-based-mux-neighbors.md) (area: `routing`, verification: `code-verified`)

## 関連カテゴリ

- [BGP / EVPN 関連](bgp-evpn.md)
- [gNMI / gNOI / OpenConfig 関連](gnmi-openconfig.md)
