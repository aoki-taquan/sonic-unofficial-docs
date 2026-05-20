---
title: ACL & QoS
description: "ACL & QoS — ACL、CoPP、mirror、buffer、PFC、watermark、scheduler などパケット制御と QoS を扱う章。"
area: acl-qos
verification: meta
last_verified: 2026-05-13
---

# ACL & QoS
[ACL](../reference/glossary.md#term-acl)、[CoPP](../reference/glossary.md#term-copp)、mirror、buffer、[PFC](../reference/glossary.md#term-pfc)、watermark、scheduler などパケット制御と [QoS](../reference/glossary.md#term-qos) を扱う章。

## この章の趣旨

データプレーンのパケット選別・優先度制御・統計を扱う。具体的には:

- **ACL**: テーブル型、ingress / egress、ユーザ定義テーブル型、L3V4V6 統合、flex counter 化
- **CoPP**: Manager 再設計、neighbor miss trap、enum capability query
- **Mirror / Everflow**: SPAN / ERSPAN、egress mirror + action capability
- **Buffer / PFC**: dynamic headroom、reclaim reserved buffer、PFC 履歴統計、[WRED](../reference/glossary.md#term-wred) / ECN
- **QoS scheduler**: SP / WRR / [DWRR](../reference/glossary.md#term-dwrr)、min/max bandwidth、shaper
- **Watermark / Drop counter**: PG / queue 占有量、buffer drop、configurable drop counter

## この章の読み方
目的の機能名からページを選び、設定名や CLI 名が必要な場合はリファレンス章を併読する。`Discrepancy-found` は [HLD](../reference/glossary.md#term-hld) と現行実装に差分が見つかったページなので、設計値として読む前に本文の注記を確認する。

## 主要ページ

- [ACL in SONiC（テーブル型 / マッチ・アクション / SWSS パイプライン）](acl-in-sonic.md)
- [ACL の基本設計（ACL_TABLE / ACL_RULE スキーマ）](acl-support-in-sonic.md)
- [ACL ユーザ定義テーブルタイプ（ACL_TABLE_TYPE と AclTableType）](acl-user-defined-table-type-support.md)
- [ACL カウンタの flex counter 化（ACL_COUNTER + COUNTERS_ACL_COUNTER_RULE_MAP）](acl-flex-counters-support.md)
- [SONiC Port Mirroring（SPAN / ERSPAN）](sonic-port-mirroring-hld.md)
- [QoS Scheduler / Shaper（SP / WRR / DWRR + min/max bandwidth）](sonic-qos-scheduler-and-shaping.md)
- [Dynamic Headroom Calculation（buffer_model = dynamic）](dynamically-headroom-calculation.md)
- [PFC 履歴統計（PFCWD lua スクリプトによる estimate と --history CLI）](pfc-historical-statistics.md)
- [バッファ Watermark カウンタ（PG / queue 占有量の最大値追跡）](watermark-counters-in-sonic.md)
- [設定可能な Drop Counter（DEBUG_COUNTER と SAI debug counter）](configurable-drop-counters-in-sonic.md)
- [CoPP Manager 再設計テストプラン（feature テーブル整合性 + always_enabled）](copp-manager-redesign-test-plan.md)
- [Port Access Control（PAC: 802.1x / MAB / RADIUS）](port-access-control-in-sonic.md)

## 扱わない範囲

- 経路選択そのもの（[ECMP](../reference/glossary.md#term-ecmp) / nexthop policy）は [routing](../routing/index.md) 章
- L2 forwarding テーブル設計（[FDB](../reference/glossary.md#term-fdb) / [VLAN](../reference/glossary.md#term-vlan) 内 flooding）は [switching](../switching/index.md) 章
- 個別ベンダーの [SAI](../reference/glossary.md#term-sai) 拡張 ACL（コミュニティ `master` の SAI 標準範囲のみ扱う）
- ACL / QoS の **CLI コマンド一覧** / **[CONFIG_DB](../reference/glossary.md#term-config_db) テーブル定義** は [reference](../reference/index.md) 章
## 検証状況
- ページ数: 31
- 分布: Code-verified: 23 / Discrepancy-found: 2 / HLD-only: 6

## 実装差分があるページ
- [DHCP DoS 緩和（ポート単位 DHCP レート制限・Linux TC ベース）](dhcp-dos-mitigation-in-sonic.md)
- [ポートの動的 add / del（zero-port 起動と post-init 操作）](enhancements-to-add-or-del-ports-dynamically.md)

## HLD-only のページ
- [Asymmetric PFC テストプラン（PTF + sonic-mgmt fixtures）](asymmetric-pfc-test-plan.md)
- [Dynamic Headroom Calculation（buffer_model = dynamic）](dynamically-headroom-calculation.md)
- [Egress Outer DSCP 書換 ACL（UNDERLAY_SET_DSCP / METADATA + EGR_SET_DSCP）](egress-outer-dscp-change-table.md)
- [Everflow テストプラン（ingress + egress mirror、LAG / ECMP / IPv6）](everflow-test-plan.md)
- [Port Access Control（PAC: 802.1x / MAB / RADIUS）](port-access-control-in-sonic.md)
- [Reclaim Reserved Buffer（admin-down ポートの zero_profile）](reclaim-reserved-buffer.md)

## ページ一覧

| ページ | 検証 |
|---|---|
| [ACL Ingress / Egress テストプラン（DATAINGRESS / DATAEGRESS テーブル）](acl-ingress-egress-test-plan.md) | Code-verified |
| [ACL in SONiC（テーブル型 / マッチ・アクション / SWSS パイプライン）](acl-in-sonic.md) | Code-verified |
| [ACL の egress mirror 対応と SAI ベース action capability 問い合わせ](egress-mirroring-support-and-acl-action-capability-check.md) | Code-verified |
| [ACL の基本設計（ACL_TABLE / ACL_RULE スキーマ）](acl-support-in-sonic.md) | Code-verified |
| [ACL カウンタの flex counter 化（ACL_COUNTER + COUNTERS_ACL_COUNTER_RULE_MAP）](acl-flex-counters-support.md) | Code-verified |
| [ACL ユーザ定義テーブルタイプ（ACL_TABLE_TYPE と AclTableType）](acl-user-defined-table-type-support.md) | Code-verified |
| [Asymmetric PFC テストプラン（PTF + sonic-mgmt fixtures）](asymmetric-pfc-test-plan.md) | HLD-only |
| [CoPP Manager 再設計テストプラン（feature テーブル整合性 + always_enabled）](copp-manager-redesign-test-plan.md) | Code-verified |
| [CoPP Neighbor Miss trap と enum capability query（show copp configuration）](copp-neighbor-miss-trap-and-enhancements.md) | Code-verified |
| [DASH ACL タグ（DASH_PREFIX_TAG_TABLE と DASH_ACL_RULE_TABLE 拡張）](dash-acl-tags.md) | Code-verified |
| [DHCP DoS 緩和（ポート単位 DHCP レート制限・Linux TC ベース）](dhcp-dos-mitigation-in-sonic.md) | Discrepancy-found |
| [Dynamic Headroom Calculation（buffer_model = dynamic）](dynamically-headroom-calculation.md) | HLD-only |
| [Egress Outer DSCP 書換 ACL（UNDERLAY_SET_DSCP / METADATA + EGR_SET_DSCP）](egress-outer-dscp-change-table.md) | HLD-only |
| [Everflow テストプラン（ingress + egress mirror、LAG / ECMP / IPv6）](everflow-test-plan.md) | HLD-only |
| [L3V4V6 ACL テーブル型（v4 / v6 ルールを 1 SAI ACL テーブルに同居）](support-a-new-acl-table-type-that-combines-l3-acl-and-l3v6-acl-tables.md) | Code-verified |
| [PFC 履歴統計（PFCWD lua スクリプトによる estimate と --history CLI）](pfc-historical-statistics.md) | Code-verified |
| [Port Access Control（PAC: 802.1x / MAB / RADIUS）](port-access-control-in-sonic.md) | HLD-only |
| [QoS Scheduler / Shaper（SP / WRR / DWRR + min/max bandwidth）](sonic-qos-scheduler-and-shaping.md) | Code-verified |
| [Reclaim Reserved Buffer（admin-down ポートの zero_profile）](reclaim-reserved-buffer.md) | HLD-only |
| [SONiC Port Mirroring（SPAN / ERSPAN）](sonic-port-mirroring-hld.md) | Code-verified |
| [VoQ アーキテクチャの分散転送（FSI/SSI と Chassis DB / redis_chassis）](distributed-forwarding-in-a-virtual-output-queue-voq-architecture.md) | Code-verified |
| [WRED / ECN 統計（per-queue / per-port、capability ベース）](wred-and-ecn-statistics.md) | Code-verified |
| [counterpoll 種別と watermark / queue / pg-drop マップの整合テストプラン](test-plan-for-align-watermark-flow-with-port-configuration.md) | Code-verified |
| [flexcounter の queue/PG map 生成と watermark 有効化の整合](align-watermark-flow-with-port-configuration-hld.md) | Code-verified |
| [ingress discards テスト計画（21 ケースで drop counter を検証）](sonic-test-ingress-discards-hld.md) | Code-verified |
| [show acl 強化（STATE_DB.ACL_TABLE_TABLE / ACL_RULE_TABLE の status）](enhancements-on-show-acl-commands.md) | Code-verified |
| [バッファ Watermark カウンタ（PG / queue 占有量の最大値追跡）](watermark-counters-in-sonic.md) | Code-verified |
| [ポートの動的 add / del（zero-port 起動と post-init 操作）](enhancements-to-add-or-del-ports-dynamically.md) | Discrepancy-found |
| [ポートバッファドロップカウンタ（PORT_BUFFER_DROP FC group）](port-buffer-drop-counters-in-sonic.md) | Code-verified |
| [未使用ポートの予約バッファ回収（reclaim reserved buffer）シーケンス](reclaim-reserved-buffer-sequence-flow.md) | Code-verified |
| [設定可能な Drop Counter（DEBUG_COUNTER と SAI debug counter）](configurable-drop-counters-in-sonic.md) | Code-verified |

<!-- glossary-links-injected: 58337c3c8df8 -->
