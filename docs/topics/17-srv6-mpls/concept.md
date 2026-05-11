---
title: 概念
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/routing/segment-routing-over-ipv6-srv6-hld.md
  - docs/routing/sonic-usid.md
  - docs/routing/srv6-sid-l3adj.md
  - docs/routing/srv6-vpn-hld.md
  - docs/routing/mpls-for-sonic-high-level-design-document.md
  - docs/routing/path-tracing-midpoint.md
---

# 概念

SRv6、MPLS、Path Tracing はいずれも「IPv4/IPv6 forwarding の上に、追加のラベルまたはオプションを積んで経路や挙動を決める」仕組みです。SONiC で読み解く前に、まずどこで通常の routing 章（[02 BGP](../02-bgp/index.md) や [04 VRF / ECMP](../04-vrf-ecmp/index.md)）と分かれるかを整理します。

## この章は何のためにあるか

通常の BGP / VRF 章では「宛先 IP に対応する nexthop を引き、L2 ヘッダを差し替えて送出する」までを扱います。本章はそこに **追加のヘッダ操作（push / pop / swap）** や **経路情報の付加（SID リスト、HbH オプション）** が入る場合、SONiC のどの daemon と DB がどう拡張されるかを読み解きます。読み手が最初に持つ疑問は次の 4 つで、本章のすべての節はそれに答える形で並んでいます。

1. SRv6 / MPLS / Path Tracing は「同じ拡張ヘッダ」の仲間か、それとも別物か
2. SONiC に入れるとき、どの daemon と DB が増えるか／流用されるか
3. 既存の BGP / VRF 設定とどこで衝突するか
4. どこまでが master 実装済みで、どこから提案段階の HLD か

## 何を解決するか

- **traffic engineering を IGP/BGP の外側に出す**: 経路を IGP メトリックではなく、operator が指定した SID リストや LSP に沿わせたい。
- **VPN を「underlay 共通」で多重化する**: SRv6 L3VPN や MPLS L3VPN は、underlay を 1 本に保ったまま customer VRF を多重化する。VRF をそのまま BGP で広告する vrf-lite と違い、PE 間で経路を共有しつつ data plane で分離できる。
- **path 観測の精度を上げる**: Path Tracing は「どの transit を経由したか」「各 hop の interface / timestamp は何か」を data plane に書き込む。ping / traceroute と違い、本物のトラフィックそのものに経路情報が残る。

## SONiC 内での位置

```mermaid
flowchart LR
  subgraph CP[制御プレーン]
    FRR[FRR<br/>bgpd / staticd]
    BGPCFGD[bgpcfgd<br/>SRv6Mgr / MplsMgr]
    FPMSYNCD[fpmsyncd]
  end
  subgraph DP[データプレーン橋渡し]
    SRV6ORCH[srv6orch]
    ROUTEORCH[routeorch]
    PORTSORCH[portsorch<br/>PT 属性]
    SYNCD[syncd / SAI]
  end
  FRR --> FPMSYNCD --> ROUTEORCH
  BGPCFGD --> SRV6ORCH
  BGPCFGD --> ROUTEORCH
  SRV6ORCH --> SYNCD
  ROUTEORCH --> SYNCD
  PORTSORCH --> SYNCD
```

通常の BGP route が `fpmsyncd -> routeorch` で流れるのに対し、SRv6 の SID / Policy / Steer 情報は `bgpcfgd (SRv6Mgr) -> srv6orch` で流れます。MPLS は label を持つ route として `LABEL_ROUTE_TABLE` に乗りますが、L3 nexthop は通常の routeorch と共有します。Path Tracing は forwarding そのものを変えず、port 属性として SAI に渡るだけです。

## 用語の整理

| 用語 | 意味 | SONiC で対応する場所 |
| --- | --- | --- |
| SID | Segment Identifier。SRv6 では 128bit IPv6 アドレス、SR-MPLS では label。 | `SRV6_MY_SID_TABLE` / `LABEL_ROUTE_TABLE` |
| Locator | uSID block + node id をまとめた IPv6 prefix。 | `SRV6_MY_LOCATORS` |
| Behavior | SID に紐づく動作（END、END.DT4、uA など）。 | `SRV6_MY_SID_TABLE.action` |
| Policy | source routing の発射台。SID list を持ち、color / endpoint で identified。 | `SRV6_POLICY` |
| Steer | どの prefix / vrf を policy に流すか。 | `SRV6_STEER` |
| LSP | Label Switched Path。MPLS の path。 | `LABEL_ROUTE_TABLE` の連鎖 |
| MCD | Midpoint Compressed Data。Path Tracing で各 transit が書く 4 byte 情報。 | port 属性で hardware が生成 |
| HbH-PT | Hop-by-Hop Path Tracing Option。IPv6 拡張ヘッダの一種。 | data plane でのみ参照 |

