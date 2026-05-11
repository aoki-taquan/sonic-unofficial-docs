---
title: gNMI / gNOI / OpenConfig / YANG
description: "gNMI / gNOI / OpenConfig / YANG — この章は、SONiC の「モデル駆動管理」を、リクエストが入る入口から ConfigDB に到達するまでの順で読み直すための入口である。"
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources: []
keywords:
  - gNMI
  - gNOI
  - OpenConfig
  - YANG
  - telemetry
  - northbound API
  - gnmi-server
  - Subscribe
  - Set/Get
---

# gNMI / gNOI / OpenConfig / YANG

この章は、SONiC の「モデル駆動管理」を、リクエストが入る入口から ConfigDB に到達するまでの順で読み直すための入口である。既存ページは HLD 単位で書かれており、Translib、Transformer、gNMI server、gNOI service が別の文書に分かれている。運用者・開発者が最初に知りたい境界は、どのプロトコル/モデルが何を直接いじっているか、という一点に集約される。

主な問いは次の 4 つ。

- REST / gNMI / Translib / Transformer はどの層で CONFIG_DB に到達するのか。
- OpenConfig YANG と SONiC native YANG はいつ使い分けるのか。
- gNOI System / OS / File / Healthz は SONiC のどの service を呼んでいるのか。
- gNSI、master arbitration、save-on-set、dial-out subscription は運用上どこで効くのか。

## 読む順番

1. [概要](concept.md): Management Framework の全体像、gNMI / REST / CLI の位置付け、OpenConfig と SONiC YANG の使い分けを整理する。
2. [アーキテクチャ](architecture.md): gNMI server から Translib、Transformer、YANG validation、CONFIG_DB までの request flow を mermaid で追う。
3. [設定](setup.md): gNMI Get / Set / Subscribe、OpenConfig interface / VLAN / PortChannel / BGP の典型例。
4. [運用](operations.md): master arbitration、save-on-set、dial-out telemetry、subscription の競合制御と永続化。
5. [gNOI / gNSI](gnoi-gnsi.md): System、OS、File、Factory Reset、Healthz、gNSI の API と SONiC service の対応表。
6. [YANG リファレンス](yang-reference.md): 機能章別の YANG モジュール参照表。
7. [内部実装](internals.md): gNMI server / Translib / Transformer / sonic-mgmt-common の責務分担と、YANG → ABNF/CONFIG_DB 変換を実装側から見る。
8. [発展トピック](advanced.md): dial-out telemetry、master arbitration、gNSI、save-on-set、他章との境界。

## 統合した既存ページ

この章は management の HLD 派生ページ 14 件、system の telemetry 関連 2 件、switching の OpenConfig 関連 2 件、routing の subscription 関連 2 件、categories の入口 1 件、reference の YANG 参照を横断している。細部のスキーマ・操作・実装裏取りは各サブページ末尾の「関連ページ」から参照する。

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [Telemetry / SNMP / Observability](../09-telemetry-snmp/index.md)

**派生で読むべき章**

- [P4 / PINS / Programmable Pipeline](../18-p4-pins/index.md)

**補完的に読む章**

- [Security / AAA / FIPS / Hardening](../15-security-aaa/index.md)
- [リファレンス横断索引](../22-reference-index/index.md)

