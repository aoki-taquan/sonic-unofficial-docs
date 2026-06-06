---
title: Active-Standby Dual ToR 制限事項と既知の課題
description: Active-Standby Dual ToR の制限事項。switchover 時のパケット破損、ARP/NDP/GARP 依存、IPv6
  neighbor FAILED 問題、HLD 上 TBD のままの directed broadcast、I2C リトライ、干渉する周辺機能を、実装裏取り済みで整理する。
area: overlay
verification: code-verified
last_verified: 2026-05-09
page_kind: split-child
sources:
- repo: sonic-net/SONiC
  path: doc/dualtor/dualtor_active_standby_hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
- repo: sonic-net/sonic-swss
  path: orchagent/muxorch.cpp
- repo: sonic-net/sonic-buildimage
  path: files/scripts/arp_update
- repo: sonic-net/sonic-buildimage
  path: dockers/docker-orchagent/tunnel_packet_handler.py
- repo: sonic-net/sonic-linkmgrd
  path: src/
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

## 2. HLD 主張と実装の対応

HLD で曖昧 / TBD だった項目を実コードで裏取りした結果を整理する。`要追跡` ラベルが残っていた 3 項目は実装で確定済みのため格上げした。

- [linkmgrd](../reference/glossary.md#term-linkmgrd) のサブモジュール構成は `link_prober/` / `mux_state/` / `link_state/` / `link_manager/` の 4 ディレクトリ + `DbInterface.cpp` で構成される<!-- evidence: sonic-linkmgrd/src/ ディレクトリ構成 -->
- MuxOrch の neighbor handling は `createStandaloneTunnelRoute` / `removeStandaloneTunnelRoute` 経由の standalone tunnel route 案で確定[^2]
- arp_update の FAILED / INCOMPLETE neighbor 書き換えロジックは buildimage 同梱スクリプトで実装済[^3]
- ycabled の I2C リトライ + MUX_FAIL 報告ロジック詳細（`sonic-platform-daemons/sonic-ycabled/` 配下）は別ページで取り扱う
- Loopback0 宛 encap パケット listen + ping 駆動 service は `docker-orchagent/tunnel_packet_handler.py` の `TunnelPacketHandler` クラスとして実装済（HLD §6.3.5.1 相当）[^4]
- zero MAC neighbor を契機とした standalone tunnel route 自動 install は [muxorch](../reference/glossary.md#term-muxorch) の `MuxOrch::updateNeighbor` 内で実装済（HLD §6.3.5.2 相当）[^5]
- `accept_untracked_na` への依存は arp_update の IPv6 FAILED neighbor 復旧ロジックが前提としており、kernel 側で当該 sysctl が backport されていない環境では本ページの IPv6 neighbor 復旧フローは成立しない[^3]

## 3. 干渉する機能

- **`linkmgrd`**: state machine 主体
- **`orchagent` (`MuxCfgOrch` / `MuxOrch` / `TunnelOrch`)**: [SAI](../reference/glossary.md#term-sai) 反映 + tunnel + [ACL](../reference/glossary.md#term-acl) drop
- **`ycabled` (旧 `xcvrd`)**: I2C 経由の [MUX](../reference/glossary.md#term-mux) 制御
- **`nbrmgrd` / `arp_update` / kernel sysctl**: proxy ARP / GARP / [NDP](../reference/glossary.md#term-ndp) / proxy_ndp / accept_untracked_na
- **decap-after-tunnel CPU trap 対策の Python service**: encap パケット受信時の neighbor miss 解消用（HLD §6.3.5.1 相当）
- **`bgpd`**: 両 ToR が同じ [VLAN](../reference/glossary.md#term-vlan) を広告

## 関連ページ

- [Active-Standby Dual ToR（概要ハブ）](active-standby-dual-tor.md)
- [active-standby-dual-tor-concepts.md](active-standby-dual-tor-concepts.md) — 構成と要件
- [active-standby-dual-tor-operations.md](active-standby-dual-tor-operations.md) — 設定・CLI
- [active-standby-dual-tor-internals.md](active-standby-dual-tor-internals.md) — 内部実装

## 引用元

[^1]: `sonic-net/SONiC` `doc/dualtor/dualtor_active_standby_hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
[^2]: `sonic-net/sonic-swss` `orchagent/muxorch.cpp` L1968 / L1983 / L2442 / L2455（`createStandaloneTunnelRoute` / `removeStandaloneTunnelRoute` 呼び出しと定義）
[^3]: `sonic-net/sonic-buildimage` `files/scripts/arp_update` L182-L216（IPv6 FAILED/INCOMPLETE neighbor の zero MAC 経由再解決と permanent INCOMPLETE 設定。`accept_untracked_na` 有効化が前提）
[^4]: `sonic-net/sonic-buildimage` `dockers/docker-orchagent/tunnel_packet_handler.py` L65（`class TunnelPacketHandler`）/ L209（Loopback0 アドレスを sniff フィルタへ展開）/ L289-L302（`start_sniffer`）。`tunnel_packet_handler.conf` で supervisord 配下に常駐
[^5]: `sonic-net/sonic-swss` `orchagent/muxorch.cpp` L1956-L1980（`MuxOrch::updateNeighbor` 内の zero MAC neighbor 判定と `createStandaloneTunnelRoute` 呼び出し）

<!-- glossary-links-injected: fa77d98b9e28 -->