## 典型シーンを 1 枚で

```mermaid
sequenceDiagram
  participant CTRL as Controller / Operator
  participant CDB as CONFIG_DB
  participant SR as srv6orch
  participant FRR as FRR (bgpd)
  participant FPM as fpmsyncd
  participant RO as routeorch
  participant SAI as syncd / SAI
  CTRL->>CDB: SRV6_MY_LOCATORS / SRV6_MY_SIDS
  CDB-->>SR: SRv6Mgr 経由で受信
  SR->>SAI: My SID entry 作成
  CTRL->>CDB: SRV6_POLICY / SRV6_STEER
  CDB-->>SR: policy + steer 反映
  SR->>SAI: SID list + nexthop group
  FRR->>FPM: SR-MPLS / SRv6 L3VPN route
  FPM->>RO: AF_MPLS / IPv6+SRH route
  RO->>SAI: label route / encap nexthop
```

ポイントは、**operator が直接書く部分（locator / sid / policy / steer）** と **FRR 経由で来る部分（L3VPN route）** が同じ章で扱われる点です。Phase 1 では FRR の SRv6 が未成熟なため、operator が CONFIG_DB を書く割合が大きくなります。

## 似た機能との違い

| 比較 | 共通点 | 違い |
| --- | --- | --- |
| EVPN-VXLAN との違い | underlay が L3、tenant を多重化する | EVPN は L2 拡張も含み、VXLAN UDP を使う。SRv6 は IPv6 SRH、MPLS は label。 |
| Static route との違い | 経路を operator が指定する | static route は「次の hop」のみ指定。SRv6 / MPLS は **経路全体を SID/label の列で指定** できる。 |
| GRE / IPinIP との違い | encap で tenant を運ぶ | GRE は単純な tunnel、SRv6 は SID 列で TE / VPN / function を同時に表現できる。 |
| Inband telemetry (INT) との違い | data plane に観測情報を埋め込む | INT は metadata stack をパケットに積む。Path Tracing は 4 byte MCD と HbH オプションに限定。 |

## SRv6 の積み上げ順

SRv6 は HLD が一気に揃っているわけではなく、機能ごとに別 HLD として段階的に追加されています。読む順は実装の追加順と一致させると迷いません。

1. **SRv6 base** — `END` / `END.DT46` / `H.Encaps.Red` などの基本 behavior、`SRV6_SID_LIST` / `SRV6_MY_SID_TABLE` / `SRV6_POLICY` / `SRV6_STEER` のスキーマ。Phase 1 では FRR の SRv6 が未成熟なため、静的 SID と policy を CONFIG_DB に直接書く運用が前提です。
2. **uSID** — 128bit IPv6 アドレスに最大 6 個の uSID を圧縮して詰める方式。SAI 変更なしで `srv6orch` の `end_behavior_map` に `un` / `ua` / `udt4` / `udt6` / `udt46` / `udx4` / `udx6` を追加する拡張です。
3. **Static SID / Locator 設定** — `SRV6_MY_LOCATORS` / `SRV6_MY_SIDS` を CONFIG_DB 経由で受け、`bgpcfgd` の `SRv6Mgr` が `vtysh` で FRR の `segment-routing srv6` 設定に流し込む経路です。
4. **L3 隣接** — `uA` / `End.X` / `uDX4` / `uDX6` / `End.DX4` / `End.DX6` のような cross-connect 系 behavior は出口の nexthop（L3 隣接）が必要で、`srv6orch` が pending queue で Neighbor 解決を待ちます。
5. **VPN / Policy** — L3VPN over SRv6 は `srv6_prefix_agg_id_table_` のような Prefix AGG_ID と VPN encap mapper を介して `vpn_sid` を管理し、SRv6 Policy で steering します。

この順序を踏まえると、`SRV6_MY_SID_TABLE` の `action` 値や `adj` パラメータが「どの phase で意味を持つか」が分かれます。

