---
title: YANG 横断索引
description: docs/reference/yang/ 配下に辞書化済みの 84 native SONiC YANG モジュールを、本サイトの機能章ごとに並べ直した逆引き索引である。
area: topics
verification: meta
last_verified: 2026-06-04
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# YANG 横断索引

`docs/reference/yang/` 配下に辞書化済みの **84** native [SONiC](../../reference/glossary.md#term-sonic) [YANG](../../reference/glossary.md#term-yang) モジュールを、機能章ごとに並べ直した逆引き索引である<!-- evidence: docs/reference/yang/sonic-*.md (84 pages) -->。SONiC の native YANG は概ね `sonic-<feature>.yang` の命名で [CONFIG_DB](../../reference/glossary.md#term-config_db) の table family に 1 対 1 ないし 1 対多で対応している。

management framework (Sonic-MGMT-Framework) / [gNMI](../../reference/glossary.md#term-gnmi) / OpenConfig との対応関係は別章で扱う方針で、本ページは native SONiC YANG モジュールから機能章へ戻る逆引きに専念する。アルファベット順の一覧が必要な場合は [リファレンス: YANG モジュール](../../reference/yang/index.md) を参照すること。

## 機能章別 YANG モジュール

### 01 SONiC 全体像と設定基盤

- [sonic-device_metadata](../../reference/yang/sonic-device_metadata.md)
- [sonic-feature](../../reference/yang/sonic-feature.md)
- [sonic-system-defaults](../../reference/yang/sonic-system-defaults.md)
- [sonic-versions](../../reference/yang/sonic-versions.md)
- [sonic-flex_counter](../../reference/yang/sonic-flex_counter.md)
- [sonic-banner](../../reference/yang/sonic-banner.md)

### 02 BGP と FRR 制御プレーン

- [sonic-bgp-global](../../reference/yang/sonic-bgp-global.md)
- [sonic-bgp-device-global](../../reference/yang/sonic-bgp-device-global.md)
- [sonic-bgp-neighbor](../../reference/yang/sonic-bgp-neighbor.md)
- [sonic-bgp-peergroup](../../reference/yang/sonic-bgp-peergroup.md)
- [sonic-bgp-peerrange](../../reference/yang/sonic-bgp-peerrange.md)
- [sonic-bgp-aggregate-address](../../reference/yang/sonic-bgp-aggregate-address.md)
- [sonic-bgp-bbr](../../reference/yang/sonic-bgp-bbr.md)
- [sonic-bgp-sentinel](../../reference/yang/sonic-bgp-sentinel.md)
- [sonic-bgp-monitor](../../reference/yang/sonic-bgp-monitor.md)
- [sonic-bmp](../../reference/yang/sonic-bmp.md)
- [sonic-route-common](../../reference/yang/sonic-route-common.md)
- [sonic-route-map](../../reference/yang/sonic-route-map.md)
- [sonic-static-route](../../reference/yang/sonic-static-route.md)

### 03 VXLAN / EVPN / VNET オーバーレイ

- [sonic-vxlan](../../reference/yang/sonic-vxlan.md)
- [sonic-vnet](../../reference/yang/sonic-vnet.md)
- [sonic-nvgre-tunnel](../../reference/yang/sonic-nvgre-tunnel.md)

### 04 VRF / ECMP / RIB-FIB

- [sonic-vrf](../../reference/yang/sonic-vrf.md)
- [sonic-fine-grained-ecmp](../../reference/yang/sonic-fine-grained-ecmp.md)
- [sonic-hash](../../reference/yang/sonic-hash.md)
- [sonic-neigh](../../reference/yang/sonic-neigh.md)
- [sonic-static-route](../../reference/yang/sonic-static-route.md) (02 章と共有)

### 05 Dual-ToR と Mux 制御

- [sonic-mux-cable](../../reference/yang/sonic-mux-cable.md)
- [sonic-tunnel](../../reference/yang/sonic-tunnel.md)

### 06 L2 / VLAN / LAG / MC-LAG

- [sonic-vlan](../../reference/yang/sonic-vlan.md)
- [sonic-vlan-sub-interface](../../reference/yang/sonic-vlan-sub-interface.md)
- [sonic-port](../../reference/yang/sonic-port.md)
- [sonic-portchannel](../../reference/yang/sonic-portchannel.md)
- [sonic-interface](../../reference/yang/sonic-interface.md)
- [sonic-loopback-interface](../../reference/yang/sonic-loopback-interface.md)
- [sonic-mclag](../../reference/yang/sonic-mclag.md)
- [sonic-lldp](../../reference/yang/sonic-lldp.md)
- [sonic-spanning-tree](../../reference/yang/sonic-spanning-tree.md)
- [sonic-storm-control](../../reference/yang/sonic-storm-control.md)

### 07 ACL / CoPP / Mirror

- [sonic-copp](../../reference/yang/sonic-copp.md)
- [sonic-mirror-session](../../reference/yang/sonic-mirror-session.md)
- [sonic-pbh](../../reference/yang/sonic-pbh.md)

### 08 QoS / Buffer / PFC / Watermark

- [sonic-buffer-pool](../../reference/yang/sonic-buffer-pool.md)
- [sonic-buffer-profile](../../reference/yang/sonic-buffer-profile.md)
- [sonic-buffer-pg](../../reference/yang/sonic-buffer-pg.md)
- [sonic-buffer-queue](../../reference/yang/sonic-buffer-queue.md)
- [sonic-queue](../../reference/yang/sonic-queue.md)
- [sonic-scheduler](../../reference/yang/sonic-scheduler.md)
- [sonic-wred-profile](../../reference/yang/sonic-wred-profile.md)
- [sonic-dot1p-tc-map](../../reference/yang/sonic-dot1p-tc-map.md)
- [sonic-dscp-tc-map](../../reference/yang/sonic-dscp-tc-map.md)
- [sonic-tc-queue-map](../../reference/yang/sonic-tc-queue-map.md)
- [sonic-tc-priority-group-map](../../reference/yang/sonic-tc-priority-group-map.md)
- [sonic-port-qos-map](../../reference/yang/sonic-port-qos-map.md)
- [sonic-pfc-priority-priority-group-map](../../reference/yang/sonic-pfc-priority-priority-group-map.md)
- [sonic-pfc-priority-queue-map](../../reference/yang/sonic-pfc-priority-queue-map.md)
- [sonic-pfcwd](../../reference/yang/sonic-pfcwd.md)
- [sonic-trimming](../../reference/yang/sonic-trimming.md)

### 09 Telemetry / SNMP / Observability

- [sonic-sflow](../../reference/yang/sonic-sflow.md)
- [sonic-snmp](../../reference/yang/sonic-snmp.md)
- [sonic-syslog](../../reference/yang/sonic-syslog.md)
- [sonic-debug-counter](../../reference/yang/sonic-debug-counter.md)
- [sonic-crm](../../reference/yang/sonic-crm.md)

### 10 gNMI / gNOI / OpenConfig / YANG

- (native YANG なし — `gNMI` / `gNOI` / OpenConfig 連携は management framework 経由で扱い、本サイトの管轄外。telemetry 系の native module は 09 章を参照)

### 11 Reboot / Upgrade / Lifecycle

- [sonic-warm-restart](../../reference/yang/sonic-warm-restart.md)
- [sonic-kdump](../../reference/yang/sonic-kdump.md)

### 12 Multi-ASIC / VOQ Chassis

- [sonic-fabric-monitor](../../reference/yang/sonic-fabric-monitor.md)
- [sonic-fabric-port](../../reference/yang/sonic-fabric-port.md)

### 13 DASH と SmartSwitch

- (native SONiC YANG なし — [DASH](../../reference/glossary.md#term-dash) appliance/[ENI](../../reference/glossary.md#term-eni) 制御は dedicated データプレーン API 経由)

### 14 Platform / Port / Optics / PHY

- [sonic-port](../../reference/yang/sonic-port.md) (06 章と共有)
- [sonic-breakout_cfg](../../reference/yang/sonic-breakout_cfg.md)
- [sonic-macsec](../../reference/yang/sonic-macsec.md)
- [sonic-mgmt_interface](../../reference/yang/sonic-mgmt_interface.md)
- [sonic-mgmt_port](../../reference/yang/sonic-mgmt_port.md)
- [sonic-mgmt_vrf](../../reference/yang/sonic-mgmt_vrf.md)

### 15 Security / AAA / FIPS / Hardening

- [sonic-system-aaa](../../reference/yang/sonic-system-aaa.md)
- [sonic-system-ldap](../../reference/yang/sonic-system-ldap.md)
- [sonic-system-radius](../../reference/yang/sonic-system-radius.md)
- [sonic-system-tacacs](../../reference/yang/sonic-system-tacacs.md)
- [sonic-ssh-server](../../reference/yang/sonic-ssh-server.md)
- [sonic-passw-hardening](../../reference/yang/sonic-passw-hardening.md)
- [sonic-fips](../../reference/yang/sonic-fips.md)

### 16 NAT / DHCP Relay / Time-DNS Services

- [sonic-nat](../../reference/yang/sonic-nat.md)
- [sonic-dhcp-server](../../reference/yang/sonic-dhcp-server.md)
- [sonic-ntp](../../reference/yang/sonic-ntp.md)
- [sonic-dns](../../reference/yang/sonic-dns.md)
- [sonic-restapi](../../reference/yang/sonic-restapi.md)

### 17 SRv6 / MPLS / Path Tracing

- [sonic-srv6](../../reference/yang/sonic-srv6.md)

## OpenConfig / management framework との対応

native SONiC YANG は CONFIG_DB の table 構造を素直に表す。一方、management framework (Sonic-MGMT-Framework) は OpenConfig / IETF YANG を入力し、内部で SONiC YANG に変換する。両者の対応表は本章の対象外とし、`gNMI / gNOI / OpenConfig / YANG` 章 (10 章) に置く方針である。

現時点で参考になる既存ページ:

- [SONiC YANG モデル ガイドライン](../../management/sonic-yang-model-guidelines.md)

## 未カバーのモジュール

upstream の `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/` には 136 個の `sonic-*.yang` ファイルが存在するが<!-- evidence: src/sonic-yang-models/yang-models/sonic-*.yang (sonic-buildimage master, 136 entries) -->、本サイトで個別ページ化済みなのは上記 84 モジュールである。差分には以下のような共通モジュール / 内部モジュール / 派生機能が含まれる:

- 共通: `sonic-bgp-common`、`sonic-bgp-internal-neighbor`、`sonic-bgp-voq-chassis-neighbor`、`sonic-bgp-prefix-list`、`sonic-bgp-allowed-prefix`
- DASH: `sonic-dash`
- イベントモデル: `sonic-events-bgp`、`sonic-events-common`、`sonic-events-dhcp-relay`、`sonic-events-host`、`sonic-events-swss`、`sonic-events-syncd`
- DHCP / Relay 派生: `sonic-dhcp-server-ipv4`、`sonic-dhcpv4-relay`、`sonic-dhcpv6-relay`
- platform / chassis: `sonic-chassis-module`、`sonic-asic-sensors`、`sonic-console`、`sonic-cable-length`、`sonic-default-lossless-buffer-parameter`
- その他: `sonic-gnmi`、`sonic-grpcclient`、`sonic-heartbeat`、`sonic-high-frequency-telemetry`、`sonic-auto_techsupport`、`sonic-logger`、`sonic-memory-statistics`、`sonic-fast-linkup`、`sonic-peer-switch`、`sonic-mux-linkmgr`、`sonic-kubernetes_master`、`sonic-dscp-fc-map`、`sonic-exp-fc-map`、`sonic-mpls-tc-map`、`sonic-lossless-traffic-pattern`、`sonic-buffer-port-egress-profile-list`、`sonic-buffer-port-ingress-profile-list`

辞書化未着手の項目は `meta/reference-gaps.md` にも反映していく方針である。本ページの章別マッピングは現状辞書化済の 84 モジュールに限定する。

<!-- glossary-links-injected: cc54e00e3a88 -->
