---
title: MCLAG Enhancements 運用（CLI / 設定手順 / 確認 / トラブルシュート）
description: MCLAG Enhancements の運用手順。click / KLISH の両 CLI、典型的な設定例、show / redis / mclagdctl での確認、よくある不具合と切り分け手順を扱う。
area: switching
verification: code-verified
last_verified: 2026-05-10
page_kind: split-child
sources:
- repo: sonic-net/SONiC
  path: doc/mclag/MCLAG_Enhancements_HLD.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - MCLAG_DOMAIN
  - MCLAG_INTERFACE
  - MCLAG_UNIQUE_IP
  - VLAN
  - VLAN_MEMBER
  cli:
  - config mclag
  - show mclag
  - mclagdctl
  - config portchannel
  - config vlan
  - show mac
  yang:
  - sonic-mclag
  - sonic-portchannel
  - sonic-vlan
---

# MCLAG Enhancements 運用

このページは [MCLAG Enhancements（概要ハブ）](mclag-enhancements.md) の派生で、**CLI / 設定手順 / 確認 / トラブルシュート** に絞る。概念は [mclag-enhancements-concepts.md](mclag-enhancements-concepts.md)、内部実装は [mclag-enhancements-internals.md](mclag-enhancements-internals.md) を参照。

!!! success "裏取りステータス: code-verified"
    CLI シンタックスは HLD §3.8 と現行 `sonic-utilities` 由来 click コマンドで確認。テーブル名は `sonic-swss-common/common/schema.h` で確認。

## 1. 前提

