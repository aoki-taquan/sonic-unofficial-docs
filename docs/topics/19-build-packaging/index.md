---
title: Build / Packaging / Application Extension
area: topics
verification: meta
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
---

# Build / Packaging / Application Extension

この章は、SONiC を「どう作って配るか」と「外部アプリケーションをどう持ち込むか」を、開発者と運用者が同じ地図で読むための入口である。既存ページは build 改善 HLD、Debian cadence、image versioning、application extension（SPM）、ARM、container hardening、feature quality の各 HLD に分散しているが、ビルド成果物が ASIC に届くまでの導線で読み直すと位置関係がはっきりする。

主な問いは次の 4 つ。

- SONiC の build system、build profile、RFS split build はそれぞれ何の遅さや煩雑さを減らすのか。
- Application Extension / sonic-package-manager (SPM) は外部 docker をどう配布し、`config feature` の管理面にどう載るのか。
- Base OS と docker image のバージョニングは、互換性とアップグレード手順とどう結びつくのか。
- ARM サポート、container hardening、feature quality は、ビルドとリリースのどの段階に効くのか。

## 読む順番

1. [概要](concept.md): build → image → package → extension の責務を分ける。
2. [アーキテクチャ](architecture.md): build artifact が ONIE installer になるまでの流れと RFS split を追う。
3. [設定 / 運用](operations.md): SPM・application extension・package manager の lifecycle を運用面から見る。
4. [発展トピック](advanced.md): ARM、container hardening、feature quality を、リリース品質の導線として読む。
5. [内部実装](internals.md): sonic-buildimage の Makefile / docker 階層、slave container、`rules/` / `dockers/` の責務分担、Application Extension マニフェストの解釈を実装側から見る。

## 統合した既存ページ

この章は architecture / system / management / categories の build・package 系ページ 13 件を横断している。各サブページ末尾の「関連ページ」から原文の HLD と裏取りステータスへ辿れる。

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

