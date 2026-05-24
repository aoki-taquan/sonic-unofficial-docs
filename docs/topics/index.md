---
title: 読み物
description: "読み物（章立て駆動） — 機能ドメイン単位で複数の HLD・実コードを横断統合した「読み物」章群。HLD 1 件 = 1 ページの reference（docs/<area>/）に対し、こちらは 読み手の質問順 に章立てから書き直したもの。"
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
related:
  config_db: []
  cli: []
  yang: []
  _no_related: true
---

# 読み物（章立て駆動）

機能ドメイン単位で複数の [HLD](../reference/glossary.md#term-hld)・実コードを横断統合した「読み物」章群。HLD 1 件 = 1 ページの reference（`docs/<area>/`）に対し、こちらは **読み手の質問順** に章立てから書き直したもの。

## 章一覧

順次拡充中。詳細な章設計は `meta/topics-plan-feature.md` を参照。

主要章へのリンク:

- Foundation: [01 Overview](01-overview/index.md) / [20 SWSS / SAI / Redis](20-swss-sai-redis/index.md)
- L3: [02 BGP](02-bgp/index.md) / [03 VXLAN / EVPN](03-vxlan-evpn/index.md) / [04 VRF / ECMP](04-vrf-ecmp/index.md)
- L2: [05 Dual-ToR](05-dual-tor/index.md) / [06 L2 / VLAN / LAG](06-l2-vlan-lag/index.md)
- Policy: [07 ACL / CoPP / Mirror](07-acl-copp-mirror/index.md) / [08 QoS / Buffer](08-qos-buffer/index.md)
- Observe: [09 Telemetry / SNMP](09-telemetry-snmp/index.md) / [10 gNMI / OpenConfig](10-gnmi-openconfig/index.md)
- Lifecycle: [11 Reboot](11-reboot/index.md) / [19 Build / Packaging](19-build-packaging/index.md) / [21 Lab / VS](21-lab-vs-developer/index.md)
- Extension: [12 Multi-ASIC / VOQ](12-multi-asic-voq/index.md) / [13 DASH / SmartSwitch](13-dash-smartswitch/index.md) / [17 SRv6 / MPLS](17-srv6-mpls/index.md) / [18 P4 / PINS](18-p4-pins/index.md)
- Periphery: [14 Platform / Optics](14-platform-port-optics/index.md) / [15 Security / AAA](15-security-aaa/index.md) / [16 NAT / DHCP / DNS](16-nat-dhcp-dns/index.md) / [22 Reference Index](22-reference-index/index.md)

## 読み進め方マップ

22 章の依存関係を、カテゴリ別の色分けと **前提 (実線)** / **派生・補完 (点線)** の 2 種類のエッジで示す。読み方の指針は次のとおり。

- **Foundation (黄)**: `01-overview` と `20-swss-sai-redis` は他章のほぼ全ての前提となる土台。
- **L3 core (青)**: `02-bgp` / `03-vxlan-evpn` / `04-vrf-ecmp` は L3 の中核。
- **L2 core (緑)**: `05-dual-tor` / `06-l2-vlan-lag` は L2 の中核。
- **Policy (橙)**: `07-acl-copp-mirror` / `08-qos-buffer` は転送ポリシー。
- **Observe (紫)**: `09-telemetry-snmp` / `10-gnmi-openconfig` は観測と北向き API。
- **Lifecycle (灰)**: `11-reboot` / `19-build-packaging` / `21-lab` はビルドからリブートまでのライフサイクル。
- **Extension (桃)**: `12-multi-asic-voq` / `13-dash-smartswitch` / `17-srv6-mpls` / `18-p4-pins` は拡張トポロジと programmability。
- **Periphery (薄灰)**: `14-platform-port-optics` / `15-security-aaa` / `16-nat-dhcp-dns` / `22-reference-index` は周辺基盤と索引。

向きは左→右、上→下に統一し、Foundation → core → Policy/Observe → Extension の順に層を積む。

```mermaid
graph LR
  subgraph FOUND["Foundation (土台)"]
    direction TB
    C01["<b>01 Overview</b><br/>全体像と設定基盤"]
    C20["<b>20 SWSS / SAI / Redis</b><br/>内部実装の土台"]
  end

  subgraph L3["L3 core (経路)"]
    direction TB
    C04["<b>04 VRF / ECMP</b><br/>RIB と FIB"]
    C02["<b>02 BGP / FRR</b><br/>外部経路"]
    C03["<b>03 VXLAN / EVPN</b><br/>オーバレイ"]
  end

  subgraph L2["L2 core (転送)"]
    direction TB
    C06["<b>06 L2 / VLAN / LAG</b><br/>ブリッジング"]
    C05["<b>05 Dual-ToR</b><br/>高可用 ToR"]
  end

  subgraph POL["Policy (制御)"]
    direction TB
    C07["<b>07 ACL / CoPP / Mirror</b><br/>選別とミラー"]
    C08["<b>08 QoS / Buffer</b><br/>PFC と輻輳制御"]
  end

  subgraph OBS["Observe (観測)"]
    direction TB
    C09["<b>09 Telemetry / SNMP</b><br/>カウンタ集約"]
    C10["<b>10 gNMI / OpenConfig</b><br/>北向き API"]
  end

  subgraph EXT["Extension (拡張)"]
    direction TB
    C12["<b>12 Multi-ASIC / VOQ</b><br/>シャーシ"]
    C13["<b>13 DASH / SmartSwitch</b><br/>SDN appliance"]
    C17["<b>17 SRv6 / MPLS</b><br/>ラベル転送"]
    C18["<b>18 P4 / PINS</b><br/>programmable"]
  end

  subgraph LC["Lifecycle (運用)"]
    direction TB
    C11["<b>11 Reboot / Upgrade</b><br/>warm/fast/cold"]
    C19["<b>19 Build / Packaging</b><br/>image build"]
    C21["<b>21 Lab / Virtual SONiC</b><br/>VS / KVM"]
  end

  subgraph PER["Periphery (周辺)"]
    direction TB
    C14["<b>14 Platform / Optics</b><br/>port / PHY"]
    C15["<b>15 Security / AAA</b><br/>認証認可"]
    C16["<b>16 NAT / DHCP / DNS</b><br/>サービス系"]
    C22["<b>22 Reference Index</b><br/>CLI / DB / YANG 索引"]
  end

  %% 強い前提 (実線、太線は土台→中核)
  C01 ==> C20
  C20 ==> C04
  C20 ==> C07
  C20 ==> C08
  C04 --> C02
  C02 --> C03
  C04 --> C03
  C06 --> C05
  C03 --> C05
  C14 --> C06
  C14 --> C08
  C09 --> C10
  C04 --> C17
  C02 --> C17
  C20 --> C13
  C03 --> C13
  C20 --> C12
  C02 --> C12
  C20 --> C18
  C10 --> C18
  C21 --> C19
  C01 --> C22

  %% 派生・補完 (点線)
  C08 -.-> C07
  C11 -.-> C19
  C04 -.-> C16
  C20 -.-> C09
  C20 -.-> C11
  C15 -.-> C10
  C22 -.-> C10

  classDef found fill:#fff3cd,stroke:#856404,stroke-width:2px,color:#000;
  classDef l3 fill:#d1ecf1,stroke:#0c5460,stroke-width:2px,color:#000;
  classDef l2 fill:#d4edda,stroke:#155724,stroke-width:2px,color:#000;
  classDef policy fill:#ffe0b2,stroke:#8a4b00,stroke-width:1.5px,color:#000;
  classDef observe fill:#e8d5f0,stroke:#4b0082,stroke-width:1.5px,color:#000;
  classDef extension fill:#fde2e4,stroke:#a83279,stroke-width:1.5px,color:#000;
  classDef lifecycle fill:#e2e3e5,stroke:#41464b,stroke-width:1.5px,color:#000;
  classDef periphery fill:#f5f5f5,stroke:#666,stroke-width:1px,color:#000;

  class C01,C20 found;
  class C02,C03,C04 l3;
  class C05,C06 l2;
  class C07,C08 policy;
  class C09,C10 observe;
  class C12,C13,C17,C18 extension;
  class C11,C19,C21 lifecycle;
  class C14,C15,C16,C22 periphery;
```

各章の `index.md` 末尾「関連する章」と `concept.md` 末尾「この章の前提知識」も合わせて参照すること。

<!-- glossary-links-injected: 167700005048 -->
