---
title: スイッチング
description: "スイッチング — VLAN、LAG、MCLAG、STP、MACsec、L2 forwarding など L2 制御面を扱う章。"
area: switching
verification: meta
last_verified: 2026-05-13
---

# スイッチング
[VLAN](../reference/glossary.md#term-vlan)、[LAG](../reference/glossary.md#term-lag)、[MCLAG](../reference/glossary.md#term-mclag)、STP、[MACsec](../reference/glossary.md#term-macsec)、L2 forwarding など L2 制御面を扱う章。

## この章の趣旨

L2 / link layer の制御面を扱う。具体的には:

- **VLAN / Switchport モード**: access / trunk / routed、VLAN range、OpenConfig [YANG](../reference/glossary.md#term-yang) 対応
- **LAG ([PortChannel](../reference/glossary.md#term-portchannel))**: teammgrd、[LACP](../reference/glossary.md#term-lacp)、warm-reboot 中の retry、分散 [VOQ](../reference/glossary.md#term-voq) シャシでの system LAG
- **MCLAG / ICCP**: dynamic config、unique IP、isolation group
- **MSTP**: Multiple Spanning Tree Protocol on [SONiC](../reference/glossary.md#term-sonic)
- **MACsec**: wpa_supplicant 連携、Gearbox PHY 上の backend 選択、FIPS POST
- **L2 forwarding**: [FDB](../reference/glossary.md#term-fdb) flush / aging、static MAC、リンクイベントダンピング、Wake-on-LAN

## この章の読み方
目的の機能名からページを選び、設定名や CLI 名が必要な場合はリファレンス章を併読する。`Discrepancy-found` は [HLD](../reference/glossary.md#term-hld) と現行実装に差分が見つかったページなので、設計値として読む前に本文の注記を確認する。

## 主要ページ

- [L2 Forwarding 強化（FDB flush / aging / static MAC / VLAN range）](layer-2-forwarding-enhancements.md)
- [Switchport モード（access / trunk / routed）と VLAN CLI 拡張](switch-port-modes-and-vlan-cli-enhancement.md)
- [MCLAG Enhancements（dynamic config / unique IP / isolation group / static MAC）](mclag-enhancements.md)
- [Multiple Spanning Tree Protocol (MSTP) on SONiC](multiple-spanning-tree-protocol.md)
- [MACsec on SONiC（wpa_supplicant + MACsec Mgr/Orch + SAI）](macsec-sonic-high-level-design-document.md)
- [VLAN インタフェースの OpenConfig YANG 対応（REST / gNMI）](add-support-for-vlan-interface-using-openconfig-yang.md)
- [PortChannel (LAG) の OpenConfig YANG サポート（REST / gNMI）](openconfig-support-for-portchannel-aggregate-interface.md)
- [BUM ストームコントロール（PORT_STORM_CONTROL）](sonic-bum-storm-control.md)
- [Wake-on-LAN（wol CLI と SonicWolService gNOI）](wake-on-lan-in-sonic.md)
- [リンクイベントダンピング（AIED アルゴリズムと SyncD intercept）](link-event-damping-hld.md)

## 扱わない範囲

- L3 機能（IP routing / [BGP](../reference/glossary.md#term-bgp) / [VRF](../reference/glossary.md#term-vrf)）は [routing](../routing/index.md) 章
- L2 over IP ([VXLAN](../reference/glossary.md#term-vxlan) / NVGRE / VNet) は [overlay](../overlay/index.md) 章
- [ACL](../reference/glossary.md#term-acl) / [QoS](../reference/glossary.md#term-qos) / buffer / scheduler は [acl-qos](../acl-qos/index.md) 章
- PortChannel / VLAN の **CLI コマンド一覧** や **[CONFIG_DB](../reference/glossary.md#term-config_db) テーブル定義** は [reference](../reference/index.md) 章
## 検証状況
- ページ数: 19
- 分布: Code-verified: 12 / Discrepancy-found: 4 / HLD-only: 3

## 実装差分があるページ
- [L2 Forwarding 強化（FDB flush / aging / static MAC / VLAN range）](layer-2-forwarding-enhancements.md)
- [Switchport モード（access / trunk / routed）と VLAN CLI 拡張](switch-port-modes-and-vlan-cli-enhancement.md)
- [Wake-on-LAN（wol CLI と SonicWolService gNOI）](wake-on-lan-in-sonic.md)
- [リンクイベントダンピング（AIED アルゴリズムと SyncD intercept）](link-event-damping-hld.md)

## HLD-only のページ
- [ICCPd 内部構成（MC-LAG / MLACP FSM ファイル別マップ）](brief-introduction-of-iccp-code.md)
- [SYSTEM_DEFAULTS テーブルによる SONiC 既定値の集約](control-sonic-behaviors-with-system-defaults-table.md)

## ページ一覧

| ページ | 検証 |
|---|---|
| [BUM ストームコントロール（PORT_STORM_CONTROL）](sonic-bum-storm-control.md) | Code-verified |
| [FIPS 向け MACsec SAI POST（FIPS_MACSEC_POST_TABLE）](sonic-sai-post-support-for-macsec.md) | Code-verified |
| [Gearbox PHY ごとの MACsec backend 決定（macsec_supported）](sonic-hld-deterministic-macsec-backend-selection-for-gearbox-ports.md) | Code-verified |
| [ICCPd 内部構成（MC-LAG / MLACP FSM ファイル別マップ）](brief-introduction-of-iccp-code.md) | HLD-only |
| [IP / LAG / MTU の Incremental Update（portmgrd / intfmgrd / teammgrd 分担）](sonic-ip-lag-incremental-update.md) | Code-verified |
| [L2 Forwarding 強化（FDB flush / aging / static MAC / VLAN range）](layer-2-forwarding-enhancements.md) | Discrepancy-found |
| [MACsec on SONiC（wpa_supplicant + MACsec Mgr/Orch + SAI）](macsec-sonic-high-level-design-document.md) | Code-verified |
| [MCLAG Enhancements（dynamic config / unique IP / isolation group / static MAC）](mclag-enhancements.md) | Code-verified |
| [Multiple Spanning Tree Protocol (MSTP) on SONiC](multiple-spanning-tree-protocol.md) | Code-verified |
| [PortChannel (LAG) の OpenConfig YANG サポート（REST / gNMI）](openconfig-support-for-portchannel-aggregate-interface.md) | Code-verified |
| [ProducerStateTable の view switching（warm reboot 用の差分適用）](view-switching-in-producerstatetable.md) | Code-verified |
| [SONiC Basic L2 モードテストプラン（FDB / VLAN / SNMP の最小機能検証）](sonic-basic-l2-mode-test-plan.md) | Code-verified |
| [SYSTEM_DEFAULTS テーブルによる SONiC 既定値の集約](control-sonic-behaviors-with-system-defaults-table.md) | HLD-only |
| [Switchport モード（access / trunk / routed）と VLAN CLI 拡張](switch-port-modes-and-vlan-cli-enhancement.md) | Discrepancy-found |
| [VLAN インタフェースの OpenConfig YANG 対応（REST / gNMI）](add-support-for-vlan-interface-using-openconfig-yang.md) | Code-verified |
| [Wake-on-LAN（wol CLI と SonicWolService gNOI）](wake-on-lan-in-sonic.md) | Discrepancy-found |
| [Warm-reboot 中の LACP retry count 拡張（LACP version 0xf1 / 新規 TLV）](increasing-lacp-pdu-timeout-during-warm-reboot.md) | Code-verified |
| [リンクイベントダンピング（AIED アルゴリズムと SyncD intercept）](link-event-damping-hld.md) | Discrepancy-found |
| [分散 VOQ シャシでの LAG（SYSTEM_LAG_TABLE と system_lag_id）](lag-on-distributed-voq-system.md) | Code-verified |

<!-- glossary-links-injected: 65a8d86c0245 -->
