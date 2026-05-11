---
title: 発展トピック
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 発展トピック

評価・初学を超えて、CI / 大規模 lab / DPU 検証まで踏み込むときに開く話題を集めます。基本的にはここのリンク先 HLD を直接読むのが早く、本ページは「どれを開くか」のしおりです。

## DASH SONiC KVM

DASH（Disaggregated API for SONiC Hosts）の DPU 検証を実機 SmartSwitch なしで行うための環境です。データプレーンは BMv2、control plane は SONiC 側、というハイブリッド構成で、ENI / ACL / metering といった DASH HLD の核を仮想で踏むことができます。詳細は [DASH SONiC KVM](../../overlay/dash-sonic-kvm.md) を参照します。

DASH 章本文の機能仕様と組で読むのが前提で、DPU の HW 機能（offload 性能、PPS など）はこの環境では測れません。

## ALViS / KNE と CI 連携

ALViS / KNE は、多数ノードを軽量にデプロイしたい場合の選択肢です。CI で `n` 台の SONiC を立てる、KNE で他 NOS と混在 topology を組む、Pod 単位で個別 reload するなどの運用が想定されています。設計と制約は [Alpine 仮想 SONiC](../../architecture/alpine-high-level-design.md) を読みます。

実装は本家 SONiC-VS と一致しない部分があるため、機能完全性が必要なテストは SONiC-VS で、ノード数が必要なテストは ALViS で、と棲み分けます。

## 仮想で再現しづらい依存

章本文を読むときに「これは VS では確かめられない」と分けるべき要素を、まとめておきます。

| 領域 | VS で困る理由 | 実機 / 別環境が要る |
| --- | --- | --- |
| optics / PHY / CMIS | 物理 transceiver がない | 実機 + 対象 optics |
| buffer / PFC / watermark / queue | SAI VS の capability 範囲外 | ASIC 実機、または ASIC simulator |
| thermal / PSU / fan / BMC / PCIe | platform docker が dummy | 実機 platform |
| HW offload を伴う mux / EVPN encap / DASH 高速 path | data plane が Linux / BMv2 | 対応 ASIC / DPU |
| 微小遅延・micro-burst・線速 drop | Linux datapath 性能 | 専用テスト機材 |
| reboot 高速化検証（fast / warm / express） | platform 依存と timing 依存 | 実機 + telemetry。[Reboot / Upgrade / Lifecycle 章](../11-reboot/index.md) も参照 |

これらは仮想 lab の欠点ではなく、対象範囲が違うだけです。HLD を読むときに「VS の試験で十分」「実機が要る」を区別すると、章本文の限界も自然に見えてきます。

## CI で test plan をどう束ねるか

機能ごとの test plan は HLD と並行して存在しますが、CI 側で実際に回る集合は test plan の一部に絞られます。読み手が「この章は CI でどこまで担保されているか」を知りたいときに参照する順序は次のとおりです。

1. 機能章本文（仕様）
2. 該当 test plan（検証境界）
3. test plan で要求される topology / PTF（[DIP=SIP PTF validation HLD](../../architecture/dip-sip-ptf-validation-high-level-design.md) など共通設計）

CI 構成自体（GitHub Actions、Azure Pipelines）は本リポジトリの非公式ドキュメントの対象外です。upstream SONiC repo の `.github` と `azure-pipelines.yml` が一次資料になります。
