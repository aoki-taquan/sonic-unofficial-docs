---
title: Active-Standby Dual ToR 制限事項と既知の課題
description: Active-Standby Dual ToR の制限事項。switchover 時のパケット破損、ARP/NDP/GARP 依存、IPv6
  neighbor FAILED 問題、HLD 上 TBD のままの directed broadcast、I2C リトライ、干渉する周辺機能を整理する。
area: overlay
verification: code-verified
last_verified: 2026-05-09
page_kind: split-child
sources:
- repo: sonic-net/SONiC
  path: doc/dualtor/dualtor_active_standby_hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - VLAN
  - ACL_RULE
  - ACL_TABLE
  - VLAN_INTERFACE
  - VLAN_MEMBER
  - MUX_LINKMGR
  - MUX_CABLE
  cli:
  - show arp
  - config vlan
  - show acl
  - config acl
  - show vlan
  - show ndp
  yang:
  - sonic-vlan
  - sonic-mux-cable
  - sonic-vlan-sub-interface
  - sonic-port
  - sonic-crm
---

# Active-Standby Dual ToR 制限事項と既知の課題

このページは [Active-Standby Dual ToR（概要ハブ）](active-standby-dual-tor.md) の派生ページで、**制限事項・既知の課題・干渉する機能** に絞って整理する。概念は [active-standby-dual-tor-concepts.md](active-standby-dual-tor-concepts.md)、設定は [active-standby-dual-tor-operations.md](active-standby-dual-tor-operations.md)、内部実装は [active-standby-dual-tor-internals.md](active-standby-dual-tor-internals.md) を参照。

## 1. 設計上の制約

- ToR → NIC 方向 switchover で **数パケットの破損 / drop** あり[^1]
- standby ToR は [ARP](../reference/glossary.md#term-arp) request drop で **GARP / unsolicited NA に依存**
- IPv6 neighbor `FAILED` 問題は kernel patch + `arp_update` 修正に依存
- [HLD](../reference/glossary.md#term-hld) では neighbor 取扱い 3 案の最終採用案を明示していない（実コード裏取りで確定: standalone tunnel route 案）
- directed broadcast は HLD 上 TBD
- y-cable I2C 失敗時の MUX_FAIL 復旧シナリオは HLD 上限定的
- LinkManager は LinkProber より低頻度（hysteresis 抑制）

## 2. 既知の懸念点（Verifier hint）

- [linkmgrd](../reference/glossary.md#term-linkmgrd) の LinkProber / MuxState / LinkState / LinkManager 4 サブモジュールの現行実装確認 — 実装の構成は `link_prober/` / `mux_state/` / `link_manager/` の 3 ディレクトリ + `DbInterface.cpp` で概ね一致を確認済
- MuxOrch の neighbor handling 3 案のうちどれが採用されているか確認 — `createStandaloneTunnelRoute` / `removeStandaloneTunnelRoute` 案で確定
- ycabled の I2C リトライ + MUX_FAIL 報告ロジック実装確認
- 6.3.5.1 の Loopback0 宛 encap パケット listen + ping 駆動 service の所在確認
- 6.3.5.2 の zero mac neighbor + tunnel route 自動 install の [neighsyncd](../reference/glossary.md#term-neighsyncd) / [muxorch](../reference/glossary.md#term-muxorch) 実装確認
- arp_update の FAILED → INCOMPLETE 書き換えの取り込み確認
- accept_untracked_na の kernel backport 状況確認

## 3. 干渉する機能

- **`linkmgrd`**: state machine 主体
- **`orchagent` (`MuxCfgOrch` / `MuxOrch` / `TunnelOrch`)**: [SAI](../reference/glossary.md#term-sai) 反映 + tunnel + [ACL](../reference/glossary.md#term-acl) drop
- **`ycabled` (旧 `xcvrd`)**: I2C 経由の [MUX](../reference/glossary.md#term-mux) 制御
- **`nbrmgrd` / `arp_update` / kernel sysctl**: proxy ARP / GARP / [NDP](../reference/glossary.md#term-ndp) / proxy_ndp / accept_untracked_na
- **decap-after-tunnel CPU trap 対策の Python service**: 6.3.5.1 の neighbor miss 解消用
- **`bgpd`**: 両 ToR が同じ [VLAN](../reference/glossary.md#term-vlan) を広告

## 関連ページ

- [Active-Standby Dual ToR（概要ハブ）](active-standby-dual-tor.md)
- [active-standby-dual-tor-concepts.md](active-standby-dual-tor-concepts.md) — 構成と要件
- [active-standby-dual-tor-operations.md](active-standby-dual-tor-operations.md) — 設定・CLI
- [active-standby-dual-tor-internals.md](active-standby-dual-tor-internals.md) — 内部実装

## 引用元

[^1]: `sonic-net/SONiC` `doc/dualtor/dualtor_active_standby_hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- glossary-links-injected: fa77d98b9e28 -->
