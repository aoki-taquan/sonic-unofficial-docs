---
title: SONiC ビルドシステム既知問題
description: >
  sonic-buildimage のビルドシステムにおける既知の問題、
  Docker / chroot 環境の制限、プラットフォーム固有ビルドエラーを
  issue tracker から収集したリファレンス。
area: architecture
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
hard: 0
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

### 1-1. P4 プラットフォームでの `sonic-slave` イメージ取得失敗 (#6804)

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

### 1-2. `chroot ./fsroot docker info` でのビルド失敗 (#7354)

```
Build fails with "chroot ./fsroot docker info"
```

**原因**: Ubuntu 20.10 などの新しいホスト OS で
chroot 環境内の Docker 互換性問題が発生する。
デフォルトのビルド設定では chroot 内で `docker info` を実行する。

**対処**:

```bash
# ネイティブ Docker を使用（Docker-in-Docker を回避）
export SONIC_CONFIG_USE_NATIVE_DOCKERD_FOR_BUILD=y
make configure PLATFORM=<platform>
```

---

## 2. Docker / systemd 関連

### 2-1. Aboot 環境での Docker 起動失敗（systemd アップグレード後）(#7372)

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

### 2-2. Docker-in-Docker が非 Ubuntu ホストで動作しない (#9919)

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

### 3-1. Innovium プラットフォームでの並列ビルド失敗 (#7139)

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

### 3-2. Marvell ARM アーキテクチャのビルド失敗 (#7465, #11337)

```
[202012] Build failure: marvell-armhf
```

**対象**: Azure Pipelines（AzP）の CI 環境で特有のエラーが発生。
プライベートビルド環境では再現しない場合がある。

**確認ポイント**:
- クロスコンパイルツールチェーンのバージョン
- ARM エミュレーション（QEMU）の設定

---

### 3-3. Bullseye (Debian 11) ビルドの無限ループ (#11769)

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

### 4-1. `sonic-slave-stretch` の取得失敗 (#9741)

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

### 5-1. P4RT コンテナ有効時の VS ビルド失敗 (#9885)

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

<!-- glossary-links-injected: 4702d64416ec -->
