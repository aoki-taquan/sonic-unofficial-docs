---
title: YANG 横断索引
description: YANG 横断索引 — docs/reference/yang/ 配下の 39 モジュールを、機能章ごとに並べ直した索引です。SONiC
  の YANG は概ね sonic-.yang の命名で CONFIG_DB の table family に 1 対 1 ないし 1 対多で対応しています。
area: topics
verification: meta
last_verified: 2026-05-10
related:
  cli:
  - config vlan
  - show vlan
  config_db:
  - VLAN
  - VLAN_MEMBER
  - VLAN_SUB_INTERFACE
  - VLAN_INTERFACE
  - TELEMETRY
  - GNMI
  - PORT
  yang:
  - sonic-static-route
  - sonic-feature
  - sonic-bgp-global
  - sonic-bgp-neighbor
  - sonic-bgp-peergroup
  - sonic-bgp-aggregate-address
  - sonic-route-common
---

# YANG 横断索引

`docs/reference/yang/` 配下の 39 モジュールを、機能章ごとに並べ直した索引である。[SONiC](../../reference/glossary.md#term-sonic) の [YANG](../../reference/glossary.md#term-yang) は概ね `sonic-<feature>.yang` の命名で [CONFIG_DB](../../reference/glossary.md#term-config_db) の table family に 1 対 1 ないし 1 対多で対応している。

management framework / [gNMI](../../reference/glossary.md#term-gnmi) / OpenConfig との対応関係は別章 (今後予定) で扱う。本ページは native SONiC YANG モジュールから機能章へ戻る逆引きに専念する。

## 機能章別 YANG モジュール

### 01 SONiC 全体像と設定基盤

- [sonic-device_metadata](../../reference/yang/sonic-device_metadata.md)
- [sonic-feature](../../reference/yang/sonic-feature.md)

### 02 BGP と FRR 制御プレーン

- [sonic-bgp-global](../../reference/yang/sonic-bgp-global.md)
- [sonic-bgp-neighbor](../../reference/yang/sonic-bgp-neighbor.md)
- [sonic-bgp-peergroup](../../reference/yang/sonic-bgp-peergroup.md)
- [sonic-bgp-aggregate-address](../../reference/yang/sonic-bgp-aggregate-address.md)
- [sonic-route-common](../../reference/yang/sonic-route-common.md)
- [sonic-route-map](../../reference/yang/sonic-route-map.md)
- [sonic-static-route](../../reference/yang/sonic-static-route.md)

### 03 VXLAN / EVPN / VNET オーバーレイ

- [sonic-vxlan](../../reference/yang/sonic-vxlan.md)
- [sonic-vnet](../../reference/yang/sonic-vnet.md)

### 04 VRF / ECMP / RIB-FIB

- [sonic-vrf](../../reference/yang/sonic-vrf.md)
- [sonic-static-route](../../reference/yang/sonic-static-route.md) (02 章と共有)

### 05 Dual-ToR と Mux 制御

- (native YANG なし — table のみ。[VLAN](../../reference/glossary.md#term-vlan) / interface 系で間接的に表現)

### 06 L2 / VLAN / LAG / MC-LAG

- [sonic-vlan](../../reference/yang/sonic-vlan.md)
- [sonic-vlan-sub-interface](../../reference/yang/sonic-vlan-sub-interface.md)
- [sonic-port](../../reference/yang/sonic-port.md)
- [sonic-portchannel](../../reference/yang/sonic-portchannel.md)
- [sonic-interface](../../reference/yang/sonic-interface.md)
- [sonic-loopback-interface](../../reference/yang/sonic-loopback-interface.md)
- [sonic-mclag](../../reference/yang/sonic-mclag.md)
- [sonic-lldp](../../reference/yang/sonic-lldp.md)

### 07 ACL / CoPP / Mirror

- [sonic-copp](../../reference/yang/sonic-copp.md)
- [sonic-mirror-session](../../reference/yang/sonic-mirror-session.md)
- [sonic-pbh](../../reference/yang/sonic-pbh.md)

### 08 QoS / Buffer / PFC / Watermark (未実装章)

- [sonic-buffer-pool](../../reference/yang/sonic-buffer-pool.md)
- [sonic-buffer-profile](../../reference/yang/sonic-buffer-profile.md)
- [sonic-buffer-pg](../../reference/yang/sonic-buffer-pg.md)
- [sonic-buffer-queue](../../reference/yang/sonic-buffer-queue.md)
- [sonic-queue](../../reference/yang/sonic-queue.md)
- [sonic-scheduler](../../reference/yang/sonic-scheduler.md)
- [sonic-dscp-tc-map](../../reference/yang/sonic-dscp-tc-map.md)
- [sonic-tc-queue-map](../../reference/yang/sonic-tc-queue-map.md)
- [sonic-port-qos-map](../../reference/yang/sonic-port-qos-map.md)
- [sonic-pfcwd](../../reference/yang/sonic-pfcwd.md)

### 15 Security / AAA / FIPS (未実装章)

- [sonic-system-aaa](../../reference/yang/sonic-system-aaa.md)
- [sonic-syslog](../../reference/yang/sonic-syslog.md)

### 16 NAT / DHCP Relay / Time-DNS (未実装章)

- [sonic-nat](../../reference/yang/sonic-nat.md)
- [sonic-dhcp-server](../../reference/yang/sonic-dhcp-server.md)
- [sonic-ntp](../../reference/yang/sonic-ntp.md)
- [sonic-dns](../../reference/yang/sonic-dns.md)

## OpenConfig / management framework との対応

native SONiC YANG は CONFIG_DB の table 構造を素直に表す。一方、management framework (Sonic-MGMT-Framework) は OpenConfig / IETF YANG を入力し、内部で SONiC YANG に変換する。両者の対応表は本章の対象外とし、今後扱う `gNMI / gNOI / OpenConfig / YANG` 章に置く。

現時点で参考になる既存ページ:

- [SONiC YANG モデル ガイドライン](../../management/sonic-yang-model-guidelines.md)

## 未カバーのモジュール

`meta/reference-gaps.md` に、CONFIG_DB table はあるが YANG モジュール辞書化が未着手のものが積まれている。本ページの章別マッピングは現状辞書化済の 39 モジュールに限定する。

<!-- glossary-links-injected: 8ba32e5aa69d -->
