---
title: SONiC 全体像と設定基盤
description: "SONiC 全体像と設定基盤 — この章は、SONiC を読むときに最初に混乱しやすい「設定はどこから入るのか」「Redis DB は何を分担するのか」「変更はどこまで安全に戻せるのか」を、HLD 単位ではなく読者の質問順に並べ直した入口です。"
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources:
  - docs/guides/beginner.md
  - docs/guides/operator.md
  - docs/guides/developer.md
  - docs/guides/evaluator.md
  - docs/management/sonic-user-manual.md
  - docs/management/sonic-nos-configuration-methods.md
keywords:
  - SONiC overview
  - 全体像
  - CONFIG_DB
  - Redis
  - YANG
  - 設定基盤
  - アーキテクチャ
  - config reload
  - warm reboot
---

# SONiC 全体像と設定基盤

この章は、SONiC を読むときに最初に混乱しやすい「設定はどこから入るのか」「[Redis](../../reference/glossary.md#term-redis) DB は何を分担するのか」「変更はどこまで安全に戻せるのか」を、[HLD](../../reference/glossary.md#term-hld) 単位ではなく読者の質問順に並べ直した入口です。

対象読者は、SONiC の全体像を先に掴みたい初学者、設定変更の影響範囲を確認したい運用者、[CONFIG_DB](../../reference/glossary.md#term-config_db) / [YANG](../../reference/glossary.md#term-yang) / daemon の責務境界を把握したい開発者です。個別コマンドやテーブルの完全な仕様は既存の reference / area ページへ譲り、この章では「どこを読めば判断できるか」を明確にします。

## この章で答える質問

- SONiC の設定は CLI、`config_db.json`、YANG、[GCU](../../reference/glossary.md#term-gcu)、[gNMI](../../reference/glossary.md#term-gnmi) のどれを入口に読むべきか。
- `CONFIG_DB`、`APPL_DB`、`STATE_DB`、`ASIC_DB` はどの章の前提知識になるか。
- `config reload`、`config replace`、`config apply-patch`、rollback、[ZTP](../../reference/glossary.md#term-ztp)、factory reset はどう使い分けるか。
- 既存の `guides/`、`categories/`、`reference/`、area 別 HLD ページは読み物章からどう辿るか。

## サブページ

- [概念と読み始め方](concept.md): 読者別の最短導線、CLI / ConfigDB / YANG / GCU の役割、既存 guides / categories の使い方。
- [設定データフロー](architecture.md): `CONFIG_DB` から daemon、`APPL_DB`、[orchagent](../../reference/glossary.md#term-orchagent)、[SAI](../../reference/glossary.md#term-sai) へ流れる全体像。
- [設定変更の選び方](configuration.md): `config save/load/reload/replace`、GCU、JSON Patch、`sonic-cfggen` の使い分け。
- [運用入口](operations.md): feature enable、system defaults、config reload、factory reset、基本的な切り戻し判断。
- [内部実装](internals.md): first boot / migration、複数 Redis、Multi-ASIC namespace、管理 API 側 Redis client の見方。

## 読み順

初めて読む場合は [概念と読み始め方](concept.md) から [設定データフロー](architecture.md) へ進むのが近道です。設定作業に入る読者は [設定変更の選び方](configuration.md) と [運用入口](operations.md) を先に読み、実装や大規模構成を追う読者は [内部実装](internals.md) を最後に確認してください。

## 関連ページ

- [初学者向けガイド](../../guides/beginner.md)
- [運用者向けガイド](../../guides/operator.md)
- [開発者向けガイド](../../guides/developer.md)
- [評価者向けガイド](../../guides/evaluator.md)
- [SONiC User Manual の位置づけ](../../management/sonic-user-manual.md)
- [SONiC NOS の設定手段一覧](../../management/sonic-nos-configuration-methods.md)

<!-- xref-related-chapters -->
## 関連する章

**派生で読むべき章**

- [SWSS / SAI / Redis 内部実装](../20-swss-sai-redis/index.md)
- [gNMI / gNOI / OpenConfig / YANG](../10-gnmi-openconfig/index.md)
- [リファレンス横断索引](../22-reference-index/index.md)

**補完的に読む章**

- [Reboot / Upgrade / Lifecycle](../11-reboot/index.md)
- [Lab / Virtual SONiC / Developer Entry](../21-lab-vs-developer/index.md)

<!-- glossary-links-injected: 99ff3d378f44 -->
