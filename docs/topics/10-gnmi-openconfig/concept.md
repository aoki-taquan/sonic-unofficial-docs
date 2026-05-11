---
title: 概要
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 概要

SONiC のモデル駆動管理は、CLI、gNMI、REST という 3 つの入口が、Translib / Transformer という共通の中間層を通って ConfigDB へ到達するように作られている。どの入口を使うかで操作対象が変わるわけではなく、同じ YANG モデルで定義された操作が、別の transport で表現されているにすぎない。この理解がないと「gNMI Set で OpenConfig をいじったら CLI が反映していない」ように見えてしまう。

## 入口の責務を分ける

| 層 | 主な責務 | 代表コンポーネント |
| --- | --- | --- |
| Transport | gRPC / REST 受付、認証 | telemetry container, gnmi server, REST server |
| Model 変換 | OpenConfig / SONiC YANG → 内部表現 | Translib, Transformer |
| Validation | YANG 制約のチェック、依存解決 | sonic-yang-models, ConfigDB validator |
| 永続化 | CONFIG_DB への書き込み、save-on-set | mgmt-framework, configdb writer |
| 反映 | daemon / orchagent / SAI への伝搬 | swss, orchagent, syncd |

詳細は [Management Framework 全体像](../../management/sonic-management-framework.md) を参照する。gNMI server 単体の責務は [gNMI server interface design](../../management/sonic-gnmi-server-interface-design.md) にまとまっている。入口別の使い分けの俯瞰は [gnmi-openconfig カテゴリ](../../categories/gnmi-openconfig.md) を起点にする。

## OpenConfig と SONiC native YANG の使い分け

SONiC は両方の YANG モデルを並行サポートする。

- **OpenConfig**: ベンダー非依存、業界標準。ethernet interface、VLAN、PortChannel、BGP など主要機能のサブセットがマップされる。NMS から差分を取り、複数ベンダー混在環境で運用するときの選択肢。
- **SONiC native YANG**: CONFIG_DB のスキーマに 1:1 で対応する。SONiC 固有機能や、OpenConfig がまだ表現しない operational 詳細を扱うときに使う。YANG モデルの命名規約と書き方は [SONiC YANG model guidelines](../../management/sonic-yang-model-guidelines.md) を参照する。

同じ機能を OpenConfig と SONiC YANG の両方から触れる場合、Transformer がフィールド単位で変換するため、片方からの設定がもう片方の get でも見えるのが原則である。ただし、OpenConfig 側がそのフィールドを表現しない場合は SONiC YANG だけで操作する。OpenConfig マップの実装範囲は機能ごとに異なるため、interface は [OpenConfig support for ethernet interfaces](../../management/openconfig-support-for-ethernet-interfaces.md)、PortChannel は [OpenConfig PortChannel](../../switching/openconfig-support-for-portchannel-aggregate-interface.md)、VLAN は [OpenConfig VLAN](../../switching/add-support-for-vlan-interface-using-openconfig-yang.md)、BGP は [SONiC FRR BGP Unified Mgmt Framework](../../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md) を参照する。

## CLI と gNMI の整合

SONiC の CLI は YANG モデルから自動生成される仕組みを持つ。同じ操作を CLI と gNMI で別実装にしないための設計で、CLI 追加時の重複を減らす目的もある。自動生成の流れは [SONiC CLI auto-generation tool](../../management/sonic-cli-auto-generation-tool.md) にまとまっている。CLI から入った設定が gNMI Get で同じ表現で戻ってくることを期待するなら、その機能が YANG モデル経由で扱われているかを最初に確認する。

## この章での読み方

- リクエストの内部フローを追いたいときは [アーキテクチャ](architecture.md) へ。
- 実際に Get / Set / Subscribe を書くときは [設定](setup.md) へ。
- 競合制御 (master arbitration)、永続化 (save-on-set)、dial-out subscription は [運用](operations.md) へ。
- gNOI、gNSI で reboot / file / OS install / healthz / 証明書配布を扱うときは [gNOI / gNSI](gnoi-gnsi.md) へ。
- YANG モジュールを機能章から逆引きするときは [YANG リファレンス](yang-reference.md) へ。

## 関連ページ

- [Management Framework 全体像](../../management/sonic-management-framework.md)
- [gNMI server interface design](../../management/sonic-gnmi-server-interface-design.md)
- [gnmi-openconfig カテゴリ](../../categories/gnmi-openconfig.md)
- [SONiC YANG model guidelines](../../management/sonic-yang-model-guidelines.md)
- [SONiC CLI auto-generation tool](../../management/sonic-cli-auto-generation-tool.md)