## MPLS の位置付け

SONiC の MPLS は **静的 LSP** を前提に、IPv4/IPv6 routing インフラを MPLS にも拡張する設計です。動的シグナリング（LDP / RSVP-TE）は初期 scope 外で、以下の 4 点が基盤になります。

- **per-RIF で MPLS を enable/disable** — `INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` の `mpls` 属性で明示的に許可した interface のみ MPLS を扱う。
- **Push / Pop / Swap** — implicit-null / explicit-null を含むラベル操作。
- **bulk MPLS in-segment entry の SAI programming** — `LABEL_ROUTE_TABLE` を APP_DB 経由で `fpmsyncd` が `AF_MPLS` の netlink から受けて流し込む。
- **CRM 統合** — MPLS in-segment / nexthop の使用量を Critical Resource Monitoring に乗せる。

QoS 連携は `MPLS_TC_TO_TC_MAP` と `PORT_QOS_MAP` の `mpls_tc_to_tc_map` フィールドで、MPLS パケットの TC を SONiC 内部 TC に変換します。

## Path Tracing は何を観測するか

Path Tracing は IETF spring-path-tracing で定義され、各 transit が **MCD（Midpoint Compressed Data）** を IPv6 **Hop-by-Hop Path Tracing Option (HbH-PT)** に書き足していく仕組みです。SRC が probe を生成、Midpoint が MCD を追記、SINK が回収して Regional Collector で時系列に再構築します。

SONiC は **Midpoint** を実装する側で、`PORT` テーブルの `pt_interface_id` / `pt_timestamp_template` が SAI の `SAI_PORT_ATTR_PATH_TRACING_INTF` / `SAI_PORT_ATTR_PATH_TRACING_TIMESTAMP_TYPE` に対応します。通常 IPv6 forwarding に MCD 書き込みが追加されるだけで、経路選択そのものは変えません。

## 三者の境界

```mermaid
flowchart LR
  PKT[packet] --> CL{header}
  CL -->|IPv6 + SRH| SR[SRv6 endpoint<br/>srv6orch / MY_SID]
  CL -->|MPLS label| MP[MPLS LSP<br/>LABEL_ROUTE_TABLE]
  CL -->|IPv6 + HbH-PT| PT[Path Tracing Midpoint<br/>PORT attrs]
  SR --> FWD[L3 forwarding]
  MP --> FWD
  PT --> FWD
  FWD --> OUT[egress port]
```

要点は、SRv6 と Path Tracing は IPv6 forwarding の中でそれぞれの拡張ヘッダ／オプションを処理する点が共通している一方、MPLS は AF_MPLS という別の address family で動く点です。

## 読了後にできること

- SRv6 の uSID / Locator / Behavior / Policy / Steer がそれぞれ CONFIG_DB のどのテーブルに対応するかを思い出せる。
- MPLS の per-RIF enable、in-segment programming、QoS map の流れを 1 本で説明できる。
- Path Tracing が forwarding を変えないこと、PORT 属性が SAI のどの属性に対応するかを言える。
- 「BGP route が反映されない」「policy で steer されない」「MPLS label が pop されない」が起きたとき、`bgpcfgd` / `srv6orch` / `routeorch` のうちどれを最初に疑うかを決められる。
- 章末の発展トピックや operations 章に進む準備が整う。

## 他章との境界

- BGP / FRR 連携は [02 BGP](../02-bgp/index.md) の章に、SRv6 / MPLS で追加される BGP family（SR-MPLS、SRv6 L3VPN）はこの章で扱います。
- VRF / VPN の一般的な構造は [04 VRF / ECMP](../04-vrf-ecmp/index.md) で、SRv6 VPN による L3VPN の SID マッピングはこの章です。
- EVPN-VXLAN は [03 VXLAN-EVPN](../03-vxlan-evpn/index.md) で、SRv6 を underlay にする方向は本章の発展トピックから辿ります。

## 関連ページ

- [SRv6 HLD](../../routing/segment-routing-over-ipv6-srv6-hld.md)
- [SRv6 uSID](../../routing/sonic-usid.md)
- [SONiC の MPLS 基盤](../../routing/mpls-for-sonic-high-level-design-document.md)
- [Path Tracing Midpoint](../../routing/path-tracing-midpoint.md)
