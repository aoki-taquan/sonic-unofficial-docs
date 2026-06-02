---
title: YANG リファレンス
description: YANG リファレンス — このページは、機能章 (本書の章 01〜21) から YANG モジュールを逆引きするための索引です。SONiC
  native YANG のページは docs/reference/yang/*.md に並んでおり、CONFIG_DB のテーブルスキーマと 1:1 対応します。
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
related:
  cli:
  - show pfc
  - config aaa
  - show aaa
  - config vlan
  - show vlan
  - config vnet
  - show nat
  config_db:
  - VNET
  - VLAN
  - VRF
  - SNMP
  - AAA
  - NAT
  - PFC_WD
  yang:
  - sonic-feature
  - sonic-bgp-global
  - sonic-bgp-neighbor
  - sonic-bgp-peergroup
  - sonic-bgp-aggregate-address
  - sonic-route-map
  - sonic-route-common
---

# YANG リファレンス

このページは、機能章 (本書の章 01〜21) から [YANG](../../reference/glossary.md#term-yang) モジュールを逆引きするための索引である。[SONiC](../../reference/glossary.md#term-sonic) native YANG のページは `docs/reference/yang/*.md` に並んでおり、[CONFIG_DB](../../reference/glossary.md#term-config_db) のテーブルスキーマと 1:1 対応する。OpenConfig 側のマップ範囲は、機能ごとに [概要](concept.md) の表と、各機能 [HLD](../../reference/glossary.md#term-hld) を参照する。

## 機能章別 YANG モジュール

| 章 | モジュール | 概要 |
| --- | --- | --- |
| 01 全体像・設定基盤 | [sonic-device_metadata](../../reference/yang/sonic-device_metadata.md), [sonic-feature](../../reference/yang/sonic-feature.md) | device 識別、機能 enable / disable |
| 02 [BGP](../../reference/glossary.md#term-bgp) / [FRR](../../reference/glossary.md#term-frr) | [sonic-bgp-global](../../reference/yang/sonic-bgp-global.md), [sonic-bgp-neighbor](../../reference/yang/sonic-bgp-neighbor.md), [sonic-bgp-peergroup](../../reference/yang/sonic-bgp-peergroup.md), [sonic-bgp-aggregate-address](../../reference/yang/sonic-bgp-aggregate-address.md), [sonic-route-map](../../reference/yang/sonic-route-map.md), [sonic-route-common](../../reference/yang/sonic-route-common.md), [sonic-static-route](../../reference/yang/sonic-static-route.md) | BGP 設定、route map、static route |
| 03 [VXLAN](../../reference/glossary.md#term-vxlan) / [EVPN](../../reference/glossary.md#term-evpn) / [VNET](../../reference/glossary.md#term-vnet) | [sonic-vxlan](../../reference/yang/sonic-vxlan.md), [sonic-vnet](../../reference/yang/sonic-vnet.md) | VXLAN tunnel、VNET overlay |
| 04 [VRF](../../reference/glossary.md#term-vrf) / [ECMP](../../reference/glossary.md#term-ecmp) | [sonic-vrf](../../reference/yang/sonic-vrf.md) | VRF テーブル |
| 05 Dual-ToR | （該当 YANG モジュールなし。設定は `MUX_CABLE` / `MUX_LINKMGR` / `TUNNEL` 等の CONFIG_DB 直接記述） | Dual-ToR / MuxCable 設定 |
| 06 L2 / [VLAN](../../reference/glossary.md#term-vlan) / [LAG](../../reference/glossary.md#term-lag) / MC-LAG | [sonic-vlan](../../reference/yang/sonic-vlan.md), [sonic-vlan-sub-interface](../../reference/yang/sonic-vlan-sub-interface.md), [sonic-portchannel](../../reference/yang/sonic-portchannel.md), [sonic-mclag](../../reference/yang/sonic-mclag.md), [sonic-lldp](../../reference/yang/sonic-lldp.md) | L2 / LAG / MC-LAG 設定 |
| 07 [ACL](../../reference/glossary.md#term-acl) / [CoPP](../../reference/glossary.md#term-copp) / Mirror | [sonic-copp](../../reference/yang/sonic-copp.md), [sonic-mirror-session](../../reference/yang/sonic-mirror-session.md), [sonic-pbh](../../reference/yang/sonic-pbh.md) | CoPP、mirror、PBH |
| 08 [QoS](../../reference/glossary.md#term-qos) / Buffer / [PFC](../../reference/glossary.md#term-pfc) | [sonic-buffer-pool](../../reference/yang/sonic-buffer-pool.md), [sonic-buffer-profile](../../reference/yang/sonic-buffer-profile.md), [sonic-buffer-pg](../../reference/yang/sonic-buffer-pg.md), [sonic-buffer-queue](../../reference/yang/sonic-buffer-queue.md), [sonic-queue](../../reference/yang/sonic-queue.md), [sonic-scheduler](../../reference/yang/sonic-scheduler.md), [sonic-dscp-tc-map](../../reference/yang/sonic-dscp-tc-map.md), [sonic-tc-queue-map](../../reference/yang/sonic-tc-queue-map.md), [sonic-port-qos-map](../../reference/yang/sonic-port-qos-map.md), [sonic-pfcwd](../../reference/yang/sonic-pfcwd.md) | QoS / Buffer / PFCWD |
| 09 Telemetry / [SNMP](../../reference/glossary.md#term-snmp) | [sonic-syslog](../../reference/yang/sonic-syslog.md) | syslog |
| 14 Platform / Port / Optics | [sonic-port](../../reference/yang/sonic-port.md), [sonic-interface](../../reference/yang/sonic-interface.md), [sonic-loopback-interface](../../reference/yang/sonic-loopback-interface.md) | port / interface |
| 15 Security / [AAA](../../reference/glossary.md#term-aaa) | [sonic-system-aaa](../../reference/yang/sonic-system-aaa.md) | AAA |
| 16 [NAT](../../reference/glossary.md#term-nat) / DHCP / Time / DNS | [sonic-nat](../../reference/yang/sonic-nat.md), [sonic-dhcp-server](../../reference/yang/sonic-dhcp-server.md), [sonic-ntp](../../reference/yang/sonic-ntp.md), [sonic-dns](../../reference/yang/sonic-dns.md) | NAT / DHCP / NTP / DNS |

`docs/reference/yang/index.md` から全モジュールの一覧を参照できる。サブ章でカバーされていない module は [YANG index](../../reference/yang/index.md) を直接見る。

## YANG モジュールを読む順

各 YANG ページは「テーブル → leaf 一覧 → 型と制約 → 関連 CONFIG_DB / CLI」という共通形式で書いてある。最初の table 名と key で CONFIG_DB を当てに行くのが速い。次に leaf 単位の型・range・must / when を読む。CLI から書く場合の対応は `docs/reference/cli/*.md` を参照する。

## 関連ページ

- [YANG モジュール一覧](../../reference/yang/index.md)
- [SONiC YANG model guidelines](../../management/sonic-yang-model-guidelines.md)
- [SONiC config update validation via YANG](../../management/sonic-config-update-validation-via-yang.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
