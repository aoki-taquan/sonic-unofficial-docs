---
title: 発展トピック
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 発展トピック

リリース直前で気にする観点を 3 つ並べる。ARM 向け移植、container hardening、feature quality 定義はそれぞれ別 HLD だが、**リリース時にまとめて満たしておきたい条件** という共通点がある。

## ARM (armhf / arm64) サポート

SONiC の build system は元々 AMD64 中心だったため、ARM 系プラットフォームへ広げるには `sonic-slave`、`dockers/`、`rules/`、`Makefile`、`apt` repo、kernel ビルド、`onie-image-*.conf`、`installer/install.sh` などを横断的に修正する必要があった。

実装では `Makefile.work` の `CONFIGURED_ARCH` / `PLATFORM_ARCH`（default `amd64`）と、`sonic-slave-<dist>` を `-march-<arch>` サフィックス付きで切り替える仕組みに収束している。HLD で示された `sonic-slave-armhf` / `sonic-slave-arm64` という固定ディレクトリ命名は廃止されている。詳細と裏取りは [ARM architecture support](../../architecture/sonic-arm-architecture-support.md) を読む。

ARM 向けの注意点は次のとおり。

- qemu-user-static を使う cross-build パス（一部 platform）と native ARM ビルドパスの二系統がある。
- `onie-image-armhf.conf` / `onie-image-arm64.conf` がリポジトリルートに揃っていて、`platform/<vendor>/onie-image-arm64.conf` で上書きできる。

## Container hardening

SONiC の docker は歴史的に `--privileged` が多かった。CVE 対応とコンプライアンスの要請から、必要な linux capability・mount・device だけを与える方向で硬化が進んでいる。

- 個別 docker の `cap-add` / `cap-drop` テンプレ化は進行中で、現行値は `sonic-buildimage/dockers/<name>/` 配下の Dockerfile / start script に分散している。
- Extension manifest 側には `privileged` フラグや capability 制御の宣言枠が用意されている（`files/build_templates/default_manifest`、`manifest.json.j2`）。

実装の現状と未整備領域は [Container hardening](../../system/sonic-container-hardening.md) を読む。Extension を書く側は、まず `privileged: false` で動くかを確認し、必要な capability だけ宣言する方針が想定されている。

## Feature quality definition

リリース時に「この機能はどこまで信頼できるか」を判定するための品質グレード定義がある。CI カバレッジ、HLD の有無、コード裏取り、test plan の整備状況などを軸にする方針で、SPM 経由で配布する extension にも同じ枠組みを適用したい設計である。グレードの考え方は [Feature quality definition](../../system/sonic-feature-quality-definition.md) を読む。

## 章の出口

- ビルドを速くする / 再現可能にする → [アーキテクチャ](architecture.md) と [Build system improvements](../../architecture/build-system-improvements.md)。
- 後付け配布したい → [運用](operations.md) と [Application Extension Infrastructure](../../architecture/sonic-application-extension-infrastructure.md)。
- ARM へ移植する → [ARM architecture support](../../architecture/sonic-arm-architecture-support.md)。
- リリース判定 → [Feature quality definition](../../system/sonic-feature-quality-definition.md)。

## 関連ページ

- [ARM architecture support](../../architecture/sonic-arm-architecture-support.md)
- [Container hardening](../../system/sonic-container-hardening.md)
- [Feature quality definition](../../system/sonic-feature-quality-definition.md)
- [Disk writers analysis](../../system/analysis-of-disk-writers-in-sonic-devices.md)
