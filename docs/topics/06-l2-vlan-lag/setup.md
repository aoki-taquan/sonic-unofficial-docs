---
title: L2 設定パターン
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/reference/cli/config-vlan.md
  - docs/reference/cli/config-portchannel.md
  - docs/reference/cli/config-interface.md
  - docs/reference/config-db/vlan.md
  - docs/reference/config-db/vlan-member.md
  - docs/reference/config-db/vlan-interface.md
  - docs/reference/config-db/vlan-sub-interface.md
  - docs/reference/config-db/portchannel.md
  - docs/reference/config-db/portchannel-member.md
  - docs/reference/config-db/portchannel-interface.md
  - docs/reference/config-db/port.md
  - docs/reference/config-db/interface.md
  - docs/reference/yang/sonic-vlan.md
  - docs/reference/yang/sonic-vlan-sub-interface.md
  - docs/reference/yang/sonic-portchannel.md
  - docs/reference/yang/sonic-port.md
  - docs/architecture/sonic-sub-port-interface-high-level-design.md
  - docs/platform/sonictpidsettinghld1.md
---

# L2 設定パターン

ここでは、個別 CLI の全引数ではなく、L2 を組むときの代表的な順序を示します。詳細なオプション、制約、実装との乖離は各参照ページで確認してください。

## VLAN access port を作る

基本形は VLAN を作り、物理ポートを untagged member として入れます。

```bash
config vlan add 100
config vlan member add 100 Ethernet0 -u
```

CONFIG_DB では次の関係になります。

```text
VLAN|Vlan100
  vlanid: 100

VLAN_MEMBER|Vlan100|Ethernet0
  tagging_mode: untagged
```

注意点は、同じ物理ポートを L3 `INTERFACE`、PortChannel member、別 VLAN の untagged member として同時に使えないことです。`config vlan member add` は既存の `PORT` / `PORTCHANNEL`、mirror destination、routed mode、PortChannel 所属などを確認します。

## VLAN trunk を作る

Tagged VLAN を複数通す場合は、同じ port または PortChannel を複数 VLAN の tagged member にします。

```bash
config vlan add 100
config vlan add 200
config vlan member add 100 Ethernet0
config vlan member add 200 Ethernet0
```

複数 VLAN の一括 add / del は実装状況と CLI 世代で差分があるため、[config vlan](../../reference/cli/config-vlan.md) と [Switchport モードと VLAN CLI 拡張](../../switching/switch-port-modes-and-vlan-cli-enhancement.md) の両方を確認してください。

## VLAN interface を作る

VLAN を gateway として使う場合は、VLAN を作成し、必要な member を入れたうえで VLAN interface に IP を付けます。

```bash
config vlan add 100
config vlan member add 100 Ethernet0 -u
config interface ip add Vlan100 192.0.2.1/24
```

`VLAN_INTERFACE` は属性ロウと IP prefix ロウを持ちます。proxy ARP は `config vlan proxy_arp <vid> enabled|disabled` で `VLAN_INTERFACE|Vlan<vid>` の `proxy_arp` を切り替えます。

## PortChannel を L2 trunk にする

PortChannel は先に LAG 本体を作り、物理メンバを入れ、その PortChannel を VLAN member にします。

```bash
config portchannel add PortChannel10 --min-links 1 --fast-rate false
config portchannel member add PortChannel10 Ethernet0
config portchannel member add PortChannel10 Ethernet4
config vlan add 100
config vlan member add 100 PortChannel10
```

`config portchannel member add` は、対象物理ポートが IP interface、VLAN member、sub-interface の親、別 PortChannel member になっていないかを確認します。LAG を VLAN member から消す前に PortChannel 本体を削除しようとすると拒否されます。

## PortChannel を L3 interface にする

PortChannel を routed L3 として使う場合は `PORTCHANNEL_INTERFACE` に IP を付けます。VLAN member には入れません。

```bash
config portchannel add PortChannel10
config portchannel member add PortChannel10 Ethernet0
config interface ip add PortChannel10 192.0.2.0/31
```

`PORTCHANNEL` の `min_links` は operational up の判定に影響します。`fallback` は LACP PDU 不達時の扱いに関わるため、相手装置との設計を合わせてから使います。

## Sub-port を作る

Sub-port は VLAN bridge domain ではなく、親 interface 上の dot1q tag を L3 interface として扱います。

```bash
config subinterface add Ethernet0.100
config interface ip add Ethernet0.100 198.51.100.1/31
```

命名規則や実装確認状況は [Sub-port Interface HLD](../../architecture/sonic-sub-port-interface-high-level-design.md) と [VLAN_SUB_INTERFACE](../../reference/config-db/vlan-sub-interface.md) を参照してください。親は物理ポートまたは PortChannel です。

## TPID を変える

TPID は VLAN tag を識別する EtherType です。SONiC では `0x8100`、`0x9100`、`0x9200`、`0x88A8` が対象です。物理ポートと LAG の両方に関係しますが、ASIC capability に依存します。

```bash
config interface tpid Ethernet64 0x9200
config interface tpid PortChannel0002 0x9200
```

TPID は Q-in-Q 全体を提供する機能ではなく、「どの TPID を VLAN tag として認識するか」を設定する機能として扱います。

## 関連ページ

- [CLI: config vlan](../../reference/cli/config-vlan.md)
- [CLI: config portchannel](../../reference/cli/config-portchannel.md)
- [CLI: config interface](../../reference/cli/config-interface.md)
- [CONFIG_DB: VLAN_MEMBER](../../reference/config-db/vlan-member.md)
- [CONFIG_DB: PORTCHANNEL_MEMBER](../../reference/config-db/portchannel-member.md)
- [TPID 設定 HLD](../../platform/sonictpidsettinghld1.md)
