---
title: ACL / CoPP / Mirror / Packet Action
description: ACL / CoPP / Mirror / Packet Action — この章は、SONiC で「パケットを分類して、通す、落とす、CPU に送る、複製する、数える」という機能群をまとめて読むための入口です。
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources:
- docs/acl-qos/acl-in-sonic.md
- docs/acl-qos/acl-support-in-sonic.md
- docs/categories/sai-extensions.md
- docs/acl-qos/acl-user-defined-table-type-support.md
- docs/acl-qos/support-a-new-acl-table-type-that-combines-l3-acl-and-l3v6-acl-tables.md
- docs/acl-qos/acl-flex-counters-support.md
- docs/architecture/sonic-trap-flow-counter-design.md
- docs/reference/cli/config-acl.md
- docs/reference/cli/show-acl.md
- docs/reference/config-db/acl-table.md
- docs/reference/config-db/acl-rule.md
- docs/reference/config-db/policer.md
- docs/reference/config-db/mirror-session.md
- docs/reference/config-db/copp-group.md
- docs/reference/config-db/copp-trap.md
- docs/reference/yang/sonic-copp.md
- docs/reference/yang/sonic-mirror-session.md
- docs/acl-qos/enhancements-on-show-acl-commands.md
- docs/acl-qos/sonic-port-mirroring-hld.md
- docs/acl-qos/everflow-test-plan.md
- docs/acl-qos/configurable-drop-counters-in-sonic.md
- docs/acl-qos/sonic-test-ingress-discards-hld.md
- docs/architecture/port-illegal-packets-drop-design.md
- docs/acl-qos/egress-mirroring-support-and-acl-action-capability-check.md
- docs/acl-qos/egress-outer-dscp-change-table.md
- docs/architecture/sonic-packet-trimming.md
- docs/acl-qos/copp-manager-redesign-test-plan.md
- docs/acl-qos/copp-neighbor-miss-trap-and-enhancements.md
- docs/acl-qos/dash-acl-tags.md
- docs/acl-qos/port-access-control-in-sonic.md
- docs/acl-qos/dhcp-dos-mitigation-in-sonic.md
keywords:
- ACL
- CoPP
- Mirror
- ERSPAN
- packet action
- control plane policer
- policy-based ACL
- everflow
- TCAM
related:
  cli:
  - show acl
  - config acl
  - config bgp
  - show bgp
  - show arp
  - show flowcnt
  - config aaa
  config_db:
  - COPP_TRAP
  - ACL_RULE
  - COPP_GROUP
  - ACL_TABLE
  - MIRROR_SESSION
  - BGP_GLOBALS_AF_NETWORK
  - BGP_PEER_GROUP_AF
  yang:
  - sonic-bgp-bbr
  - sonic-bgp-global
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-copp
  - sonic-bgp-aggregate-address
---

# ACL / CoPP / Mirror / Packet Action

