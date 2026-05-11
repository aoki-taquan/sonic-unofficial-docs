---
title: Reboot / Upgrade / Lifecycle
description: "Reboot / Upgrade / Lifecycle — この章は、SONiC の reboot family と upgrade lifecycle を「どれを選ぶか」「何が保持されるか」「運用時にどこを見るか」の順で読むための入口です。"
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources:
  - docs/system/sonic-warm-reboot.md
  - docs/system/fast-reboot-flow-improvements-hld.md
  - docs/system/sonic-express-reboot-hld-spec.md
  - docs/system/system-wide-warmboot.md
  - docs/reference/cli/reboot-fast-warm.md
  - docs/reference/cli/config-warm_restart.md
  - docs/reference/cli/sonic-installer.md
keywords:
  - Reboot
  - Upgrade
  - Lifecycle
  - warm reboot
  - fast reboot
  - cold reboot
  - image install
  - SONiC firmware
  - 再起動
---

# Reboot / Upgrade / Lifecycle

この章は、SONiC の reboot family と upgrade lifecycle を「どれを選ぶか」「何が保持されるか」「運用時にどこを見るか」の順で読むための入口です。個別 HLD は warm reboot、fast reboot、express reboot、SWSS warm restart、secure upgrade、DPU upgrade などに分かれていますが、運用者や実装者が最初に知りたいのは、名前の違いよりも失う状態と守るべき前提です。

## この章で答える質問

- warm reboot、fast reboot、express reboot、SWSS warm restart は何が違うのか。
- reboot 中に FDB、route、SAI object、Redis DB、container state はどこまで保持されるのか。
- `reboot`、`fast-reboot`、`warm-reboot`、`config warm_restart`、`sonic-installer` はどの場面で使うのか。
- reboot の失敗、原因履歴、LACP/BGP peer との干渉、multi-ASIC の差分はどこから確認するのか。
- OS upgrade、secure upgrade、Debian cadence、Docker image versioning、DPU independent upgrade は reboot とどう接続するのか。

## 読む順番

1. [Overview](concept.md): reboot family の分類と、cold / fast / warm / express / service warm restart の違い。
2. [Architecture](architecture.md): warm path が状態を保持する仕組み。SAI object、view switching、idempotent libsairedis、system-wide warmboot。
3. [Setup](setup.md): CLI と設定。`reboot` 系コマンド、warm restart enable、timer、blocking mode。
4. [Operations](operations.md): 原因調査と失敗時の確認順。reboot-cause、LACP timeout、multi-ASIC、Warmboot Manager、SWSS warm restart。
5. [Upgrade](upgrade.md): image lifecycle。`sonic-installer`、secure upgrade、Debian cadence、versioning、DPU independent upgrade。
6. [内部実装 / Internals](internals.md): warm reboot で SWSS / orchagent / syncd が保持する state の構造と、SAI view switching を実装側から見る。
7. [発展トピック / Advanced](advanced.md): express boot、multi-ASIC warmboot、SmartSwitch / DPU の独立アップグレード、他章との境界。

## 章内の境界

この章は「reboot または upgrade の実行時に、SONiC の状態をどう落とし、どう戻すか」を扱います。SmartSwitch の NPU/DPU アーキテクチャ全体、Multi-ASIC/VOQ chassis の通常運用、port/optics の bring-up は別章の主題です。ただし reboot lifecycle に直接関係する DPU reboot、DPU graceful shutdown、multi-ASIC warm reboot はこの章でも扱います。

## 関連ページ

- [Warm-Reboot / Fast-Reboot 関連](../../categories/reboot.md)
- [reboot / fast-reboot / warm-reboot コマンド](../../reference/cli/reboot-fast-warm.md)
- [config warm_restart サブコマンド](../../reference/cli/config-warm_restart.md)
- [sonic-installer コマンド](../../reference/cli/sonic-installer.md)

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [SWSS / SAI / Redis 内部実装](../20-swss-sai-redis/index.md)

**派生で読むべき章**

- [Build / Packaging / Application Extension](../19-build-packaging/index.md)

**補完的に読む章**

- [Telemetry / SNMP / Observability](../09-telemetry-snmp/index.md)
- [Multi-ASIC / VOQ Chassis](../12-multi-asic-voq/index.md)
- [DASH と SmartSwitch](../13-dash-smartswitch/index.md)

