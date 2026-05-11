---
title: 概念
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/platform/1-sonic-on-multi-asic-platforms.md
  - docs/platform/voq-sonic.md
  - docs/categories/multi-asic.md
  - docs/platform/fabric-port-support-on-sonic.md
  - docs/platform/recirculation-port-support-on-voq-chassis.md
  - docs/platform/single-asic-voq-fixed-system-sonic.md
---

# 概念

Multi-ASIC と VOQ chassis は別の話に見えて段階的につながっています。ここでは pizza-box 1 ASIC を基準に、どこから「Multi-ASIC」になり、どこから「VOQ chassis」になるのかを言葉のレベルで整理します。

## Pizza-box / Multi-ASIC / VOQ Chassis の三層

- **Pizza-box (1 ASIC)**: NOS は単一の Redis インスタンスと単一の network namespace で動きます。CLI と CONFIG_DB が 1 対 1 です。
- **Multi-ASIC (1 筐体・複数 ASIC)**: 1 つの NOS インスタンスの中で、ASIC ごとに独立した network namespace (`asic0`, `asic1`, ...) と独立した Redis インスタンスを持ちます。host namespace は外向きの CLI / management、ASIC namespace は実際の port / route を持ちます。
- **VOQ Chassis (複数 line card + supervisor)**: 各 line card が Multi-ASIC SONiC として動き、supervisor 上の **Chassis DB** と fabric ASIC が、複数 line card の system port を 1 つの論理スイッチとして束ねます。

つまり VOQ chassis は Multi-ASIC を内包しつつ、さらに「複数 line card を 1 つの switch に見せる」層を持ちます。Multi-ASIC platforms HLD が namespace の枠組みを定義し、VOQ SONiC HLD がその上に Chassis DB / system port / distributed VOQ を載せる構造です。

## Namespace と Redis インスタンス

Multi-ASIC では、ASIC ごとに `/var/run/redis<N>/redis.sock` のような分離された Redis を持ち、`CONFIG_DB`, `APPL_DB`, `STATE_DB`, `ASIC_DB`, `COUNTERS_DB` がそれぞれの namespace 内に存在します。host namespace は別に `CONFIG_DB` を持ち、管理系（hostname、management interface、BGP の grouping 情報など）を扱います。

orchagent / syncd / bgpd といった主要プロセスは namespace ごとに 1 セット起動します。CLI ツールは `--namespace` 引数を取り、引数なしの場合は内部で全 namespace に対して問い合わせて集約表示します。

## System Port と Front-panel Port

VOQ chassis で重要なのが **system port** という概念です。

- **front-panel port**: line card の物理ポート。従来の `Ethernet0`, `Ethernet4`, ... と同じ感覚で、各 line card が持ちます。
- **system port**: chassis 全体で一意な論理ポート ID。`<line-card>|<asic>|<port>` のような形で命名され、Chassis DB が全 system port を保持します。

データプレーン上は、ある line card に入ったパケットが宛先 system port に向けて fabric を経由して送られます。FIB は宛先 system port を解決し、egress line card の出口で実際の front-panel port にマップされます。

## Fabric Port と Recirculation Port

- **fabric port**: line card と fabric card を結ぶ内部 port です。fabric ASIC は L2 / L3 forwarding をせず、cell ベースで line card 間をつなぐスイッチング機構を提供します。
- **recirculation port**: 1 つの ASIC の中で「もう一度パイプラインを通したい」ときに使う内部ループ用 port です。VOQ 系では特に MPLS / GRE / IP-in-IP のような multi-pass 処理で利用されます。

front-panel port は運用者が触る port、fabric port は normally hidden、recirculation port は ASIC capability に応じて自動確保されるリソース、と覚えると見分けがつきやすいです。

## Distributed VOQ アーキテクチャ

VOQ chassis では、ingress line card が egress system port ごとに **virtual output queue** を持ち、credit ベースで egress に送れるかを判断します。HOL blocking を避けつつ、line card 間で QoS を保つための仕組みです。

詳細は [アーキテクチャ](architecture.md) で扱いますが、運用上の意味として「VOQ chassis では queue は egress port 単位ではなく ingress 側で egress system port ごとに持つ」ことを押さえると、counter や輻輳調査の入口が変わることに気付けます。

## Single-ASIC Fixed VOQ System

1 ASIC の pizza-box でも、内部で VOQ アーキテクチャを採用するシステムが定義されています。これは「pizza-box でありながら、将来的に VOQ chassis の line card として組み込むことを想定する」中間形態で、Chassis DB を持たず、system port は自分自身に閉じます。

単独運用する場合は通常の Multi-ASIC として見え、`CONFIG_DB` の `DEVICE_METADATA.localhost.switch_type = voq` のような印で識別します。設定の流儀は [設定](setup.md) で扱います。

## 関連ページ

- [SONiC on Multi-ASIC Platforms](../../platform/1-sonic-on-multi-asic-platforms.md)
- [VOQ SONiC](../../platform/voq-sonic.md)
- [Fabric Port Support](../../platform/fabric-port-support-on-sonic.md)
- [Recirculation Port on VOQ Chassis](../../platform/recirculation-port-support-on-voq-chassis.md)
- [Single-ASIC VOQ Fixed System](../../platform/single-asic-voq-fixed-system-sonic.md)
