---
title: 運用
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 運用

ここでは lab を「日常的にどう回すか」を、persona 別と test plan 別に整理します。実機運用の章本文ではなく、lab 環境の運用に閉じた話だけを書きます。

## persona ごとの典型ループ

### 評価者

- 仮想 lab を 1 つ立て、[評価者向けガイド](../../guides/evaluator.md) を起点に章をめくる。
- 必要なら GNS3 で 2〜3 台つなぎ、BGP / VLAN / L3 / VRF の章を試す。
- ASIC 依存の挙動（buffer、PFC、watermark、optics）は VS では再現しないため、評価対象から外すか、対応 HW での検証に切り替える。

### 初学者

- SONiC-VS 1 台で `docker ps`、Redis、orchagent、syncd を見る。
- [初学者向けガイド](../../guides/beginner.md) から章本文の概念ページに進む。
- CONFIG_DB と CLI を写経しながら、章本文の設定ページを開く。

### 運用者

- 実機を触る前に SONiC-VS で CLI / CONFIG_DB の手応えを確認する。
- [運用者向けガイド](../../guides/operator.md) と [Reboot / Upgrade / Lifecycle 章](../11-reboot/index.md) で reboot 系の流れを掴む。
- console / terminal server の構成は本章 [設定](setup.md) の物理 lab セクションを使う。

### 開発者

- [開発者向けガイド](../../guides/developer.md) で build / test / HLD 起票の流れを押さえる。
- VS で再現可能な範囲は VS で完結させ、CI（test plan ページ）に乗せる。
- ASIC 依存の改修は HW lab を別途確保し、SAI / syncd / platform 章と組で読む。

## test plan の読み方

test plan ページは「何を検証するか」「どの topology / PTF を使うか」「想定 result」が書かれています。実機 troubleshooting や運用手順書ではないので、章本文と混ぜないようにします。

| 章 | 関連 test plan |
| --- | --- |
| [VRF / ECMP / RIB-FIB](../04-vrf-ecmp/index.md) | [VRF VS test plan](../../routing/vrf-vs-test-plan.md)、[VRF Ansible test plan](../../routing/vrf-feature-ansible-test-plan-omit-in-toc.md) |
| [ACL / CoPP / Mirror / Packet Action](../07-acl-copp-mirror/index.md) | [ACL Ingress/Egress test plan](../../acl-qos/acl-ingress-egress-test-plan.md)、[Everflow test plan](../../acl-qos/everflow-test-plan.md) |
| Telemetry 系 | [Dataplane Telemetry test plan](../../system/dataplane-telemetry-test-plan.md) |
| Platform 系 | [Thermal Control test plan](../../platform/thermal-control-test-plan.md) |

実機が要らない test plan（VS test、Ansible test）はローカルで再現できます。実機 or PTF + ASIC が要る test plan は、CI 側で何が回っているかの参照として読むのが現実的です。

## lab のスナップショットとやり直し

仮想 lab は壊して作り直すのが安いので、運用上の壊れ・状態の不整合は再起動より image 再生成のほうが早い場合が多いです。実機運用の手順を「lab で何度も繰り返す」のが lab の役目で、状態を温存する設計は基本的に不要です。
