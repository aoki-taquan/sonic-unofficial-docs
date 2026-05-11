---
title: 概要
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 概要

SONiC の build / packaging は、開発者向けの「ソースから ONIE installer を作る話」と、運用者向けの「機能 docker を後から足す話」が一本の鎖でつながっている。混同を避けるために、層を先に分けると読みやすい。

## まず層を分ける

| 層 | 主な責務 | 代表ドキュメント |
| --- | --- | --- |
| Build system | Dockerfile レイヤ削減・並列ビルド・sairedis 分離 | [Build system improvements](../../architecture/build-system-improvements.md) |
| Build profile | フラグセットを `rules/profiles/<name>.mk` で束ねる提案 | [Build profiles](../../architecture/build-profiles.md) |
| RFS split build | `build_debian.sh` を 2 段化して並列化する | [RFS Split build](../../architecture/rfs-split-build-improvements-hld.md) |
| Base OS lifecycle | Debian release を取り込む cadence と廃止計画 | [Debian upgrade cadence](../../system/sonic-debian-upgrade-cadence.md) |
| Versioning | OS と docker image の semver と互換境界 | [OS / docker semver](../../system/sonic-os-sonic-docker-images-versioning.md) |
| Packaging / SPM | sonic-package-manager と manifest | [Application Extension Infrastructure](../../architecture/sonic-application-extension-infrastructure.md) |
| Extension 開発 | 既存 docker の Extension 化と新規開発 | [Application Extension 開発ガイド](../../management/sonic-application-extension-guide.md) |
| Multi-arch | ARM (armhf / arm64) ビルドサポート | [ARM architecture support](../../architecture/sonic-arm-architecture-support.md) |
| Container security | capability / privileged 削減 | [Container hardening](../../system/sonic-container-hardening.md) |
| Release quality | feature の品質グレード定義 | [Feature quality definition](../../system/sonic-feature-quality-definition.md) |

build 系 HLD は「ビルドを速くする」「ビルドを再現可能にする」「ビルドを ARM へ広げる」を、packaging 系 HLD は「ビルド済み docker をどう配布・install するか」を担っている。両者の接点が **image versioning** と **manifest** である。

## なぜ Application Extension が必要か

Inbox の機能 docker（bgp、teamd、snmp 等）はすべて `sonic-buildimage` ツリーで一緒にビルドされ、ONIE installer に焼き込まれる。一方、3rd party や任意の docker を **後から** 入れて、`config feature` と同じ管理面で扱いたいケースが増えた。SPM はこれを満たすために、`sonic-package-manager install` で `FEATURE` テーブルへの登録、`docker_image_ctl` 経由の起動、warm reboot / showtech / syslog のフックを揃える設計になっている。詳細は [Application Extension Infrastructure](../../architecture/sonic-application-extension-infrastructure.md) を参照する。

## なぜ build profile / RFS split / Debian cadence が並ぶのか

build profile は「フラグ一式の再現性」、RFS split は「直列ルールの並列化」、Debian cadence は「base 入れ替えのリズム」と、それぞれ別の遅さを解消する。注意点として、build profile HLD は現行 master に取り込まれていない提案であり、RFS split は HLD の単一フラグでなく `RFS_SPLIT_FIRST_STAGE` / `RFS_SPLIT_LAST_STAGE` の 2 段フラグで実装されている。HLD と実装の差は各ページ冒頭の裏取りバナーに明記してある。

## この章での読み方

ビルド時間や CI を改善したい場合は [アーキテクチャ](architecture.md) から入る。SPM で docker を配布したい場合や `config feature` との接続を確認したい場合は [運用](operations.md) を読む。ARM 向け移植や container 硬化、リリース品質判断は [発展トピック](advanced.md) にまとめている。

## 関連ページ

- [Build system improvements](../../architecture/build-system-improvements.md)
- [Build profiles](../../architecture/build-profiles.md)
- [RFS Split build](../../architecture/rfs-split-build-improvements-hld.md)
- [Application Extension Infrastructure](../../architecture/sonic-application-extension-infrastructure.md)
