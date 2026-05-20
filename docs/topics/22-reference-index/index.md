---
title: リファレンス横断索引
description: リファレンス横断索引 — この章は、docs/reference/ 配下に集めた CLI / CONFIG_DB / YANG の辞書ページと、Phase B で新設された機能章 (docs/topics/) との間を行き来するための索引である。
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
keywords:
- Reference
- 横断索引
- リファレンス
- CLI
- CONFIG_DB
- YANG
- HLD
- ナビゲーション
related:
  cli:
  - config bgp
  - config interface
  - config vlan
  - show ip
  - config platform firmware
  - config qos
  - config vnet
  config_db:
  - CRM
  - PORT
  - VLAN
  - VLAN_INTERFACE
  - VLAN_MEMBER
  - VRF
  - ACL_TABLE
  yang:
  - sonic-bgp-neighbor
  - sonic-vrf
  - sonic-bgp-global
  - sonic-crm
  - sonic-bgp-aggregate-address
  - sonic-bgp-bbr
  - sonic-bgp-device-global
---

# リファレンス横断索引

この章は、`docs/reference/` 配下に集めた CLI / [CONFIG_DB](../../reference/glossary.md#term-config_db) / [YANG](../../reference/glossary.md#term-yang) の辞書ページと、Phase B で新設された機能章 (`docs/topics/`) との間を行き来するための索引である。機能章は読み物として運用導線を提供し、reference は辞書として「テーブル名」「コマンド名」「モジュール名」から逆引きできる。両者は別物だが、本来は両方向にリンクされていることが望ましい。

`docs/reference/` 配下の現状は以下の通り (2026-05-11 時点)。最新の機械集計は [reference/index.md のカバー率表](../../reference/index.md#coverage) を参照する (本ページの数字は読み物中の参考値)。

- CLI ページ: 72 件 (`config-*` / `show-*` / `debug-*` / `clear` / `reboot-fast-warm` / `sonic-*` ツール)
- CONFIG_DB ページ: 121 件 (table family ごと)
- YANG ページ: 84 件 (`sonic-*` モジュールごと)
- Runbooks: 45 件 (症状逆引き)
- Verification: 1 件 (`discrepancy-index`)

この章では、これらを「機能章のどこから引かれるか」「逆に辞書からどの章へ戻るか」の対応表で並べ直す。既存 reference ページの本文と frontmatter は変更しない。

## reference/index.md との分担

- **早見リンク集 (機能 → CLI / CONFIG_DB / YANG / Runbook の主要ページ)** は [reference/index.md](../../reference/index.md#quickref) が canonical。
- **章番号別の詳細表 (Phase B topics 章のどこから何が引かれるか)** は本章の [cli-index](cli-index.md) / [config-db-index](config-db-index.md) / [yang-index](yang-index.md) が canonical。
- 統計 (カバー率 / verification 内訳) は reference/index.md が canonical。本章は数値を引用するのみ。

## 想定読み手の質問

- CLI / CONFIG_DB / YANG の辞書ページは機能章からどう探すか。
- 既存の `docs/reference/` は章本文に吸収するのか、独立した辞書として残すのか。
- カテゴリページ (`docs/categories/`) と topics 章はどう役割分担するか。
- discrepancy / reference gap はどこに置き、誰が消化していくのか。

## 読み進め方

1. [概要](concept.md): reference を辞書として残す設計と、章 / 辞書 / カテゴリの 3 層の関係。
2. [CLI 横断索引](cli-index.md): `config-*` / `show-*` / `debug-*` / ツール系を機能章ごとに並べた表。
3. [CONFIG_DB 横断索引](config-db-index.md): table family を機能章ごとに並べ、逆引きを提供する。
4. [YANG 横断索引](yang-index.md): native [SONiC](../../reference/glossary.md#term-sonic) YANG と OpenConfig / management framework との関係。
5. [品質と gap](quality-gaps.md): discrepancy ページと reference gap の追跡方法。
6. [内部実装](internals.md): reference ページの生成パイプライン (Indexer / gen_coverage / gen_cross_ref) と、frontmatter / verification status の運用を実装側から見る。

## 関連ページ

- [リファレンス](../../reference/index.md)
- [CLI リファレンス](../../reference/cli/index.md)
- [CONFIG_DB リファレンス](../../reference/config-db/index.md)
- [YANG リファレンス](../../reference/yang/index.md)
- [Discrepancy index](../../reference/verification/discrepancy-index.md)

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 状態 | verification |
|---|---|---|
| concept | ✅ 完成 (107 行) | meta |
| setup | ✅ 完成 (125 行) | meta |
| operations | ✅ 完成 (113 行) | meta |
| internals | ✅ 完成 (133 行) | meta |
| advanced | ✅ 完成 (101 行) | meta |

<!-- /chapter-progress -->

<!-- next-reads -->
## 次に読むべき記事

**この章を読み進める順**

- [概要: リファレンス設計の考え方](concept.md)
- [設定](setup.md)
- [運用](operations.md)
- [内部実装](internals.md)
- [発展トピック](advanced.md)

**関連する HLD 7 件**

- [libsairedis API idempotence（warm restart 用 OID キャッシュと duplicate 抑止）](../../system/sonic-libsairedis-api-idempotence-support.md)
- [Error Handling Framework 制限事項と HLD との乖離（コア機構未実装 / CRM 代替）](../../architecture/error-handling-framework-in-sonic-limitations.md)
- [SONiC NOS の設定手段一覧（CLI / sonic-cfggen / config_db.json / RESTCONF / gNMI / ZTP / vtysh / redis / apply-patch）](../../management/sonic-nos-configuration-methods.md)
- [Send to Ingress（CPU から ingress pipeline へパケット注入する hostif）](../../management/send-to-ingress-hld.md)
- [FRR 用 sysctl チューニングのデフォルト](../../system/useful-sysctl-settings.md)
- [Warmboot Manager（shutdown orchestration / reconciliation 統一）](../../system/warmboot-manager-hld.md)
- [SONiC Disk I/O 削減（writer 分析と tmpfs 化）](../../system/analysis-of-disk-writers-in-sonic-devices.md)

**関連トラブルシュート 5 件**

- [APPL_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)
- [経路は RIB にあるが FIB / ASIC に降りない](../../reference/runbooks/route-not-installed-in-fib.md)
- [orchagent が CPU 100% で詰まる](../../reference/runbooks/swss-orchagent-busy-loop.md)
- [Warm Reboot が失敗 / 通信断が長引く](../../reference/runbooks/warm-reboot-failure.md)
- [Multi-ASIC で namespace 間通信できない](../../reference/runbooks/multi-asic-namespace.md)

<!-- /next-reads -->

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)

**補完的に読む章**

- [SWSS / SAI / Redis 内部実装](../20-swss-sai-redis/index.md)
- [gNMI / gNOI / OpenConfig / YANG](../10-gnmi-openconfig/index.md)
- [Lab / Virtual SONiC / Developer Entry](../21-lab-vs-developer/index.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
