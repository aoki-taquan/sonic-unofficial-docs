---
title: 発展トピック
description: 発展トピック — ここでは、port / platform 章の中でも比較的新しい、または運用上の影響が大きい設計を 3 つ取り上げます。詳細は元
  HLD に従い、本章では「ほかの章と何が変わるか」に絞ります。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/platform/1-6t-support-in-sonic.md
- docs/platform/sonic-port-naming-convention-change.md
- docs/acl-qos/enhancements-to-add-or-del-ports-dynamically.md
related:
  cli:
  - show acl
  - config snmp
  - config qos
  - config acl
  - config vlan
  - show vlan
  config_db:
  - PORT
  - VLAN
  - SNMP
  - SNMP_AGENT_ADDRESS_CONFIG
  - ACL_RULE
  - ACL_TABLE
  - VLAN_SUB_INTERFACE
  yang:
  - sonic-snmp
  - sonic-vlan
  - sonic-vlan-sub-interface
---

# 発展トピック

ここでは、port / platform 章の中でも比較的新しい、または運用上の影響が大きい設計を 3 つ取り上げます。詳細は元 [HLD](../../reference/glossary.md#term-hld) に従い、本章では「ほかの章と何が変わるか」に絞ります。

## 1.6T 対応

[1.6T support in SONiC](../../platform/1-6t-support-in-sonic.md) は、1.6Tbps クラスの port をサポートするための拡張設計です。speed 値、lanes、FEC、buffer profile、optics、Gearbox など、port 章のほぼ全要素が影響を受けます。既存の `PORT` テーブルや [YANG](../../reference/glossary.md#term-yang) の制約値を見直す必要があるため、設定面・運用面の双方を再点検する観点で読むのが安全です。

## Port naming convention

[SONiC port naming convention change](../../platform/sonic-port-naming-convention-change.md) は、現行の `EthernetN` ベース命名から、より装置構造を反映した命名へ移行する提案です。

影響範囲が広く、CLI、[CONFIG_DB](../../reference/glossary.md#term-config_db)、YANG、運用スクリプトのほぼすべてに波及します。新規スクリプトを書くときは、port 名を直接ハードコードせず、`PORT` テーブルのキー一覧から取得する書き方にしておくと変更耐性が上がります。

## Dynamic add / delete

[enhancements to add or del ports dynamically](../../acl-qos/enhancements-to-add-or-del-ports-dynamically.md) は、運用中に port を追加・削除する操作の整合性向上に関する設計です。breakout や 1.6T 対応と直接重なるテーマで、[ACL](../../reference/glossary.md#term-acl) bind や [QoS](../../reference/glossary.md#term-qos) buffer の付け替えが正しく走るかが論点になります。

dynamic add / delete を多用する運用 ([ZTP](../../reference/glossary.md#term-ztp) や検証ラボなど) では、buffer / QoS / ACL 章の挙動とあわせてこの設計を読むと、副作用の予測がしやすくなります。

## どの章と相互参照するか

- breakout / 速度変更 → QoS / Buffer 章 (今後執筆) と、関連 reference の [PORT テーブル](../../reference/config-db/port.md)。
- ACL bind の付け替え → [ACL / CoPP / Mirror 章](../07-acl-copp-mirror/index.md)。
- [LAG](../../reference/glossary.md#term-lag) / [VLAN](../../reference/glossary.md#term-vlan) とのメンバ整合 → [L2 / VLAN / LAG 章](../06-l2-vlan-lag/index.md)。

## 関連ページ

- [1.6T support in SONiC](../../platform/1-6t-support-in-sonic.md)
- [SONiC port naming convention change](../../platform/sonic-port-naming-convention-change.md)
- [enhancements to add or del ports dynamically](../../acl-qos/enhancements-to-add-or-del-ports-dynamically.md)

## 発展トピック

- **CMIS 5.x optics**: 400G/800G ZR / ZR+ など coherent optics の管理は CMIS で行い、SONiC `xcvrd` が state machine を実装する。Application select、re-provisioning、firmware download などが要点。
- **Optics firmware upgrade**: `gnoi.os.Install` の概念に近く、optics 内 firmware を host から書き換える。途中で reboot を挟まない hot upgrade 対応が ASIC / optics で異なる。
- **Linkmgrd と link prober**: Dual-ToR の link prober 以外にも、汎用 link healthcheck 機能が `linkmgrd` 系で拡張されつつある。[SAI](../../reference/glossary.md#term-sai) sub-second link state notification が前提。
- **Breakout dynamic**: port breakout (4x25G / 2x50G など) の動的切替は `dynamic-port-breakout` HLD と組合せ、buffer / QoS / ACL を全部 reprovision する。
- **PoE / 外部給電**: 一部 platform で PoE 機能 (`POE` schema 提案) があり、port lifecycle と組合せる。

## 既知の制約と回避方法

- **mixed-lane optics の制限**: 一部 platform で同じ port group 内に異速度 optics を入れると lane assignment が動かない。SKU docs を必ず参照する。
- **xcvrd の polling 間隔**: DOM polling は 60s 程度がデフォルトで、瞬時の異常を逃すことがある。[SNMP](../../reference/glossary.md#term-snmp) / [gNMI](../../reference/glossary.md#term-gnmi) からの query との同期を考える。
- **port naming 変更の運用影響**: スクリプトや監視 dashboard が `Ethernet*` 直接参照だと壊れる。`PORT` table key を動的に取得する書き方に揃える。
- **dynamic add/del のリソースリーク**: ACL bind / buffer profile / counter object が delete 時に残る不具合事例がある。`show acl`、`COUNTERS_DB` を保守時に確認する。

## 将来計画 / ロードマップ

- 1.6T と coherent ZR+ への対応拡張で、`PORT` schema / SAI attribute が継続的に拡張される。
- Port naming 規約の改定は community 議題で、deprecation 期間設計が論点。
- Linecard / Module hot-swap の改善 ([12 VOQ](../12-multi-asic-voq/index.md)) と組み合わせて platform lifecycle 全体を再整理する流れ。

## 関連 RFC / 仕様書

- [CMIS spec (OIF)](https://www.oiforum.com/) — Common Management Interface Specification
- [SFF-8636 / SFF-8472](https://www.snia.org/) — QSFP / SFP+ management interface
- [IEEE 802.3 series](https://standards.ieee.org/) — Ethernet PHY/MAC
- [RFC 3635](https://datatracker.ietf.org/doc/html/rfc3635) — Ethernet-Like Interface MIB (port stats 参考)
- [RFC 8343](https://datatracker.ietf.org/doc/html/rfc8343) — IETF interface YANG (OpenConfig との比較)

## upstream 開発の最新動向

- `sonic-platform-common` / `sonic-platform-daemons` で CMIS state machine、PM (Performance Monitoring)、firmware upgrade の PR が定期的に入る。
- `pmon` docker (xcvrd / psud / thermalctld / ledd 等) の安定化と SKU 拡張が継続。
- 1.6T / 800G 対応 PR がコア component (port management, buffer model, sai profile) に分散して入っており、追跡には複数 repo を横断する必要がある。

<!-- glossary-links-injected: f7c82909d898 -->
