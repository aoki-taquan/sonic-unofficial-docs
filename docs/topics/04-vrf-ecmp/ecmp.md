---
title: ECMP Family
description: ECMP Family — ECMP は「複数 next hop に分散する」だけなら単純ですが、SONiC には用途に応じて複数の拡張があります。まず通常
  ECMP を基準にし、重み、bucket 安定性、順序、hash 入力、traffic class による path 選択を別々の問題として分けます。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/routing/sonic-fine-grained-ecmp.md
- docs/routing/sonic-weighted-ecmp.md
- docs/routing/high-level-design-document.md
- docs/architecture/sonic-generic-hash.md
- docs/routing/class-based-forwarding-enhancement.md
related:
  cli:
  - show techsupport
  - show platform
  - show version
  - show acl
  - config acl
  config_db:
  - FG_NHG
  - FG_NHG_PREFIX
  - FG_NHG_MEMBER
  - SWITCH_HASH
  - CRM
  - DSCP_TO_TC_MAP
  - ACL_RULE
  - ACL_TABLE
  - CHASSIS_MODULE
  yang:
  - sonic-fine-grained-ecmp
  - sonic-crm
  - sonic-dscp-tc-map
---

# ECMP Family

[ECMP](../../reference/glossary.md#term-ecmp) は「複数 next hop に分散する」だけなら単純ですが、SONiC には用途に応じて複数の拡張があります。まず通常 ECMP を基準にし、重み、bucket 安定性、順序、hash 入力、traffic class による path 選択を別々の問題として分けます。

## 方式比較

| 方式 | 解きたい問題 | 主な入力 | 向いている場面 |
|------|--------------|----------|----------------|
| ECMP | 同じ cost の複数 next hop へ分散する。 | route の nexthop set | 一般的な L3 冗長 / 分散。 |
| WCMP | next hop ごとに重みを付ける。 | weight 付き nexthop | link 容量や意図した比率が異なる経路。 |
| Fine Grained ECMP | member 変化時の flow 移動を抑える。 | `FG_NHG` bucket / member / prefix | appliance 経由、flow stickiness が重要な構成。 |
| Ordered ECMP | ECMP member の順序を揃える。 | ordered NHG / sequence id | 複数装置で同じ flow を同じ上流へ寄せたい構成。 |
| Generic Hash | hash field / algorithm を制御する。 | `SWITCH_HASH` | ECMP / [LAG](../../reference/glossary.md#term-lag) の分散キーを設計したい場合。 |
| CBF | forwarding class ごとに path を変える。 | [DSCP](../../reference/glossary.md#term-dscp)/EXP to FC、class-based NHG | traffic engineering。 |

## 通常 ECMP を基準にする

通常 ECMP は route の next-hop set から [SAI](../../reference/glossary.md#term-sai) next hop group を作り、ASIC の hash によって flow を member に割り振ります。運用上は、route の nexthop set、neighbor 解決、hash field、member の up/down を確認します。

この基準を理解してから、重み付けや bucket 固定のような拡張を読むと混乱しにくくなります。

## WCMP は比率の問題

Weighted ECMP は、next hop の選択比率を重みで変える機能です。同じ経路数でも、全 member を等確率にしたくない場合に使います。単に member を増減するのではなく、ASIC の next hop group member に weight を反映できるかが前提になります。

詳細は [Weighted ECMP](../../routing/sonic-weighted-ecmp.md) を参照してください。

## Fine Grained ECMP は flow 移動の問題

Fine Grained ECMP は、固定数 bucket を使って flow の割り当てを安定させます。member 障害や復旧時に全 flow を再分散するのではなく、影響する bucket だけを動かすことで、stateful appliance や load-balanced VM のような構成で flow stickiness を維持しやすくします。

設定面では `FG_NHG`、`FG_NHG_PREFIX`、`FG_NHG_MEMBER` を読みます。動作面では `fgnhgorch` が bucket と member を SAI FG ECMP group に反映します。詳細は [Fine Grained ECMP](../../routing/sonic-fine-grained-ecmp.md) と [FG_NHG テーブル](../../reference/config-db/fg-nhg.md) を参照してください。

## Ordered ECMP は装置間の一貫性の問題

Ordered ECMP は、複数の ToR や tier で ECMP member の順序を揃え、同じ hash 結果が同じ論理 path を選びやすくするための方式です。通常の ECMP では member set が同じでも内部順序の差で flow が別 path に行くことがあります。

plan 上の `docs/routing/high-level-design-document.md` はこの Ordered ECMP 系の既存ページとして扱います。ページ名が一般的なので、章内では [Ordered ECMP HLD](../../routing/high-level-design-document.md) として参照します。

## Generic Hash は分散キーの問題

ECMP の偏りを見たとき、next hop group だけでなく hash field も確認します。[Generic Hash](../../architecture/sonic-generic-hash.md) は ECMP / LAG の hash field と algorithm を `SWITCH_HASH` で制御する機能です。inner / outer IP、L4 port、IPv6 flow label など、どのフィールドを hash 入力にするかは overlay や traffic pattern に強く影響します。

## CBF は path を traffic class で選ぶ問題

Class Based Forwarding は、DSCP / [MPLS](../../reference/glossary.md#term-mpls) EXP から Forwarding Class を決め、その FC に応じて異なる child NHG を選ぶ traffic engineering です。ECMP の hash で均等に分散する話ではなく、「この class はこの path set」を選ぶ機能です。

詳細は [クラスベース転送](../../routing/class-based-forwarding-enhancement.md) を参照してください。

## 関連ページ

- [Fine Grained ECMP](../../routing/sonic-fine-grained-ecmp.md)
- [Weighted ECMP](../../routing/sonic-weighted-ecmp.md)
- [Ordered ECMP HLD](../../routing/high-level-design-document.md)
- [Generic Hash](../../architecture/sonic-generic-hash.md)
- [クラスベース転送](../../routing/class-based-forwarding-enhancement.md)

<!-- glossary-links-injected: e1fd4940b990 -->
