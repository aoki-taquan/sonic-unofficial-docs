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

## ハンドオフ

- **概念とアーキテクチャ**は本章の [concept](concept.md) / [architecture](architecture.md) と、area HLD の [1-6t-support-in-sonic](../../platform/1-6t-support-in-sonic.md), [cmis-and-c-cmis-support-for-zr](../../platform/cmis-and-c-cmis-support-for-zr.md), [fec-flr-support-in-sonic](../../platform/fec-flr-support-in-sonic.md) で完結する。pmon daemon 群 (xcvrd, psud, thermalctld, ledd) の責務分担はそこに詳細がある。
- **設定とリファレンス**は [reference/cli](../../reference/cli/index.md) の `config interface` / `show interfaces transceiver` 系、[reference/config_db/PORT](../../reference/config-db/index.md), `INTERFACE`, `BREAKOUT_CFG` に集約されている。
- **本ページ**は基本 port lifecycle を押さえた読者向けに、1.6T 対応, port naming 改革, dynamic add/del, CMIS 5.x, optics firmware, breakout dynamic などの発展領域だけを扱う。

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

- **CMIS 5.x optics**: 400G/800G ZR / ZR+ など coherent optics の管理は CMIS で行い、[SONiC](../../reference/glossary.md#term-sonic) `xcvrd` が state machine を実装する。Application select、re-provisioning、firmware download などが要点。
- **Optics firmware upgrade**: `gnoi.os.Install` の概念に近く、optics 内 firmware を host から書き換える。途中で reboot を挟まない hot upgrade 対応が [ASIC](../../reference/glossary.md#term-asic) / optics で異なる。
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

## トラブルシュート観点

- link up しない場合、(1) FEC 設定 (`port admin_status up` 時の `fec` 値) と peer 側設定一致、(2) `xcvrd` の DOM 値で受光レベルが reference 内、(3) `STATE_DB|TRANSCEIVER_INFO` の vendor/part が認識できているか、を順に確認する。
- breakout 後に古い port が残るときは、`config_db.json` 上の `PORT|Ethernet*` と `BREAKOUT_CFG` 整合を確認し、`config reload` で再同期する。
- CMIS module の application select 失敗は `pmon` docker の `xcvrd` log で `CMIS_REINIT` の繰り返しが手がかりになる。module の host management 設定 (`HOST_MGMT_INTF`) と CMIS profile の MaxPower mismatch が原因のことが多い。

## 検証パスとラボ要件

- 1.6T サポートは現状 vendor SDK + 対応 SKU が前提で、community VS lab では速度シミュレーションのみ。SAI profile の `port-config.ini` を実機準拠で用意して機能テストする流れになる。
- dynamic breakout の検証は `sonic-mgmt` の `platform/test_port_toggle.py` 系で再現可能。breakout 時の ACL/QoS reprovision が抜けると次の機能テストで露見する。

## 関連ページ (追補)

- [CMIS and C-CMIS support for ZR](../../platform/cmis-and-c-cmis-support-for-zr.md)
- [Custom SI settings for CMIS modules](../../platform/custom-si-settings-for-cmis-modules.md)
- [Enhancement of CMIS module management](../../management/enhancement-of-cmis-module-management.md)
- [FEC FLR support in SONiC](../../platform/fec-flr-support-in-sonic.md)
- [Automatic module provisioning for chassis](../../platform/automatic-module-provisioning-for-chassis.md)
- [Enhancements to add or del ports dynamically](../../acl-qos/enhancements-to-add-or-del-ports-dynamically.md)
- [1.6T support in SONiC](../../platform/1-6t-support-in-sonic.md)
- [SONiC port naming convention change](../../platform/sonic-port-naming-convention-change.md)
- [Enhanced LPO debug registers HLD](../../platform/enhanced-lpo-debug-registers-hld.md)
- [Global platform-specific psuutil class instance](../../platform/global-platform-specific-psuutil-class-instance.md)
- [Handle ASIC SDK health event](../../platform/handle-asic-sdk-health-event.md)
- [06 L2 / VLAN / LAG: port を VLAN / LAG メンバとして組み込む](../06-l2-vlan-lag/index.md)
- [07 ACL / CoPP / Mirror: port lifecycle と ACL bind の付け替え](../07-acl-copp-mirror/index.md)
- [12 Multi-ASIC / VOQ: chassis 内 module hot-swap](../12-multi-asic-voq/index.md)

<!-- glossary-links-injected: ec18b66e3507 -->
