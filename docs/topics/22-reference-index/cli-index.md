---
title: CLI 横断索引
description: docs/reference/cli/ 配下の 73 ページを機能章ごとに束ね直した索引。各 CLI ページは config- / show- / debug- の辞書ページとして独立しており、本ページでは機能章からの入口として再構成する。
area: topics
verification: meta
last_verified: 2026-06-04
related:
  cli:
  - config bgp
  - show bgp
  - config interface
  - show ip
  - config vxlan
  - config vnet
  - config qos
  - config buffer
  - config aaa
  - config nat
  - config platform firmware
  config_db: []
  yang: []
related_opt_out: true
---

# CLI 横断索引

`docs/reference/cli/` 配下の 73 ページを、機能章でどこから引かれるかで並べ直した索引である。各 CLI ページは `config-*` / `show-*` / `debug-*` のグループごとに辞書として独立しており、本ページではこれを機能章ごとに束ね直す。

## 機能章別 CLI 表

全章とも `docs/topics/` 配下にディレクトリが存在し、`concept` / `setup` / `operations` / `architecture` / `internals` / `advanced` の構成で公開されている。本表では機能章の主入口 (`setup.md` / `operations.md` / `index.md`) を併記する。

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
- [config mirror-session](../../reference/cli/config-mirror-session.md)

入口: [07-acl-copp-mirror/setup.md](../07-acl-copp-mirror/setup.md) / [07-acl-copp-mirror/operations.md](../07-acl-copp-mirror/operations.md)。

### 08 QoS / Buffer / PFC / Watermark

- [config qos](../../reference/cli/config-qos.md)
- [config buffer](../../reference/cli/config-buffer.md)
- [show buffer](../../reference/cli/show-buffer.md)
- [show buffer-pool](../../reference/cli/show-buffer-pool.md)
- [config pfcwd](../../reference/cli/config-pfcwd.md)
- [show pfc](../../reference/cli/show-pfc.md)
- [show priority-group](../../reference/cli/show-priority-group.md)
- [show queue](../../reference/cli/show-queue.md)

入口: [08-qos-buffer/setup.md](../08-qos-buffer/setup.md) / [08-qos-buffer/operations.md](../08-qos-buffer/operations.md)。

### 09 Telemetry / SNMP / Observability

- [config snmp](../../reference/cli/config-snmp.md)
- [config sflow](../../reference/cli/config-sflow.md)
- [config syslog](../../reference/cli/config-syslog.md)
- [show snmpagentaddress](../../reference/cli/show-snmpagentaddress.md)
- [show snmptrap](../../reference/cli/show-snmptrap.md)
- [show techsupport](../../reference/cli/show-techsupport.md)
- [show system-health](../../reference/cli/show-system-health.md)
- [show feature](../../reference/cli/show-feature.md)
- [debug-group](../../reference/cli/debug-group.md)
- [clear](../../reference/cli/clear.md)

入口: [09-telemetry-snmp/setup.md](../09-telemetry-snmp/setup.md) / [09-telemetry-snmp/operations.md](../09-telemetry-snmp/operations.md)。

### 11 Reboot / Upgrade / Lifecycle

- [config warm_restart](../../reference/cli/config-warm_restart.md)
- [reboot-fast-warm](../../reference/cli/reboot-fast-warm.md)
- [config kdump](../../reference/cli/config-kdump.md)
- [config platform firmware](../../reference/cli/config-platform-firmware.md)
- [sonic-installer](../../reference/cli/sonic-installer.md)
- [sonic-package-manager](../../reference/cli/sonic-package-manager.md)

入口: [11-reboot/index.md](../11-reboot/index.md)。

### 14 Platform / Port / Optics

- [show platform](../../reference/cli/show-platform.md)
- [show environment](../../reference/cli/show-environment.md)
- [config platform firmware](../../reference/cli/config-platform-firmware.md)
- [show interfaces](../../reference/cli/show-interfaces.md)

入口: [14-platform-port-optics/setup.md](../14-platform-port-optics/setup.md) / [14-platform-port-optics/operations.md](../14-platform-port-optics/operations.md)。

### 15 Security / AAA / FIPS

- [config aaa](../../reference/cli/config-aaa.md)
- [show aaa](../../reference/cli/show-aaa.md)
- [config mgmt-trio](../../reference/cli/config-mgmt-trio.md)
- [show mgmt-vrf](../../reference/cli/show-mgmt-vrf.md)
- [config ssh](../../reference/cli/config-ssh.md)

入口: [15-security-aaa/setup.md](../15-security-aaa/setup.md) / [15-security-aaa/operations.md](../15-security-aaa/operations.md)。

### 16 NAT / DHCP Relay / Time-DNS

- [config nat](../../reference/cli/config-nat.md)
- [show nat](../../reference/cli/show-nat.md)
- [config dhcp-relay](../../reference/cli/config-dhcp-relay.md)
- [config ntp](../../reference/cli/config-ntp.md)
- [config clock](../../reference/cli/config-clock.md)
- [show clock](../../reference/cli/show-clock.md)

入口: [16-nat-dhcp-dns/setup.md](../16-nat-dhcp-dns/setup.md) / [16-nat-dhcp-dns/operations.md](../16-nat-dhcp-dns/operations.md)。

### 19 Build / Packaging

- [sonic-cfggen](../../reference/cli/sonic-cfggen.md)
- [sonic-package-manager](../../reference/cli/sonic-package-manager.md)
- [show running-config](../../reference/cli/show-running-config.md)
- [show version](../../reference/cli/show-version.md)

入口: [19-build-packaging/setup.md](../19-build-packaging/setup.md) / [19-build-packaging/operations.md](../19-build-packaging/operations.md)。

## 辞書から章への逆引き

`docs/reference/cli/` の辞書ページに「関連章」を埋め込む変更は本章のスコープ外 (既存ページ本文不変)。代わりに、辞書側を起点に章を探す読者は本ページの上記表を逆方向に辿るか、`docs/reference/cli/index.md` のトップから本章 [index](index.md) に戻る運用を想定する。

## 補足

- `show ip` / `show ipv6` ページは [BGP](../../reference/glossary.md#term-bgp) 章と [VRF](../../reference/glossary.md#term-vrf) 章の両方から参照される。主入口は VRF 章。
- `config interface` は L2 章 / VRF 章 / Platform 章の三章から参照される。主入口は L2 章。
- `config-mgmt-trio` は management framework / [gNMI](../../reference/glossary.md#term-gnmi) 章でも扱う想定だが、CLI 入口としては 15 Security 章に集約する。
- `show interfaces` は L2 章と Platform 章の両方から参照される。物理層の counters / FEC / transceiver 情報は Platform 章を主入口とする。

<!-- glossary-links-injected: d913b2e2ebed -->
