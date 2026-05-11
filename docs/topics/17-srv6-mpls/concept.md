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

## 他章との境界

- BGP / FRR 連携は [02 BGP](../02-bgp/index.md) の章に、SRv6 / MPLS で追加される BGP family（SR-MPLS、SRv6 L3VPN）はこの章で扱います。
- VRF / VPN の一般的な構造は [04 VRF / ECMP](../04-vrf-ecmp/index.md) で、SRv6 VPN による L3VPN の SID マッピングはこの章です。
- EVPN-VXLAN は [03 VXLAN-EVPN](../03-vxlan-evpn/index.md) で、SRv6 を underlay にする方向は本章の発展トピックから辿ります。

## まず読み手の質問に答える

### この章はそもそも何の章か

「SRv6 / MPLS / Path Tracing」は **IPv4/IPv6 forwarding の上に「ラベル」「セグメント」「観測メタデータ」を積む 3 種類の機能** をまとめた章です。

- **SRv6**: IPv6 アドレスを SID（Segment Identifier）として使い、経路 / VPN / Policy を表現する
- **MPLS**: 4 byte ラベルを別 address family（AF_MPLS）として扱い、静的 LSP / L3VPN underlay に使う
- **Path Tracing**: IPv6 HbH オプション（HbH-PT）に各 transit が MCD を書き加え、経路と遅延を観測する

通常の routing が「どこ宛か」を決めるのに対し、この章は「どのラベル / セグメント / 観測メタを積むか」を扱います。

### 何を解決するか

- **テナント / SLA 別の経路指定** → SRv6 Policy / Binding SID で「この trafic は東経路、別 traffic は西経路」のような明示経路を作る
- **L3VPN / L2VPN underlay の現代化** → SRv6 で IPv6 だけの underlay に L3VPN を載せる（MPLS underlay を畳む）
- **既存 MPLS 網との接続** — SONiC を MPLS LSR として配置し、静的 LSP で連携する
- **障害観測の解像度向上** → Path Tracing で経路上の各 hop の通過時刻と nexthop を probe 単位で取る

純粋な BGP / ECMP では表現できない「経路の制御」「経路の可観測性」を担うのがこの章です。

### SONiC 内での位置

```mermaid
flowchart TB
    subgraph CFG[(CONFIG_DB)]
        IF[INTERFACE.mpls]
        LOC[SRV6_MY_LOCATORS]
        SID[SRV6_MY_SIDS]
        POL[SRV6_POLICY]
        STR[SRV6_STEER]
        PT[PORT.pt_*]
    end
    subgraph CTRL[制御面]
        FRR[FRR<br/>bgpd / zebra / staticd]
        BCFG[bgpcfgd / SRv6Mgr]
        FPM[fpmsyncd]
    end
    subgraph SWSS[swss]
        SRORC[srv6orch]
        MORC[MplsOrch / RouteOrch]
        PORTORC[PortOrch]
    end
    subgraph SAI[SAI / syncd]
        MYSID[MY_SID_ENTRY]
        SIDLIST[SRV6_SIDLIST]
        LBL[INSEG_ENTRY]
        PTATTR[port PT attrs]
    end
    LOC --> BCFG --> FRR --> FPM --> SRORC --> MYSID
    SID --> SRORC --> SIDLIST
    POL --> SRORC
    IF --> MORC --> LBL
    PT --> PORTORC --> PTATTR
    FRR -.AF_MPLS netlink.-> FPM
```

「経路の決定」は FRR、「ラベル / SID の生成と SAI への落とし込み」は SONiC 内 orchagent と分担しています。

### 用語の最短整理

