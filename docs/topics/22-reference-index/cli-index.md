---
title: CLI 横断索引
description: docs/reference/cli/ 配下の主要 CLI ページを機能章ごとに束ね直した抜粋索引。全 72 ページの辞書一覧ではなく、各機能章の主入口から引かれる代表 CLI のみを並べる。網羅索引は docs/reference/cli/index.md を参照。
area: topics
verification: meta
last_verified: 2026-06-04
page_kind: chapter-index
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
  _no_related_config_db: true
  _no_related_yang: true
---

# CLI 横断索引

`docs/reference/cli/` 配下の主要 CLI ページを、機能章でどこから引かれるかで並べ直した抜粋索引である。各 CLI ページは `config-*` / `show-*` / `debug-*` のグループごとに辞書として独立しており、本ページでは機能章の主入口から実際に参照される代表 CLI のみを束ね直す。

本ページは網羅索引ではない。辞書ページの全件一覧は [docs/reference/cli/index.md](../../reference/cli/index.md) を参照する。本ページに収録していない章・辞書ページは末尾「索引対象外」節にまとめている。

## 機能章別 CLI 表

各機能章は `docs/topics/NN-<slug>/` 配下に `concept` / `setup` / `operations` / `internals` / `advanced` を基本構成として公開しており、章によっては `architecture.md` を併設する。本表では機能章の主入口 (`setup.md` / `operations.md` / `index.md`) を併記する。

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

入口: [11-reboot/setup.md](../11-reboot/setup.md) / [11-reboot/operations.md](../11-reboot/operations.md)。

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

## 補足

- `show ip` / `show ipv6` ページは [BGP](../../reference/glossary.md#term-bgp) 章と [VRF](../../reference/glossary.md#term-vrf) 章の両方から参照される。主入口は VRF 章。
- `config interface` は L2 章 / VRF 章 / Platform 章の三章から参照される。主入口は L2 章。
- `config-mgmt-trio` は management framework / [gNMI](../../reference/glossary.md#term-gnmi) 章でも扱う想定だが、CLI 入口としては 15 Security 章に集約する。
- `show interfaces` は L2 章と Platform 章の両方から参照される。物理層の counters / FEC / transceiver 情報は Platform 章を主入口とする。

## 索引対象外

本ページは抜粋索引であり、以下は意図的に対象から外している。網羅的に CLI を辿る場合は [docs/reference/cli/index.md](../../reference/cli/index.md) を起点とする。

### 収録していない機能章

機能章 `docs/topics/` 配下のうち、上記表に並べていないのは次の章である。各章とも `setup.md` / `operations.md` での CLI 参照が章固有 CLI に偏らないか、汎用 CLI (`show interfaces` / `show platform` 等) で間に合うため、本表では独立節を設けていない。

- `10-gnmi-openconfig` — gNMI / OpenConfig 系。`config-mgmt-trio` は 15 Security 章にまとめている。
- `12-multi-asic-voq` — [Multi-ASIC](../../reference/glossary.md#term-multi-asic) / VoQ。専用 CLI は限定的で `show platform` / `show interfaces` が主。
- `13-dash-smartswitch` — [DASH](../../reference/glossary.md#term-dash) / [SmartSwitch](../../reference/glossary.md#term-smartswitch)。CLI ではなく gNMI / [NPU](../../reference/glossary.md#term-npu) 直叩きが中心。
- `17-srv6-mpls` — [SRv6](../../reference/glossary.md#term-srv6) / [MPLS](../../reference/glossary.md#term-mpls)。`config bgp` / `show ip` から派生し独立 CLI は無し。
- `18-p4-pins` — P4 / [PINS](../../reference/glossary.md#term-pins)。CLI ではなく P4Runtime / gNMI 制御。
- `20-swss-sai-redis` — SWSS / [SAI](../../reference/glossary.md#term-sai) / [Redis](../../reference/glossary.md#term-redis)。`swssloglevel` 等の補助コマンドは辞書に未掲載。
- `01-overview` / `21-lab-vs-developer` / `22-reference-index` — 概説・開発者向け章で CLI 入口を持たない。

### 収録していない辞書ページ

`docs/reference/cli/` の辞書ページ全 72 ページのうち、機能章入口として上記表に並べていないのは次の 12 ページである。`show-*` のサブカテゴリで複数章から薄く参照されるもの、または章入口に直結しない単発設定を中心に省いている。

- `show-arp` / `show-ndp` / `show-mac` — L2 / VRF 章で補助参照。
- `show-bfd` — BGP / VRF 章で補助参照。
- `show-lldp` — Platform / L2 章で補助参照。
- `show-flowcnt` / `show-storm-control` — [QoS](../../reference/glossary.md#term-qos) / [ACL](../../reference/glossary.md#term-acl) 章で補助参照。
- `show-services` / `show-uptime` — 全章共通の運用 CLI で章固有の主入口を持たない。
- `clear-counters` — counters リセット系で章固有の主入口を持たない (なお `clear` は 09 Telemetry 章で再掲済み)。
- `config-banner` / `config-default-route` — 単発設定で章入口に直結しない。

### 上記表で再掲・集約済みの辞書ページ

以下の辞書ページは複数章から参照されるが、本表では単一の主入口章にまとめて再掲している (上記表に含まれているため未収録ではない)。

- `show-running-config` / `show-version` — 19 Build 章に集約。
- `clear` — 09 Telemetry 章に集約。
- `config-clock` / `show-clock` — 16 [NAT](../../reference/glossary.md#term-nat)/DHCP/DNS 章に集約 (時刻系)。
- `show-snmpagentaddress` / `show-snmptrap` / `show-system-health` / `show-feature` / `show-techsupport` — 09 Telemetry 章に集約。

## 辞書から章への逆引き

`docs/reference/cli/` の辞書ページに「関連章」を埋め込む変更は本章のスコープ外 (既存ページ本文不変)。代わりに、辞書側を起点に章を探す読者は本ページの上記表を逆方向に辿るか、`docs/reference/cli/index.md` のトップから本章 [index](index.md) に戻る運用を想定する。

<!-- glossary-links-injected: 0e7015f195c5 -->
