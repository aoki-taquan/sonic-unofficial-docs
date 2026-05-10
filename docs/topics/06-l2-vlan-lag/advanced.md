---
title: L2 発展トピック
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/switching/openconfig-support-for-portchannel-aggregate-interface.md
  - docs/switching/add-support-for-vlan-interface-using-openconfig-yang.md
  - docs/switching/lag-on-distributed-voq-system.md
  - docs/switching/wake-on-lan-in-sonic.md
---

# L2 発展トピック

このページは、通常の VLAN / PortChannel / MC-LAG 設計から一歩外れる話題の入口です。OpenConfig は管理 API 章、distributed VOQ LAG は VOQ 章、Wake-on-LAN は運用ツールとしても読む対象です。

## OpenConfig VLAN / PortChannel

SONiC 独自 CLI / CONFIG_DB ではなく、REST / gNMI で OpenConfig YANG モデルを使う場合は、transformer が OpenConfig tree と SONiC の既存 CONFIG_DB を対応付けます。

PortChannel では `openconfig-interfaces` と `openconfig-if-aggregate` を使い、Ethernet 側の `aggregate-id` で member を表現し、PortChannel 側の `aggregation/config/min-links` で集約条件を表現します。

VLAN では `openconfig-vlan` の `switched-vlan` と `routed-vlan` を使います。`switched-vlan` は access / trunk と VLAN member、`routed-vlan` は VLAN interface の IP 設定に対応します。CONFIG_DB の `VLAN` / `VLAN_MEMBER` / `VLAN_INTERFACE` はそのまま使われ、スキーマ自体を増やす設計ではありません。

## Distributed VOQ LAG

分散 VOQ シャシでは、各 ASIC が独立した SONiC インスタンスとして動作し、ASIC 間共有情報を `CHASSIS_APP_DB` に載せます。LAG は全 ASIC から一貫して見える必要があるため、`SYSTEM_LAG_TABLE` と `SYSTEM_LAG_MEMBER_TABLE` で system-wide な LAG 情報を共有します。

重要な制約は、メンバが複数 ASIC を跨ぐ LAG はサポートしないことです。各 ASIC のローカル LAG は通常どおり `PORTCHANNEL` / `PORTCHANNEL_MEMBER` で設定され、他 ASIC から見える remote LAG は swss / syncd 側で扱われます。

通常の L2 章では「PortChannel の作り方」までを扱い、VOQ 章では「system_lag_id、CHASSIS_APP_DB、remote LAG programming」を扱う、と分けて読むのが自然です。

## Wake-on-LAN

Wake-on-LAN は L2 frame または UDP payload で Magic Packet を送る機能です。VLAN / LAG の forwarding 設計そのものではありませんが、スイッチを Magic Packet の送信元として使うため、L2 到達性やブロードキャストの扱いと関係します。

現行ページでは HLD と実装の差分があり、CLI は Rust 実装、gNOI service は取り込み未確認と整理されています。運用ツールとして使う場合は、対象 NIC の WoL 受信設定、送信方式、ブロードキャスト / ルーティング境界を別途確認します。

## 他章との境界

| 話題 | この章で扱う範囲 | 主に読む章 |
|---|---|---|
| gNMI / REST | OpenConfig がどの L2 テーブルに写るか | 管理 API |
| Distributed VOQ LAG | 通常 LAG との違いと制約 | VOQ / Chassis |
| Dual-ToR MC-LAG | MC-LAG の基礎と ICCP 観測点 | Dual-ToR |
| WoL | L2 到達性と Magic Packet の概要 | 運用 / 管理 |

## 関連ページ

- [PortChannel OpenConfig YANG サポート](../../switching/openconfig-support-for-portchannel-aggregate-interface.md)
- [VLAN interface OpenConfig YANG 対応](../../switching/add-support-for-vlan-interface-using-openconfig-yang.md)
- [分散 VOQ シャシでの LAG](../../switching/lag-on-distributed-voq-system.md)
- [Wake-on-LAN](../../switching/wake-on-lan-in-sonic.md)
