---
title: SONiC ビルドシステム既知問題
description: >
  sonic-buildimage のビルドシステムにおける既知の問題、
  Docker / chroot 環境の制限、プラットフォーム固有ビルドエラーを
  issue tracker から収集したリファレンス。
area: system
verification: code-verified
last_verified: 2026-05-13
sources:
  - repo: sonic-net/sonic-buildimage
    ref: master
    note: >
      issues #6804, #7076, #7139, #7354, #7372, #7465, #9741, #9885, #9919,
      #11337, #11769
related:
  config_db: []
  cli: []
  yang: []
---

!!! success "裏取りステータス: code-verified"
    sonic-buildimage issue tracker の実環境報告から抽出。master ブランチ対象。

# SONiC ビルドシステム既知問題

## 概要

[sonic-buildimage](../reference/glossary.md#term-sonic-buildimage) は Docker ベースの階層的なビルドシステムを使用する。
ホスト OS・Docker バージョン・プラットフォームの組み合わせによって
様々なビルドエラーが発生することが報告されている。

---

## 1. `make configure` 関連

### 1-1. P4 プラットフォームでの `sonic-slave` イメージ取得失敗 (#6804)[^6804]

```bash
$ make configure PLATFORM=p4
# → docker: Error response from daemon: pull access denied for sonic-slave-stretch-sonic
```

**原因**: `sonic-slave-stretch-sonic` イメージが Docker Hub で
一般公開されていないか、認証が必要。

**対処**:

```bash
# Docker ログインが必要な場合
docker login
# または自前でビルド
make configure PLATFORM=p4 SONIC_BUILD_JOBS=4
# sonic-slave イメージをローカルでビルドする場合
make sonic-slave-stretch
```

---

### 1-2. `chroot ./fsroot docker info` でのビルド失敗 (#7354)[^7354]

```
Build fails with "chroot ./fsroot docker info"
```

**原因**: Ubuntu 20.10 などの新しいホスト OS で
chroot 環境内の Docker 互換性問題が発生する。
デフォルトのビルド設定では chroot 内で `docker info` を実行する。

**対処**: `SONIC_CONFIG_USE_NATIVE_DOCKERD_FOR_BUILD=y` でネイティブ Docker を使い、
Docker-in-Docker を回避する。このフラグは `Makefile.work` でビルド経路を分岐する[^nativedockerd]。

```bash
# ネイティブ Docker を使用（Docker-in-Docker を回避）
export SONIC_CONFIG_USE_NATIVE_DOCKERD_FOR_BUILD=y
make configure PLATFORM=<platform>
```

<!-- evidence:
source: sonic-net/sonic-buildimage/Makefile.work#L332-L407 (sha: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
excerpt: |
  ifeq ($(strip $(SONIC_CONFIG_USE_NATIVE_DOCKERD_FOR_BUILD)),y)
reasoning: >
  SONIC_CONFIG_USE_NATIVE_DOCKERD_FOR_BUILD が現行 master の Makefile.work で
  ビルド経路を分岐する実在の設定変数であることを確認。Docker-in-Docker 回避策の裏取り。
  デフォルト無効であることは rules/config L60-L65 のコメントアウトされた既定値で確認できる。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-buildimage/Makefile.work#L332-L407 (sha: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)"

    **出典**:

    `sonic-net/sonic-buildimage/Makefile.work#L332-L407 (sha: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)`

    **抜粋**:

    ```text
    ifeq ($(strip $(SONIC_CONFIG_USE_NATIVE_DOCKERD_FOR_BUILD)),y)
    ```

    **判断根拠**: SONIC_CONFIG_USE_NATIVE_DOCKERD_FOR_BUILD が現行 master の Makefile.work で ビルド経路を分岐する実在の設定変数であることを確認。Docker-in-Docker 回避策の裏取り。 デフォルト無効であることは rules/config L60-L65 のコメントアウトされた既定値で確認できる。

<!-- evidence-rendered:end -->

---

## 2. Docker / systemd 関連

### 2-1. Aboot 環境での Docker 起動失敗（systemd アップグレード後）(#7372)[^7372]

```
Docker startup broken in master for aboot due to systemd upgrade
```

**現象**: 特定の Arista aboot 環境で systemd のバージョンアップ後に
Docker が起動しなくなる。

**確認**:

```bash
sudo journalctl -u docker | tail -50
systemctl status docker
```

---

### 2-2. Docker-in-Docker が非 Ubuntu ホストで動作しない (#9919)[^9919]

```
Docker in docker builds do not work in build container (Arch linux host)
```

**原因**: [SONiC](../reference/glossary.md#term-sonic) のビルドコンテナ（sonic-slave）は Ubuntu ベースで
設計されており、Arch Linux などの非 Ubuntu ホストでは
カーネルパラメータや cgroup の設定が異なる。

**対処**:

```bash
# ネイティブ Docker ソケットを使用
export SONIC_CONFIG_USE_NATIVE_DOCKERD_FOR_BUILD=y
make configure PLATFORM=<platform>
```

---

## 3. プラットフォーム固有ビルドエラー

### 3-1. Innovium プラットフォームでの並列ビルド失敗 (#7139)[^7139]

```
201811 parallel build failure seen with Innovium platform
```

**原因**: Innovium プラットフォームの一部のビルドターゲットが
並列ビルド時に競合する。

**回避策**:

```bash
# ジョブ数を制限
make SONIC_BUILD_JOBS=1
# または
make -j1
```

---

### 3-2. Marvell プラットフォームのビルド失敗 (#7465, #11337)[^7465][^11337]

```
[202012] Build failure: marvell-armhf
Build failed. Marvell amd64.
```

**対象**: Marvell プラットフォーム関連のビルド失敗が複数アーキテクチャで報告されている。
#7465 は Marvell ARM（marvell-armhf）の AzP CI 環境でのビルド失敗、
#11337 は Marvell amd64 ビルド失敗で、それぞれ異なるアーキテクチャの問題。

**確認ポイント**:
- クロスコンパイルツールチェーン（armhf）のバージョン
- ARM エミュレーション（QEMU）の設定
- amd64 ビルドのプラットフォーム依存パッケージ

---

### 3-3. Bullseye (Debian 11) ビルドの無限ループ (#11769)[^11769]

```
Build fails with only BULLSEYE enabled
# endless loop during libsnmp-dev install
```

**現象**: `docker-fpm-frr.gz` のビルド中に
`libsnmp-dev` のインストールが無限ループする。

**対処**: キャッシュをクリアして再ビルドを試みる。

```bash
make reset
make configure PLATFORM=<platform>
make target/docker-fpm-frr.gz
```

---

## 4. sonic-slave イメージ

### 4-1. `sonic-slave-stretch` の取得失敗 (#9741)[^9741]

```
Unable to fetch sonic-slave-stretch
```

**背景**: Debian Stretch（9）は EOL となり、
公式パッケージリポジトリが更新されなくなっている。
`sonic-slave-stretch` イメージの pull が失敗する場合がある。

**対処**:
1. Buster（Debian 10）または Bullseye（Debian 11）ベースに移行
2. ローカルでイメージをビルドする

```bash
make sonic-slave-bullseye
```

---

## 5. 特定機能のビルドエラー

### 5-1. P4RT コンテナ有効時の VS ビルド失敗 (#9885)[^9885]

```
VS image build failed when P4RT container is enabled
```

**背景**: [P4RT](../reference/glossary.md#term-p4rt)（P4 Runtime）は [PINS](../reference/glossary.md#term-pins) プロジェクトの opt-in 機能。
デフォルト設定では無効のため、通常のビルドには影響しない。

**対処**:

```bash
# P4RT を無効化してビルド
export INCLUDE_P4RT=n
make configure PLATFORM=<platform>
```

---

## ビルド環境要件

| 項目 | 推奨 |
|------|------|
| ホスト OS | Ubuntu 20.04 LTS |
| Docker | 20.10 以上 |
| RAM | 32GB 以上（並列ビルド時） |
| ディスク | 200GB 以上（SSD 推奨） |
| CPU | 8 コア以上 |

---

## よく使うビルドオプション

```bash
# 並列ビルドジョブ数
export SONIC_BUILD_JOBS=4

# キャッシュ有効化
export SONIC_DPKG_CACHE_METHOD=rcache

# ネイティブ Docker 使用
export SONIC_CONFIG_USE_NATIVE_DOCKERD_FOR_BUILD=y

# BuildKit 有効化（互換性確認後）
export DOCKER_BUILDKIT=1

# デバッグ出力
export SONIC_DEBUGGING_ON=y
```

---

## 参照

- [ビルドシステム改善 HLD](../architecture/build-system-improvements.md)
- [ビルドプロファイル](../architecture/build-profiles.md)

## 引用元

各項目の一次情報は sonic-buildimage の issue tracker。ビルド設定変数は `sonic-net/sonic-buildimage` (sha `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`) の `Makefile.work` / `rules/config` で裏取りした。

[^nativedockerd]: `Makefile.work` L332-L407、`sonic-net/sonic-buildimage` (sha `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`)。`SONIC_CONFIG_USE_NATIVE_DOCKERD_FOR_BUILD` でビルド経路を分岐。既定値は `rules/config` L60-L65 でコメントアウト（無効）。
[^6804]: [sonic-buildimage #6804](https://github.com/sonic-net/sonic-buildimage/issues/6804) — P4 プラットフォームでの `sonic-slave-stretch-sonic` イメージ取得失敗。
[^7354]: [sonic-buildimage #7354](https://github.com/sonic-net/sonic-buildimage/issues/7354) — `chroot ./fsroot docker info` でのビルド失敗。
[^7372]: [sonic-buildimage #7372](https://github.com/sonic-net/sonic-buildimage/issues/7372) — Arista aboot で systemd アップグレード後に Docker が起動しない件。
[^9919]: [sonic-buildimage #9919](https://github.com/sonic-net/sonic-buildimage/issues/9919) — 非 Ubuntu ホスト（Arch Linux）で Docker-in-Docker ビルドが動作しない件。
[^7139]: [sonic-buildimage #7139](https://github.com/sonic-net/sonic-buildimage/issues/7139) — Innovium プラットフォームの並列ビルド失敗。
[^7465]: [sonic-buildimage #7465](https://github.com/sonic-net/sonic-buildimage/issues/7465) — Marvell ARM（marvell-armhf）のビルド失敗。
[^11337]: [sonic-buildimage #11337](https://github.com/sonic-net/sonic-buildimage/issues/11337) — Marvell amd64 ビルド失敗（"Build failed. Marvell amd64."）。
[^11769]: [sonic-buildimage #11769](https://github.com/sonic-net/sonic-buildimage/issues/11769) — BULLSEYE のみ有効時の `libsnmp-dev` インストール無限ループ。
[^9741]: [sonic-buildimage #9741](https://github.com/sonic-net/sonic-buildimage/issues/9741) — EOL の `sonic-slave-stretch` イメージ取得失敗。
[^9885]: [sonic-buildimage #9885](https://github.com/sonic-net/sonic-buildimage/issues/9885) — P4RT コンテナ有効時の [VS](../reference/glossary.md#term-vs) イメージビルド失敗。

<!-- glossary-links-injected: 9fb3fca99a59 -->
