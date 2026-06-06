---
title: アーキテクチャ
description: SRv6 / MPLS / Path Tracing を SONiC の共通 2 系統データ経路 (CONFIG_DB → orchagent → SAI と FRR/netlink → fpmsyncd → APP_DB → orchagent → SAI) に当てはめて読む章扉。
area: topics
verification: code-verified
last_verified: 2026-06-06
sources:
- repo: sonic-net/sonic-swss
  path: orchagent/srv6orch.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-swss
  path: orchagent/srv6orch.h
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-swss
  path: fpmsyncd/routesync.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-swss
  path: orchagent/portsorch.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-buildimage
  path: src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py
  ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
- repo: sonic-net/sonic-utilities
  path: show/srv6.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  cli:
  - show srv6
  - show srv6 locators
  - show srv6 static-sids
  - show srv6 stats
  config_db:
  - SRV6_MY_LOCATORS
  - SRV6_MY_SIDS
  - SRV6_MY_SID_TABLE
  - SRV6_SID_LIST
  - SRV6_POLICY
  - SRV6_STEER
  - CRM
  yang:
  - sonic-srv6
  - sonic-interface
  - sonic-port
  - sonic-crm
---

# アーキテクチャ

[SRv6](../../reference/glossary.md#term-srv6) / [MPLS](../../reference/glossary.md#term-mpls) / Path Tracing は別機能ですが、[SONiC](../../reference/glossary.md#term-sonic) 内部では「[CONFIG_DB](../../reference/glossary.md#term-config_db) → [orchagent](../../reference/glossary.md#term-orchagent) → [SAI](../../reference/glossary.md#term-sai) → [ASIC](../../reference/glossary.md#term-asic)」「[FRR](../../reference/glossary.md#term-frr)/netlink → [fpmsyncd](../../reference/glossary.md#term-fpmsyncd) → APP_DB → orchagent → SAI」という同じ 2 系統のデータ経路に乗ります。ここでは feature ごとの object flow を、その共通図に当てはめて読みます。

## SRv6 の object flow

SRv6 の中核は `srv6orch` で、APP_DB の `SRV6_MY_SID_TABLE` / `SRV6_SID_LIST` / `SRV6_POLICY` / `SRV6_STEER` を読み、SAI の `SAI_MY_SID_ENTRY_*` や `SAI_OBJECT_TYPE_SRV6_SIDLIST` を組み立てます。Static SID 経路では `bgpcfgd` の `SRv6Mgr` が CONFIG_DB の `SRV6_MY_LOCATORS` / `SRV6_MY_SIDS` を受け、`vtysh` で FRR に `segment-routing srv6 static-sids` を書き込みます[^srv6mgr]。

[^srv6mgr]: `SRv6Mgr` のテーブル購読定義は `sonic-net/sonic-buildimage` の `src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py` (`SRV6_MY_SIDS` / `SRV6_MY_LOCATORS` の subscribe、ref 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd) を参照。

```mermaid
flowchart LR
  CFG[CONFIG_DB<br/>SRV6_MY_LOCATORS / SRV6_MY_SIDS] --> SMGR[bgpcfgd<br/>SRv6Mgr]
  SMGR -->|vtysh| FRR[FRR zebra / mgmtd]
  FRR -->|netlink| FPM[fpmsyncd]
  CFG2[APP_DB<br/>SRV6_MY_SID_TABLE / SRV6_SID_LIST / SRV6_POLICY / SRV6_STEER] --> SRC[srv6orch]
  FPM --> APP[APP_DB<br/>SRV6_MY_SID / route]
  APP --> SRC
  SRC -->|MY_SID_ENTRY<br/>SRV6_SIDLIST<br/>NEXT_HOP| SAI[SAI / syncd]
  SAI --> ASIC[ASIC]
```

`srv6orch` の `end_behavior_map` には `end` / `end.x` / `end.t` / `end.dx4` / `end.dx6` / `end.dt4` / `end.dt6` / `end.dt46` / `end.b6.encaps` / `end.b6.encaps.red` / `end.b6.insert` / `end.b6.insert.red` / `un` / `ua` / `udt4` / `udt6` / `udt46` / `udx4` / `udx6` の 19 エントリが登録されており、それぞれ `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_*` にマップされます[^endmap]。Phase 1 では `END` / `END.DT46` / `H.Encaps.Red`、uSID [HLD](../../reference/glossary.md#term-hld) で `uN` / `uA` / `uDT*` / `uDX*` が追加され、L3Adj HLD で `uA` / `End.X` 系の出口 nexthop 処理が完成しました。

[^endmap]: 完全なリストは `sonic-net/sonic-swss` の `orchagent/srv6orch.cpp` L41-L62 (ref 4305596156d70e9797e8a881b3d19b46de0bce0d) を参照。`end_flavor_map` は別表で、`end` / `end.x` / `end.t` / `ua` が PSP_AND_USD、`un` のみ NONE。

## L3 隣接の解決

`uA` / `End.X` / `uDX4` / `uDX6` / `End.DX4` / `End.DX6` のような cross-connect 系 behavior は出口に L3 隣接が必須です。`srv6orch` は `m_pendingSRv6MySIDEntries` という `NextHopKey` をキーにした pending queue を持ち、Neighbor 未解決時は SID 投入を保留、Neighbor が確定したタイミングで queue を flush し、`SAI_MY_SID_ENTRY_ATTR_NEXT_HOP_ID` を SAI に渡します[^pending]。これにより「先に SID を CONFIG_DB に書いて、後から neighbor が上がる」順序にも耐えます。

[^pending]: `m_pendingSRv6MySIDEntries` の宣言は `sonic-net/sonic-swss` の `orchagent/srv6orch.h` L277、flush/insert ロジックは `orchagent/srv6orch.cpp` L1227-L1259, L1341, L1533-L1541 を参照。

## SRv6 VPN / Policy

L3VPN over SRv6 では `srv6orch` 内部の `srv6_prefix_agg_id_table_` が VPN prefix を AGG_ID にまとめ、`createSrv6Vpn` / `deleteSrv6Vpn` で VPN encap mapper を介して `vpn_sid` を route nexthop に紐付けます。SRv6 Policy は SID list と steering 条件を別オブジェクトとして持ち、`SRV6_STEER` がトリガで対応 SID list を選ぶ構造です。

## MPLS の pipeline

MPLS は AF_MPLS という別 family を扱うため、IPv4/IPv6 routing と並走する経路を持ちます。

```mermaid
flowchart LR
  CFG[CONFIG_DB<br/>INTERFACE.mpls / VLAN_INTERFACE.mpls] --> INTF[intfmgrd / IntfMgr]
  FRR[FRR LDP/static] -->|netlink AF_MPLS| FPM[fpmsyncd]
  FPM -->|APP_LABEL_ROUTE_TABLE| APP[APP_DB<br/>LABEL_ROUTE_TABLE]
  APP --> RO[routeorch / MPLS pipeline]
  RO --> SAI[SAI<br/>SAI_OBJECT_TYPE_INSEG_ENTRY]
  SAI --> ASIC[ASIC]
  CRM[CRM] --- RO
```

`fpmsyncd` は `AF_MPLS` の route と `LWTUNNEL_ENCAP_MPLS` の attribute から push label stack を取り出し、APP_DB の `LABEL_ROUTE_TABLE` に流します[^fpmmpls]。orchagent 側で in-segment entry を bulk programming することで、大規模な静的 LSP でも load を抑える設計です。

[^fpmmpls]: `sonic-net/sonic-swss` の `fpmsyncd/routesync.cpp` で `m_label_routeTable` を `APP_LABEL_ROUTE_TABLE_NAME` で初期化 (L158)、`AF_MPLS` 分岐 (L2066)、`LWTUNNEL_ENCAP_MPLS` の RTA_DST 解釈 (L2914) を確認。

## Path Tracing の挿入点

Path Tracing Midpoint は forwarding そのものを変えず、出口 port 単位で HbH-PT に書き込む MCD を決めます。`PORT|<port>` の `pt_interface_id` と `pt_timestamp_template` を `portmgrd` / `orchagent` が SAI の `SAI_PORT_ATTR_PATH_TRACING_INTF` / `SAI_PORT_ATTR_PATH_TRACING_TIMESTAMP_TYPE` に渡し、ASIC 側が IPv6 出力時に HbH-PT に MCD を追記します[^ptattr]。Timestamp template は `12_19` のようにビット幅指定で、TimeSeries DB 側の解像度と合わせます。

[^ptattr]: 両 attribute の SAI capability 照会と set パスは `sonic-net/sonic-swss` の `orchagent/portsorch.cpp` L579-L580, L624-L625, L1420, L1435, L11487, L11507 を参照。

SRv6 endpoint 処理は HbH-PT の有無に関わらず動くため、Path Tracing は SRv6 と直交して有効化できます。逆に言うと「SRv6 endpoint で IPv6 ヘッダが書き換わる場面でも HbH option が継承されるか」は ASIC 実装依存で、運用前に確認すべき項目です。

## 共通する topic

- **counter** — SRv6 の MySID counter（後続 phase）、MPLS の in-segment 統計、router interface counter は同じ flex counter / counterd 系基盤に乗ります。[02 BGP の運用](../02-bgp/operations.md) で扱う FRR 経路と区別するには、APP_DB / netlink どちらから入った route かを見ます。
- **[CRM](../../reference/glossary.md#term-crm)** — MPLS は `CRM` テーブルに in-segment / nexthop の使用量を加えています。SRv6 系は HLD 時点で CRM 統合がはっきり書かれていない領域があり、今後拡張される想定です。
- **[YANG](../../reference/glossary.md#term-yang)** — `sonic-srv6` が SRV6_MY_LOCATORS / SRV6_MY_SIDS を、`sonic-interface` 等が `mpls` 属性を、`sonic-port` が PT 関連属性を持ちます。設定ページからの逆引きはこの章で集約します。

## 関連ページ

- [SRv6 HLD](../../routing/segment-routing-over-ipv6-srv6-hld.md)
- [SRv6 SID の L3 隣接](../../routing/srv6-sid-l3adj.md)
- [SRv6 VPN](../../routing/srv6-vpn-hld.md)
- [SRv6 Static SID / Locator 設定](../../routing/static-configuration-of-srv6-in-sonic-hld.md)
- [SONiC の MPLS 基盤](../../routing/mpls-for-sonic-high-level-design-document.md)
- [Path Tracing Midpoint](../../routing/path-tracing-midpoint.md)

<!-- glossary-links-injected: ec18b66e3507 -->
