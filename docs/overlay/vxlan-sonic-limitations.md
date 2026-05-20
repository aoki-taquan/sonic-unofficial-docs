---
title: VXLAN / VNet 制限事項と既知の課題
description: VXLAN / VNet 全体設計の制限事項。Phase 1 のスコープ外項目（BGP EVPN 統合、Warm restart など）、L2
  と L3 を別トンネルとして扱う設計上の制約、干渉する機能との関係を整理する。
area: overlay
verification: code-verified
last_verified: 2026-05-09
page_kind: split-child
sources:
- repo: sonic-net/SONiC
  path: doc/vxlan/Vxlan_hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - VXLAN_TUNNEL_MAP
  - VXLAN_TUNNEL
  - VXLAN_EVPN_NVO
  - VNET
  - VLAN
  - VRF
  - VNET_ROUTE_TUNNEL_TABLE
  cli:
  - config vxlan
  - config vnet
  yang:
  - sonic-vxlan
  - sonic-vnet
---

# VXLAN / VNet 制限事項と既知の課題

このページは [VXLAN / VNet 全体設計（概要ハブ）](vxlan-sonic.md) の派生ページで、**制限事項・既知の課題・干渉する機能** に絞って整理する。概念は [vxlan-sonic-concepts.md](vxlan-sonic-concepts.md)、設定は [vxlan-sonic-operations.md](vxlan-sonic-operations.md)、内部実装は [vxlan-sonic-internals.md](vxlan-sonic-internals.md) を参照。

## 1. Phase 1 のスコープ外

| 項目 | 状態 |
|------|------|
| [BGP](../reference/glossary.md#term-bgp) [EVPN](../reference/glossary.md#term-evpn) 統合 | Phase 1 ではなし。経路は外部から `VNET_ROUTE_TABLE` / `VNET_ROUTE_TUNNEL_TABLE` に直接投入する前提[^1] |
| L2 [VXLAN](../reference/glossary.md#term-vxlan)（タグ・無タグ） | Phase 2 で導入予定 |
| HER（Head End Replication） | Phase 2 で導入予定 |
| CLI 整備 | Phase 2 で拡充。Phase 1 では [CONFIG_DB](../reference/glossary.md#term-config_db) 直接編集 |
| Warm restart | Phase 1 で非対応。[SAI](../reference/glossary.md#term-sai) VR オブジェクトが warm restart 非互換のため Phase 2 で再検討[^1] |
| Kernel [VRF](../reference/glossary.md#term-vrf) programming | [HLD](../reference/glossary.md#term-hld) スコープ外 |

## 2. 設計上の制約

- **L3 VXLAN と L2 VXLAN は別トンネル** として作られる。同じ [VTEP](../reference/glossary.md#term-vtep) で両方使う場合は 2 つの VXLAN tunnel object が SAI に生成される[^1]
- VTEP の `src_ip` は実在 IF（通常 `Loopback0`）の IP であること
- `VXLAN_TUNNEL.dst_ip` は P2P 用のオプション。P2MP では空のままにする
- `VNET.peer_list` 経路複製は **同 VTEP 内** に閉じる（remote VTEP には複製されない）

## 3. 既知の懸念点（Verifier hint）

HLD 初版が古いため、現行 master の実装と乖離している可能性が高い項目:

- BGP EVPN 統合 (Phase 2) の現状
- Warm restart 対応状況（Phase 2 で再検討予定だった）
- `VXLAN_TUNNEL_MAP` の最終スキーマ（VNI ↔ [VLAN](../reference/glossary.md#term-vlan) / VNI ↔ VRF）
- `FdbOrch` と `VxlanOrch` の協調実装（HLD で TBD だった部分）
- HER（head-end replication）の現行実装
- CLI（`config vxlan` / `show vxlan`）の [sonic-utilities](../reference/glossary.md#term-sonic-utilities) への取り込み形

## 4. 干渉する機能

- **BGP EVPN（Phase 2）**: 経路供給源として `VNET_ROUTE_TUNNEL_TABLE` を埋める
- **VLAN / VLAN_MEMBER**: L2 VXLAN は VLAN ↔ VNI mapping 前提
- **VRF（通常 VRF）**: `VrfOrch` 経由
- **[DASH](../reference/glossary.md#term-dash) / [SmartSwitch](../reference/glossary.md#term-smartswitch)**: 新しい HLD（[ENI Based Forwarding](smartswitch-eni-based-forwarding.md)）は本 HLD の VxLAN tunnel を利用
- **MC-[LAG](../reference/glossary.md#term-lag) / dual-ToR**: 拡張あり

## 関連ページ

- [VXLAN / VNet 全体設計（概要ハブ）](vxlan-sonic.md) — 元 HLD ページ
- [vxlan-sonic-concepts.md](vxlan-sonic-concepts.md) — 概念・用語
- [vxlan-sonic-operations.md](vxlan-sonic-operations.md) — 設定・運用
- [vxlan-sonic-internals.md](vxlan-sonic-internals.md) — 内部実装

## 引用元

[^1]: `sonic-net/SONiC` `doc/vxlan/Vxlan_hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- glossary-links-injected: 0726817b0ba1 -->
