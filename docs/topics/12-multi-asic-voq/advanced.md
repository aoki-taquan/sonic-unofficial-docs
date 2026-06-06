---
title: 発展トピック
description: VOQ chassis 固有のテーマ (BGP / LAG / Everflow / Reliable TSA / Multi-ASIC warm reboot) を、他章本文と対応付けて橋渡しするメモ。
area: topics
verification: hld-only
last_verified: 2026-06-06
sources:
- repo: sonic-net/SONiC
  path: doc/voq/bgp_voq_chassis.md
  ref: 4fda6b77e4fda2db76591143d03544f7895df40b
- repo: sonic-net/SONiC
  path: doc/voq/lag_hld.md
  ref: 4fda6b77e4fda2db76591143d03544f7895df40b
- repo: sonic-net/SONiC
  path: doc/voq/everflow.md
  ref: 4fda6b77e4fda2db76591143d03544f7895df40b
- repo: sonic-net/SONiC
  path: doc/voq/Reliable_TSA.md
  ref: 4fda6b77e4fda2db76591143d03544f7895df40b
- repo: sonic-net/SONiC
  path: doc/warm-reboot/Multi_ASIC_warm_reboot.md
  ref: 4fda6b77e4fda2db76591143d03544f7895df40b
related:
  cli:
  - config bgp
  - show bgp
  - show pfc
  - show acl
  - config acl
  - warm-reboot
  config_db:
  - BGP_NEIGHBOR
  - WARM_RESTART
  - PORT
  - CHASSIS_MODULE
  - CHASSIS_APP_DB
  - SYSTEM_LAG_TABLE
  - SYSTEM_LAG_MEMBER_TABLE
  yang:
  - sonic-bgp-global
  - sonic-warm-restart
  - sonic-chassis-module
---

# 発展トピック

