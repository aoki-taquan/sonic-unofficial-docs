---
title: Route / Interface / Counter の確認
description: Route / Interface / Counter の確認 — L3 の障害調査では、最初に route だけを見ても原因を絞れません。VRF、interface、RIB、FIB、RIF
  counter、flow counter の順に、control-plane と data-plane の差を分けて確認します。
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
related:
  cli:
  - show ip
  - show interfaces
  - config interface
  - clear
  - show vlan
  - clear counters
  - config vrf
  config_db:
  - VLAN_INTERFACE
  - PORTCHANNEL_INTERFACE
  - VRF
  - INTERFACE
  - LOOPBACK_INTERFACE
  - VLAN
  - CRM
  yang:
  - sonic-route-common
  - sonic-route-map
  - sonic-interface
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-global
---

# Route / Interface / Counter の確認

L3 の障害調査では、最初に route だけを見ても原因を絞れません。[VRF](../../reference/glossary.md#term-vrf)、interface、RIB、FIB、[RIF](../../reference/glossary.md#term-rif) counter、flow counter の順に、control-plane と data-plane の差を分けて確認します。

## 確認コマンドの順番

| 目的 | コマンド / 入口 | 見ること |
|------|----------------|----------|
| Interface 状態 | `show ip interfaces`、`show interfaces status` | L3 interface の IP、admin/oper、VRF bind 前提。 |
| [FRR](../../reference/glossary.md#term-frr) RIB | `show ip route` / `show ipv6 route` | FRR が route を選んでいるか。 |
| [ASIC](../../reference/glossary.md#term-asic) FIB | `show ip fib` | FIB に入っているか。RIB にあり FIB にない場合は [orchagent](../../reference/glossary.md#term-orchagent) 側を見る。 |
| [BGP](../../reference/glossary.md#term-bgp) VRF | `show ip bgp vrf <vrf> ...` | dynamic route の入力側。 |
| RIF 統計 | `show interfaces counters rif` | RIF 単位の RX/TX packet / byte / error。 |
| Route flow | `show flowcnt-route stats` | route pattern に一致する traffic counter。 |
| Loopback action | `show ip interfaces loopback-action` | 同一 RIF 出戻りの drop / forward 設定。 |

`show ip` のコマンド体系は [show ip サブコマンド](../../reference/cli/show-ip.md)、物理 port や RIF counter 表示は [show interfaces サブコマンド](../../reference/cli/show-interfaces.md) を参照してください。

## RIB と FIB の差を分ける

`show ip route` に見える route は FRR RIB の状態です。`show ip fib` は FIB 側を見ます。RIB にあるのに FIB にない場合、次の順で確認します。

1. route の VRF が意図通りか。
2. next hop の interface が同じ VRF にあるか、または `nexthop-vrf` が意図通りか。
3. neighbor が解決しているか。
4. [ECMP](../../reference/glossary.md#term-ecmp) / NHG の member が作れる状態か。
5. ASIC resource や [SAI](../../reference/glossary.md#term-sai) エラーで route programming が失敗していないか。

BGP 由来 route の FIB 未導入や route install failure は BGP 章の運用ページも関係します。この章では L3 pipeline 側の前提、つまり RIF / NHG / RouteOrch の準備ができているかを見ます。

## RIF counter は L3 interface 単位で見る

port counter は L2 port の統計で、RIF counter は SAI router interface の統計です。L3 forwarding の RX/TX packet、octet、error を確認したい場合は [ルータインタフェース (RIF) カウンタ](../../routing/router-interface-counters-in-sonic.md) を入口にします。

同一 RIF から出戻る packet を drop する設定を使っている場合、drop は RIF counter の error 側に現れます。この挙動は [IP インタフェース ループバックアクション](../../architecture/sonic-ip-interface-loopback-action.md) と合わせて読みます。

## Route flow counter は対象 route を絞って見る

[Route Flow Counter](../../routing/sonic-route-flow-counter-design.md) は、route pattern に一致する route に Generic Counter を bind して hit / byte を見る設計です。全 route の統計を常時見る仕組みではなく、調査したい prefix pattern を指定して観測する機能として読みます。

このページは [HLD](../../reference/glossary.md#term-hld)-only として整理されています。利用可否や CLI の存在は対象ビルドで確認してください。

## Loopback action は誤転送の最後の防波堤

同じ RIF へ出戻る転送は、構成ミスや経路設計の不整合を示すことがあります。`loopback_action=drop` を設定すると ASIC で drop し、帯域消費やループを抑えられます。ただし、これは route 設計を直す代替ではありません。出戻りが見えたら、default route、VRF、next hop、ECMP member の設計も確認します。

## show ip route / interfaces の出力サンプル

`show ip route` は [zebra](../../reference/glossary.md#term-zebra) の FRR RIB を整形して出します。`>` は selected、`*` は FIB に install 済みを示します。

```text
B>* 10.1.0.0/24 [20/0] via 10.0.0.1, Ethernet0, weight 1, 00:12:34
                       via 10.0.0.5, Ethernet4, weight 1, 00:12:34
C>* 10.0.0.0/31 is directly connected, Ethernet0, 01:23:45
S>* 0.0.0.0/0 [1/0] via 10.0.0.1, Ethernet0, weight 1, 01:23:45
B   10.2.0.0/24 [20/0] via 10.0.0.1 inactive, weight 1, 00:00:05
```

`B` で `>` も `*` も付かない行は、best 選択も install も完了していない過渡状態か、SAI 側で reject されているケースです。

`show ip interfaces` は [CONFIG_DB](../../reference/glossary.md#term-config_db) の `INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` / `LOOPBACK_INTERFACE` を結合します。

```text
Interface        Master    IPv4 address/mask    Admin/Oper    BGP Neighbor    Neighbor IP
---------------  --------  -------------------  ------------  --------------  -----------
Ethernet0                  10.0.0.0/31          up/up         ARISTA01T2      10.0.0.1
Ethernet4                  10.0.0.4/31          up/up         ARISTA03T2      10.0.0.5
PortChannel101             10.1.0.32/32         up/up         N/A             N/A
Vlan1000                   192.168.0.1/21       up/up         N/A             N/A
```

VRF binding は `Master` カラムに VRF 名（`Vrf_red` 等）で表示されます。`Admin=up` だが `Oper=down` の場合、L1 / lldp / autoneg / counters を見ます。

## 異常検出パターン

| 観測 | 疑う状態 | 一次切り分け |
|---|---|---|
| RIB にあるが `>` が無い | metric/distance 競合、または next-hop unreachable | `show ip route <prefix>` の `via ... inactive`、neighbor 状態 |
| `>` あるが `*` 無し | FIB 反映失敗（orchagent / SAI） | `/var/log/swss/sairedis.rec`、[APPL_DB](../../reference/glossary.md#term-appl_db):[ROUTE_TABLE](../../reference/glossary.md#term-route_table) |
| `Master` が想定 VRF と違う | bind 漏れ、または bind 順序ミス | `config interface vrf bind`、`show vrf` |
| RIF counter の error 増 | MTU mismatch、TTL exceed、loopback drop | `show interfaces counters rif`、loopback-action 設定 |
| `show ip neighbor` で IP に対する MAC 解決なし | [ARP](../../reference/glossary.md#term-arp) / ND 失敗、または [VLAN](../../reference/glossary.md#term-vlan) tagging 不一致 | `arp -n`、`show vlan brief`、対向側 ping |
| ECMP member が偏る | hash seed、PBH 未設定、bucket 数不一致 | `show ecmp loadshare`、PBH 設定 |
| Route Flow Counter の hit が増えない | pattern miss、または対象 prefix 非導入 | `show flowcnt-route stats`、対象 prefix の install 状態 |
| `loopback_action=drop` 設定下で legitimate な return が落ちる | `loopback_action` を強くしすぎ | `show ip interfaces loopback-action`、`config interface ip loopback-action` |

## 典型的なログサンプル

```text
zebra[18]: nexthop_active_check: 10.1.0.0/24, nexthop 10.0.0.1, unreachable
zebra[18]: dplane_route_update: Failed to install route 10.1.0.0/24
fpmsyncd[15]: Received route update for prefix 10.1.0.0/24 nexthop 10.0.0.1 ifindex 4
orchagent: :- doTask: Failed to create next hop 10.0.0.1 on Ethernet0, rv:-2
orchagent: :- create: Failed to create route 10.1.0.0/24 SAI_STATUS_INSUFFICIENT_RESOURCES
neighsyncd: Received neighbor update for 10.0.0.1 lladdr aa:bb:cc:dd:ee:ff state REACHABLE
```

[CRM](../../reference/glossary.md#term-crm) 閾値ログは syslog にも出ます。

```text
crm: CRM Counter THRESHOLD_EXCEEDED for IPV4_ROUTE
crm: CRM Counter NEIGHBOR EXCEEDED HIGH threshold(85) used 8700 available 1500
```

## 対応コマンド早見表

| 目的 | コマンド |
|---|---|
| Interface 一覧 | `show ip interfaces`、`show ipv6 interfaces` |
| L1 状態 | `show interfaces status` |
| L2 counters | `show interfaces counters` |
| RIF counters | `show interfaces counters rif` |
| transceiver | `show interfaces transceiver eeprom`、`... status` |
| VRF 一覧 | `show vrf` |
| FRR RIB | `show ip route [vrf <vrf>] [<prefix>]` |
| ASIC FIB | `show ip fib` |
| neighbor | `show ip neighbor`、`show ip arp`、`show ipv6 neighbors` |
| Route Flow Counter | `show flowcnt-route stats`、`config flowcnt-route ...` |
| ECMP loadshare | `show ecmp loadshare hash-seed`（plat 依存） |
| CRM 残量 | `crm show summary`、`crm show resources all`、`crm show thresholds all` |
| neighbor flush | `sonic-clear arp`、`sonic-clear ndp` |
| RIF counter clear | `sonic-clear counters` |
| loopback-action | `show ip interfaces loopback-action` |

## 関連 CONFIG_DB / STATE_DB / counter

- `CONFIG_DB:VRF|<name>` — VRF 定義。
- `CONFIG_DB:INTERFACE|<port>` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` / `LOOPBACK_INTERFACE` — `vrf_name`、`loopback_action` 等。
- `APPL_DB:INTF_TABLE:<port>` — RIF 投入待ち。
- `APPL_DB:ROUTE_TABLE:<prefix>` — FIB 投入対象。`nexthop`、`ifname`、`weight`、`vrf`。
- `APPL_DB:NEIGH_TABLE:<intf>:<ip>` — ARP / ND が出来た neighbor。
- `APPL_DB:NEXTHOP_GROUP_TABLE:<id>` — ECMP NHG とその member。
- `STATE_DB:ROUTE_FLOW_COUNTER_TABLE` — Route Flow Counter の hit / byte。
- `COUNTERS_DB:COUNTERS_RIF_NAME_MAP` — RIF counter 用 OID 対応。
- `COUNTERS_DB:CRM:*` — LPM / NEXTHOP / NEIGHBOR / [ACL](../../reference/glossary.md#term-acl) の使用量。

## 横断参照

- BGP 由来の install 失敗は [BGP 章 運用](../02-bgp/operations.md) と組み合わせて読みます。
- VRF 跨ぎ leak や Type-5 由来 route の確認は [Overlay 章 運用](../03-vxlan-evpn/operations.md)。
- Dual-ToR 上の default route と nexthop は [Dual-ToR 章 運用](../05-dual-tor/operations.md)。
- L2 SVI（VLAN_INTERFACE）の up/down 前提は [L2 章 運用](../06-l2-vlan-lag/operations.md)。

## 追加の show 出力例

`show vrf` は CONFIG_DB の `VRF` テーブルと `INTERFACE`/`VLAN_INTERFACE`/`PORTCHANNEL_INTERFACE` の `vrf_name` を結合して表示します。

```text
VRF        Interfaces
---------  -------------------------
Vrf_red    Ethernet8
           Vlan100
Vrf_blue   Ethernet12
           PortChannel201
```

VRF が定義されているが Interface 欄が空の場合、bind 漏れか、bind 直後で APPL_DB:INTF_TABLE が未反映の過渡状態です。`config interface vrf bind` の順序、または `swssconfig` の流入を確認します。

`show interfaces counters rif` は RIF（router interface）単位の RX/TX を表示します。

```text
    IFACE    RX_OK    RX_BPS    RX_PPS    RX_ERR    TX_OK    TX_BPS    TX_PPS    TX_ERR
---------  -------  --------  --------  --------  -------  --------  --------  --------
Ethernet0   12,453  12.34 KB     8.2/s         0    9,832  10.21 KB     6.4/s         0
Ethernet4   45,210  41.22 KB    28.7/s         3   32,109  31.55 KB    21.0/s         0
Vlan1000   180,512 155.40 KB   120.3/s         0  120,330 110.11 KB    85.7/s         2
```

`RX_ERR` / `TX_ERR` の増加は MTU / TTL / loopback-action drop を疑い、CRM 閾値超過と合わせて切り分けます。

## 典型的な運用シナリオ

1. **新規 VRF 払い出し** — `config vrf add Vrf_red` → 対象 Interface に `config interface vrf bind <intf> Vrf_red` → `show vrf` で member 確認 → 必要なら BGP / static route を VRF 配下に投入。bind 順序を誤ると IP 設定が消えるので、IP 設定前に bind するのが安全です。
2. **VRF leak / import の検証** — `show ip bgp vrf <vrf>` の RT import で予期する prefix を確認し、`show ip route vrf <vrf>` に `>` `*` が付いているかを見ます。leak 経路は RT mismatch が原因の大半です。
3. **ECMP 偏りの調査** — `show interfaces counters rif` で各 member の TX 偏りを確認、`crm show summary` で NHG / NEXTHOP の使用量を確認、必要なら hash-seed / hash-field を見直します。
4. **MTU mismatch 切り分け** — `RX_ERR` の急増と TTL exceed の syslog を見て、両端 MTU を `show interfaces status` で揃え、jumbo 設定とパス MTU を確認します。
5. **loopback-action 設計確認** — `show ip interfaces loopback-action` で `drop` 設定の interface を一覧化し、設計外の interface に `drop` がついて legitimate な return traffic が落ちていないかを確認します。

## 関連ページ

- [CLI: show ip](../../reference/cli/show-ip.md)
- [CLI: show interfaces](../../reference/cli/show-interfaces.md)
- [ルータインタフェース (RIF) カウンタ](../../routing/router-interface-counters-in-sonic.md)
- [Route Flow Counter](../../routing/sonic-route-flow-counter-design.md)
- [IP インタフェース ループバックアクション](../../architecture/sonic-ip-interface-loopback-action.md)

<!-- glossary-links-injected: c006405759d8 -->
