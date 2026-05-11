---
title: 発展トピック
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/management/sonic-management-framework.md
  - docs/management/gnmi-usage.md
  - docs/management/p4rt-application-hld.md
---

# 発展トピック

PINS は data plane を P4Runtime で書く経路ですが、SDN コントローラから見ると **状態取得 / config push の管理面（gNMI / OpenConfig）と組で読む** のが自然です。SONiC 標準の管理章と PINS の境界、および HLD と実装のあいだに残っている乖離をここでまとめます。

## gNMI / OpenConfig との関係

SONiC の管理面は YANG（OpenConfig + sonic-yang）→ translib → ConfigDB / sonic-mgmt-framework という構成で、これとは別ラインで gNMI server が gNMI / gNOI を提供します。PINS は **データプレーンの forwarding テーブル書き換え** を P4Runtime で受けますが、port admin、interface address、ACL の宣言的設定といった **管理面の config / state** は gNMI 側を使うのが想定です。

つまりコントローラ側から見れば:

- **gNMI**: 管理面の config と state（OpenConfig モデル）
- **P4Runtime (PINS)**: forwarding pipeline のテーブルエントリ

の 2 系統を併用する形になります。詳細は [SONiC management framework](../../management/sonic-management-framework.md) と [gNMI usage](../../management/gnmi-usage.md) を参照してください。

## HashOrch HLD と実装の乖離

P4RT App HLD では **HashOrch（orchagent 新規追加）** がハッシュ属性を扱う前提で書かれていますが、現行 master では独立コンポーネントとしては存在せず、**既存の `SwitchOrch`（`switch_helper.cpp` の `SWITCH_HASH_FIELD_*` マップ）が `CFG_SWITCH_HASH_TABLE_NAME` 経由で扱う形** になっています。PINS 側でハッシュフィールドを controller から制御したい場合、現状は SwitchOrch 経由の経路を読む必要があります。詳細は [P4RT App HLD の Discrepancy 節](../../management/p4rt-application-hld.md) を参照してください。

## ベンダ依存の境界

PacketIO の kernel 側（`genl_packet` filter 等）と、SAI pipeline を P4 で表す部分はベンダ実装に依存します。SONiC 本体のリポジトリで読めるのは:

- `p4rt-app` Docker と P4Runtime gRPC 部分
- `P4Orch` と各 Manager
- `copporch` / `portsorch` の generic netlink hostif と SEND_TO_INGRESS hostif

までで、その先（vendor SAI / vendor kernel driver / 実 P4 program）は SONiC リポジトリの範囲外です。`saip4ext.h` は OCP SAI submodule 側で、本リポでは展開されていません。

## 他章との接続

- 管理面の入口は [10. gNMI / gNOI / OpenConfig / YANG](../../topics/index.md) 系の章で押さえる（章番号は読み物計画側を参照）。
- ACL / mirror / counter は [07. ACL / CoPP / Mirror / Packet Action](../07-acl-copp-mirror/index.md) と同じ部品を P4Orch 側でも使うため、`acl_table_manager` / `acl_rule_manager` / `mirror_session_manager` が共通点になる。
- ECMP / next-hop の振る舞いは [04. VRF / ECMP / RIB-FIB パイプライン](../04-vrf-ecmp/index.md) で読んだものが P4Orch の `wcmp_manager` でも前提になる。
