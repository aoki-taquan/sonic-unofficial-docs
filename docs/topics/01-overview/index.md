---
title: SONiC 全体像と設定基盤
description: SONiC 全体像と設定基盤 — この章は、SONiC を読むときに最初に混乱しやすい「設定はどこから入るのか」「Redis DB は何を分担するのか」「変更はどこまで安全に戻せるのか」を、HLD 単位ではなく読者の質問順に並べ直した入口です。
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources: []
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
related:
  cli:
  - config bgp
  - show bgp
  - config acl
  - show acl
  - config qos
  - config vlan
  - config vnet
  config_db:
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  - BGP_GLOBALS_AF_NETWORK
  - ACL_TABLE
  - DEVICE_METADATA
  - FEATURE
  - VLAN
  yang:
  - sonic-bgp-global
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-aggregate-address
  - sonic-bgp-bbr
  - sonic-bgp-sentinel
---

# SONiC 全体像と設定基盤

この章は、[SONiC](../../reference/glossary.md#term-sonic) を読むときに最初に混乱しやすい「設定はどこから入るのか」「[Redis](../../reference/glossary.md#term-redis) DB は何を分担するのか」「変更はどこまで安全に戻せるのか」を、[HLD](../../reference/glossary.md#term-hld) 単位ではなく読者の質問順に並べ直した入口です。

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
- [内部実装](internals.md): first boot / migration、複数 Redis、[Multi-ASIC](../../reference/glossary.md#term-multi-asic) namespace、管理 API 側 Redis client の見方。

## 読み順

初めて読む場合は [概念と読み始め方](concept.md) から [設定データフロー](architecture.md) へ進むのが近道です。設定作業に入る読者は [設定変更の選び方](configuration.md) と [運用入口](operations.md) を先に読み、実装や大規模構成を追う読者は [内部実装](internals.md) を最後に確認してください。

## 関連ページ

- [初学者向けガイド](../../guides/beginner.md)
- [運用者向けガイド](../../guides/operator.md)
- [開発者向けガイド](../../guides/developer.md)
- [評価者向けガイド](../../guides/evaluator.md)
- [SONiC User Manual の位置づけ](../../management/sonic-user-manual.md)
- [SONiC NOS の設定手段一覧](../../management/sonic-nos-configuration-methods.md)

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 行数 | 状態 | verification | 主目的 |
|---|---|---|---|---|
| concept | 153 | ✅ 完成 | meta | 概念・位置付け |
| setup | 121 | ✅ 完成 | meta | セットアップ手順 |
| architecture | 74 | ⚠️ プレースホルダ | meta | アーキテクチャ・データフロー |
| configuration | 61 | ⚠️ プレースホルダ | meta | 設定手段の選び方 |
| operations | 181 | ✅ 完成 | meta | 運用・デバッグ |
| internals | 137 | ✅ 完成 | meta | 内部実装 |
| advanced | 104 | ✅ 完成 | meta | 発展トピック |

<!-- /chapter-progress -->

<!-- next-reads -->
## 次に読むべき記事

**この章を読み進める順**

- [概要: 概念と読み始め方](concept.md)
- [アーキテクチャ: 設定データフロー](architecture.md)
- [設定](setup.md)
- [設定: 設定変更の選び方](configuration.md)
- [運用: 運用入口](operations.md)
- [内部実装](internals.md)
- [発展トピック](advanced.md)

**関連する HLD 7 件**

- [SONiC NOS の設定手段一覧（CLI / sonic-cfggen / config_db.json / RESTCONF / gNMI / ZTP / vtysh / redis / apply-patch）](../../management/sonic-nos-configuration-methods.md)
- [Warmboot Manager（shutdown orchestration / reconciliation 統一）](../../system/warmboot-manager-hld.md)
- [Warm Reboot 開発フェーズと OID 復元戦略（idempotent libsairedis vs syncd view comparison）](../../system/what-are-the-development-phases-and-scope-for-warm-reboot.md)
- [System-wide Warmboot（going down / up path / SAI 期待値）](../../system/system-wide-warmboot.md)
- [FRR 用 sysctl チューニングのデフォルト](../../system/useful-sysctl-settings.md)
- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../../architecture/error-handling-framework-in-sonic.md)
- [libsairedis API idempotence（warm restart 用 OID キャッシュと duplicate 抑止）](../../system/sonic-libsairedis-api-idempotence-support.md)

**関連トラブルシュート 5 件**

- [Warm Reboot が失敗 / 通信断が長引く](../../reference/runbooks/warm-reboot-failure.md)
- [APPL_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)
- [orchagent が CPU 100% で詰まる](../../reference/runbooks/swss-orchagent-busy-loop.md)
- [経路は RIB にあるが FIB / ASIC に降りない](../../reference/runbooks/route-not-installed-in-fib.md)
- [BGP セッションが UP しない](../../reference/runbooks/bgp-session-down.md)

<!-- /next-reads -->

<!-- xref-related-chapters -->
## 関連する章

**派生で読むべき章**

- [SWSS / SAI / Redis 内部実装](../20-swss-sai-redis/index.md)
- [gNMI / gNOI / OpenConfig / YANG](../10-gnmi-openconfig/index.md)
- [リファレンス横断索引](../22-reference-index/index.md)

**補完的に読む章**

- [Reboot / Upgrade / Lifecycle](../11-reboot/index.md)
- [Lab / Virtual SONiC / Developer Entry](../21-lab-vs-developer/index.md)

<!-- glossary-links-injected: 3abb11a5818e -->
