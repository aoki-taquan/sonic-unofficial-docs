---
title: YANG リファレンス
description: 本書の機能章 01〜21 から SONiC native YANG モジュールを逆引きするための索引。各章にどの sonic-*.yang が対応するかを 1 表で示し、`docs/reference/yang/*.md` の個別ページに接続する。
area: topics
verification: meta
last_verified: 2026-06-04
sources:
- repo: sonic-net/sonic-buildimage
  path: src/sonic-yang-models/yang-models
  ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# YANG リファレンス

このページは、機能章 (本書の章 01〜21) から [YANG](../../reference/glossary.md#term-yang) モジュールを逆引きするための索引である。[SONiC](../../reference/glossary.md#term-sonic) native YANG のページは `docs/reference/yang/*.md` に並んでおり、[CONFIG_DB](../../reference/glossary.md#term-config_db) のテーブルスキーマと 1:1 対応する。OpenConfig 側のマップ範囲は、機能ごとに [概要](concept.md) の表と、各機能 [HLD](../../reference/glossary.md#term-hld) を参照する。

native YANG のソースは `sonic-buildimage` リポジトリの `src/sonic-yang-models/yang-models/` 配下にまとまっている <!-- evidence: sonic-net/sonic-buildimage src/sonic-yang-models/yang-models @9ea932ec --> 。本ページに挙げる sonic-*.yang はすべてここに実在するモジュールに対応する。個別ページが未整備のモジュールは `.yang` のパス表記のままにしてある。

## 機能章別 YANG モジュール

| 章 | モジュール | 概要 |
| --- | --- | --- |
| 01 全体像・設定基盤 | [sonic-device_metadata](../../reference/yang/sonic-device_metadata.md), [sonic-feature](../../reference/yang/sonic-feature.md), [sonic-versions](../../reference/yang/sonic-versions.md), [sonic-system-defaults](../../reference/yang/sonic-system-defaults.md) | device 識別、機能 enable / disable、versions / system defaults |
| 02 [BGP](../../reference/glossary.md#term-bgp) / [FRR](../../reference/glossary.md#term-frr) | [sonic-bgp-global](../../reference/yang/sonic-bgp-global.md), [sonic-bgp-neighbor](../../reference/yang/sonic-bgp-neighbor.md), [sonic-bgp-peergroup](../../reference/yang/sonic-bgp-peergroup.md), [sonic-bgp-peerrange](../../reference/yang/sonic-bgp-peerrange.md), [sonic-bgp-aggregate-address](../../reference/yang/sonic-bgp-aggregate-address.md), [sonic-bgp-bbr](../../reference/yang/sonic-bgp-bbr.md), [sonic-bgp-device-global](../../reference/yang/sonic-bgp-device-global.md), [sonic-bgp-monitor](../../reference/yang/sonic-bgp-monitor.md), [sonic-bgp-sentinel](../../reference/yang/sonic-bgp-sentinel.md), [sonic-route-map](../../reference/yang/sonic-route-map.md), [sonic-route-common](../../reference/yang/sonic-route-common.md), [sonic-static-route](../../reference/yang/sonic-static-route.md), [sonic-bmp](../../reference/yang/sonic-bmp.md) | BGP / FRR 設定、route map、static route、BMP |
| 03 [VXLAN](../../reference/glossary.md#term-vxlan) / [EVPN](../../reference/glossary.md#term-evpn) / [VNET](../../reference/glossary.md#term-vnet) | [sonic-vxlan](../../reference/yang/sonic-vxlan.md), [sonic-vnet](../../reference/yang/sonic-vnet.md), [sonic-tunnel](../../reference/yang/sonic-tunnel.md), [sonic-nvgre-tunnel](../../reference/yang/sonic-nvgre-tunnel.md) | VXLAN / NVGRE tunnel、VNET overlay |
| 04 [VRF](../../reference/glossary.md#term-vrf) / [ECMP](../../reference/glossary.md#term-ecmp) | [sonic-vrf](../../reference/yang/sonic-vrf.md), [sonic-fine-grained-ecmp](../../reference/yang/sonic-fine-grained-ecmp.md), [sonic-hash](../../reference/yang/sonic-hash.md) | VRF テーブル、fine-grained ECMP、hash 制御 |
| 05 Dual-ToR | [sonic-mux-cable](../../reference/yang/sonic-mux-cable.md) （その他、`MUX_LINKMGR` / `TUNNEL` 等の CONFIG_DB 直接記述で補う） | Dual-ToR / MuxCable 設定 |
| 06 L2 / [VLAN](../../reference/glossary.md#term-vlan) / [LAG](../../reference/glossary.md#term-lag) / MC-LAG | [sonic-vlan](../../reference/yang/sonic-vlan.md), [sonic-vlan-sub-interface](../../reference/yang/sonic-vlan-sub-interface.md), [sonic-portchannel](../../reference/yang/sonic-portchannel.md), [sonic-mclag](../../reference/yang/sonic-mclag.md), [sonic-lldp](../../reference/yang/sonic-lldp.md), [sonic-spanning-tree](../../reference/yang/sonic-spanning-tree.md), [sonic-storm-control](../../reference/yang/sonic-storm-control.md), [sonic-neigh](../../reference/yang/sonic-neigh.md) | L2 / LAG / MC-LAG / STP / storm control / neighbor |
| 07 [ACL](../../reference/glossary.md#term-acl) / [CoPP](../../reference/glossary.md#term-copp) / Mirror | [sonic-copp](../../reference/yang/sonic-copp.md), [sonic-mirror-session](../../reference/yang/sonic-mirror-session.md), [sonic-pbh](../../reference/yang/sonic-pbh.md) | CoPP、mirror、PBH (ACL は CONFIG_DB 直記述で sonic-acl YANG は無し) |
| 08 [QoS](../../reference/glossary.md#term-qos) / Buffer / [PFC](../../reference/glossary.md#term-pfc) | [sonic-buffer-pool](../../reference/yang/sonic-buffer-pool.md), [sonic-buffer-profile](../../reference/yang/sonic-buffer-profile.md), [sonic-buffer-pg](../../reference/yang/sonic-buffer-pg.md), [sonic-buffer-queue](../../reference/yang/sonic-buffer-queue.md), [sonic-queue](../../reference/yang/sonic-queue.md), [sonic-scheduler](../../reference/yang/sonic-scheduler.md), [sonic-dscp-tc-map](../../reference/yang/sonic-dscp-tc-map.md), [sonic-tc-queue-map](../../reference/yang/sonic-tc-queue-map.md), [sonic-port-qos-map](../../reference/yang/sonic-port-qos-map.md), [sonic-pfcwd](../../reference/yang/sonic-pfcwd.md), [sonic-trimming](../../reference/yang/sonic-trimming.md) | QoS / Buffer / PFCWD / packet trimming |
| 09 Telemetry / [SNMP](../../reference/glossary.md#term-snmp) | [sonic-snmp](../../reference/yang/sonic-snmp.md), [sonic-syslog](../../reference/yang/sonic-syslog.md), [sonic-sflow](../../reference/yang/sonic-sflow.md), [sonic-flex_counter](../../reference/yang/sonic-flex_counter.md), [sonic-debug-counter](../../reference/yang/sonic-debug-counter.md), [sonic-crm](../../reference/yang/sonic-crm.md), [sonic-fabric-monitor](../../reference/yang/sonic-fabric-monitor.md) | SNMP / syslog / sFlow / counter 系 |
| 10 [gNMI](../../reference/glossary.md#term-gnmi) / OpenConfig | `sonic-gnmi.yang`, `sonic-telemetry.yang`, `sonic-telemetry_client.yang`, `sonic-grpcclient.yang`, `sonic-high-frequency-telemetry.yang` (個別ページは未整備、source: `src/sonic-yang-models/yang-models/`) | gNMI / streaming telemetry / gRPC client 設定 |
| 11 Reboot / Warm-restart | [sonic-warm-restart](../../reference/yang/sonic-warm-restart.md), [sonic-kdump](../../reference/yang/sonic-kdump.md) | warm / fast reboot、kernel dump |
| 12 [Multi-ASIC](../../reference/glossary.md#term-multi-asic) / [VOQ](../../reference/glossary.md#term-voq) | [sonic-fabric-port](../../reference/yang/sonic-fabric-port.md), [sonic-fabric-monitor](../../reference/yang/sonic-fabric-monitor.md), `sonic-system-port.yang`, `sonic-voq-inband-interface.yang`, `sonic-chassis-module.yang` (個別ページは未整備) | Multi-[ASIC](../../reference/glossary.md#term-asic) / VOQ chassis / system port |
| 13 [DASH](../../reference/glossary.md#term-dash) / [SmartSwitch](../../reference/glossary.md#term-smartswitch) | `sonic-dash.yang`, `sonic-smart-switch.yang` (個別ページは未整備、source: `src/sonic-yang-models/yang-models/`) | DASH / SmartSwitch overlay 設定 |
| 14 Platform / Port / Optics | [sonic-port](../../reference/yang/sonic-port.md), [sonic-interface](../../reference/yang/sonic-interface.md), [sonic-loopback-interface](../../reference/yang/sonic-loopback-interface.md), [sonic-breakout_cfg](../../reference/yang/sonic-breakout_cfg.md), [sonic-mgmt_interface](../../reference/yang/sonic-mgmt_interface.md), [sonic-mgmt_port](../../reference/yang/sonic-mgmt_port.md), [sonic-mgmt_vrf](../../reference/yang/sonic-mgmt_vrf.md) | port / interface / breakout / mgmt |
| 15 Security / [AAA](../../reference/glossary.md#term-aaa) | [sonic-system-aaa](../../reference/yang/sonic-system-aaa.md), [sonic-system-tacacs](../../reference/yang/sonic-system-tacacs.md), [sonic-system-radius](../../reference/yang/sonic-system-radius.md), [sonic-system-ldap](../../reference/yang/sonic-system-ldap.md), [sonic-passw-hardening](../../reference/yang/sonic-passw-hardening.md), [sonic-ssh-server](../../reference/yang/sonic-ssh-server.md), [sonic-fips](../../reference/yang/sonic-fips.md), [sonic-macsec](../../reference/yang/sonic-macsec.md), [sonic-banner](../../reference/yang/sonic-banner.md) | AAA / TACACS / [RADIUS](../../reference/glossary.md#term-radius) / LDAP / password / SSH / FIPS / [MACsec](../../reference/glossary.md#term-macsec) / banner |
| 16 [NAT](../../reference/glossary.md#term-nat) / DHCP / Time / DNS | [sonic-nat](../../reference/yang/sonic-nat.md), [sonic-dhcp-server](../../reference/yang/sonic-dhcp-server.md), [sonic-ntp](../../reference/yang/sonic-ntp.md), [sonic-dns](../../reference/yang/sonic-dns.md), [sonic-restapi](../../reference/yang/sonic-restapi.md) | NAT / DHCP / NTP / DNS / REST API |
| 17 [SRv6](../../reference/glossary.md#term-srv6) / [MPLS](../../reference/glossary.md#term-mpls) | [sonic-srv6](../../reference/yang/sonic-srv6.md) (MPLS 側は CONFIG_DB 直記述で sonic-mpls YANG は無し) | SRv6 sid / locator |
| 18 P4 / [PINS](../../reference/glossary.md#term-pins) | （該当する `sonic-p4*.yang` / `sonic-pins*.yang` は master の yang-models 配下に存在しない。PINS 側スキーマは別リポ sonic-net/sonic-pins を参照） | P4 / PINS は YANG ではなく gNMI/P4Runtime で扱われる |
| 19 Build / Packaging | （該当 YANG モジュールなし。build / packaging はリポジトリ構造とビルドスクリプトのスコープ） | build / packaging は YANG 対象外 |
| 20 SWSS / [SAI](../../reference/glossary.md#term-sai) / [Redis](../../reference/glossary.md#term-redis) | （該当 YANG モジュールなし。SWSS / SAI / [APPL_DB](../../reference/glossary.md#term-appl_db) の内部スキーマは YANG で定義されない） | SWSS / SAI 内部レイヤは YANG 対象外 |
| 21 Lab / Developer | （該当 YANG モジュールなし。lab / developer 用途では既存 YANG を利用） | lab セットアップは既存 YANG を流用 |

`docs/reference/yang/index.md` から全モジュールの一覧を参照できる。本表でカバーされていない module や個別ページが未整備の module は [YANG index](../../reference/yang/index.md) と上記 `yang-models/` ソースを直接見る。

## YANG モジュールを読む順

各 YANG ページは「テーブル → leaf 一覧 → 型と制約 → 関連 CONFIG_DB / CLI」という共通形式で書いてある。最初の table 名と key で CONFIG_DB を当てに行くのが速い。次に leaf 単位の型・range・must / when を読む。CLI から書く場合の対応は `docs/reference/cli/*.md` を参照する。

## 関連ページ

- [YANG モジュール一覧](../../reference/yang/index.md)
- [SONiC YANG model guidelines](../../management/sonic-yang-model-guidelines.md)
- [SONiC config update validation via YANG](../../management/sonic-config-update-validation-via-yang.md)

<!-- glossary-links-injected: e26f59110781 -->
