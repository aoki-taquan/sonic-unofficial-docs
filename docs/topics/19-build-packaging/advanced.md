---
title: 発展トピック
description: 発展トピック — リリース直前で気にする観点を 3 つ並べる。ARM 向け移植、container hardening、feature quality
  定義はそれぞれ別 HLD だが、リリース時にまとめて満たしておきたい条件 という共通点がある。
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
related:
  cli:
  - config feature
  config_db:
  - FEATURE
  yang:
  - sonic-feature
---

# 発展トピック

リリース直前で気にする観点を 3 つ並べる。ARM 向け移植、container hardening、feature quality 定義はそれぞれ別 [HLD](../../reference/glossary.md#term-hld) だが、**リリース時にまとめて満たしておきたい条件** という共通点がある。

## ARM (armhf / arm64) サポート

[SONiC](../../reference/glossary.md#term-sonic) の build system は元々 AMD64 中心だったため、ARM 系プラットフォームへ広げるには `sonic-slave`、`dockers/`、`rules/`、`Makefile`、`apt` repo、kernel ビルド、`onie-image-*.conf`、`installer/install.sh` などを横断的に修正する必要があった。

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

## マルチプラットフォーム build の並列化

`sonic-buildimage` は `PLATFORM=<vendor>` 単位で完全に独立した image を生成するため、ビルドを横方向に分割しやすい。実運用での並列化パターンは次の三段になる。

- **`make -j` レベル**: 単一 platform 内で `dpkg-buildpackage` / docker build を並列化する。`SONIC_BUILD_JOBS` と `SONIC_CONFIG_BUILD_JOBS` を物理コアに合わせて指定。
- **platform レベル**: CI runner / sub-job を `PLATFORM=broadcom` / `mellanox` / `marvell` などで分割する。共通 deb (`target/debs/`) は cache で再利用し、[syncd](../../reference/glossary.md#term-syncd) と SDK 依存パッケージだけ platform 個別に作る。
- **arch レベル**: `PLATFORM_ARCH=amd64` / `arm64` / `armhf` を別 matrix セルに展開する。`sonic-slave-<dist>-<arch>` docker を pre-pull しておくと `docker-base` のフェーズ時間が大きく短縮する。

CI 全体は「`target/debs/` cache (全 platform 共通) → platform 並列 build → image 集約」の三層パイプラインで構成するのが安定する。

## SDK 切替と vendor SDK の取り扱い

vendor SDK (Broadcom [SAI](../../reference/glossary.md#term-sai) / OpenNSL、NVIDIA SDK、Marvell Prestera 等) はバージョン依存が強く、`platform/<vendor>/<sai>.mk` で deb 名 / URL / SHA を pin している。SDK を上げるときは次を同時に確認する。

- `platform/<vendor>/*.mk` の `SAI` / `SDK` バージョン変数
- `dockers/docker-syncd-<vendor>/` の Dockerfile 依存
- `src/sonic-sairedis/` 側の SAI header バージョン整合（sai-api 不一致は build 時の `static_assert` で落ちる）
- `tests/` 側で sai-stub / sai-vs 互換が壊れていないか

複数 vendor を並走で持つチームは、SDK 切替 PR を vendor ごとに分割し、`make configure PLATFORM=<vendor>` の差分だけ review する運用にすると衝突を避けやすい。

## 再現可能ビルド (reproducible build)

同じ source tree からビルドして bit 一致の image を得る試み。SONiC 単体では未到達だが、debian 由来の `SOURCE_DATE_EPOCH` 伝播、deb 内の timestamp 正規化、docker layer の order 固定、`pip` wheel の hash pin など、段階的な改善が進む。`SONIC_VERSION_CACHE` を使った deb cache 再利用は build 時間短縮と再現性改善の両方に効く。完全 reproducible は kernel module の build-id と docker overlayfs の I/O 順序が残課題。

## CVE 対応のワークフロー

base が debian なので CVE 通知は `debian-security` announce と SBOM の突き合わせが起点になる。優先度判定の典型手順は次のとおり。

- 影響パッケージを SBOM (CycloneDX 出力) で grep し、SONiC image に含まれているかを確認。
- 含まれていれば `apt-get changelog` で fix 版を特定し、`Makefile.work` の `DEBIAN_VERSION` ピンを更新するか、`src/<pkg>/patch/` で個別 patch を当てる。
- syncd / kernel module 配下の CVE は vendor SAI / vendor kernel patch の追従が要るため、vendor SDK PR と組で進める。
- 修正後は実 image build と nightly test plan で regression を見るのが原則。

## 関連ページ

- [ARM architecture support](../../architecture/sonic-arm-architecture-support.md)
- [Container hardening](../../system/sonic-container-hardening.md)
- [Feature quality definition](../../system/sonic-feature-quality-definition.md)
- [Disk writers analysis](../../system/analysis-of-disk-writers-in-sonic-devices.md)


<!-- glossary-links-injected: 8ba32e5aa69d -->
