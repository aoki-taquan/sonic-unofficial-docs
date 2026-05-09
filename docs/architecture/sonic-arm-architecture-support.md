---
title: SONiC の ARM (armhf / arm64) ビルドサポート（PLATFORM_ARCH と qemu-static）
area: architecture
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/sonic-multi-architecture/sonic_arm_support.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli: []
  yang: []
---

!!! success "裏取りステータス: Code-verified（slave 命名のみ進化）"
    現行 master で枠組みが維持されていることを確認。`sonic-buildimage/Makefile.work:121-177` で `CONFIGURED_ARCH` / `PLATFORM_ARCH` 変数（default `amd64`）と `SLAVE_BASE_IMAGE = $(SLAVE_DIR)-march-$(CONFIGURED_ARCH)` を確認。`onie-image.conf` / `onie-image-armhf.conf` / `onie-image-arm64.conf` がリポジトリルートに揃っており、`platform/aspeed/onie-image-arm64.conf` 等も追加されている。`installer/install.sh` も存在。slave docker は `sonic-slave-{trixie,bookworm,buster}/Dockerfile*.j2` の per-distribution テンプレートに進化し、`-march-<arch>` サフィックスを実行時に付ける形（HLD の `sonic-slave-armhf` / `sonic-slave-arm64` 固定ディレクトリは廃止）。動作の枠組み・変数名は HLD と一致（verified at: 2026-05-09）。

# SONiC の ARM (armhf / arm64) ビルドサポート（`PLATFORM_ARCH` と qemu-static）

## 概要

SONiC ビルドシステムを **ARM32 (armhf) / ARM64** に対応させるための設計[^1]。SONiC は元々 x86_64 中心で書かれており、Makefile / docker / onie installer / kernel ビルド / sonic-installer 等が AMD64 をハードコードしていた。本 HLD は変更対象を整理する。

変更対象モジュール[^1]:

- `sonic-slave` (ビルド環境 docker)
- `dockers/`（base / ptf 等の docker image）
- `rules/` / `Makefile` / build script
- `apt` repo list
- ONIE image / installer

## 動作仕様

### ビルド時オプション

ユーザーは `make configure` 時に `PLATFORM` と一緒に `PLATFORM_ARCH` (or `SONIC_ARCH`) を指定[^1]:

```bash
# armhf
make configure PLATFORM=marvell-armhf SONIC_ARCH=armhf

# arm64
make configure PLATFORM=marvell-arm64 SONIC_ARCH=arm64
```

未指定なら **`amd64`** が default[^1]。

### Makefile 変数

| 変数 | 用途 |
|------|------|
| `PLATFORM_ARCH` | ターゲットアーキテクチャ（`armhf` / `arm64` / `amd64`） |
| `CONFIGURED_ARCH` | Makefile 内で `amd64` 直書きの代わりに使う変数 |

例[^1]:

```makefile
# 旧
LINUX_IMAGE = linux-image-$(KVERSION)_..._amd64.deb
# 新
LINUX_IMAGE = linux-image-$(KVERSION)_..._$(CONFIGURED_ARCH).deb
```

`amd64` をハードコードしている全 `rules/*.mk` / `src/*/Makefile` を `$(CONFIGURED_ARCH)` に置換する[^1]。

### Docker base image

SONiC docker は **`debian` ベース** から **`multiarch/<distribution>-<arm_arch>`** ベースに切替[^1]:

```text
dockers/docker-base
dockers/docker-base-stretch
dockers/docker-ptf
```

これにより各種コンパイル / packaging が ARM アーキテクチャ向けに走る。

### `sonic-slave` クロスビルド

`sonic-slave` は他全 docker のビルド環境を提供する。**ホスト x86_64 上で ARM バイナリを動かすため `binfmt-misc` + `qemu-static` を使う**[^1]:

```text
sonic-slave-armhf
sonic-slave-arm64
```

セットアップ:

- `qemu-static` をホストに install
- docker `multiarch/qemu-user-static:register` を実行して binfmt 登録

```mermaid
graph LR
    HOST[Host x86_64]
    QEMU[binfmt-misc<br/>qemu-static]
    SLA[sonic-slave-armhf / arm64<br/>(ARM image)]
    BIN[ARM bin 実行]
    HOST --> QEMU --> SLA --> BIN
```

### ARM 固有 / X86 固有パッケージの分岐

`ixgbe` / `grub` のような X86 専用パッケージは **ARM ビルドから除外**[^1]。アーキテクチャ別の package 一覧を Makefile / rules で切替。

### Platform レイアウト

同じ board でも CPU vendor が違うことがあるため、**platform を arch 別** にする[^1]:

```text
platform/marvell-armhf/
  ├ docker-syncd-mrvl-rpc.mk
  ├ docker-syncd-mrvl-rpc/...
  ├ libsaithrift-dev.mk
  ├ linux-kernel-armhf.mk
  ├ one-image.mk
  ├ platform.conf
  ├ rules.mk
  └ sai.mk
```

### apt repo

Azure debian repo は ARM パッケージを提供しないため、**ARM 用に sources.list を差し替え**[^1]:

```text
files/apt/sources.list-armhf
files/build_templates/sonic_debian_extension.j2
```

### ONIE image / installer