[VOQ](../../reference/glossary.md#term-voq) chassis 固有の機能は、[BGP](../../reference/glossary.md#term-bgp)・[LAG](../../reference/glossary.md#term-lag)・Everflow・TSA・warm reboot のような既存機能領域ごとに別 [HLD](../../reference/glossary.md#term-hld) として書かれています。ここでは「他章で読むべきテーマ」と「VOQ chassis 視点で押さえるポイント」を対応付け、各章への橋渡しに徹します。

## VOQ Chassis での BGP

`bgp-setup-for-voq-chassis` は、VOQ chassis 上の BGP セッション設計を扱う HLD である。要点:

- BGP プロセスは line card の [ASIC](../../reference/glossary.md#term-asic) namespace ごとに起動し、各 ASIC インスタンスで同じ BGP 経路が programming されるよう設計されている。
- BGP 経路の next hop には、host route で resolve される system port 上の inband nexthop が用いられる。
- chassis 内部の iBGP（ASIC インスタンス間の経路同期用）と外向き eBGP は別ロールとして扱う。

BGP の章本文での読み順は [02 BGP](../02-bgp/index.md) を参照し、VOQ 観点では「namespace ごとの BGP プロセス」「inband iBGP と外向き eBGP の分離」「system port を介した nexthop resolution」の 3 点を意識する。

<!-- evidence: bgp_voq_chassis.md scope / VOQ HLD §2.5.1 inband recycle port; .cache/sonic-sources/SONiC/doc/voq/bgp_voq_chassis.md L30-L40 / L89-L93 -->

- 関連: [BGP Setup for VOQ Chassis](../../routing/bgp-setup-for-voq-chassis.md)
- 章: [02 BGP / Routing](../02-bgp/index.md)

## Distributed VOQ System での LAG

`lag-on-distributed-voq-system` は、Distributed VOQ system における LAG ([PortChannel](../../reference/glossary.md#term-portchannel)) の動作設計を扱う HLD である。要点:

- **メンバーポートは 1 つの ASIC 内に閉じる**: 1 つの LAG のメンバーが複数 ASIC に跨ることは現状サポートされない。LAG 設定そのものは非 VOQ system と同じく local port のみで構成する。
- 一方で、ある ASIC を ingress、別 ASIC の LAG を egress とするトラフィック (片方向のトラフィックがファブリック経由で別 ASIC の LAG に抜けるケース) はサポートされ、egress LAG member の選択は同一 ASIC 上の ingress/egress と同等となる。
- すべての LAG は全 ASIC の SAI 上に同じ active member 一覧で作成される必要があり、これを実現するために LAG メンバー一覧は CHASSIS_APP_DB の `SYSTEM_LAG_TABLE` / `SYSTEM_LAG_MEMBER_TABLE` で全 ASIC 間に共有される。member は system port alias で表現される。
- [LACP](../../reference/glossary.md#term-lacp) を動かす [teamd](../../reference/glossary.md#term-teamd-teamsyncd-teammgrd) / teamsyncd は **local の ASIC インスタンスにのみ存在** し、remote LAG を意識するのは SWSS と SYNCD のみ。

L2 / LAG の章本文は [06 L2 / VLAN / LAG](../06-l2-vlan-lag/index.md) を参照し、VOQ 視点では「メンバーは ASIC 内に閉じる」「remote ASIC への egress LAG 解決」「CHASSIS_APP_DB の SYSTEM_LAG_TABLE で全 ASIC 同期」を押さえる。

<!-- evidence: .cache/sonic-sources/SONiC/doc/voq/lag_hld.md L53-L54 (LAG members spanning more than one ASIC NOT supported / cross-ASIC forwarding via LAG supported), L67-L80 (SYSTEM_LAG_TABLE / SYSTEM_LAG_MEMBER_TABLE / teamsyncd local-only) -->

- 関連: [LAG on Distributed VOQ System](../../switching/lag-on-distributed-voq-system.md)
- 章: [06 L2 / VLAN / LAG](../06-l2-vlan-lag/index.md)

## Everflow on VOQ Chassis

`everflow-support-on-voq-chassis` は、Everflow (ERSPAN ベースの mirror) の mirror source / destination が別 line card にいる構成のための HLD である。要点:

- mirror source 側の line card で **ingress 時点で GRE ヘッダーを付与** し、その後通常のトラフィックとして fabric を経由し destination 側 line card へ運ばれる。
- [ACL](../../reference/glossary.md#term-acl) bind 先や session 識別は ASIC インスタンス単位で持ち、destination resolution は chassis 全体で一意に行う。

mirror / ACL の章本文は [07 ACL / CoPP / Mirror](../07-acl-copp-mirror/index.md) を参照し、VOQ 視点では「ingress line card で GRE 化してから fabric を流れる」「per-ASIC session を複数の line card で運用する」点を押さえる。

<!-- evidence: .cache/sonic-sources/SONiC/doc/voq/everflow.md L29-L31 (About this Manual: GRE rewrite at ingress linecard), L45-L47 (mirror source/destination on different linecards) -->

- 関連: [Everflow on VOQ Chassis](../../platform/everflow-support-on-voq-chassis.md)
- 章: [07 ACL / CoPP / Mirror](../07-acl-copp-mirror/index.md)

## Reliable TSA

`reliable-tsa` (Traffic Shift Away) は、特定 router を BGP route policy で広告から外して traffic を退避させる仕組みである。VOQ chassis 向けには次の設計が示されている:

- **旧実装**: Supervisor の `TSA`/`TSB` が各 line card へ SSH で順次同じコマンドを発行する形式で、unresponsive な LC で全体が遅延・失敗する問題があった。
- **Reliable TSA**: Supervisor host [CONFIG_DB](../../reference/glossary.md#term-config_db) と LC 上の per-asic CONFIG_DB がそれぞれ独立した `tsa_enabled` 属性を持ち、operational TSA 状態は Supervisor と LC 設定の **OR** で決まる。Supervisor 側の変更は `CHASSIS_APP_DB` を介して全 LC の asic インスタンスへ伝搬される。
- LC で `TSA` を実行した場合は当該 LC の asic にのみ適用され、Supervisor で `TSA` を実行した場合は LC 個別設定に関わらず全体が TSA となる。
- LC reboot 後も `startup_tsa_tsb` サービスが起動時 TSA 状態を CONFIG_DB に書き戻し、Supervisor 側 `tsa_enabled == TRUE` の間は operational 状態が TSA に保たれる。

ルーティング保守の章で扱うべきテーマで、ここでは「chassis 全体での同期が必要な保守操作」として位置付ける。

<!-- evidence: .cache/sonic-sources/SONiC/doc/voq/Reliable_TSA.md L33-L40 (legacy SSH-based behavior and its issues), L45-L59 (tsa_enabled on Supervisor + per-asic CONFIG_DB / OR semantics / CHASSIS_APP_DB propagation / startup_tsa_tsb) -->

- 関連: [Reliable TSA](../../routing/reliable-tsa.md)
- 章: [02 BGP / Routing](../02-bgp/index.md)

## Multi-ASIC Warm Reboot

`multi-asic-warm-reboot` は、[Multi-ASIC](../../reference/glossary.md#term-multi-asic) [SONiC](../../reference/glossary.md#term-sonic) device の warm reboot 設計を扱う HLD である。

- すべての ASIC で FW / SDK / SAI / [syncd](../../reference/glossary.md#term-syncd) / [orchagent](../../reference/glossary.md#term-orchagent) は同じバージョンを前提とする。
- warm reboot のプロセスは single-ASIC 観点では従来と同じで、ASIC ローカルの障害が他の健全な ASIC の warm reboot を阻害しないことが要件となる。

VOQ chassis に拡張する際は、line card 単独の warm reboot 中に Supervisor / fabric / 他の LC 側状態を維持する考慮が加わるが、その細部は別 HLD / 運用ガイドの領域である。reboot 系の章本文は [11 Reboot](../11-reboot/index.md) を参照する。

<!-- evidence: .cache/sonic-sources/SONiC/doc/warm-reboot/Multi_ASIC_warm_reboot.md L58 (scope), L78-L81 (assumption: same FW/SDK/SAI/syncd/orchagent; warm-reboot process same per single-ASIC view; ASIC-local failures must not block healthy ASICs) -->

- 関連: [Multi-ASIC Warm Reboot](../../system/multi-asic-warm-reboot.md)
- 章: [11 Reboot](../11-reboot/index.md)

## まとめ

VOQ chassis 固有のテーマは、機能としては既存の章（BGP、LAG、Mirror、Reboot）に属しつつ、namespace 跨ぎ / line card 跨ぎ / Chassis DB との協調という観点を持ちます。各章本文で機能の中身を読み、本章の [概念](concept.md) と [アーキテクチャ](architecture.md) で「どこが namespace を超えるか」を意識すると、HLD を縦横に往復しやすくなります。

## 追加の発展トピック

- **Fabric link telemetry**: VOQ chassis では fabric link 自体が監視対象。`FABRIC_PORT_TABLE` の counter / error / link state を telemetry agent から export し、cell drop の兆候を早期検出する。
- **VOQ scheduling と credit loop**: ingress VOQ が egress credit を受けて送出する仕組みで、credit return が遅延すると HOL blocking が出る。[SAI](../../reference/glossary.md#term-sai) 側 `SAI_QUEUE_ATTR_PFC_DLR_INIT_TYPE` などで dead-lock 検出と復旧を行う。
- **Chassis DB の scale**: line card / port / nexthop が増えると Chassis DB の [Redis](../../reference/glossary.md#term-redis) サイズが伸びる。memory pressure と replication 遅延が運用課題になる。
- **packet trim (truncate)**: drop されるパケットの header だけ collector に送って visibility を確保する手法。chassis 級 drop 解析で有効。
- **Multi-ASIC host のテスト**: [VS](../../reference/glossary.md#term-vs) テストで multi-ASIC を再現する場合 ([21 Lab](../21-lab-vs-developer/index.md))、namespace ごとの sonic-vs を立ち上げる手順がある。

## 既知の制約と回避方法

- **LAG メンバ line card 跨ぎの制約**: ASIC によっては line card 跨ぎ LAG メンバの hash が偏る / 未サポート。`lag-on-distributed-voq-system` の制約を SKU 別に確認する。
- **TSA 部分適用**: 一部 line card だけ TSA 適用済みの状態が長く続くと traffic がループする。Chassis DB の TSA state を全 line card で揃える運用ガイドが必要。
- **Warm reboot per line card vs. chassis**: line card 単独の warm reboot 中に Supervisor が fabric 状態を維持する。Supervisor 側だけ reboot するシナリオは要件が限定的。
- **Chassis DB schema 変更時の互換性**: Supervisor と line card の SONiC バージョン差で Chassis DB schema 互換が崩れる。staged upgrade ガイドラインに従う。

## 将来計画 / ロードマップ

- VOQ chassis の disaggregated software model (Supervisor と Line card の独立バージョン) が中長期テーマ。
- Multi-ASIC 単一 host (pizza box の multi-ASIC switch) と分散 chassis を同じ orchestration で扱う統一が進行中。
- [DASH](../../reference/glossary.md#term-dash) / [SmartSwitch](../../reference/glossary.md#term-smartswitch) 構成と VOQ chassis を組合せる構成 ([13 DASH](../13-dash-smartswitch/index.md)) の議論が早期段階で進む。

## 関連 RFC / 仕様書

- [IEEE 802.1Qcz](https://1.ieee802.org/dcb/) — Congestion Isolation (fabric 内 [PFC](../../reference/glossary.md#term-pfc) のヒント)
- [RFC 7567](https://datatracker.ietf.org/doc/html/rfc7567) — [AQM](../../reference/glossary.md#term-aqm) (VOQ credit と組合せ参考)
- VOQ アーキテクチャは商用 ASIC ベンダー仕様書に依存し、IETF/IEEE 標準は限定的。

## upstream 開発の最新動向

- `sonic-buildimage` で `chassis_db` / `database-chassis` 関連の修正が継続。replication 安定性とスキーマ拡張が主軸。
- `sonic-swss` の `vrforch` / `routeorch` / `lagorch` で system port / system LAG 周りの race fix が散発的に入る。
- VOQ chassis のテスト基盤 ([sonic-mgmt](../../reference/glossary.md#term-sonic-mgmt)) で multi-DUT scenario の coverage 拡張 PR が定期的にある。

<!-- glossary-links-injected: 4c28d1c25460 -->
