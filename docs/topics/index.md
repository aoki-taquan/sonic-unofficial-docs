---
title: 読み物
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
related:
  config_db: []
  cli: []
  yang: []
---

# 読み物（章立て駆動）

機能ドメイン単位で複数の HLD・実コードを横断統合した「読み物」章群。HLD 1 件 = 1 ページの reference（`docs/<area>/`）に対し、こちらは **読み手の質問順** に章立てから書き直したもの。

## 章一覧

順次拡充中。詳細な章設計は `meta/topics-plan-feature.md` を参照。

## 読み進め方マップ

22 章の依存関係を、**前提（実線）** と **派生（点線）** の 2 種類で示す。`01-overview` と `20-swss-sai-redis` は他章のほぼ全ての前提となる土台。`02-bgp` / `03-vxlan-evpn` / `04-vrf-ecmp` は L3 系の中核、`06-l2-vlan-lag` / `05-dual-tor` は L2 系の中核、`07-08` は転送ポリシー、`09-10` は観測、`11/19/21` はライフサイクル、`12-13-17-18` は拡張トポロジと programmability、`14-15-16-22` は周辺基盤と索引である。

```mermaid
graph LR
  C01["01 全体像と設定基盤"]
  C20["20 SWSS/SAI/Redis"]
  C02["02 BGP/FRR"]
  C03["03 VXLAN/EVPN"]
  C04["04 VRF/ECMP/RIB-FIB"]
  C05["05 Dual-ToR"]
  C06["06 L2/VLAN/LAG"]
  C07["07 ACL/CoPP/Mirror"]
  C08["08 QoS/Buffer/PFC"]
  C09["09 Telemetry/SNMP"]
  C10["10 gNMI/OpenConfig"]
  C11["11 Reboot/Upgrade"]
  C12["12 Multi-ASIC/VOQ"]
  C13["13 DASH/SmartSwitch"]
  C14["14 Platform/Port/Optics"]
  C15["15 Security/AAA"]
  C16["16 NAT/DHCP/DNS"]
  C17["17 SRv6/MPLS"]
  C18["18 P4/PINS"]
  C19["19 Build/Packaging"]
  C21["21 Lab/Virtual SONiC"]
  C22["22 リファレンス索引"]

  C01 --> C02
  C01 --> C03
  C01 --> C04
  C01 --> C05
  C01 --> C06
  C01 --> C07
  C01 --> C08
  C01 --> C09
  C01 --> C10
  C01 --> C11
  C01 --> C12
  C01 --> C13
  C01 --> C14
  C01 --> C15
  C01 --> C16
  C01 --> C17
  C01 --> C18
  C01 --> C20
  C01 --> C21
  C01 --> C22

  C20 --> C04
  C20 --> C07
  C20 --> C08
  C20 --> C09
  C20 --> C11
  C20 --> C12
  C20 --> C13
  C20 --> C18

  C04 --> C02
  C04 --> C03
  C04 --> C16
  C04 --> C17
  C04 --> C05

  C02 --> C03
  C02 --> C12
  C02 --> C17

  C14 --> C06
  C14 --> C08

  C06 --> C05
  C06 --> C03

  C03 --> C13
  C03 --> C05

  C09 --> C10
  C10 --> C18

  C21 --> C19

  C02 -.-> C03
  C03 -.-> C13
  C04 -.-> C17
  C10 -.-> C18
  C08 -.-> C07
  C11 -.-> C19

  classDef base fill:#fff3cd,stroke:#856404;
  classDef core fill:#d1ecf1,stroke:#0c5460;
  class C01,C20 base;
  class C02,C03,C04,C06 core;
```

各章の `index.md` 末尾「関連する章」と `concept.md` 末尾「この章の前提知識」も合わせて参照すること。


