---
title: L2 機能の考え方
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/switching/layer-2-forwarding-enhancements.md
  - docs/switching/sonic-basic-l2-mode-test-plan.md
  - docs/switching/switch-port-modes-and-vlan-cli-enhancement.md
  - docs/reference/config-db/vlan.md
  - docs/reference/config-db/vlan-member.md
  - docs/reference/config-db/vlan-interface.md
  - docs/reference/config-db/port.md
  - docs/reference/config-db/portchannel.md
  - docs/architecture/sonic-sub-port-interface-high-level-design.md
---

# L2 機能の考え方

SONiC の L2 を読むときは、まず「どの interface がどの forwarding domain に属するか」と「その interface を L2 として使うのか、L3 として使うのか」を分けると理解しやすくなります。

## 最初に押さえる単位

| 単位 | 主な CONFIG_DB | 役割 |
|---|---|---|
| 物理ポート | `PORT` | Ethernet ポートの速度、MTU、admin state、switchport mode、TPID など |
| VLAN | `VLAN` | L2 broadcast domain の定義。名前は `Vlan<id>` |
| VLAN メンバ | `VLAN_MEMBER` | `PORT` または `PORTCHANNEL` を VLAN に tagged / untagged で所属させる |
| VLAN interface | `VLAN_INTERFACE` | VLAN を L3 SVI として使い、IP / VRF / proxy ARP などを持たせる |
| PortChannel | `PORTCHANNEL` / `PORTCHANNEL_MEMBER` | 複数物理ポートを LACP LAG として束ねる |
| PortChannel interface | `PORTCHANNEL_INTERFACE` | PortChannel を L3 interface として使う |
| Sub-port | `VLAN_SUB_INTERFACE` | 親 `Ethernet` / `PortChannel` 上に `.<vlan-id>` の L3 sub-interface を作る |

VLAN は L2 の入れ物です。`VLAN_MEMBER` はその入れ物にポートを入れる設定です。`VLAN_INTERFACE` は同じ VLAN 名を L3 の gateway interface として扱う設定で、L2 メンバとは別の役割を持ちます。

## Access / trunk / routed の見方

Switchport mode は、ポートや PortChannel をどう扱うかを運用者に明示するための概念です。

| モード | 期待される使い方 |
|---|---|
| `routed` | L3 interface として IP を持たせる。VLAN_MEMBER には入れない |
| `access` | 1 つの VLAN に untagged で所属させる |
| `trunk` | 1 つ以上の VLAN に tagged、必要なら native VLAN に untagged で所属させる |

実装上の中心は `PORT.<name>.mode` または `PORTCHANNEL.<name>.mode` です。詳細な CLI と実装差分は [Switchport モードと VLAN CLI 拡張](../../switching/switch-port-modes-and-vlan-cli-enhancement.md) を参照してください。

## VLAN interface と sub-port の違い

VLAN interface は、VLAN 全体に対する L3 gateway です。`Vlan100` に `192.0.2.1/24` を持たせると、その VLAN に属する member port から来る端末の gateway になります。

Sub-port は、親 interface 上の dot1q tag を L3 RIF として直接扱います。`Ethernet0.100` や `PortChannel100.20` のように、VLAN bridge domain へ入れるのではなく、親 interface + VLAN ID の組を L3 interface にします。既存 HLD では sub-port を L2 bridge port として使うことはスコープ外です。

## LAG と MC-LAG の境界

通常の PortChannel は 1 台のスイッチ内で複数の物理ポートを束ねます。SONiC では `PORTCHANNEL` と `PORTCHANNEL_MEMBER` を `teammgrd` が読み、Linux `teamd` と orchagent の LAG programming へつなぎます。

MC-LAG は 2 台のスイッチが peer になり、下流ホストから 1 つの LAG に見えるように協調します。通常 LAG の設定に加えて、ICCP セッション、peer-link、MCLAG domain、remote MAC / ARP / ND 同期、isolation group、unique IP といった制御面が必要です。通常の PortChannel の延長ではなく、「2 台の制御面を同期する仕組み」として読むのが安全です。

## FDB、STP、storm control の位置づけ

FDB は VLAN 内で MAC address と出力 port を結び付ける学習テーブルです。ポート down、VLAN member 削除、STP topology change、PortChannel down では FDB flush の範囲が変わります。

STP / MSTP は L2 ループを避ける制御面です。Storm control はループや誤接続で BUM traffic が増えたときに物理ポート単位でレート制限します。Link event damping はポート up/down の連続発生を抑え、L2 / L3 の制御面へイベントを流しすぎないための保護です。

## 関連ページ

- [L2 Forwarding 強化](../../switching/layer-2-forwarding-enhancements.md)
- [Basic L2 モードテストプラン](../../switching/sonic-basic-l2-mode-test-plan.md)
- [Switchport モードと VLAN CLI 拡張](../../switching/switch-port-modes-and-vlan-cli-enhancement.md)
- [Sub-port Interface HLD](../../architecture/sonic-sub-port-interface-high-level-design.md)
