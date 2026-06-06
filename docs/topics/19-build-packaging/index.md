---
title: Build / Packaging / Application Extension
description: Build / Packaging / Application Extension — この章は、SONiC を「どう作って配るか」と「外部アプリケーションをどう持ち込むか」を、開発者と運用者が同じ地図で読むための入口である。
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources: []
keywords:
- Build
- Packaging
- Application Extension
- sonic-buildimage
- Debian
- Docker
- image build
- azp
- ビルド
related:
  cli:
  - show feature
  - show techsupport
  - config feature
  - config acl
  - show acl
  - show platform
  - show version
  config_db:
  - FEATURE
  - CRM
  - WARM_RESTART
  - ACL_RULE
  - ACL_TABLE
  - CHASSIS_MODULE
  - DEVICE_METADATA
  yang:
  - sonic-crm
  - sonic-feature
  - sonic-device-metadata
  - sonic-system-defaults
  - sonic-versions
---

# Build / Packaging / Application Extension

この章は、[SONiC](../../reference/glossary.md#term-sonic) を「どう作って配るか」と「外部アプリケーションをどう持ち込むか」を、開発者と運用者が同じ地図で読むための入口である。既存ページは build 改善 [HLD](../../reference/glossary.md#term-hld)、Debian cadence、image versioning、application extension（SPM）、ARM、container hardening、feature quality の各 HLD に分散しているが、ビルド成果物が [ASIC](../../reference/glossary.md#term-asic) に届くまでの導線で読み直すと位置関係がはっきりする。

主な問いは次の 4 つ。

- SONiC の build system、build profile、RFS split build はそれぞれ何の遅さや煩雑さを減らすのか。
- Application Extension / sonic-package-manager (SPM) は外部 docker をどう配布し、`config feature` の管理面にどう載るのか。
- Base OS と docker image のバージョニングは、互換性とアップグレード手順とどう結びつくのか。
- ARM サポート、container hardening、feature quality は、ビルドとリリースのどの段階に効くのか。

## 読む順番

1. [概要](concept.md): build → image → package → extension の責務を分ける。
2. [アーキテクチャ](architecture.md): build artifact が ONIE installer になるまでの流れと RFS split を追う。
3. [設定](setup.md): build 環境と submodule・ベース構成のセットアップを押さえる。
4. [設定 / 運用](operations.md): SPM・application extension・package manager の lifecycle を運用面から見る。
5. [発展トピック](advanced.md): ARM、container hardening、feature quality を、リリース品質の導線として読む。
6. [内部実装](internals.md): [sonic-buildimage](../../reference/glossary.md#term-sonic-buildimage) の Makefile / docker 階層、slave container、`rules/` / `dockers/` の責務分担、Application Extension マニフェストの解釈を実装側から見る。

## 統合した既存ページ

この章は architecture / system / management / categories の build・package 系ページ 13 件を横断している。各サブページ末尾の「関連ページ」から原文の HLD と裏取りステータスへ辿れる。

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 行数 | 状態 | verification | 主目的 |
|---|---|---|---|---|
| concept | 140 | ✅ 完成 | meta | 概念・位置付け |
| architecture | 54 | ⚠️ プレースホルダ | meta | アーキテクチャ・データフロー |
| setup | 142 | ✅ 完成 | meta | セットアップ手順 |
| operations | 180 | ✅ 完成 | meta | 運用・デバッグ |
| internals | 238 | ✅ 完成 | code-verified | 内部実装 |
| advanced | 74 | ⚠️ プレースホルダ | meta | 発展トピック |

<!-- /chapter-progress -->

<!-- next-reads -->
## 次に読むべき記事

**この章を読み進める順**

- [概要](concept.md)
- [アーキテクチャ](architecture.md)
- [設定](setup.md)
- [運用: 設定 / 運用](operations.md)
- [内部実装](internals.md)
- [発展トピック](advanced.md)

**関連する HLD 7 件**

- [Alpine 仮想 SONiC（ALViS / KNE デプロイ）](../../architecture/alpine-high-level-design.md)
- [libsairedis API idempotence（warm restart 用 OID キャッシュと duplicate 抑止）](../../system/sonic-libsairedis-api-idempotence-support.md)
- [Port Profile Init（SAI bulk port API による fast-boot 高速化）](../../architecture/port-profile-init-hld.md)
- [SONiC-VS のビルドと libvirt 起動手順](../../architecture/steps-to-bring-up-sonic-vs.md)
- [SWSS docker の Warm Restart 実装メモ（開発時リファレンス）](../../system/swss-docker-warm-restart-code-reference.md)
- [SmartSwitch HA - DPU-Scope-DPU-Driven 構成](../../architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md)
- [SmartSwitch HA HAMgrD 内部実装（actor workflow / DPU-Driven 詳細）](../../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design-internals.md)

**関連トラブルシュート 5 件**

- [SAI failure / syncd リスタート多発](../../reference/runbooks/sai-failure.md)
- [Warm Reboot が失敗 / 通信断が長引く](../../reference/runbooks/warm-reboot-failure.md)
- [Multi-ASIC で namespace 間通信できない](../../reference/runbooks/multi-asic-namespace.md)
- [PINS gRPC (P4Runtime) が応答しない](../../reference/runbooks/pins-grpc-unresponsive.md)
- [APPL_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)

<!-- /next-reads -->

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [Lab / Virtual SONiC / Developer Entry](../21-lab-vs-developer/index.md)

**派生で読むべき章**

- [Reboot / Upgrade / Lifecycle](../11-reboot/index.md)
- [Security / AAA / FIPS / Hardening](../15-security-aaa/index.md)

**補完的に読む章**

- [P4 / PINS / Programmable Pipeline](../18-p4-pins/index.md)
- [SWSS / SAI / Redis 内部実装](../20-swss-sai-redis/index.md)

<!-- glossary-links-injected: ec18b66e3507 -->
