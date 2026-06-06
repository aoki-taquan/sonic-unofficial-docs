---
title: 発展トピック
description: PINS の data plane (P4Runtime) と管理面 (gNMI / OpenConfig) を組で読み、HashOrch HLD 乖離 / WCMP scale / PacketIO scale / standard ACL との TCAM 共存といった発展論点を扱う。
area: topics
verification: meta
last_verified: 2026-06-06
sources: []
keywords:
- PINS
- P4Runtime
- gNMI
- HashOrch
- WCMP
- PacketIO
- 発展トピック
related:
  cli:
  - show acl
  - config acl
  config_db:
  - ACL_RULE
  - ACL_TABLE
  - COPP_TRAP
  - P4RT_TABLE
  - SWITCH_HASH
  yang:
  - sonic-copp
---

# 発展トピック

[PINS](../../reference/glossary.md#term-pins) は data plane を P4Runtime で書く経路ですが、SDN コントローラから見ると **状態取得 / config push の管理面（[gNMI](../../reference/glossary.md#term-gnmi) / OpenConfig）と組で読む** のが自然です。[SONiC](../../reference/glossary.md#term-sonic) 標準の管理章と PINS の境界、および [HLD](../../reference/glossary.md#term-hld) と実装のあいだに残っている乖離をここでまとめます。

## ハンドオフ

- **概念とアーキテクチャ**は兄弟ページの [concept](concept.md) / [architecture](architecture.md) と、area HLD の [pins-hld](../../management/pins-hld.md), [p4rt-application-hld](../../management/p4rt-application-hld.md), [p4-orchagent](../../internals/p4-orchagent.md) で完結する。P4Runtime gRPC server と P4Orch の責務分担はそこに詳細がある。
- **設定とリファレンス**は [reference/cli](../../reference/cli/index.md) の `p4rt` 系コマンド (限定的)、[reference/config_db](../../reference/config-db/index.md) の `CFG_SWITCH_HASH_TABLE`, `COPP_TRAP` に集約されている。
- **本ページ**は PINS 基本 (P4Runtime → P4Orch → SAI) を押さえた読者向けに、gNMI と PINS の二系統管理、HashOrch の HLD 乖離、gRIBI 統合、WCMP scale, PacketIO scale, PINS と standard ACL の TCAM 共存などの発展領域だけを扱う。

## gNMI / OpenConfig との関係

SONiC の管理面は [YANG](../../reference/glossary.md#term-yang)（OpenConfig + sonic-yang）→ translib → ConfigDB / [sonic-mgmt](../../reference/glossary.md#term-sonic-mgmt)-framework という構成で、これとは別ラインで gNMI server が gNMI / [gNOI](../../reference/glossary.md#term-gnoi) を提供します。PINS は **データプレーンの forwarding テーブル書き換え** を P4Runtime で受けますが、port admin、interface address、[ACL](../../reference/glossary.md#term-acl) の宣言的設定といった **管理面の config / state** は gNMI 側を使うのが想定です。

つまりコントローラ側から見れば:

- **gNMI**: 管理面の config と state（OpenConfig モデル）
- **P4Runtime (PINS)**: forwarding pipeline のテーブルエントリ

の 2 系統を併用する形になります。詳細は [SONiC management framework](../../management/sonic-management-framework.md) と [gNMI usage](../../management/gnmi-usage.md) を参照してください。

## HashOrch HLD と実装の乖離

[P4RT](../../reference/glossary.md#term-p4rt) App HLD では **HashOrch（[orchagent](../../reference/glossary.md#term-orchagent) 新規追加）** がハッシュ属性を扱う前提で書かれていますが、現行 master では独立コンポーネントとしては存在せず、**既存の `SwitchOrch` が `CFG_SWITCH_HASH_TABLE_NAME` を消費し、`orchagent/switch/switch_helper.cpp` の `SWITCH_HASH_FIELD_*` ↔ `SAI_NATIVE_HASH_FIELD_*` マップ経由で SAI 属性を設定する形** になっています。PINS 側でハッシュフィールドを controller から制御したい場合、現状は SwitchOrch 経由の経路を読む必要があります。詳細は [P4RT App HLD の Discrepancy 節](../../management/p4rt-application-hld.md) を参照してください。

## ベンダ依存の境界

PacketIO の kernel 側（`genl_packet` filter 等）と、[SAI](../../reference/glossary.md#term-sai) pipeline を P4 で表す部分はベンダ実装に依存します。SONiC 本体のリポジトリで読めるのは:

- `p4rt-app` Docker と P4Runtime gRPC 部分
- `P4Orch` と各 Manager
- `copporch` / `portsorch` の generic netlink hostif と SEND_TO_INGRESS hostif

までで、その先（vendor SAI / vendor kernel driver / 実 P4 program）は SONiC リポジトリの範囲外です。`saip4ext.h` は OCP SAI submodule 側で、本リポでは展開されていません。

## 他章との接続

- 管理面の入口は [10. gNMI / gNOI / OpenConfig / YANG](../10-gnmi-openconfig/index.md) 系の章で押さえる（章番号は読み物計画側を参照）。
- ACL / mirror / counter は [07. ACL / CoPP / Mirror / Packet Action](../07-acl-copp-mirror/index.md) と同じ部品を P4Orch 側でも使うため、`acl_table_manager` / `acl_rule_manager` / `mirror_session_manager` が共通点になる。
- [ECMP](../../reference/glossary.md#term-ecmp) / next-hop の振る舞いは [04. VRF / ECMP / RIB-FIB パイプライン](../04-vrf-ecmp/index.md) で読んだものが P4Orch の `wcmp_manager` でも前提になる。

## 追加の発展トピック

- **gRIBI と PINS の組合せ**: gRIBI で RIB を直接 push しつつ、P4Runtime で forwarding 細部を補完する組合せ。Google 系 SDN controller での標準パターン。
- **P4 program upgrade**: pipeline 更新時の atomic swap。`SetForwardingPipelineConfig` の VERIFY / SAVE / COMMIT / RECONCILE_AND_COMMIT モードの違いを理解する。
- **WCMP 大規模化**: 数万 nexthop の WCMP group を扱う性能テスト。`wcmp_manager` の resize と SAI hash optimization が論点。
- **PacketIO scale**: punt → CPU → controller の経路で、PacketIO rate が [CoPP](../../reference/glossary.md#term-copp) / hostif queue / gRPC stream の各層で制限される。
- **PINS と SONiC standard ACL の共存**: 同じ [ASIC](../../reference/glossary.md#term-asic) [TCAM](../../reference/glossary.md#term-tcam) を分け合うため、resource allocation を deployment で固定する必要がある。

## 既知の制約と回避方法

- **HashOrch HLD と現実の差分**: HLD どおりの `HashOrch` は無く `SwitchOrch` 経由。controller 側で HashOrch 名前を前提にすると壊れる。
- **vendor SAI 依存の透明性**: P4 program と SAI pipeline の対応は vendor 依存で、SONiC リポだけ読んでも全体像にならない。vendor SDK docs を併読する。
- **PacketIO の遅延**: punt rate が高いと controller 到達まで数 ms 級遅延が出る。重要 control trap は CoPP の専用 policer に分離する。
- **gNMI と P4RT の整合性**: gNMI で port を down にした場合、P4RT 側 table 状態は残る。controller 側で両 API を協調させるアプリ層が必要。

## 将来計画 / ロードマップ

- PINS のコミュニティリリース整理と、PINS-only / PINS+SONiC standard 構成の使い分けガイドライン整備。
- gRIBI / P4RT / gNMI を統一した SDN controller framework (Google PINS, ONF Stratum 系) との互換性向上。
- vendor SAI と P4 model の bridging を SAI 標準で固める作業が継続。

## 関連 RFC / 仕様書

- [P4 Language Specification](https://p4.org/specs/) — P4_16 spec
- [P4Runtime Specification](https://p4.org/p4-spec/p4runtime/) — Controller-to-data plane API
- [OpenConfig models](https://github.com/openconfig/public)
- [gRIBI Specification](https://github.com/openconfig/gribi)
- [Stratum project](https://opennetworking.org/stratum/) — P4Runtime + gNMI + gNOI 標準実装

## upstream 開発の最新動向

- `sonic-pins` (and `pins-infra`) で Manager 群の機能拡張と test coverage 拡充の PR が継続。
- `sonic-swss` で P4Orch と既存 orch (SwitchOrch, AclOrch) の境界整理 PR が散発。
- P4Runtime gRPC server (`p4rt-app`) の認証・TLS 周りの強化、PacketIO scale 改善の PR が議題化。

## トラブルシュート観点

- `Write` RPC が `INVALID_ARGUMENT` を返すときは、(1) P4Info とコントローラ側の match-field 解釈一致、(2) `P4RT_TABLE` に既存 entry と key 衝突、(3) `wcmp_manager` の group ID 範囲外、を確認する。
- PacketIO で controller に届かない場合、(1) `CoPP` の `trap_group` が PINS 用 queue を保有、(2) `hostif_trap` が SAI 側で attach、(3) gRPC stream の back-pressure (controller 側で stall) を順に切り分け。
- HashOrch 期待で動かない controller は、`CFG_SWITCH_HASH_TABLE` 経由で SwitchOrch が処理する現実に合わせて、`/set_hash` style の RPC ではなく gNMI Set で `openconfig-load-balancing` を投入する形に書き換える。

## 検証パスとラボ要件

- `sonic-pins` の `pins_ondatra` (Google OnDatra fork) が integration test として available。[VS](../../reference/glossary.md#term-vs) lab で P4Orch を起こし、controller 側で P4Info push → table entry write → PacketIO の往復を観察できる。
- P4Orch と SwitchOrch / AclOrch の境界が不明確なとき、[ASIC_DB](../../reference/glossary.md#term-asic_db) を `redis-cli MONITOR` で観察すると、両 orch が同じ SAI object に対して update を出すケースが識別できる。

## 関連ページ (追補)

- [PINS HLD](../../management/pins-hld.md)
- [P4Runtime application HLD](../../management/p4rt-application-hld.md)
- [P4Runtime read cache HLD](../../management/p4rt-read-cache-hld.md)
- [P4 Orchagent](../../internals/p4-orchagent.md)
- [SONiC management framework](../../management/sonic-management-framework.md)
- [gNMI usage](../../management/gnmi-usage.md)
- [gNMI master arbitration HLD](../../management/gnmi-master-arbitration-hld.md)
- [SONiC gNMI server interface design](../../management/sonic-gnmi-server-interface-design.md)
- [04 VRF / ECMP: nexthop と WCMP の前提](../04-vrf-ecmp/index.md)
- [07 ACL / CoPP / Mirror: P4Orch と AclOrch の共通部品](../07-acl-copp-mirror/index.md)
- [10 gNMI / OpenConfig: 管理面 API との二系統運用](../10-gnmi-openconfig/index.md)

<!-- glossary-links-injected: 9fb3fca99a59 -->
