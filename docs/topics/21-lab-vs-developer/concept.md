---
title: 概念
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 概念

「lab」と一口に言っても、SONiC では大きく次の 3 つの面が混ざっています。読み手の役割と目的で使い分けを決めると迷いません。

## persona と lab の対応

SONiC のガイドは目的別に 4 つに分かれており、章本文への入口もそこで決まります。

| persona | 入口 | 主な関心 |
| --- | --- | --- |
| 評価者 (evaluator) | [評価者向けガイド](../../guides/evaluator.md) | NOS としての機能と限界を短時間で把握する |
| 初学者 (beginner) | [初学者向けガイド](../../guides/beginner.md) | docker / Redis / orchagent などの基本構造を学ぶ |
| 運用者 (operator) | [運用者向けガイド](../../guides/operator.md) | CLI、CONFIG_DB、reboot、telemetry を実機運用で扱う |
| 開発者 (developer) | [開発者向けガイド](../../guides/developer.md) | ビルド、テスト、HLD 起票、SAI / orchagent 改修 |

評価者と初学者は仮想環境で十分に進められます。運用者と開発者は、途中から物理 lab・PTF・CI を組み合わせる必要があります。

## virtual / physical の境界

仮想 SONiC は ASIC を SAI VS（virtual switch）で置き換えた構成です。SAI VS は Linux kernel の bridge / route table を ASIC の代わりに使うため、次のような層が「実機と挙動が違う」または「再現されない」ことに注意します。

- ASIC 固有の SAI capability、buffer / queue 容量、PFC / watermark のような ASIC counter
- optics（CMIS / SFP）、PHY、gearbox、retimer
- thermal、PSU、fan、LED、BMC、PCIe
- HW offload に依存する mux / EVPN VXLAN encap / DASH の一部
- 線速で出る drop / 微小遅延 / micro-burst

逆に、CONFIG_DB / sairedis / orchagent / FRR / lldp / snmp / gNMI といった control plane の動作は、SONiC-VS で十分に再現できます。仕様レベルの HLD 検証は virtual で、HW capability に踏み込む検証は physical で、と切り分けるのが基本です。

## test plan を「どの persona の読み物か」で読む

`docs/routing/`、`docs/acl-qos/`、`docs/system/`、`docs/platform/` には test plan 系のページが多くあります。これらは developer / CI 担当のためのページで、運用者が日常で開く章ではありません。

- VS で完結する test plan: [VRF VS test plan](../../routing/vrf-vs-test-plan.md)、[VRF Ansible test plan](../../routing/vrf-feature-ansible-test-plan-omit-in-toc.md)、[ACL Ingress/Egress test plan](../../acl-qos/acl-ingress-egress-test-plan.md)、[Everflow test plan](../../acl-qos/everflow-test-plan.md)
- 実 ASIC または PTF + ASIC が要る test plan: [Dataplane Telemetry test plan](../../system/dataplane-telemetry-test-plan.md)、[Thermal Control test plan](../../platform/thermal-control-test-plan.md)
- 共通フレームワーク: [DIP=SIP PTF validation HLD](../../architecture/dip-sip-ptf-validation-high-level-design.md)

test plan ページは「機能章の検証可能性を読み解く参考」と捉えてください。機能仕様は機能章本文を読み、その章で何が CI に乗っているかを見るときに test plan を開きます。