ONIE image 設定 / インストーラスクリプトを arch 別に分ける[^1]:

| 設定ファイル | 用途 |
|-----------|------|
| `onie-image.conf` | x86_64 |
| `onie-image-armhf.conf` | ARMHF |
| `onie-image-arm64.conf` | ARM64 |
| `platform/<TARGET>/platform.conf` | 各プラットフォーム固有設定。primary storage / partition / bootloader |

ONIE installer script[^1]:

```text
installer/x86_64/install.sh
installer/arm64/install.sh
installer/armhf/install.sh
```

役割:

- bootloader update（boot image 詳細）
- primary disk のフォーマット / パーティション
- SONiC image を `/host` に展開

#### ストレージとブートローダ

ARM はストレージとブートローダのバリエーションが大きいため `platform.conf` で差を吸収[^1]:

| 区分 | x86_64 | ARM |
|------|--------|-----|
| Primary storage | SATA 系 | NAND / NOR / SD / MMC など |
| Bootloader | grub | uboot or 独自 |

`platform.conf` で:

- primary storage の選択 / partition / format / mount
- bootloader 設定（boot image 詳細を書く方法）

mount path を共通 SONiC installer に渡し、image 展開等の共通処理は再利用する設計。

### `sonic-installer`

`sonic-installer/main.py` は image upgrade / deletion / boot order 変更のため bootloader 設定を扱う。x86 では grub、**ARM では uboot 用ファームウェアユーティリティ** で boot 設定を読み書き[^1]。

### Kernel ARM サポート

`src/sonic-linux-kernel` の Makefile / patch を ARM 向けにも make できるよう更新[^1]。`.config` は debian build infrastructure 経由で生成されるため、`dpkg` 環境変数で対象アーキテクチャを正しく選択する必要。

#### Custom Kernel (Expert Mode)

ARM では SONiC default kernel と異なるバージョンが必要なケースがあり、**platform 固有 makefile で上書き** する[^1]:

```text
platform/marvell-armhf/linux-kernel-armhf.mk
```

## 設定

### CLI / CONFIG_DB / YANG

本 HLD は **runtime 設定を伴わない**。ビルド時オプション (`SONIC_ARCH`) と Makefile / docker 構成のみ。

### 設定例

```bash
# ARMHF (32-bit ARM) image
make configure PLATFORM=marvell-armhf SONIC_ARCH=armhf
make target/sonic-marvell-armhf.bin

# ARM64 image
make configure PLATFORM=marvell-arm64 SONIC_ARCH=arm64
make target/sonic-marvell-arm64.bin

# 既定（x86_64）
make configure PLATFORM=mellanox
make
```

ビルド前提:

```bash
# qemu-static を有効化（ホスト x86_64 上で ARM バイナリを実行）
docker run --rm --privileged multiarch/qemu-user-static:register
```

## 制限事項

- ARM では **debian repo を別途用意** する必要がある（azure debian repo 非対応）[^1]
- カスタムカーネルは platform 固有 makefile で上書きが必要[^1]
- ARM ビルドはホスト x86_64 上で **qemu emulation** が必須。ネイティブ ARM ホストでビルドする場合は別経路
- `amd64` ハードコード箇所が **多数の Makefile に散在**。新機能追加時にも `$(CONFIGURED_ARCH)` を使うことを忘れないよう注意
- HLD は ARM 対応初期のものであり、**現在の SONiC build 構成と差分** がある可能性大
- ONIE installer の partition / bootloader 部分は **platform vendor 依存度が高い**

## 干渉する機能

- **`sonic-buildimage` 全体**: rules / Makefile / docker 構成
- **`sonic-slave`**: クロスビルド環境
- **`sonic-linux-kernel`**: kernel build
- **`sonic-installer`**: bootloader アクセス（grub / uboot）
- **ONIE installer**: image インストール
- **platform vendor のリポジトリ** (`platform/marvell-armhf` 等): platform 固有 mk / conf

## トラブルシューティング

- ARM build が x86 binary を吐く → `SONIC_ARCH` 指定漏れ、`PLATFORM_ARCH` の参照箇所を確認
- docker build が失敗 → `multiarch/qemu-user-static:register` 実行済みか、`binfmt-misc` が有効か (`update-binfmts --display`)
- apt 取得失敗 → `files/apt/sources.list-armhf` の repo 設定が正しいか
- onie installer が動かない → `platform/<target>/platform.conf` の partition / bootloader 設定を確認
- sonic-installer が boot order を変更できない → ARM では uboot ファームウェアユーティリティが入っているかを確認

## 引用元

[^1]: `sonic-net/SONiC` `doc/sonic-multi-architecture/sonic_arm_support.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- PLATFORM_ARCH / CONFIGURED_ARCH 変数の現行 Makefile 命名と amd64 ハードコード残存の確認
- sonic-slave-armhf / sonic-slave-arm64 の現行 Dockerfile 構成と qemu-static 連携確認
- onie-image-armhf.conf / onie-image-arm64.conf / installer/<arch>/install.sh の現行存在確認
- sonic-installer.main の uboot 連携経路実装確認
- src/sonic-linux-kernel の ARM 向けパッチと .config 生成 (dpkg 環境変数) の現行確認
- platform/marvell-armhf 等のリファレンス platform 配下構成の現行確認
-->
