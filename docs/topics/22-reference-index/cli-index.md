---
title: CLI 横断索引
description: CLI 横断索引 — docs/reference/cli/ 配下の 72 ページを、機能章でどこから引かれるかで並べ直した索引である。各
  CLI ページは config- / show- / debug-* のグループごとに分かれており、本ページではこれを機能章ごとに束ね直す。
area: topics
verification: meta
last_verified: 2026-05-10
related:
  cli:
  - config interface
  - show ip
  - config platform firmware
  - config bgp
  - show bgp
  - config vxlan
  - config vnet
  config_db:
  - VRF
  - BGP_NEIGHBOR
  - BGP_GLOBALS
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_NETWORK
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  - BGP_AGGREGATE_ADDRESS
  yang:
  - sonic-bgp-global
  - sonic-bgp-neighbor
  - sonic-vrf
  - sonic-bgp-bbr
  - sonic-bgp-peerrange
  - sonic-bgp-device-global
  - sonic-bgp-sentinel
---

# CLI 横断索引

`docs/reference/cli/` 配下の 72 ページを、機能章でどこから引かれるかで並べ直した索引である。各 CLI ページは `config-*` / `show-*` / `debug-*` のグループごとに分かれており、本ページではこれを機能章ごとに束ね直す。

## 機能章別 CLI 表

実装済の章は本表からリンクする。未実装の章はプレースホルダとして「章番号 / 主題」のみ記載する。

### 02 BGP と FRR 制御プレーン

- [config bgp](../../reference/cli/config-bgp.md)
- [show bgp](../../reference/cli/show-bgp.md)
- [show ip / ipv6 route](../../reference/cli/show-ip.md)
- [show route-map](../../reference/cli/show-route-map.md)

入口: [02-bgp/setup.md](../02-bgp/setup.md) / [02-bgp/operations.md](../02-bgp/operations.md)。

### 03 VXLAN / EVPN / VNET オーバーレイ

- [config vxlan](../../reference/cli/config-vxlan.md)
- [config vnet](../../reference/cli/config-vnet.md)

入口: [03-vxlan-evpn/setup.md](../03-vxlan-evpn/setup.md)。

### 04 VRF / ECMP / RIB-FIB

- [config vrf](../../reference/cli/config-vrf.md)
- [config route](../../reference/cli/config-route.md)
- [config interface](../../reference/cli/config-interface.md)

入口: [04-vrf-ecmp/setup.md](../04-vrf-ecmp/setup.md)。

### 05 Dual-ToR と Mux 制御

- [config muxcable](../../reference/cli/config-muxcable.md)
- [show muxcable](../../reference/cli/show-muxcable.md)

入口: [05-dual-tor/setup.md](../05-dual-tor/setup.md) / [05-dual-tor/operations.md](../05-dual-tor/operations.md)。

### 06 L2 / VLAN / LAG / MC-LAG

- [config vlan](../../reference/cli/config-vlan.md)
- [show vlan](../../reference/cli/show-vlan.md)
- [config portchannel](../../reference/cli/config-portchannel.md)
- [config mclag](../../reference/cli/config-mclag.md)
- [show mclag](../../reference/cli/show-mclag.md)
- [config interface](../../reference/cli/config-interface.md)
- [show interfaces](../../reference/cli/show-interfaces.md)

入口: [06-l2-vlan-lag/setup.md](../06-l2-vlan-lag/setup.md)。

### 07 ACL / CoPP / Mirror

- [config acl](../../reference/cli/config-acl.md)
- [show acl](../../reference/cli/show-acl.md)

入口: [07-acl-copp-mirror/setup.md](../07-acl-copp-mirror/setup.md) / [07-acl-copp-mirror/operations.md](../07-acl-copp-mirror/operations.md)。

### 08 QoS / Buffer / PFC / Watermark (未実装章)

- [config qos](../../reference/cli/config-qos.md)
- [config buffer](../../reference/cli/config-buffer.md)
- [show buffer](../../reference/cli/show-buffer.md)
- [config pfcwd](../../reference/cli/config-pfcwd.md)
- [show pfc](../../reference/cli/show-pfc.md)
- [show priority-group](../../reference/cli/show-priority-group.md)
- [show queue](../../reference/cli/show-queue.md)

### 09 Telemetry / SNMP / Observability (未実装章)

- [config snmp](../../reference/cli/config-snmp.md)
- [config sflow](../../reference/cli/config-sflow.md)
- [config syslog](../../reference/cli/config-syslog.md)
- [show techsupport](../../reference/cli/show-techsupport.md)
- [show system-health](../../reference/cli/show-system-health.md)
- [show feature](../../reference/cli/show-feature.md)
- [debug-group](../../reference/cli/debug-group.md)
- [clear](../../reference/cli/clear.md)

### 11 Reboot / Upgrade / Lifecycle

- [config warm_restart](../../reference/cli/config-warm_restart.md)
- [reboot-fast-warm](../../reference/cli/reboot-fast-warm.md)
- [config kdump](../../reference/cli/config-kdump.md)
- [config platform firmware](../../reference/cli/config-platform-firmware.md)
- [sonic-installer](../../reference/cli/sonic-installer.md)
- [sonic-package-manager](../../reference/cli/sonic-package-manager.md)

入口: [11-reboot/index.md](../11-reboot/index.md)。

### 14 Platform / Port / Optics (未実装章)

- [show platform](../../reference/cli/show-platform.md)
- [config platform firmware](../../reference/cli/config-platform-firmware.md)

### 15 Security / AAA / FIPS (未実装章)

- [config aaa](../../reference/cli/config-aaa.md)
- [config mgmt-trio](../../reference/cli/config-mgmt-trio.md)

### 16 NAT / DHCP Relay / Time-DNS (未実装章)

- [config nat](../../reference/cli/config-nat.md)
- [show nat](../../reference/cli/show-nat.md)
- [config dhcp-relay](../../reference/cli/config-dhcp-relay.md)

### 19 Build / Packaging (未実装章)

- [sonic-cfggen](../../reference/cli/sonic-cfggen.md)
- [sonic-package-manager](../../reference/cli/sonic-package-manager.md)
- [show running-config](../../reference/cli/show-running-config.md)

## 辞書から章への逆引き

`docs/reference/cli/` の辞書ページに「関連章」を埋め込む変更は本章のスコープ外 (既存ページ本文不変)。代わりに、辞書側を起点に章を探す読者は本ページの上記表を逆方向に辿るか、`docs/reference/cli/index.md` のトップから本章 [index](index.md) に戻る運用を想定する。

## 補足

- `show ip / show ipv6` ページは [BGP](../../reference/glossary.md#term-bgp) 章と [VRF](../../reference/glossary.md#term-vrf) 章の両方から参照される。主入口は VRF 章。
- `config interface` は L2 章と VRF 章の双方から参照される。主入口は L2 章。
- `config-mgmt-trio` は management framework / [gNMI](../../reference/glossary.md#term-gnmi) 章で扱う想定だが、現時点では未実装のため上記 15 章プレースホルダとして残す。

<!-- glossary-links-injected: d913b2e2ebed -->
