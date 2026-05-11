---
title: 内部実装
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/routing/segment-routing-over-ipv6-srv6-hld.md
  - docs/routing/sonic-usid.md
  - docs/routing/srv6-sid-l3adj.md
  - docs/routing/srv6-vpn-hld.md
  - docs/routing/static-configuration-of-srv6-in-sonic-hld.md
  - docs/routing/mpls-for-sonic-high-level-design-document.md
  - docs/routing/path-tracing-midpoint.md
---

# 内部実装

ここでは SRv6 / MPLS / Path Tracing の主要 daemon・ファイル・SAI 属性のうち、設計を理解する上で欠かせない部分を集約します。コード位置は元 HLD ページに紐付いており、verifier が裏取り済みです。

## srv6orch の構造

`sonic-swss/orchagent/srv6orch.cpp` / `srv6orch.h` が中核です。

- **end_behavior_map** — `end` / `end.dt4` / `end.dt6` / `end.dt46` / `un` / `ua` / `udt4` / `udt6` / `udt46` / `udx4` / `udx6` 等の文字列を、SAI の `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_*` に対応付けます。uSID 拡張で `uN` / `uA` / `uDT*` / `uDX*` が追加されています。
- **MY_SID_ENTRY 作成** — `createUpdateMysidEntry(my_sid_string, vrf, adj, end_action)` が SAI への投入入口です。L3 隣接が必要な behavior では `adj` から nexthop を解決し、`SAI_MY_SID_ENTRY_ATTR_NEXT_HOP_ID` に渡します。
- **pending queue** — `m_pendingSRv6MySIDEntries: map<NextHopKey, set<tuple<...>>>` が Neighbor 未解決の SID を保留します。Neighbor 確定時の `updateNeighbor` 系コールバックで pending を flush します。
- **VPN** — `srv6_prefix_agg_id_table_` が Prefix を AGG_ID に集約、`createSrv6Vpn` / `deleteSrv6Vpn` が VPN encap mapper と `vpn_sid` を route nexthop に紐付けます。
- **SID list** — `SAI_OBJECT_TYPE_SRV6_SIDLIST` で SID 列を 1 オブジェクト化し、policy で参照します。

## bgpcfgd の SRv6Mgr

Static SID / Locator は `src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py` の `SRv6Mgr` が処理します。

- `locators_set_handler` / `sids_set_handler` が CONFIG_DB の subscribe ハンドラ。
- locator 不在のまま SID が来ても、`SRV6_MY_LOCATORS` を subscribe して deferred 解決する経路を持ちます。
- 最終的に `vtysh -c "segment-routing" -c "srv6" -c "static-sids" -c "sid {} locator {} behavior {} vrf {}"` を発行して FRR に流し込みます。

`frrcfgd` 側では `SRV6_MY_LOCATORS` を `zebra`、`SRV6_MY_SIDS` を `mgmtd` に向けるターゲット daemon 設定があります。CONFIG_DB → FRR の中継経路が二重化されているわけではなく、各テーブルで担当 daemon が異なる構造です。

## MPLS データパス

`sonic-swss/fpmsyncd/routesync.cpp` が MPLS netlink を APP_DB に変換する入口です。

- `APP_LABEL_ROUTE_TABLE_NAME` を `ProducerStateTable` として開きます。
- `AF_MPLS` の netlink route を受け取り、`RTA_NEWDST` から MPLS NH label stack、`LWTUNNEL_ENCAP_MPLS` から encap label を取り出して APP_DB に書きます。
- APP_DB の `LABEL_ROUTE_TABLE` を orchagent 側が消費し、SAI `INSEG_ENTRY` を bulk で programming します。

per-RIF の MPLS 有効化（`INTERFACE.<intf>.mpls = enable`）は `intfmgrd` / `IntfMgr` が SAI の RIF 属性として渡し、ASIC が MPLS フレームを受理するかどうかを切り替えます。

## QoS との接続

`sonic-swss/orchagent/qosorch.cpp` の `m_qos_handler_map` に `CFG_MPLS_TC_TO_TC_MAP_TABLE_NAME` が登録され、`mpls_tc_to_tc_field_name` が `PORT_QOS_MAP` のフィールド名として参照されます。ハンドラは `QosOrch::handleMplsTcToTcTable` です。DSCP / TC / PG マップと同じ枠組みで MPLS TC が扱われるため、QoS 側の運用知識がそのまま使えます。

## Path Tracing の SAI 属性

Path Tracing Midpoint は SAI 側で port 属性として実装されています。

- `SAI_PORT_ATTR_PATH_TRACING_INTF` — `pt_interface_id` に対応。
- `SAI_PORT_ATTR_PATH_TRACING_TIMESTAMP_TYPE` — `pt_timestamp_template` に対応。値は `SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_12_19` のようにビット切り出し位置で命名されます。

orchagent 側の処理は port 系で、`sonic-swss/tests/test_port.py` に `test_PortPathTracing` として単体テストが存在します。

## SAI MY_SID_ENTRY の使い分け

SAI 視点では、SRv6 endpoint は `SAI_OBJECT_TYPE_MY_SID_ENTRY` 1 種類でほぼ表現されます。違いは behavior 属性と、cross-connect 系での `NEXT_HOP_ID` の有無です。uSID も SAI レベルでは behavior 値が増えただけで、データ構造の追加はありません。HLD レベルで複数に見えるものが SAI レベルで同じ object なのは、設定や運用で「同じ場所を見ればよい」という指針につながります。

## 関連ページ

- [SRv6 HLD](../../routing/segment-routing-over-ipv6-srv6-hld.md)
- [SRv6 uSID](../../routing/sonic-usid.md)
- [SRv6 SID の L3 隣接](../../routing/srv6-sid-l3adj.md)
- [SRv6 VPN](../../routing/srv6-vpn-hld.md)
- [SRv6 Static SID / Locator 設定](../../routing/static-configuration-of-srv6-in-sonic-hld.md)
- [MPLS HLD](../../routing/mpls-for-sonic-high-level-design-document.md)
- [Path Tracing Midpoint](../../routing/path-tracing-midpoint.md)
