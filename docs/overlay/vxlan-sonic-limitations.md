---
title: VXLAN / VNet 制限事項と既知の課題
description: VXLAN / VNet 全体設計の制限事項を整理する。元 HLD の Phase 1 スコープ外項目を現行
  master 実装と突き合わせ、L2 と L3 を別トンネルとして扱う設計上の制約、干渉する機能との関係をまとめる。
area: overlay
verification: code-verified
last_verified: 2026-06-04
page_kind: split-child
sources:
- repo: sonic-net/SONiC
  path: doc/vxlan/Vxlan_hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
- repo: sonic-net/sonic-swss
  path: orchagent/vxlanorch.cpp
- repo: sonic-net/sonic-swss
  path: orchagent/fdborch.cpp
- repo: sonic-net/sonic-utilities
  path: config/vxlan.py
- repo: sonic-net/sonic-utilities
  path: show/vxlan.py
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

元 HLD は Phase 1 / Phase 2 の段階的計画として書かれているが、現行 master では Phase 2 想定項目の大半が実装済みである。本ページは **HLD 上の制約と現行実装の差分** を切り分けて記述する。

## 1. 元 HLD で「Phase 1 スコープ外」とされていた項目の現状

| 項目 | 元 HLD での扱い | 現行 master の状態 |
|------|----------------|---------------------|
| [BGP](../reference/glossary.md#term-bgp) [EVPN](../reference/glossary.md#term-evpn) 統合 | Phase 1 ではなし。経路は外部から `VNET_ROUTE_TABLE` / `VNET_ROUTE_TUNNEL_TABLE` に直接投入する前提[^1] | 実装済み。`VxlanOrch` 配下に `EvpnNvoOrch` / `EvpnRemoteVnip2pOrch` / `EvpnRemoteVnip2mpOrch` が存在し、EVPN MAC/IP 学習経路を取り込む[^2] |
| L2 [VXLAN](../reference/glossary.md#term-vxlan)（タグ・無タグ） | Phase 2 で導入予定[^1] | 実装済み。`VXLAN_TUNNEL_MAP` で [VLAN](../reference/glossary.md#term-vlan) ↔ VNI を mapping し、`FdbOrch` が `APP_VXLAN_FDB_TABLE_NAME` 由来エントリを `FDB_ORIGIN_VXLAN_ADVERTIZED` として扱う[^2][^3] |
| HER（Head End Replication） | Phase 2 で導入予定[^1] | 実装済み。`VxlanTunnel` は `SAI_TUNNEL_PEER_MODE_P2MP` で生成され、P2MP tunnel bridge port で [FDB](../reference/glossary.md#term-fdb) 学習が行われる[^2] |
| CLI 整備 | Phase 2 で拡充。Phase 1 では [CONFIG_DB](../reference/glossary.md#term-config_db) 直接編集[^1] | 実装済み。[sonic-utilities](../reference/glossary.md#term-sonic-utilities) に `config vxlan` / `show vxlan` コマンド群が取り込まれている[^4][^5] |
| Warm restart | Phase 1 で非対応。[SAI](../reference/glossary.md#term-sai) VR オブジェクトが warm restart 非互換のため Phase 2 で再検討[^1] | 実装済み。`vxlanorch.cpp` は `WarmStart::getWarmStartState("orchagent", state)` で warmboot 状態を判定し、新規 tunnel のみ追加する分岐を持つ[^2] |
| Kernel [VRF](../reference/glossary.md#term-vrf) programming | [HLD](../reference/glossary.md#term-hld) スコープ外[^1] | スコープ外のまま（変更なし） |

## 2. 設計上の制約（現行 master でも残る）

- **L3 VXLAN と L2 VXLAN は別トンネル** として作られる。同じ [VTEP](../reference/glossary.md#term-vtep) で両方使う場合は 2 つの VXLAN tunnel object が SAI に生成される[^1]
- VTEP の `src_ip` は実在 IF（通常 `Loopback0`）の IP であること
- `VXLAN_TUNNEL.dst_ip` は P2P 用のオプション。P2MP では空のままにする（`dst_ip == nullptr` のとき `SAI_TUNNEL_PEER_MODE_P2MP` で生成される）[^2]
- `VNET.peer_list` 経路複製は **同 VTEP 内** に閉じる（remote VTEP には複製されない）[^1]

## 3. 干渉する機能

- **BGP EVPN**: 経路供給源として `VNET_ROUTE_TUNNEL_TABLE` および `APP_VXLAN_FDB_TABLE` を埋める[^2][^3]
- **VLAN / VLAN_MEMBER**: L2 VXLAN は VLAN ↔ VNI mapping 前提（`VXLAN_TUNNEL_MAP` の `vlan` / `vni` キー）[^2]
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
[^2]: `sonic-net/sonic-swss` `orchagent/vxlanorch.cpp`（`WarmStart::getWarmStartState` L1919-1948 / `SAI_TUNNEL_PEER_MODE_P2MP` L368 / `EvpnNvoOrch` L1678・`EvpnRemoteVnip2pOrch` L2449・`EvpnRemoteVnip2mpOrch` L2611 / `VXLAN_TUNNEL_MAP` L2010-2060）
[^3]: `sonic-net/sonic-swss` `orchagent/fdborch.cpp`（`APP_VXLAN_FDB_TABLE_NAME` 処理と `FDB_ORIGIN_VXLAN_ADVERTIZED` 分岐 L719-893）
[^4]: `sonic-net/sonic-utilities` `config/vxlan.py`
[^5]: `sonic-net/sonic-utilities` `show/vxlan.py`

<!-- glossary-links-injected: e945c9c07207 -->
