---
title: 発展トピック
description: 発展トピック — VOQ chassis 固有の機能は、BGP・LAG・Everflow・TSA・warm reboot のような既存機能領域ごとに別
  HLD として書かれています。ここでは「他章で読むべきテーマ」と「VOQ chassis 視点で押さえるポイント」を対応付け、各章への橋渡しに徹します。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/routing/bgp-setup-for-voq-chassis.md
- docs/switching/lag-on-distributed-voq-system.md
- docs/platform/everflow-support-on-voq-chassis.md
- docs/routing/reliable-tsa.md
- docs/system/multi-asic-warm-reboot.md
related:
  cli:
  - config bgp
  - show bgp
  - show pfc
  - show acl
  - config acl
  config_db:
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_NETWORK
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  - BGP_AGGREGATE_ADDRESS
  - BGP_PEER_GROUP
  - BGP_NEIGHBOR_AF
  - BGP_NEIGHBOR
  yang:
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-global
  - sonic-bgp-bbr
  - sonic-bgp-aggregate-address
  - sonic-bgp-sentinel
---

# 発展トピック

[VOQ](../../reference/glossary.md#term-voq) chassis 固有の機能は、[BGP](../../reference/glossary.md#term-bgp)・[LAG](../../reference/glossary.md#term-lag)・Everflow・TSA・warm reboot のような既存機能領域ごとに別 [HLD](../../reference/glossary.md#term-hld) として書かれています。ここでは「他章で読むべきテーマ」と「VOQ chassis 視点で押さえるポイント」を対応付け、各章への橋渡しに徹します。

## VOQ Chassis での BGP

`bgp-setup-for-voq-chassis` は、VOQ chassis 上の BGP セッション設計を扱います。要点:

- BGP プロセスは line card の [ASIC](../../reference/glossary.md#term-asic) namespace ごとに起動します。
- chassis 内部の inband BGP（line card 間の同期用）と外向き BGP は別物として扱います。
- system port を経由する route の next hop は、line card 跨ぎの場合に system port 経由のシグナリングが必要になります。

BGP の章本文での読み順は [02 BGP](../02-bgp/index.md) を参照し、VOQ 観点では「namespace ごとの BGP プロセス」「inband / 外向きの分離」「system port next hop」の 3 点を意識します。

- 関連: [BGP Setup for VOQ Chassis](../../routing/bgp-setup-for-voq-chassis.md)
- 章: [02 BGP / Routing](../02-bgp/index.md)

## Distributed VOQ System での LAG

`lag-on-distributed-voq-system` は、line card 跨ぎの LAG（メンバーが複数 line card に分散する portchannel）の設計を扱います。

- LAG メンバーは複数 line card の system port にまたがれる。
- hash 結果に応じて egress system port が選ばれ、ingress 側 VOQ が宛先を切り替える。
- [LACP](../../reference/glossary.md#term-lacp) は line card 側の [teamd](../../reference/glossary.md#term-teamd-teamsyncd-teammgrd) が動かし、chassis 全体としての membership は Chassis DB と協調する。

L2 / LAG の章本文は [06 L2 / VLAN / LAG](../06-l2-vlan-lag/index.md) を参照し、VOQ 視点では「メンバーが line card 跨ぎになる可能性」「fabric を経由する hash 分散」を押さえます。

- 関連: [LAG on Distributed VOQ System](../../switching/lag-on-distributed-voq-system.md)
- 章: [06 L2 / VLAN / LAG](../06-l2-vlan-lag/index.md)

## Everflow on VOQ Chassis

`everflow-support-on-voq-chassis` は、mirror セッションが line card 跨ぎで成立するための拡張を扱います。

- mirror 元と mirror 宛先（collector）が別 line card にいる場合、cell スイッチングで fabric を経由する。
- ingress mirror と egress mirror は line card ごとに発生する。
- [ACL](../../reference/glossary.md#term-acl) bind 先や session 識別は ASIC namespace 単位で持つが、collector resolution は chassis 全体で一意。

mirror / ACL の章本文は [07 ACL / CoPP / Mirror](../07-acl-copp-mirror/index.md) を参照し、VOQ 視点では「mirror traffic も fabric を流れる」「per-line-card session が増える」点を押さえます。

- 関連: [Everflow on VOQ Chassis](../../platform/everflow-support-on-voq-chassis.md)
- 章: [07 ACL / CoPP / Mirror](../07-acl-copp-mirror/index.md)

## Reliable TSA

`reliable-tsa` （Traffic Shift Away）は、特定 device を BGP コミュニティで隔離して traffic を退避させる仕組みです。VOQ chassis では:

- 旧実装では Supervisor が各 LC へ SSH で順次発行する chassis 単位の動作だったが、Reliable TSA では Supervisor と LC がそれぞれ独立した `tsa_enabled` を持ち、operational TSA 状態は両者の OR で決まる。
- LC 単位での独立適用と、Supervisor からの全体強制 TSA の両方が可能。LC で `TSA` を実行した場合は当該 LC の各 asic にのみ適用される。
- 失敗や部分適用を避けるため、状態は Chassis DB を通じて共有される。

ルーティング保守の章で扱うべきテーマで、ここでは「chassis 全体での同期が必要な保守操作」として位置付けます。

- 関連: [Reliable TSA](../../routing/reliable-tsa.md)
- 章: [02 BGP / Routing](../02-bgp/index.md)

## Multi-ASIC Warm Reboot

`multi-asic-warm-reboot` は、[Multi-ASIC](../../reference/glossary.md#term-multi-asic) [SONiC](../../reference/glossary.md#term-sonic) の warm reboot 設計を扱います。VOQ chassis では line card 単位 / chassis 単位の両方が議論されます。

- 各 ASIC namespace の [syncd](../../reference/glossary.md#term-syncd) / [orchagent](../../reference/glossary.md#term-orchagent) / bgpd は ASIC ごとに warm restart する。
- supervisor 側は Chassis DB を温存したまま再起動する。
- line card 単独 warm reboot 中、他 line card と fabric の状態を維持する。

reboot 系の章本文は [11 Reboot](../11-reboot/index.md) を参照し、VOQ 視点では「ASIC ごとの syncd warm restart」「chassis 状態の維持」「line card 隔離 reboot」を押さえます。

- 関連: [Multi-ASIC Warm Reboot](../../system/multi-asic-warm-reboot.md)
- 章: [11 Reboot](../11-reboot/index.md)

## まとめ

VOQ chassis 固有のテーマは、機能としては既存の章（BGP、LAG、Mirror、Reboot）に属しつつ、namespace 跨ぎ / line card 跨ぎ / Chassis DB との協調という観点を持ちます。各章本文で機能の中身を読み、本章の [概念](concept.md) と [アーキテクチャ](architecture.md) で「どこが namespace を超えるか」を意識すると、HLD を縦横に往復しやすくなります。

## 追加の発展トピック

- **Fabric link telemetry**: VOQ chassis では fabric link 自体が監視対象。`FABRIC_PORT_TABLE` の counter / error / link state を telemetry agent から export し、cell drop の兆候を早期検出する。
- **VOQ scheduling と credit loop**: ingress VOQ が egress credit を受けて送出する仕組みで、credit return が遅延すると HOL blocking が出る。[SAI](../../reference/glossary.md#term-sai) 側 `SAI_QUEUE_ATTR_PFC_DLR_INIT_TYPE` などで dead-lock 検出と復旧を行う。
- **Chassis DB の scale**: line card / port / nexthop が増えると Chassis DB の [Redis](../../reference/glossary.md#term-redis) サイズが伸びる。memory pressure と replication 遅延が運用課題になる。
- **packet trim (truncate)**: drop されるパケットの header だけ collector に送って visibility を確保する手法。chassis 級 drop 解析で有効。
- **Multi-ASIC host のテスト**: VS テストで multi-ASIC を再現する場合 ([21 Lab](../21-lab-vs-developer/index.md))、namespace ごとの sonic-vs を立ち上げる手順がある。

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
- [RFC 7567](https://datatracker.ietf.org/doc/html/rfc7567) — AQM (VOQ credit と組合せ参考)
- VOQ アーキテクチャは商用 ASIC ベンダー仕様書に依存し、IETF/IEEE 標準は限定的。

## upstream 開発の最新動向

- `sonic-buildimage` で `chassis_db` / `database-chassis` 関連の修正が継続。replication 安定性とスキーマ拡張が主軸。
- `sonic-swss` の `vrforch` / `routeorch` / `lagorch` で system port / system LAG 周りの race fix が散発的に入る。
- VOQ chassis のテスト基盤 ([sonic-mgmt](../../reference/glossary.md#term-sonic-mgmt)) で multi-DUT scenario の coverage 拡張 PR が定期的にある。

<!-- glossary-links-injected: 5c9b3765d470 -->
