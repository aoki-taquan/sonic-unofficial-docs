---
title: Upgrade lifecycle
description: Upgrade lifecycle — upgrade は reboot と同じではありません。upgrade は「どの image /
  package / container を次に使うか」を決める lifecycle で、reboot はその変更を有効化する transition です。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/reference/cli/sonic-installer.md
- docs/system/secure-upgrade.md
- docs/system/sonic-debian-upgrade-cadence.md
- docs/system/sonic-os-sonic-docker-images-versioning.md
- docs/system/independent-dpu-upgrade.md
related:
  cli:
  - config warm_restart
  - config platform firmware
  config_db:
  - DPU
  - CHASSIS_MODULE
  - MID_PLANE_BRIDGE
  - DPUS
  yang:
  - sonic-warm-restart
  - sonic-chassis-module
  - sonic-smart-switch
---

# Upgrade lifecycle

upgrade は reboot と同じではありません。upgrade は「どの image / package / container を次に使うか」を決める lifecycle で、reboot はその変更を有効化する transition です。[SONiC](../../reference/glossary.md#term-sonic) では OS image、Docker image、Debian base、[FRR](../../reference/glossary.md#term-frr)、[DPU](../../reference/glossary.md#term-dpu) image などが別々の粒度で更新されます。

## image upgrade の基本線

`sonic-installer` は SONiC OS image の install、list、default/next boot 設定、FIPS 設定、image 検証を扱う CLI です。reboot script は次回 boot image の検証に `sonic-installer verify-next-image` を使うため、upgrade と reboot はここで接続します。コマンド詳細は [sonic-installer コマンド](../../reference/cli/sonic-installer.md) を参照します。

一般的な流れは、image を install し、next boot/default を確認し、必要なら secure/FIPS 条件を満たしてから reboot で切り替える、という順です。reboot に入ってから image 検証で失敗する状態は避けます。

```mermaid
flowchart LR
  Fetch[image を取得]
  Install[sonic-installer install]
  Verify[verify-next-image]
  Select[set-default / set-next-boot]
  Reboot[reboot / fast-reboot / warm-reboot]
  Validate[起動後検証]
  Fetch --> Install --> Select --> Verify --> Reboot --> Validate
```

## secure upgrade

secure upgrade は image の署名と install 時の検証を扱います。build 側では署名済み artifact を作り、install 側では `SECURE_UPGRADE_MODE` などの条件に応じて検証します。upgrade/downgrade の許可関係は [Secure Upgrade](../../system/secure-upgrade.md) の matrix を確認します。

secure upgrade は reboot を速くする機能ではなく、reboot 前に「次に起動する image を信頼できるか」を決める機能です。そのため、fast/warm reboot の設計とは独立していても、運用フロー上は必ず reboot 前の gate になります。

## Debian cadence と Docker image versioning

[SONiC Debian アップグレード方針](../../system/sonic-debian-upgrade-cadence.md) は、base image、container、submodule、廃止 cadence の考え方を扱います。これは単発の `sonic-installer` 実行手順ではなく、リリース全体でどの Debian と package set に追随するかの方針です。

[SONiC OS と Docker イメージのセマンティックバージョニング](../../system/sonic-os-sonic-docker-images-versioning.md) は、OS package API、Docker image、Conventional Commits、package release flow の整合性を見るページです。container warm restart を使う場合でも、versioning の互換性が崩れると復元 path は成立しません。

## DPU independent upgrade

[SmartSwitch](../../reference/glossary.md#term-smartswitch) では DPU が独立して upgrade される場合があります。[Smart Switch: DPU 独立アップグレード](../../system/independent-dpu-upgrade.md) は [gNOI](../../reference/glossary.md#term-gnoi) 経路、upgrade sequence、影響範囲を説明します。[NPU](../../reference/glossary.md#term-npu) 側 SONiC image の切替とは別 lifecycle なので、全体 reboot、DPU reboot、DPU graceful shutdown と区別して計画します。

## 関連ページ

- [sonic-installer コマンド](../../reference/cli/sonic-installer.md)
- [Secure Upgrade](../../system/secure-upgrade.md)
- [SONiC Debian アップグレード方針](../../system/sonic-debian-upgrade-cadence.md)
- [SONiC OS と Docker イメージのセマンティックバージョニング](../../system/sonic-os-sonic-docker-images-versioning.md)
- [Smart Switch: DPU 独立アップグレード](../../system/independent-dpu-upgrade.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
