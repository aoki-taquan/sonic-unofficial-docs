---
title: L2 設定パターン
description: L2 設定パターン — ここでは、個別 CLI の全引数ではなく、L2 を組むときの代表的な順序を示します。詳細なオプション、制約、実装との乖離は各参照ページで確認してください。
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
related:
  cli:
  - config vlan
  - config portchannel
  - config interface
  - show vlan
  - show ip
  - show interfaces
  - show arp
  config_db:
  - PORTCHANNEL
  - PORTCHANNEL_MEMBER
  - VLAN
  - VLAN_MEMBER
  - VLAN_SUB_INTERFACE
  - INTERFACE
  - PORT
  - VLAN_INTERFACE
  - PORTCHANNEL_INTERFACE
  yang:
  - sonic-portchannel
  - sonic-vlan
  - sonic-vlan-sub-interface
---

# L2 設定パターン

ここでは、個別 CLI の全引数ではなく、L2 を組むときの代表的な順序を示します。詳細なオプション、制約、実装との乖離は各参照ページで確認してください。

## VLAN access port を作る

基本形は [VLAN](../../reference/glossary.md#term-vlan) を作り、物理ポートを untagged member として入れます。

```bash
config vlan add 100
config vlan member add 100 Ethernet0 -u
```

[CONFIG_DB](../../reference/glossary.md#term-config_db) では次の関係になります。

```text
VLAN|Vlan100
  vlanid: 100

VLAN_MEMBER|Vlan100|Ethernet0
  tagging_mode: untagged
```

注意点は、同じ物理ポートを L3 `INTERFACE`、[PortChannel](../../reference/glossary.md#term-portchannel) member、別 VLAN の untagged member として同時に使えないことです。`config vlan member add` は既存の `PORT` / `PORTCHANNEL`、mirror destination、routed mode、PortChannel 所属などを確認します。

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

`VLAN_INTERFACE` は属性ロウと IP prefix ロウを持ちます。proxy [ARP](../../reference/glossary.md#term-arp) は `config vlan proxy_arp <vid> enabled|disabled` で `VLAN_INTERFACE|Vlan<vid>` の `proxy_arp` を切り替えます。

## PortChannel を L2 trunk にする

PortChannel は先に [LAG](../../reference/glossary.md#term-lag) 本体を作り、物理メンバを入れ、その PortChannel を VLAN member にします。

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

`PORTCHANNEL` の `min_links` は operational up の判定に影響します。`fallback` は [LACP](../../reference/glossary.md#term-lacp) PDU 不達時の扱いに関わるため、相手装置との設計を合わせてから使います。

## Sub-port を作る

Sub-port は VLAN bridge domain ではなく、親 interface 上の dot1q tag を L3 interface として扱います。

```bash
config subinterface add Ethernet0.100
config interface ip add Ethernet0.100 198.51.100.1/31
```

命名規則や実装確認状況は [Sub-port Interface HLD](../../architecture/sonic-sub-port-interface-high-level-design.md) と [VLAN_SUB_INTERFACE](../../reference/config-db/vlan-sub-interface.md) を参照してください。親は物理ポートまたは PortChannel です。

## TPID を変える

TPID は VLAN tag を識別する EtherType です。[SONiC](../../reference/glossary.md#term-sonic) では `0x8100`、`0x9100`、`0x9200`、`0x88A8` が対象です。物理ポートと LAG の両方に関係しますが、[ASIC](../../reference/glossary.md#term-asic) capability に依存します。

```bash
config interface tpid Ethernet64 0x9200
config interface tpid PortChannel0002 0x9200
```

TPID は Q-in-Q 全体を提供する機能ではなく、「どの TPID を VLAN tag として認識するか」を設定する機能として扱います。

## 典型シナリオ 1: サーバ access port (VLAN 100 untagged)

最も基本的な構成。

### CLI

```bash
sudo config vlan add 100
sudo config vlan member add 100 Ethernet0 -u
```

### CONFIG_DB JSON

```json
{
  "VLAN": {
    "Vlan100": {
      "vlanid": "100"
    }
  },
  "VLAN_MEMBER": {
    "Vlan100|Ethernet0": {
      "tagging_mode": "untagged"
    }
  }
}
```

### 確認

```bash
show vlan brief
```

```text
+-----------+-----------------+-----------------+----------------+-------------+
|   VLAN ID | IP Address      | Ports           | Port Tagging   | Proxy ARP   |
+===========+=================+=================+================+=============+
|       100 |                 | Ethernet0       | untagged       | disabled    |
+-----------+-----------------+-----------------+----------------+-------------+
```

## 典型シナリオ 2: LACP LAG を作って trunk として上位 switch に上げる

```bash
sudo config portchannel add PortChannel10 --min-links 1 --fallback false
sudo config portchannel member add PortChannel10 Ethernet0
sudo config portchannel member add PortChannel10 Ethernet4
sudo config vlan member add 100 PortChannel10
sudo config vlan member add 200 PortChannel10
```

CONFIG_DB:

```json
{
  "PORTCHANNEL": {
    "PortChannel10": {
      "admin_status": "up",
      "mtu": "9100",
      "min_links": "1",
      "fallback": "false",
      "lacp_key": "auto"
    }
  },
  "PORTCHANNEL_MEMBER": {
    "PortChannel10|Ethernet0": { "NULL": "NULL" },
    "PortChannel10|Ethernet4": { "NULL": "NULL" }
  },
  "VLAN_MEMBER": {
    "Vlan100|PortChannel10": { "tagging_mode": "tagged" },
    "Vlan200|PortChannel10": { "tagging_mode": "tagged" }
  }
}
```

確認:

```bash
show interfaces portchannel
```

```text
  No.  Team Dev         Protocol     Ports
-----  ---------------  -----------  ---------------------------
   10  PortChannel10    LACP(A)(Up)  Ethernet4(S) Ethernet0(S)
```

`(S)` selected、`(D)` deselected。`Up` 状態でないと VLAN member であっても traffic は流れません。

## 典型シナリオ 3: VLAN interface に IP を付けて SVI として使う

```bash
sudo config vlan add 100
sudo config vlan member add 100 Ethernet0 -u
sudo config vlan member add 100 Ethernet4 -u
sudo config interface ip add Vlan100 192.168.100.1/24
```

```json
{
  "VLAN_INTERFACE": {
    "Vlan100": { "NULL": "NULL" },
    "Vlan100|192.168.100.1/24": { "NULL": "NULL" }
  }
}
```

確認:

```bash
show ip interfaces
show vlan brief
```

`show ip interfaces` の出力で `Vlan100` に IP が付き、`Oper` が `up` になれば SVI として動作。`down` の場合は VLAN 配下に operational up な member が無い可能性が高いです (member が全 link down)。

## sonic-cfggen で部分パッチを当てる

deployment template ではなく、運用中に [config_db.json](../../reference/glossary.md#term-config_db.json) の小規模変更を行うときの典型パターン:

```bash
cat > /tmp/vlan_patch.json <<'EOF'
{
  "VLAN": { "Vlan300": { "vlanid": "300" } },
  "VLAN_MEMBER": { "Vlan300|Ethernet8": { "tagging_mode": "tagged" } }
}
EOF
sudo sonic-cfggen -a "$(cat /tmp/vlan_patch.json)" --write-to-db
sudo config save -y
```

`config save -y` を打たないと reboot で揮発します。

## よくある設定エラーと対処

`sonic-utilities/config/vlan.py` と `config/main.py` の `ctx.fail()` から抜粋:

| エラーメッセージ | 原因 | 対処 |
|---|---|---|
| `Invalid VLAN ID <vid> (2-4094)` | 1 や 4095 以上を指定 | 範囲内に修正 (1 は default VLAN で reserved) |
| `<vlan> is default VLAN` | Vlan1 を作成/削除 | default VLAN は対象外 |
| `<vlan> already exists.` | 二重作成 | 既存を確認 |
| `<vlan> does not exist` | 未作成の VLAN への member add | 先に `config vlan add` |
| `VLAN ID <vid> can not be removed. First remove all members assigned to this VLAN.` | member 残存で VLAN 削除 | 先に member を削除 |
| `<vlan> can not be removed. First remove IP addresses assigned to this VLAN` | VLAN_INTERFACE に IP あり | 先に `config interface ip remove` |
| `<port> cannot have more than one untagged Vlan.` | 同一物理 port を 2 VLAN の untagged に追加 | tagged にするか、片方を削除 |
| `<port> is already a member of <vlan>` | 同じ port を二重追加 | 既存 member を確認 |
| `<port> is configured as mirror destination port` | mirror dst の port を VLAN に入れた | mirror session を先に解除 |
| `<portchannel> already exists!` | LAG 二重作成 | 既存を確認 |
| `<portchannel> is invalid! name should have prefix 'PortChannel' and suffix '<digits>'` | 命名規則違反 | `PortChannel<NNNN>` 形式に従う |
| `Error: Portchannel <name> contains members. Remove members before deleting Portchannel!` | member 残存で LAG 削除 | 先に member 削除 |
| `<port> has subinterfaces configured` | sub-port 親を VLAN member に入れた | 先に subinterface を削除 |
| `<port> Interface configured as VLAN_MEMBER under vlan : <vid>` | LAG member 化したい port が VLAN member | 先に VLAN_MEMBER 解除 |
| `<port> Interface is already member of <portchannel>` | LAG 二重所属 | 既存 LAG から削除 |
| `Port speed of <port> is different than the other members of the portchannel <name>` | LAG member の speed 不一致 | 同一 speed の port を揃える |

LAG 削除順序: `VLAN_MEMBER (LAG)` → `PORTCHANNEL_MEMBER` → `PORTCHANNEL`。途中をスキップすると上記の `contains members` などで止まります。

## 関連ページ

- [CLI: config vlan](../../reference/cli/config-vlan.md)
- [CLI: config portchannel](../../reference/cli/config-portchannel.md)
- [CLI: config interface](../../reference/cli/config-interface.md)
- [CONFIG_DB: VLAN](../../reference/config-db/vlan.md)
- [CONFIG_DB: VLAN_MEMBER](../../reference/config-db/vlan-member.md)
- [CONFIG_DB: VLAN_INTERFACE](../../reference/config-db/vlan-interface.md)
- [CONFIG_DB: PORTCHANNEL](../../reference/config-db/portchannel.md)
- [CONFIG_DB: PORTCHANNEL_MEMBER](../../reference/config-db/portchannel-member.md)
- [CONFIG_DB: PORTCHANNEL_INTERFACE](../../reference/config-db/portchannel-interface.md)
- [TPID 設定 HLD](../../platform/sonictpidsettinghld1.md)

<!-- glossary-links-injected: ec18b66e3507 -->