- 両 peer で **同じ [PortChannel](../reference/glossary.md#term-portchannel) 名** を [MCLAG](../reference/glossary.md#term-mclag) メンバとして用意する
- L2 MCLAG では `peer_link` は必須、L3 MCLAG では optional
- ICCP は **2 台ピアまで**。3-way は非対応

## 2. Click ベース CLI（一般 community）

### 2.1 MCLAG domain 設定

```bash
config mclag add <domain-id> <local-ip> <peer-ip> [<peer-ifname>]
config mclag del <domain-id>
```

- `domain-id`: 1–4095
- `local-ip` / `peer-ip`: IPv4 のみ
- `peer-ifname`: L2 MCLAG は必須、L3 MCLAG は省略可

### 2.2 MCLAG interface 追加

```bash
config mclag member add <domain-id> <PortChannel-list>   # カンマ区切り可
config mclag member del <domain-id> <PortChannel-list>
```

### 2.3 Keep-alive / session timeout

```bash
config mclag keepalive-interval <domain-id> <1-60>      # default 1
config mclag session-timeout    <domain-id> <3-3600>    # default 15、keep-alive の 3 倍以上推奨
```

### 2.4 Unique IP（L3 プロトコル対応）

```bash
config mclag unique-ip add <Vlan-interface>   # 例: Vlan100
config mclag unique-ip del <Vlan-interface>
```

## 3. KLISH 系 CLI

```text
sonic(config)# mclag domain <domain-id>
sonic(config-mclag-domain)# source-address <ipv4>
sonic(config-mclag-domain)# peer-address   <ipv4>
sonic(config-mclag-domain)# peer-link      <if-name>
sonic(config-mclag-domain)# keepalive-interval <1-60>
sonic(config-mclag-domain)# session-timeout    <3-3600>

sonic(config)# interface PortChannel 10
sonic(config-if-PortChannel10)# mclag <domain-id>
```

## 4. 典型的な設定シナリオ

### 4.1 L2 active-active (Static Anycast GW 想定)

両 peer で以下を実行（IP のみ入れ替え）:

```bash
config vlan add 100
config interface ip add Vlan100 10.1.1.254/24    # 両 peer 同一 IP（SAG）
config portchannel add PortChannel10
config portchannel member add PortChannel10 Ethernet0
config vlan member add 100 PortChannel10
config portchannel add PortChannel999             # peer-link
config vlan member add 100 PortChannel999 -u

# Switch A
config mclag add 1 192.168.0.1 192.168.0.2 PortChannel999
config mclag member add 1 PortChannel10

# Switch B
config mclag add 1 192.168.0.2 192.168.0.1 PortChannel999
config mclag member add 1 PortChannel10
```

### 4.2 Unique IP + L3 プロトコル

```bash
# Switch A
config interface ip add Vlan100 10.1.1.1/24
config mclag unique-ip add Vlan100
# BGP / BFD など L3 プロトコルを Vlan100 上で起動

# Switch B
config interface ip add Vlan100 10.1.1.2/24
config mclag unique-ip add Vlan100
```

データプレーン gateway は別途 SAG または [VRRP](../reference/glossary.md#term-vrrp) 必須。

## 5. 確認コマンド

### 5.1 SONiC show

```bash
show mclag brief
show mclag interface <domain-id> <PortChannel>
show mac        # type=Static / origin が見える環境ではローカル/リモート判別
show ip route
```

`show mclag brief` 出力例[^1]:

```text
Domain ID                   : 5
Role                        : Active
Session Status              : Up
Peer Link Status            : Up
Source Address              : 192.168.1.1
Peer Address                : 192.168.1.2
Peer Link                   : PortChannel30
Keepalive Interval          : 1 secs
Session Timeout             : 15 secs
System MAC                  : b8:6a:97:73:6c:96
Number of MCLAG Interfaces  : 2
MCLAG Interface             Local/Remote Status
PortChannel50               Up/Up
PortChannel60               Up/Up
```

### 5.2 mclagdctl

```bash
mclagdctl -i <domain-id> dump state
mclagdctl -i <domain-id> dump debug counters
mclagdctl -i <domain-id> dump local interface
mclagdctl -i <domain-id> dump peer interface
mclagdctl -i <domain-id> dump mac
```

`dump state` には `MCLAG info sync is: completed` 行が追加され、初期 sync 完了を確認できる[^1]。`dump debug counters` で ICCP TLV ごとの TX/RX/ERR をカウント[^1]（内訳は [内部実装ページの ICCP メッセージ統計節](mclag-enhancements-internals.md) 参照）。

### 5.3 Redis (CONFIG_DB / APPL_DB / STATE_DB) 直接確認

```bash
# CONFIG_DB (DB 4)
redis-cli -n 4 KEYS "MCLAG_*"
redis-cli -n 4 HGETALL "MCLAG_DOMAIN|1"

# APPL_DB (DB 0)
redis-cli -n 0 KEYS "MCLAG_FDB_TABLE:*" | head
redis-cli -n 0 HGETALL "ISOLATION_GROUP_TABLE:1"

# STATE_DB (DB 6)
redis-cli -n 6 HGETALL "MCLAG_TABLE|1"
redis-cli -n 6 KEYS "MCLAG_REMOTE_INTF_TABLE|*"
redis-cli -n 6 KEYS "MCLAG_REMOTE_FDB_TABLE|*" | head
```

## 6. トラブルシュート

### 6.1 セッションが Up にならない

| 観察 | 切り分け |
|------|---------|
| `Session Status : Down` 持続 | `peer-link` の [VLAN](../reference/glossary.md#term-vlan) tag 通過 / `source_ip` の reachability / firewall。`ping <peer-ip>` で peer に届くか確認 |
| keep-alive が頻繁にロス | `keepalive-interval` を 1s から 2-3s に緩める。`session-timeout` を `keepalive × 3` 以上にする |
| 片側だけ Active | `mclagdctl -i <id> dump state` で system MAC を比較。tie-break で低い MAC が Active |

### 6.2 MAC が peer に同期されない

```bash
mclagdctl -i 1 dump debug counters | grep -E "MacInfo|FdbChange"
redis-cli -n 0 KEYS "MCLAG_FDB_TABLE:*" | wc -l
```

`MacInfo TX` が増えない場合 ICCPd 側、`FdbChange RX` が来ているのに [APPL_DB](../reference/glossary.md#term-appl_db) に上がらない場合 MclagSyncd 側、APPL_DB にあるのに [ASIC](../reference/glossary.md#term-asic) に乗らない場合 FdbOrch 側を疑う。

### 6.3 BUM が peer-link 経由で MHD に重複到達

isolation group が attach されていない可能性。

```bash
redis-cli -n 0 HGETALL "ISOLATION_GROUP_TABLE:1"
# platform が SAI isolation group 未対応の場合は egress ACL fallback に切り替わる
syslog で "isolation group" / "ACL fallback" を grep
```

### 6.4 L2 MC-LAG 環境での ICMPv6 RS/NS ループ（#1253）

L2 MC-[LAG](../reference/glossary.md#term-lag) 構成において、ICMPv6 Router Solicitation (type 133) や Neighbor Solicitation (type 135) パケットが peer-link を経由してループを形成する既知の問題がある。[SONiC](../reference/glossary.md#term-sonic) kernel がこれらのパケットを処理する際に isolation group を迂回するためと考えられる[^2]。

**回避策（再起動で消えるため startup script 化推奨）:**

```bash
sudo ebtables -A FORWARD -p 802_1Q --vlan-encap IPv6 -j DROP
```

### 6.5 Unique IP で OSPF / BGP 隣接が立たない

- `MCLAG_UNIQUE_IP` テーブルに該当 VLAN intf が登録されているか
- 両 peer で **異なる IP** を設定しているか（同一 IP のままだと旧モードで重複検知に陥る）
- Standby 側で peer の VLAN intf MAC が L2 table に program されているか (`show mac | grep <peer-mac>`)
- 隣接が片方向の場合は [ARP](../reference/glossary.md#term-arp) / ND sync 経路を疑う

## 7. 制限事項

- ICCP は **2 台ピアまで**（3-way 以上は未対応）
- isolation group は [SAI](../reference/glossary.md#term-sai) 対応必須。未対応 ASIC では peer-link 経由のループ抑止は egress [ACL](../reference/glossary.md#term-acl) fallback
- unique IP では active/active 両方が L3 で見える。OSPF cost / [BGP](../reference/glossary.md#term-bgp) を peer 間で揃える必要
- 大量 static MAC sync は ICCP メッセージ量増、scalability 影響あり
- 旧版（`config_db.json` 直書き）からの **upgrade / downgrade は非対応**[^1]
- Warm Boot 後は ICCP が local [FDB](../reference/glossary.md#term-fdb) を再 advertise する必要がある（[HLD](../reference/glossary.md#term-hld) §6）

## 8. 引用元

[^1]: `sonic-net/SONiC` `doc/mclag/MCLAG_Enhancements_HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
[^2]: [`sonic-net/SONiC#1253`](https://github.com/sonic-net/SONiC/issues/1253)

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: L2 / VLAN / LAG / MC-LAG](../topics/06-l2-vlan-lag/index.md)
- [Topics: Dual ToR](../topics/05-dual-tor/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 639b1e55333b -->
