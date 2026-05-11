---
title: SWSS / SAI / Redis 内部実装
description: "SWSS / SAI / Redis 内部実装 — この章は、SONiC の機能章を読み解くときに何度も出てくる「Redis DB」「orchagent」「syncd」「SAI」の関係を、機能横断の内部実装としてまとめ直すための入口である。"
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
---

# SWSS / SAI / Redis 内部実装

この章は、SONiC の機能章を読み解くときに何度も出てくる「Redis DB」「orchagent」「syncd」「SAI」の関係を、機能横断の内部実装としてまとめ直すための入口である。各機能章（BGP、L2、ACL、VRF など）では Redis DB と daemon の名前が前提のように出てくるが、その共通の地図はここに置く。

主な問いは次の 4 つ。

- `CONFIG_DB`、`APPL_DB`、`STATE_DB`、`COUNTERS_DB`、`ASIC_DB` はどの daemon が読み書きし、どこで境界を持つのか。
- orchagent、syncd、sairedis、SAI、Redis はそれぞれ何を責務にしているのか。
- SAI failure handling、dump、API version、stats capability は運用と開発のどちらの観点で読めばよいのか。
- Bulk counter、flex counter、debug framework、dump utility は内部実装章としてどう整理されるのか。

## 読む順番

1. [概要](concept.md): 内部実装章の読み方と、機能章との重複を避けるためのスコープを定義する。
2. [アーキテクチャ](architecture.md): Redis DB、ProducerStateTable、orchagent、syncd、SAI の関係を一枚図で押さえる。
3. [設定](setup.md): 内部実装側の設定面（database_config.json、multi-namespace、FEATURE delay 等）を扱う。
4. [運用](operations.md): SAI 失敗時の見方、ERROR_DB、dump、health-check、system ready など運用観点を扱う。
5. [内部実装](internals.md): SAI API version、stats capability、CRM 拡張、bulk/flex counter、debug framework、dump utility を比較する。
6. [発展トピック](advanced.md): app health、system ready、FEATURE delayed、warm reboot の view switching など起動・再構成系を扱う。

## 統合した既存ページ

この章は internals / architecture / platform / system 配下の HLD 派生ページを横断する。スキーマや SAI 呼び出しの詳細は各サブページ末尾の「関連ページ」から、機能固有の話は当該機能章（[BGP](../02-bgp/index.md)、[L2 VLAN LAG](../06-l2-vlan-lag/index.md)、[ACL / CoPP / Mirror](../07-acl-copp-mirror/index.md) など）から参照する。

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