この章は、[SONiC](../../reference/glossary.md#term-sonic) で「パケットを分類して、通す、落とす、CPU に送る、複製する、数える」という機能群をまとめて読むための入口です。既存ページは [ACL](../../reference/glossary.md#term-acl)、[CoPP](../../reference/glossary.md#term-copp)、mirror、drop counter、packet trimming などの [HLD](../../reference/glossary.md#term-hld) 単位に分かれているため、ここでは運用者や設計者の質問順に並べ直します。

ACL は data plane の分類器、CoPP は control plane へ punt されるパケットの保護、mirror は観測用コピー、counter は設定が本当に効いているかを確かめる計測面です。これらは別機能に見えますが、SONiC 内部では `ACL_TABLE` / `ACL_RULE`、[SAI](../../reference/glossary.md#term-sai) ACL action、policer、hostif trap、flex counter といった共通部品でつながっています。

## この章で答える質問

- ACL table type、match、action、counter はどの階層で理解するのか。
- CoPP、policer、trap、mirror は ACL とどこで交わり、どこから別物なのか。
- `show acl`、`aclshow`、trap flow counter、drop counter は運用でどう使い分けるのか。
- egress mirror、outer [DSCP](../../reference/glossary.md#term-dscp) 書換、packet trimming のような [ASIC](../../reference/glossary.md#term-asic) 依存 action はどう確認するのか。
- [DASH](../../reference/glossary.md#term-dash) ACL、PAC、DHCP DoS 緩和は通常 ACL と同じ章で読むべきか。

## 読み進め方

1. [概念](concept.md): ACL / CoPP / mirror / counter の境界と、table type が決めること。
2. [アーキテクチャ](architecture.md): `AclOrch`、SAI ACL、counter、CoPP trap の流れ。
3. [設定](setup.md): `ACL_TABLE` / `ACL_RULE`、policer、mirror、CoPP の最小構成。
4. [運用](operations.md): `show acl`、counter、mirror、drop 調査の実用順序。
5. [内部実装](internals.md): action capability、egress mirror、outer DSCP、packet trimming。
6. [発展トピック](advanced.md): CoPP redesign、DASH ACL、PAC、DHCP DoS との境界。

## 関連ページ

- [ACL in SONiC](../../acl-qos/acl-in-sonic.md)
- [ACL の基本設計](../../acl-qos/acl-support-in-sonic.md)
- [SAI 拡張属性追加系](../../categories/sai-extensions.md)

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 状態 | verification |
|---|---|---|
| concept | ✅ 完成 (196 行) | meta |
| setup | ✅ 完成 (282 行) | meta |
| operations | ✅ 完成 (186 行) | meta |
| internals | ✅ 完成 (128 行) | meta |
| advanced | ✅ 完成 (110 行) | meta |

<!-- /chapter-progress -->

<!-- next-reads -->
## 次に読むべき記事

**この章を読み進める順**

- [概要: 概念](concept.md)
- [アーキテクチャ](architecture.md)
- [設定](setup.md)
- [運用](operations.md)
- [内部実装](internals.md)
- [発展トピック](advanced.md)

**関連する HLD 7 件**

- [Everflow テストプラン（ingress + egress mirror、LAG / ECMP / IPv6）](../../acl-qos/everflow-test-plan.md)
- [CoPP Manager 再設計テストプラン（feature テーブル整合性 + always_enabled）](../../acl-qos/copp-manager-redesign-test-plan.md)
- [ACL の egress mirror 対応と SAI ベース action capability 問い合わせ](../../acl-qos/egress-mirroring-support-and-acl-action-capability-check.md)
- [ACL の基本設計（ACL_TABLE / ACL_RULE スキーマ）](../../acl-qos/acl-support-in-sonic.md)
- [Port Access Control（PAC: 802.1x / MAB / RADIUS）](../../acl-qos/port-access-control-in-sonic.md)
- [SONiC Port Mirroring（SPAN / ERSPAN）](../../acl-qos/sonic-port-mirroring-hld.md)
- [ACL ユーザ定義テーブルタイプ（ACL_TABLE_TYPE と AclTableType）](../../acl-qos/acl-user-defined-table-type-support.md)

**関連トラブルシュート 5 件**

- [APP_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)
- [orchagent が CPU 100% で詰まる](../../reference/runbooks/swss-orchagent-busy-loop.md)
- [Warm Reboot が失敗 / 通信断が長引く](../../reference/runbooks/warm-reboot-failure.md)
- [経路は RIB にあるが FIB / ASIC に降りない](../../reference/runbooks/route-not-installed-in-fib.md)
- [BGP セッションが UP しない](../../reference/runbooks/bgp-session-down.md)

<!-- /next-reads -->

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [SWSS / SAI / Redis 内部実装](../20-swss-sai-redis/index.md)

**派生で読むべき章**

- [QoS / Buffer / PFC / Watermark](../08-qos-buffer/index.md)
- [DASH と SmartSwitch](../13-dash-smartswitch/index.md)

**補完的に読む章**

- [Telemetry / SNMP / Observability](../09-telemetry-snmp/index.md)
- [Security / AAA / FIPS / Hardening](../15-security-aaa/index.md)
- [L2 / VLAN / LAG / MC-LAG](../06-l2-vlan-lag/index.md)

<!-- glossary-links-injected: ec18b66e3507 -->
