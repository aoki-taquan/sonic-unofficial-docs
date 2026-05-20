---
title: L2 発展トピック
description: L2 発展トピック — このページは、通常の VLAN / PortChannel / MC-LAG 設計から一歩外れる話題の入口です。OpenConfig
  は管理 API 章、distributed VOQ LAG は VOQ 章、Wake-on-LAN は運用ツールとしても読む対象です。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/switching/openconfig-support-for-portchannel-aggregate-interface.md
- docs/switching/add-support-for-vlan-interface-using-openconfig-yang.md
- docs/switching/lag-on-distributed-voq-system.md
- docs/switching/wake-on-lan-in-sonic.md
related:
  cli:
  - config portchannel
  - show interfaces
  - config bgp
  - show bgp
  - show bfd
  - config vlan
  - show vlan
  config_db:
  - VLAN
  - VLAN_INTERFACE
  - VLAN_MEMBER
  - PORTCHANNEL
  - PORTCHANNEL_MEMBER
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_NETWORK
  yang:
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-global
  - sonic-bgp-bbr
  - sonic-bgp-aggregate-address
  - sonic-bgp-sentinel
---

# L2 発展トピック

このページは、通常の [VLAN](../../reference/glossary.md#term-vlan) / [PortChannel](../../reference/glossary.md#term-portchannel) / MC-[LAG](../../reference/glossary.md#term-lag) 設計から一歩外れる話題の入口です。OpenConfig は管理 API 章、distributed [VOQ](../../reference/glossary.md#term-voq) LAG は VOQ 章、Wake-on-LAN は運用ツールとしても読む対象です。

## OpenConfig VLAN / PortChannel

[SONiC](../../reference/glossary.md#term-sonic) 独自 CLI / [CONFIG_DB](../../reference/glossary.md#term-config_db) ではなく、REST / [gNMI](../../reference/glossary.md#term-gnmi) で OpenConfig [YANG](../../reference/glossary.md#term-yang) モデルを使う場合は、transformer が OpenConfig tree と SONiC の既存 CONFIG_DB を対応付けます。

PortChannel では `openconfig-interfaces` と `openconfig-if-aggregate` を使い、Ethernet 側の `aggregate-id` で member を表現し、PortChannel 側の `aggregation/config/min-links` で集約条件を表現します。

VLAN では `openconfig-vlan` の `switched-vlan` と `routed-vlan` を使います。`switched-vlan` は access / trunk と VLAN member、`routed-vlan` は VLAN interface の IP 設定に対応します。CONFIG_DB の `VLAN` / `VLAN_MEMBER` / `VLAN_INTERFACE` はそのまま使われ、スキーマ自体を増やす設計ではありません。

## Distributed VOQ LAG

分散 VOQ シャシでは、各 [ASIC](../../reference/glossary.md#term-asic) が独立した SONiC インスタンスとして動作し、ASIC 間共有情報を `CHASSIS_APP_DB` に載せます。LAG は全 ASIC から一貫して見える必要があるため、`SYSTEM_LAG_TABLE` と `SYSTEM_LAG_MEMBER_TABLE` で system-wide な LAG 情報を共有します。

重要な制約は、メンバが複数 ASIC を跨ぐ LAG はサポートしないことです。各 ASIC のローカル LAG は通常どおり `PORTCHANNEL` / `PORTCHANNEL_MEMBER` で設定され、他 ASIC から見える remote LAG は swss / [syncd](../../reference/glossary.md#term-syncd) 側で扱われます。

通常の L2 章では「PortChannel の作り方」までを扱い、VOQ 章では「system_lag_id、CHASSIS_APP_DB、remote LAG programming」を扱う、と分けて読むのが自然です。

## Wake-on-LAN

Wake-on-LAN は L2 frame または UDP payload で Magic Packet を送る機能です。VLAN / LAG の forwarding 設計そのものではありませんが、スイッチを Magic Packet の送信元として使うため、L2 到達性やブロードキャストの扱いと関係します。

現行ページでは [HLD](../../reference/glossary.md#term-hld) と実装の差分があり、CLI は Rust 実装、[gNOI](../../reference/glossary.md#term-gnoi) service は取り込み未確認と整理されています。運用ツールとして使う場合は、対象 NIC の WoL 受信設定、送信方式、ブロードキャスト / ルーティング境界を別途確認します。

## 他章との境界

| 話題 | この章で扱う範囲 | 主に読む章 |
|---|---|---|
| gNMI / REST | OpenConfig がどの L2 テーブルに写るか | 管理 API |
| Distributed VOQ LAG | 通常 LAG との違いと制約 | VOQ / Chassis |
| Dual-ToR | mux state machine / linkmgrd / MuxOrch による ToR 間切替 | Dual-ToR |
| WoL | L2 到達性と Magic Packet の概要 | 運用 / 管理 |

## 関連ページ

- [PortChannel OpenConfig YANG サポート](../../switching/openconfig-support-for-portchannel-aggregate-interface.md)
- [VLAN interface OpenConfig YANG 対応](../../switching/add-support-for-vlan-interface-using-openconfig-yang.md)
- [分散 VOQ シャシでの LAG](../../switching/lag-on-distributed-voq-system.md)
- [Wake-on-LAN](../../switching/wake-on-lan-in-sonic.md)

## 発展トピック

- **[LACP](../../reference/glossary.md#term-lacp) fast rate と sub-second 切替**: `LACP_RATE` を fast にすると 1 秒間隔で PDU を送る。LAG メンバ障害の検出を 1 秒未満で行いたい場合、[BFD](../../reference/glossary.md#term-bfd) micro-BFD (RFC 7130) を LAG メンバごとに張る選択肢もある。
- **MAC learning rate limiting / [FDB](../../reference/glossary.md#term-fdb) aging**: 大規模 L2 (Dual-ToR + 大量 VM) では MAC 学習 burst が ASIC FDB を埋める。`FDB_AGING_TIME` と `MAC_LEARN_LIMIT` の設計が運用に効く。
- **PVST / RPVST との互換**: SONiC は STP/RSTP を実装するが、ベンダー混在環境では PVST/RPVST との BPDU 互換性で詰まる例がある。MST に寄せるのが安全策。
- **Storm Control の per-VLAN 化**: `STORM_CONTROL` は通常 port 単位だが、VLAN 単位で broadcast/multicast/unknown unicast を別々に絞る拡張提案がある。
- **PortChannel min-links と graceful drain**: メンバ link を保守で外すとき、min-links を下回ると LAG 全体がダウンする。`config portchannel member del` の手順と上流 [BGP](../../reference/glossary.md#term-bgp) の drain を組み合わせる。

## 既知の制約と回避方法

- **異種速度のメンバ混在**: 100G + 400G を同じ PortChannel に入れるとハッシュが偏る。WCMP 相当の weight 設定が ASIC でサポートされない限り、同速度で揃える。
- **VLAN interface のホスト側設定漏れ**: Linux kernel 側 `Vlan100` interface の MTU と CONFIG_DB の `VLAN_INTERFACE` MTU が食い違うと一部 traffic で fragmentation 起こる。`show interfaces status` と `ip -d link show` 双方で確認する。
- **MC-LAG ICCP の peer link 障害**: peer link が落ちると split-brain になりうる。keepalive 経路を peer link と別物理経路で組む。
- **WoL の VLAN flood 制限**: Magic Packet を VLAN flood で送るとき、unknown unicast flooding が抑制されていると届かない。送信前に target MAC を FDB に静的登録するなどの回避が必要。

## 将来計画 / ロードマップ

- OpenConfig による L2 設定は段階的に追加されており、`openconfig-network-instance` ベースの L2 bridge モデルへの収束が長期テーマ。
- LACP の hardware offload (high-availability platform 向け) は ASIC 依存だが、[SAI](../../reference/glossary.md#term-sai) 拡張提案がある。
- distributed LAG (複数 ASIC 跨ぎ member) は VOQ chassis では制約付きで、将来的に system-wide LAG への拡張が議論される。

## 関連 RFC / 仕様書

- [IEEE 802.1AX](https://1.ieee802.org/lacp/) — Link Aggregation
- [IEEE 802.1Q](https://1.ieee802.org/tsn/) — VLAN tagging
- [IEEE 802.1D / 802.1w / 802.1s](https://1.ieee802.org/spanning-tree/) — STP / RSTP / MST
- [RFC 7130](https://datatracker.ietf.org/doc/html/rfc7130) — Micro-BFD for LAG
- [RFC 7432](https://datatracker.ietf.org/doc/html/rfc7432) — [EVPN](../../reference/glossary.md#term-evpn) multihoming は MC-LAG の代替

## upstream 開発の最新動向

- `sonic-swss` の `portsorch` / `lagorch` で min-links と member 増減時の race 修正 PR が継続。
- `teamd` カスタマイズ層と Linux upstream `libteam` のバージョン差で LACP debug ログのフォーマットがずれる事例があり、PR でフォーマット安定化が進む。
- OpenConfig transformer ([sonic-mgmt](../../reference/glossary.md#term-sonic-mgmt)-common) で VLAN / PortChannel の YANG 対応拡張が定期的に入る。設定変換の境界が拡張されるごとに `show running-configuration` の出力が変わる。

## ハンドオフ

- **概念とアーキテクチャ**は本章の [concept](concept.md) / [internals](internals.md) と、area HLD の [switching/](../../switching/index.md) 配下のページ群で完結する。VLAN_MEMBER / PORTCHANNEL_MEMBER のテーブル遷移と [portsorch](../../reference/glossary.md#term-portsorch) / lagorch の責務分担は internals で扱う。
- **設定とリファレンス**は [reference/cli](../../reference/cli/index.md) の `config vlan` / `config portchannel` 系と、`VLAN`, `VLAN_MEMBER`, `VLAN_INTERFACE`, `PORTCHANNEL`, `PORTCHANNEL_MEMBER` の [CONFIG_DB スキーマ](../../reference/config-db/index.md)、および `sonic-vlan`, `sonic-portchannel` YANG モジュールに集約。
- **本ページ** は OpenConfig 変換、distributed VOQ LAG の制約、WoL、micro-BFD、storm control、PortChannel min-links/drain など、L2 単独で閉じない発展トピックを扱う。

## トラブルシュート観点

- PortChannel が up しないときは、まず `show interfaces portchannel` で member の collected/distributed 状態を確認する。LACP PDU が片方向しか流れていない場合 (一方が active/passive 設定不一致) は `teamdctl <po> state` の `runner.actor_lacpdu_info` と `runner.partner_lacpdu_info` を見比べる。
- VLAN flooding が想定外の port に届く・届かないときは、`fdbshow` と `bcmcmd 'l2 show'` (Broadcom 系) で FDB と ASIC の MAC table を突き合わせる。`MAC_LEARN_LIMIT` 到達時は新規 MAC が flooding 扱いになる。
- distributed VOQ chassis で `SYSTEM_LAG_TABLE` に LAG が現れない場合、`chassis_db` の [Redis](../../reference/glossary.md#term-redis) 接続と、各 ASIC の `bgp` docker から `redis-cli -h <supervisor>` でアクセスできるかを点検する。

## 検証パスとラボ要件

- LACP fast rate と member down 検出時間は、`sonic-mgmt` の `lag/test_lag_2.py` 系テストで member を意図的に shut/no-shut させ、上流 BGP が再収束するまでの時間を計測する。target は fast rate で 3 秒以内、micro-BFD 併用で 1 秒以内。
- VLAN 大量 (4k 近く) 構成での scale 検証は、CONFIG_DB へ `VLAN|Vlan100`〜`Vlan4094` を投入し、`swssloglevel` を notice にして [orchagent](../../reference/glossary.md#term-orchagent) / [vlanmgrd](../../reference/glossary.md#term-vlanmgrd) のレイテンシを観測する。`syncd` queue depth が異常に伸びる場合、ASIC capability の VLAN 数上限を確認する。
- OpenConfig 変換は `gnmi_cli` で `openconfig-interfaces:interfaces` を get/set し、変換後の CONFIG_DB と round-trip 一致を確認する。`sonic-mgmt-common` の `transformer/test_*` がベースライン。

## 関連ページ (追補)

- [OpenConfig support for PortChannel](../../switching/openconfig-support-for-portchannel-aggregate-interface.md)
- [VLAN interface OpenConfig YANG support](../../switching/add-support-for-vlan-interface-using-openconfig-yang.md)
- [LAG on distributed VOQ system](../../switching/lag-on-distributed-voq-system.md)
- [Wake-on-LAN in SONiC](../../switching/wake-on-lan-in-sonic.md)
- [05 Dual-ToR: mux 制御の構成と運用](../05-dual-tor/index.md)
- [10 gNMI / OpenConfig: 変換層の責務](../10-gnmi-openconfig/index.md)
- [12 Multi-ASIC / VOQ: chassis 内 LAG とリモート LAG](../12-multi-asic-voq/index.md)

<!-- glossary-links-injected: 45f78fb52e76 -->
