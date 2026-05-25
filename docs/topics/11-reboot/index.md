---
title: Reboot / Upgrade / Lifecycle
description: Reboot / Upgrade / Lifecycle — この章は、SONiC の reboot family と upgrade lifecycle を「どれを選ぶか」「何が保持されるか」「運用時にどこを見るか」の順で読むための入口です。
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
related:
  cli:
  - config bgp
  - show bgp
  - show bfd
  - show interfaces
  - show ip
  - show techsupport
  - show version
  config_db:
  - BGP_AGGREGATE_ADDRESS
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  - BGP_GLOBALS_AF_NETWORK
  - BGP_PEER_GROUP
  - BGP_PEER_GROUP_AF
  - BGP_NEIGHBOR_AF
  - BGP_NEIGHBOR
  yang:
  - sonic-bgp-aggregate-address
  - sonic-bgp-bbr
  - sonic-bgp-global
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-sentinel
---

# Reboot / Upgrade / Lifecycle

この章は、[SONiC](../../reference/glossary.md#term-sonic) の reboot family と upgrade lifecycle を「どれを選ぶか」「何が保持されるか」「運用時にどこを見るか」の順で読むための入口です。個別 [HLD](../../reference/glossary.md#term-hld) は warm reboot、fast reboot、express reboot、SWSS warm restart、secure upgrade、[DPU](../../reference/glossary.md#term-dpu) upgrade などに分かれていますが、運用者や実装者が最初に知りたいのは、名前の違いよりも失う状態と守るべき前提です。

## この章で答える質問

- warm reboot、fast reboot、express reboot、SWSS warm restart は何が違うのか。
- reboot 中に [FDB](../../reference/glossary.md#term-fdb)、route、[SAI](../../reference/glossary.md#term-sai) object、[Redis](../../reference/glossary.md#term-redis) DB、container state はどこまで保持されるのか。
- `reboot`、`fast-reboot`、`warm-reboot`、`config warm_restart`、`sonic-installer` はどの場面で使うのか。
- reboot の失敗、原因履歴、[LACP](../../reference/glossary.md#term-lacp)/[BGP](../../reference/glossary.md#term-bgp) peer との干渉、multi-[ASIC](../../reference/glossary.md#term-asic) の差分はどこから確認するのか。
- OS upgrade、secure upgrade、Debian cadence、Docker image versioning、DPU independent upgrade は reboot とどう接続するのか。

## 読む順番

1. [Overview](concept.md): reboot family の分類と、cold / fast / warm / express / service warm restart の違い。
2. [Architecture](architecture.md): warm path が状態を保持する仕組み。SAI object、view switching、idempotent libsairedis、system-wide warmboot。
3. [Setup](setup.md): CLI と設定。`reboot` 系コマンド、warm restart enable、timer、blocking mode。
4. [Operations](operations.md): 原因調査と失敗時の確認順。reboot-cause、LACP timeout、multi-ASIC、Warmboot Manager、SWSS warm restart。
5. [Upgrade](upgrade.md): image lifecycle。`sonic-installer`、secure upgrade、Debian cadence、versioning、DPU independent upgrade。
6. [内部実装 / Internals](internals.md): warm reboot で SWSS / [orchagent](../../reference/glossary.md#term-orchagent) / [syncd](../../reference/glossary.md#term-syncd) が保持する state の構造と、SAI view switching を実装側から見る。
7. [発展トピック / Advanced](advanced.md): express boot、multi-ASIC warmboot、[SmartSwitch](../../reference/glossary.md#term-smartswitch) / DPU の独立アップグレード、他章との境界。

## 章内の境界

この章は「reboot または upgrade の実行時に、SONiC の状態をどう落とし、どう戻すか」を扱います。SmartSwitch の [NPU](../../reference/glossary.md#term-npu)/DPU アーキテクチャ全体、[Multi-ASIC](../../reference/glossary.md#term-multi-asic)/[VOQ](../../reference/glossary.md#term-voq) chassis の通常運用、port/optics の bring-up は別章の主題です。ただし reboot lifecycle に直接関係する DPU reboot、DPU graceful shutdown、multi-ASIC warm reboot はこの章でも扱います。

## 関連ページ

- [Warm-Reboot / Fast-Reboot 関連](../../categories/reboot.md)
- [reboot / fast-reboot / warm-reboot コマンド](../../reference/cli/reboot-fast-warm.md)
- [config warm_restart サブコマンド](../../reference/cli/config-warm_restart.md)
- [sonic-installer コマンド](../../reference/cli/sonic-installer.md)

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 行数 | 状態 | verification | 主目的 |
|---|---|---|---|---|
| concept | 140 | ✅ 完成 | meta | 概念・位置付け |
| architecture | 57 | ⚠️ プレースホルダ | meta | アーキテクチャ・データフロー |
| setup | 176 | ✅ 完成 | meta | セットアップ手順 |
| operations | 182 | ✅ 完成 | meta | 運用・デバッグ |
| internals | 121 | ✅ 完成 | meta | 内部実装 |
| upgrade | 47 | ⚠️ プレースホルダ | meta | アップグレード手順 |
| advanced | 91 | ⚠️ プレースホルダ | meta | 発展トピック |

<!-- /chapter-progress -->

<!-- next-reads -->
## 次に読むべき記事

**この章を読み進める順**

- [概要: Reboot family の選び方](concept.md)
- [アーキテクチャ: Warm path の内部構造](architecture.md)
- [設定: Reboot / warm restart の設定](setup.md)
- [運用: Reboot 運用と障害調査](operations.md)
- [内部実装](internals.md)
- [発展トピック: Reboot / Upgrade の発展トピック](advanced.md)

**関連する HLD 7 件**

- [System-wide Warmboot（going down / up path / SAI 期待値）](../../system/system-wide-warmboot.md)
- [Warm Reboot 開発フェーズと OID 復元戦略（idempotent libsairedis vs syncd view comparison）](../../system/what-are-the-development-phases-and-scope-for-warm-reboot.md)
- [Warmboot Manager（shutdown orchestration / reconciliation 統一）](../../system/warmboot-manager-hld.md)
- [FRR 用 sysctl チューニングのデフォルト](../../system/useful-sysctl-settings.md)
- [SONiC NOS の設定手段一覧（CLI / sonic-cfggen / config_db.json / RESTCONF / gNMI / ZTP / vtysh / redis / apply-patch）](../../management/sonic-nos-configuration-methods.md)
- [libsairedis API idempotence（warm restart 用 OID キャッシュと duplicate 抑止）](../../system/sonic-libsairedis-api-idempotence-support.md)
- [YANG モデルによる ConfigDB 更新検証（GCU + ConfigDBConnector デコレータ）](../../management/sonic-config-update-validation-via-yang.md)

**関連トラブルシュート 5 件**

- [APPL_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)
- [orchagent が CPU 100% で詰まる](../../reference/runbooks/swss-orchagent-busy-loop.md)
- [Warm Reboot が失敗 / 通信断が長引く](../../reference/runbooks/warm-reboot-failure.md)
- [経路は RIB にあるが FIB / ASIC に降りない](../../reference/runbooks/route-not-installed-in-fib.md)
- [BGP Graceful Restart のネゴシエーションに失敗する](../../reference/runbooks/bgp-graceful-restart-failure.md)

<!-- /next-reads -->

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

<!-- glossary-links-injected: 5c9b3765d470 -->