- **SID**: Segment Identifier。SRv6 では 128bit IPv6 アドレス相当
- **uSID**: SID を 16 / 32bit 単位に圧縮し 1 つの IPv6 アドレスに最大 6 個積む方式
- **Locator**: SID のうち「装置を指す prefix」部分。SRv6 では 1 装置の SID 群が同じ Locator を共有する
- **Function**: SID の挙動を示す部分（`uN` / `uA` / `uDT4` / `uDX6` 等）
- **`END.X` / `End.DT4` / `End.DT46`**: SRv6 endpoint behavior。例えば `End.DT4` は SID から VRF を抜く挙動
- **`SRV6_MY_SID_TABLE`**: 自装置が処理するべき SID を保持する APP_DB テーブル
- **`SRV6_SID_LIST` / `SRV6_POLICY` / `SRV6_STEER`**: encap 側 SID list / Policy bind / steering rule
- **`srv6orch`**: SRv6 関連の orchagent
- **`LABEL_ROUTE_TABLE`**: MPLS in-segment entry の APP_DB 表現
- **AF_MPLS**: Linux の MPLS address family。netlink で route が流れる
- **PHP / explicit-null / implicit-null**: penultimate hop popping と end-of-LSP のラベル挙動
- **`MPLS_TC_TO_TC_MAP`**: MPLS パケットの TC（traffic class）を SONiC 内部 TC に変換する QoS map
- **HbH-PT / MCD**: IPv6 Hop-by-Hop Path Tracing Option / Midpoint Compressed Data
- **SRC / Midpoint / SINK**: Path Tracing の役割。SONiC は Midpoint を実装
- **Regional Collector**: SINK が集めた MCD を時系列で再構築する外部システム（HLD 外）

### 典型シーン: SRv6 L3VPN 着信ノードでの SID 解決

```mermaid
sequenceDiagram
    participant SRC as Ingress PE
    participant TR as Transit Router (uN)
    participant DST as Egress PE (this switch)
    participant ORC as srv6orch
    participant VRF as VRF route table

    SRC->>TR: IPv6 + SRH (SID=...:eDT4:...)
    TR->>DST: forward by uN
    Note over DST: SAI MY_SID_ENTRY match
    DST->>ORC: lookup End.DT4 SID
    ORC->>VRF: SRH 剥がす + VRF X で IPv4 lookup
    VRF-->>DST: nexthop = customer side
    DST->>DST: SRv6 decap して IPv4 forward
```

ここで Neighbor 未解決の `uA` / `End.X` 系は `srv6orch` の pending queue で待ち、Neighbor 解決後に SAI への push がリトライされます。設定したのに動かない場合は ARP/ND 状態と pending queue の双方を確認します。

### 似ているが別物のもの

| 比較対象 | この章との違い |
| --- | --- |
| [BGP](../02-bgp/index.md) | 経路情報の交換そのもの。SRv6/MPLS で追加される BGP family（SR-MPLS / SRv6 L3VPN）の挙動は本章 |
| [VRF / ECMP](../04-vrf-ecmp/index.md) | VRF 一般構造は 04 章。SRv6 SID と VRF の紐付けは本章 |
| [VXLAN / EVPN](../03-vxlan-evpn/index.md) | overlay は UDP encap 主体。SRv6 / MPLS は IPv6 / AF_MPLS native |
| [DASH / SmartSwitch](../13-dash-smartswitch/index.md) | DASH は per-ENI overlay。SRv6 / MPLS は装置間 fabric の話 |
| [Telemetry / SNMP](../09-telemetry-snmp/index.md) | counter / event の収集。Path Tracing は data plane に観測ヘッダを埋める点で別軸 |
| LDP / RSVP-TE | 動的 MPLS シグナリング。SONiC は初期 scope 外、本章は静的 LSP + bulk programming のみ |

### 読了後にできるようになること

- 機能ごとの HLD（SRv6 base / uSID / static SID / L3 隣接 / VPN / MPLS / Path Tracing）が **どの phase の話か** を識別できる
- `SRV6_MY_SID_TABLE` の `action` と SAI MY_SID_ENTRY の attribute の対応が読める
- 「MPLS が forward しない」事象で per-RIF `mpls` 属性、AF_MPLS netlink、`INSEG_ENTRY` の順に切り分けできる
- Path Tracing を有効化するときの `pt_interface_id` / `pt_timestamp_template` の意味と SAI 対応 attribute が答えられる
- 自社の網設計に SRv6 / MPLS / Path Tracing のどれを採用するか、設定範囲と必要 HLD を提示できる

## 関連ページ

- [SRv6 HLD](../../routing/segment-routing-over-ipv6-srv6-hld.md)
- [SRv6 uSID](../../routing/sonic-usid.md)
- [SONiC の MPLS 基盤](../../routing/mpls-for-sonic-high-level-design-document.md)
- [Path Tracing Midpoint](../../routing/path-tracing-midpoint.md)
