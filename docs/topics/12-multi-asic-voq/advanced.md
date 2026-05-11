---
title: 発展トピック
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/routing/bgp-setup-for-voq-chassis.md
  - docs/switching/lag-on-distributed-voq-system.md
  - docs/platform/everflow-support-on-voq-chassis.md
  - docs/routing/reliable-tsa.md
  - docs/system/multi-asic-warm-reboot.md
---

# 発展トピック

VOQ chassis 固有の機能は、BGP・LAG・Everflow・TSA・warm reboot のような既存機能領域ごとに別 HLD として書かれています。ここでは「他章で読むべきテーマ」と「VOQ chassis 視点で押さえるポイント」を対応付け、各章への橋渡しに徹します。

## VOQ Chassis での BGP

`bgp-setup-for-voq-chassis` は、VOQ chassis 上の BGP セッション設計を扱います。要点:

- BGP プロセスは line card の ASIC namespace ごとに起動します。
- chassis 内部の inband BGP（line card 間の同期用）と外向き BGP は別物として扱います。
- system port を経由する route の next hop は、line card 跨ぎの場合に system port 経由のシグナリングが必要になります。

BGP の章本文での読み順は [02 BGP](../02-bgp/index.md) を参照し、VOQ 観点では「namespace ごとの BGP プロセス」「inband / 外向きの分離」「system port next hop」の 3 点を意識します。

- 関連: [BGP Setup for VOQ Chassis](../../routing/bgp-setup-for-voq-chassis.md)
- 章: [02 BGP / Routing](../02-bgp/index.md)

## Distributed VOQ System での LAG

`lag-on-distributed-voq-system` は、line card 跨ぎの LAG（メンバーが複数 line card に分散する portchannel）の設計を扱います。

- LAG メンバーは複数 line card の system port にまたがれる。
- hash 結果に応じて egress system port が選ばれ、ingress 側 VOQ が宛先を切り替える。
- LACP は line card 側の teamd が動かし、chassis 全体としての membership は Chassis DB と協調する。

L2 / LAG の章本文は [06 L2 / VLAN / LAG](../06-l2-vlan-lag/index.md) を参照し、VOQ 視点では「メンバーが line card 跨ぎになる可能性」「fabric を経由する hash 分散」を押さえます。

- 関連: [LAG on Distributed VOQ System](../../switching/lag-on-distributed-voq-system.md)
- 章: [06 L2 / VLAN / LAG](../06-l2-vlan-lag/index.md)

## Everflow on VOQ Chassis

`everflow-support-on-voq-chassis` は、mirror セッションが line card 跨ぎで成立するための拡張を扱います。

- mirror 元と mirror 宛先（collector）が別 line card にいる場合、cell スイッチングで fabric を経由する。
- ingress mirror と egress mirror は line card ごとに発生する。
- ACL bind 先や session 識別は ASIC namespace 単位で持つが、collector resolution は chassis 全体で一意。

mirror / ACL の章本文は [07 ACL / CoPP / Mirror](../07-acl-copp-mirror/index.md) を参照し、VOQ 視点では「mirror traffic も fabric を流れる」「per-line-card session が増える」点を押さえます。

- 関連: [Everflow on VOQ Chassis](../../platform/everflow-support-on-voq-chassis.md)
- 章: [07 ACL / CoPP / Mirror](../07-acl-copp-mirror/index.md)

## Reliable TSA

`reliable-tsa` （Traffic Shift Away）は、特定 device を BGP コミュニティで隔離して traffic を退避させる仕組みです。VOQ chassis では:

- TSA は line card 単位ではなく chassis 単位で発動する。
- chassis 内の複数 BGP プロセスを一貫して isolate / unisolate する必要がある。
- 失敗 / 部分適用を避けるため、Chassis DB を通じた一斉切替を行う。

ルーティング保守の章で扱うべきテーマで、ここでは「chassis 全体での同期が必要な保守操作」として位置付けます。

- 関連: [Reliable TSA](../../routing/reliable-tsa.md)
- 章: [02 BGP / Routing](../02-bgp/index.md)

## Multi-ASIC Warm Reboot

`multi-asic-warm-reboot` は、Multi-ASIC SONiC の warm reboot 設計を扱います。VOQ chassis では line card 単位 / chassis 単位の両方が議論されます。

- 各 ASIC namespace の syncd / orchagent / bgpd は ASIC ごとに warm restart する。
- supervisor 側は Chassis DB を温存したまま再起動する。
- line card 単独 warm reboot 中、他 line card と fabric の状態を維持する。

reboot 系の章本文は [11 Reboot](../11-reboot/index.md) を参照し、VOQ 視点では「ASIC ごとの syncd warm restart」「chassis 状態の維持」「line card 隔離 reboot」を押さえます。

- 関連: [Multi-ASIC Warm Reboot](../../system/multi-asic-warm-reboot.md)
- 章: [11 Reboot](../11-reboot/index.md)

## まとめ

VOQ chassis 固有のテーマは、機能としては既存の章（BGP、LAG、Mirror、Reboot）に属しつつ、namespace 跨ぎ / line card 跨ぎ / Chassis DB との協調という観点を持ちます。各章本文で機能の中身を読み、本章の [概念](concept.md) と [アーキテクチャ](architecture.md) で「どこが namespace を超えるか」を意識すると、HLD を縦横に往復しやすくなります。
