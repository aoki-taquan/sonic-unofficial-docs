---
title: DASH と SmartSwitch の考え方
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/overlay/sonic-dash-hld.md
  - docs/overlay/smartswitch-eni-based-forwarding.md
  - docs/architecture/smart-switch-database-design.md
  - docs/categories/dash.md
  - docs/categories/smartswitch.md
---

# DASH と SmartSwitch の考え方

DASH と SmartSwitch は混同されやすい言葉ですが、別レイヤのものです。DASH は **「ENI 単位で VNet / ACL / metering / Service Tunnel を高速にこなす」データプレーン API と SONiC 実装** を指し、SmartSwitch は **「NPU スイッチに複数の DPU をぶら下げ、DASH を含む処理を DPU で動かす」物理 / 制御プラットフォーム** を指します。

つまり「DASH を動かす器」が SmartSwitch であり、SmartSwitch 上で動く主役のオーバーレイ処理が DASH です。

## DASH は何を解くか

DASH は ENI（Elastic Network Interface）という単位を中心に置きます。1 つの ENI は 1 つの VM ないしテナント接続点で、その配下に VNet（VxLAN VNI と underlay）、Outbound / Inbound ルーティング、ACL、metering、Service Tunnel、Private Link 等の設定が紐付きます。コントローラはこれらを `DASH_VNET` / `DASH_ENI` / `DASH_ROUTE` / `DASH_ACL_GROUP` 等のテーブルとしてプッシュし、`DashOrch` / `DashVnetOrch` / `DashAclOrch` といった orchagent が SAI へ落とします。

DASH 自体はホスト型 SmartNIC でも appliance card でも動く設計ですが、SONiC コミュニティの SmartSwitch では「DPU を SONiC で動かし、その上で DASH を回す」形を取ります。

## SmartSwitch の役割分担

SmartSwitch は次の 2 つから成ります。

- **NPU**: 従来の SONiC スイッチ。物理 port、underlay forwarding、ACL、BGP、HA の制御 daemon、DPU 管理を担う。
- **DPU**: DASH オーバーレイ処理用の SoC。SONiC OS が乗り、`DashOrch` 系の orchagent と SAI 実装が走る。NPU と midplane で繋がる。

NPU は DPU に対して次を提供します。

- DPU の電源 / リセット / PCIe 制御（PMON）
- 管理 IP の払い出し（midplane bridge 上の DHCP server）
- overlay 設定の中継先 redis（後述）
- HA actor（HAMgrD）
- gNMI / gNOI 経由の外部 API 接続点

DPU は NPU を gateway のように扱い、自身の overlay 状態を NPU 側に置いた redis に書き出します。

## NPU 側 DB と DPU overlay DB

DPU はメモリが厳しいため、DASH の全オブジェクト（多数の ENI、VNET、ACL、route 等）を DPU 自身の redis に保持するのは現実的ではありません。そこで **DPU 用の overlay redis を NPU 上に立てて、DPU から remote 接続させる** 構成を取ります。NPU 上には DPU 数だけ独立した `database` container（`redisdpu0` / `redisdpu1` …）が動き、それぞれ別 redis インスタンスとして DPU 1 つに対応します。

この設計の利点は次の通りです。

- DPU 側の RAM 圧迫を避ける
- コントローラは NPU 側に書くだけで DPU を意識せず済む（API 表面が単純化）
- multi-ASIC と同じ daemon (`featured`) で機構を再利用できる

## ENI ベース転送と VIP

NPU から DPU へのトラフィック振り分け方式は 2 つあります。

| 方式 | 振り分けの単位 | VIP 消費 | 拡張性 |
|---|---|---|---|
| VIP ベース | DPU ごとに別 VIP | DPU 数だけ消費 | 小規模向け |
| ENI ベース転送 | スイッチ単位 VIP + ENI 単位 ACL リダイレクト | 1 cluster 1 VIP | SmartSwitch を跨いだ ENI 配置が可能 |

SmartSwitch では ENI ベース転送が採用され、NPU 上で `ENI_REDIRECT` 型 ACL が ENI 宛パケットをローカル DPU またはリモート DPU の tunnel nexthop へ落とします。これを生成するのが `DashEniFwdOrch` です。

## HA の考え方

SmartSwitch HA は「DPU レベルで active / standby のペアを作り、フェイルオーバーは NPU 側の HAMgrD が駆動する」モデルです。HAMgrD は NPU 側の actor で、DPU の状態、peer DPU との同期、SAI HA セッションを管理します。DPU 自体は自分の HA 状態を knows しますが、誰と誰がペアか・どちらが active かは NPU 側で決めます。

## 用語の整理

| 用語 | 意味 |
|---|---|
| DASH | ENI 単位で VNet / ACL / metering を扱うオーバーレイデータプレーン API |
| ENI | Elastic Network Interface。テナント / VM 接続点の論理単位 |
| DPU | DASH 処理をこなす SoC。SONiC OS が動く |
| NPU | 従来の SONiC スイッチ部分。DPU を抱える親 |
| SmartSwitch | NPU + 複数 DPU から成る物理プラットフォーム |
| midplane bridge | NPU と DPU を繋ぐ内部 L2 / 管理ネットワーク（`169.254.200.254` 系） |
| HAMgrD | NPU 側 HA actor daemon |
| `has_per_dpu_scope` | FEATURE テーブルの leaf。DPU 数分の instance を起動するかを示す |

## 関連ページ

- [SONiC-DASH アーキテクチャ概観](../../overlay/sonic-dash-hld.md)
- [Smart Switch のデータベース構成](../../architecture/smart-switch-database-design.md)
- [SmartSwitch ENI Based Forwarding](../../overlay/smartswitch-eni-based-forwarding.md)
- [DASH 関連カテゴリ](../../categories/dash.md)
- [SmartSwitch 関連カテゴリ](../../categories/smartswitch.md)
