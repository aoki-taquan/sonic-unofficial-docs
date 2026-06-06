---
title: SWSS / SAI / Redis 内部実装
description: SWSS / SAI / Redis 内部実装 — この章は、SONiC の機能章を読み解くときに何度も出てくる「Redis DB」「orchagent」「syncd」「SAI」の関係を、機能横断の内部実装としてまとめ直すための入口である。
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources: []
keywords:
- SWSS
- SAI
- Redis
- orchagent
- syncd
- APPL_DB
- ASIC_DB
- STATE_DB
- 内部実装
related:
  cli:
  - config bgp
  - show bgp
  - config acl
  - show acl
  - config vrf
  - show techsupport
  - config vnet
  config_db:
  - BGP_GLOBALS
  - BGP_NEIGHBOR
  - ACL_RULE
  - ACL_TABLE
  - BGP_PEER_GROUP_AF
  - CRM
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  yang:
  - sonic-bgp-bbr
  - sonic-bgp-device-global
  - sonic-bgp-global
  - sonic-bgp-neighbor
  - sonic-bgp-peerrange
  - sonic-crm
  - sonic-bgp-monitor
---

# SWSS / SAI / Redis 内部実装

この章は、[SONiC](../../reference/glossary.md#term-sonic) の機能章を読み解くときに何度も出てくる「[Redis](../../reference/glossary.md#term-redis) DB」「[orchagent](../../reference/glossary.md#term-orchagent)」「[syncd](../../reference/glossary.md#term-syncd)」「[SAI](../../reference/glossary.md#term-sai)」の関係を、機能横断の内部実装としてまとめ直すための入口である。各機能章（[BGP](../../reference/glossary.md#term-bgp)、L2、[ACL](../../reference/glossary.md#term-acl)、[VRF](../../reference/glossary.md#term-vrf) など）では Redis DB と daemon の名前が前提のように出てくるが、その共通の地図はここに置く。

主な問いは次の 4 つ。

- `CONFIG_DB`、`APPL_DB`、`STATE_DB`、`COUNTERS_DB`、`ASIC_DB` はどの daemon が読み書きし、どこで境界を持つのか。
- orchagent、syncd、sairedis、SAI、Redis はそれぞれ何を責務にしているのか。
- SAI failure handling、dump、API version、stats capability は運用と開発のどちらの観点で読めばよいのか。
- Bulk counter、flex counter、debug framework、dump utility は内部実装章としてどう整理されるのか。

## 読む順番

1. [概要](concept.md): 内部実装章の読み方と、機能章との重複を避けるためのスコープを定義する。
2. [アーキテクチャ](architecture.md): Redis DB、[ProducerStateTable](../../reference/glossary.md#term-producerstatetable)、orchagent、syncd、SAI の関係を一枚図で押さえる。
3. [設定](setup.md): 内部実装側の設定面（database_config.json、multi-namespace、FEATURE delay 等）を扱う。
4. [運用](operations.md): SAI 失敗時の見方、ERROR_DB、dump、health-check、system ready など運用観点を扱う。
5. [内部実装](internals.md): SAI API version、stats capability、[CRM](../../reference/glossary.md#term-crm) 拡張、bulk/flex counter、debug framework、dump utility を比較する。
6. [発展トピック](advanced.md): app health、system ready、FEATURE delayed、warm reboot の view switching など起動・再構成系を扱う。

## 統合した既存ページ

この章は internals / architecture / platform / system 配下の [HLD](../../reference/glossary.md#term-hld) 派生ページを横断する。スキーマや SAI 呼び出しの詳細は各サブページ末尾の「関連ページ」から、機能固有の話は当該機能章（[BGP](../02-bgp/index.md)、[L2 VLAN LAG](../06-l2-vlan-lag/index.md)、[ACL / CoPP / Mirror](../07-acl-copp-mirror/index.md) など）から参照する。

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 行数 | 状態 | verification | 主目的 |
|---|---|---|---|---|
| advanced | 155 | ✅ 完成 | meta | 発展トピック |
| architecture | 90 | ⚠️ プレースホルダ | meta | アーキテクチャ・データフロー |
| concept | 156 | ✅ 完成 | meta | 概念・位置付け |
| internals | 189 | ✅ 完成 | meta | 内部実装 |
| operations | 230 | ✅ 完成 | meta | 運用・デバッグ |
| setup | 275 | ✅ 完成 | meta | セットアップ手順 |

<!-- /chapter-progress -->

<!-- next-reads -->
## 次に読むべき記事

**この章を読み進める順**

- [概要](concept.md)
- [アーキテクチャ](architecture.md)
- [設定](setup.md)
- [運用](operations.md)
- [内部実装](internals.md)
- [発展トピック](advanced.md)

**関連する HLD 7 件**

- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../../architecture/error-handling-framework-in-sonic.md)
- [swss-schema（APPL_DB / STATE_DB の中心スキーマ参照）](../../internals/swss-schema.md)
- [Alpine 仮想 SONiC（ALViS / KNE デプロイ）](../../architecture/alpine-high-level-design.md)
- [flex counter 初期化最適化（pending_sai_objects + バッチ bulk_get_stats）](../../internals/sonic-counter-initialization-optimization.md)
- [dump utility（モジュール単位で複数 DB から関連 key を集約する debug CLI）](../../internals/dump-utility-for-easy-debugging.md)
- [Port Profile Init（SAI bulk port API による fast-boot 高速化）](../../architecture/port-profile-init-hld.md)
- [SONiC-VS のビルドと libvirt 起動手順](../../architecture/steps-to-bring-up-sonic-vs.md)

**関連トラブルシュート 5 件**

- [APPL_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)
- [orchagent が CPU 100% で詰まる](../../reference/runbooks/swss-orchagent-busy-loop.md)
- [経路は RIB にあるが FIB / ASIC に降りない](../../reference/runbooks/route-not-installed-in-fib.md)
- [Warm Reboot が失敗 / 通信断が長引く](../../reference/runbooks/warm-reboot-failure.md)
- [SAI failure / syncd リスタート多発](../../reference/runbooks/sai-failure.md)

<!-- /next-reads -->

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)

**派生で読むべき章**

- [VRF / ECMP / RIB-FIB パイプライン](../04-vrf-ecmp/index.md)
- [L2 / VLAN / LAG / MC-LAG](../06-l2-vlan-lag/index.md)
- [ACL / CoPP / Mirror / Packet Action](../07-acl-copp-mirror/index.md)
- [QoS / Buffer / PFC / Watermark](../08-qos-buffer/index.md)

**補完的に読む章**

- [Telemetry / SNMP / Observability](../09-telemetry-snmp/index.md)
- [Reboot / Upgrade / Lifecycle](../11-reboot/index.md)
- [P4 / PINS / Programmable Pipeline](../18-p4-pins/index.md)
- [リファレンス横断索引](../22-reference-index/index.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
