---
title: 設定
description: 設定 — Build / Packaging 章での「設定」は、機能 docker の有効化と extension のインストール、build 時の
  platform / arch 選択を整理する。実行時の機能 on/off は FEATURE テーブル、後付け配布は SPM、再ビルドは Makefile.work
  が中心。
area: topics
verification: meta
last_verified: 2026-05-12
sources: []
related:
  cli:
  - config feature
  - show feature
  - sonic-package-manager
  - sonic-installer
  config_db:
  - FEATURE
  - VERSIONS
  - DEVICE_METADATA
  yang:
  - sonic-feature
  - sonic-device-metadata
---

# 設定

Build / Packaging 章での「設定」は、機能 docker の有効化と extension のインストール、build 時の platform / arch 選択を整理する。**実行時の機能 on/off は `FEATURE` テーブル**、**後付け配布は SPM**、**再ビルドは `Makefile.work`** が中心になる。

## 設定入口の地図

| 目的 | 入口 | 補足 |
| --- | --- | --- |
| 既存 docker (機能) を on/off する | `config feature state` / [FEATURE](../../reference/config-db/feature.md) | image 再ビルド不要 |
| 機能 docker を後付けで追加する | SPM (`sonic-package-manager install`) | manifest + docker image |
| image そのものを差し替える | `sonic-installer install <bin>` | `next` / `current` の 2 image slot |
| 別 platform / arch を build する | `make configure PLATFORM=<vendor>` + `make target/sonic-<vendor>.bin` | [sonic-buildimage](../../reference/glossary.md#term-sonic-buildimage) を clone してから |
| build 速度や CI cache を変える | `Makefile.work` 変数 (`SONIC_BUILD_JOBS` ほか) | 環境変数で override 可 |

混在しても問題ない (`FEATURE` と SPM は別レイヤ) が、変更履歴を追えるよう「機能 on/off は config CLI」「extension 追加は SPM」「image 全替えは sonic-installer」と入口を固定するのが運用上は無難。

## FEATURE テーブルで docker を on/off する

[SONiC](../../reference/glossary.md#term-sonic) では、機能の多くが独立 docker として動く。実行時の有効化は CLI から行う。

```bash
# 現状確認
show feature config
show feature status

# 機能 ON / OFF (永続)
sudo config feature state bgp enabled
sudo config feature state telemetry disabled

# 起動タイミングを auto / disabled / enabled で切り替える
sudo config feature autorestart bgp enabled
```

[CONFIG_DB](../../reference/glossary.md#term-config_db) 側の構造は次の通り。

```text
FEATURE|<docker-name>
  state: enabled | disabled | always_enabled | always_disabled
  auto_restart: enabled | disabled
  has_global_scope: True | False
  has_per_asic_scope: True | False
```

`always_enabled` は image build 時に固定された機能 (swss / [syncd](../../reference/glossary.md#term-syncd) など) を示し、CLI から変更しても無視される。`has_per_asic_scope` が True の機能は multi-[ASIC](../../reference/glossary.md#term-asic) 構成で ASIC 数ぶん docker が起動する。詳細は [FEATURE table](../../reference/config-db/feature.md)。

## extension を SPM で入れる (運用パス)

build をやり直さずに新機能 docker を追加する標準パスは SONiC Package Manager (SPM)。`sonic-package-manager` (`spm`) コマンドが入口になる。

```bash
# repository を登録
sudo sonic-package-manager repository add my-pkg docker.example.com/my-pkg

# 最新版を install (manifest と image を同時に pull)
sudo sonic-package-manager install my-pkg

# 特定バージョン
sudo sonic-package-manager install my-pkg=1.2.3

# 一覧と削除
sonic-package-manager list
sudo sonic-package-manager uninstall my-pkg
```

install が成功すると、`FEATURE` テーブルに対象 docker が追加され、`config feature state` で on にすると docker が起動する。manifest は `/usr/share/sonic/templates/` 配下に展開され、container の起動引数、CLI 拡張、CONFIG_DB schema 拡張を宣言する。manifest schema の詳細は [Application Extension Infrastructure](../../architecture/sonic-application-extension-infrastructure.md)。

## image を差し替える (sonic-installer)

`.bin` を `sonic-installer` で書き、次回 boot で切り替える。

```bash
# 現在の image / 次回 boot image を確認
sonic-installer list

# 新 image を install (次回 boot から有効)
sudo sonic-installer install /path/to/sonic-<platform>.bin

# rollback を念のため
sudo sonic-installer set-next-boot <old-image>

# 古い image を削除
sudo sonic-installer remove <image-name>
```

image 切替は再 boot を伴うため、データプレーン断を許容できないなら fast/warm reboot との組合せが必要。reboot 種別の選び分けは [Reboot 章](../11-reboot/index.md)。

## ソースから build する最小手順

開発者が ONIE installer を作るときの最小手順は次の通り。

```bash
git clone https://github.com/sonic-net/sonic-buildimage.git
cd sonic-buildimage
git submodule update --init --recursive

# 例: Broadcom platform
make init
make configure PLATFORM=broadcom

# build (full)
make target/sonic-broadcom.bin

# debug / 並列度を上げる
SONIC_BUILD_JOBS=8 make target/sonic-broadcom.bin
```

`make configure PLATFORM=` の時点で `Makefile.work` の `CONFIGURED_PLATFORM` / `CONFIGURED_ARCH` が固定され、これ以降は同 platform 専用 tree になる。別 platform に切り替えたいときは別ディレクトリで clone するのが事故が少ない。

主要な build 変数は次の通り (詳細は `Makefile.work`)。

| 変数 | 意味 |
| --- | --- |
| `PLATFORM=` | broadcom / mellanox / marvell / vs など |
| `PLATFORM_ARCH=` | amd64 / arm64 / armhf |
| `SONIC_BUILD_JOBS=` | docker build / dpkg-buildpackage の並列度 |
| `SONIC_CONFIG_BUILD_JOBS=` | 一部 deb build 内の並列度 |
| `SONIC_DPKG_CACHE_METHOD=cache` | deb cache 再利用 (CI で必須) |
| `INCLUDE_NAT=y` 等の機能フラグ | `rules/config` で `INCLUDE_*` 系を上書き |

## つまずきパターン

- **`config feature state` で enable しても docker が上がらない**: `always_disabled` が build 時に固定されているか、`has_global_scope`/`per_asic_scope` の組合せで対象 namespace が違う。`show feature config` で `state` を直接確認する。
- **SPM install が失敗する**: extension manifest の `depends` で SONiC core 版を要求しているが image 側が古い。`show version` を確認し、core 版を上げるか extension を旧版に固定する。
- **`make target/...` が deb cache miss で遅い**: `SONIC_DPKG_CACHE_METHOD=cache` を設定し、`target/cache/` を再利用する。
- **arm64 build が `sonic-slave` で落ちる**: `PLATFORM_ARCH=arm64` 指定なし、または `sonic-slave-bookworm-arm64` docker が pull されていない。`make sonic-slave-bookworm-arm64` を先に走らせる。
- **`sonic-installer install` 後に reboot で旧 image に戻る**: GRUB の `default` 設定が `next` でなく `current` を指している。`sonic-installer set-default <image>` で固定する。

## 関連リファレンス

- [show feature](../../reference/cli/show-feature.md)
- [FEATURE table](../../reference/config-db/feature.md)
- [Application Extension Infrastructure](../../architecture/sonic-application-extension-infrastructure.md)
- [Build system improvements](../../architecture/build-system-improvements.md)

## 章の出口

- 構造を読み直す → [アーキテクチャ](architecture.md)。
- 後付け配布の運用 → [運用](operations.md)。
- ARM や container hardening、再現可能ビルド → [発展トピック](advanced.md)。

<!-- glossary-links-injected: ec18b66e3507 -->
