---
title: 運用
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/routing/segment-routing-over-ipv6-srv6-hld.md
  - docs/routing/mpls-for-sonic-high-level-design-document.md
  - docs/routing/path-tracing-midpoint.md
  - docs/routing/router-interface-counters-in-sonic.md
---

# 運用

SRv6 / MPLS / Path Tracing の運用確認は、「設定が CONFIG_DB に正しく入ったか」「FRR / netlink 経由で APP_DB に渡ったか」「SAI / ASIC に programming されたか」の三段を順に追います。各 feature で必要な確認系の出口は次のとおりです。

## SRv6

1. `show runningconfiguration` / `redis-cli -n 4 HGETALL "SRV6_MY_SID_TABLE|<sid>"` で CONFIG_DB が期待どおりか確認します。Static SID 経路では `SRV6_MY_LOCATORS` / `SRV6_MY_SIDS` も合わせて見ます。
2. `vtysh -c "show segment-routing srv6 locator"` / `vtysh -c "show segment-routing srv6 sid"` で FRR 側に渡ったかを確認します。bgpcfgd の `SRv6Mgr` が `vtysh` 経由で投入する経路（[アーキテクチャ](architecture.md)）はここで切り分けます。
3. `redis-cli -n 0 KEYS "SRV6_MY_SID_TABLE:*"` で APP_DB を、`redis-cli -n 1 KEYS "ASIC_STATE:SAI_OBJECT_TYPE_MY_SID_ENTRY:*"` で ASIC_DB を確認すると、`srv6orch` が SAI に programming した範囲が見えます。
4. uA / End.X 系で「設定したのに反映されない」場合は、Neighbor が解決できていない可能性があります。`srv6orch` の pending queue に入ったままになっていないか、対応する nexthop の neighbor / route を確認します。
5. MySID counter / SRv6 traffic 量の確認は後続 phase 機能で、現状は IPv6 forwarding 全体の RIF counter で代用するのが現実的です（[router interface counter](../../routing/router-interface-counters-in-sonic.md)）。

## MPLS

1. `show interfaces mpls` 系（CLI 提供範囲は実装依存）で per-RIF の有効化状態を確認します。CONFIG_DB の `INTERFACE.<intf>.mpls` を直接見ても同じです。
2. `vtysh -c "show mpls table"` で FRR 側の LSP / in-segment を確認します。
3. APP_DB の `LABEL_ROUTE_TABLE` と ASIC_DB の `SAI_OBJECT_TYPE_INSEG_ENTRY` を redis-cli で見ると、`fpmsyncd` → orchagent → SAI の流れがどこで止まっているか切り分けられます。
4. CRM で `mpls_inseg` / `mpls_nexthop` の使用量を確認します。大規模静的 LSP では `crm config thresholds` をあらかじめ設定しておくと枯渇前に検出できます。
5. QoS の効きは `MPLS_TC_TO_TC_MAP` / `PORT_QOS_MAP` の組み合わせで決まります。MPLS パケットが期待した queue に乗らないときは、まず map の参照関係を確認します。

## Path Tracing

1. `show interface path-tracing` で `pt_interface_id` / `pt_timestamp_template` の現在値を確認します。CONFIG_DB の `PORT|<port>` を直接見ても同じです。
2. ASIC_DB の `SAI_PORT_ATTR_PATH_TRACING_INTF` / `SAI_PORT_ATTR_PATH_TRACING_TIMESTAMP_TYPE` を確認すると、orchagent が SAI に渡せているかが分かります。
3. probe 自体は SONiC 外側（PT Source / Sink / Regional Collector）で生成・回収するため、SONiC 側は「MCD が HbH-PT に書かれているか」を確認するためのキャプチャ環境を別途用意します。
4. SRv6 endpoint と Path Tracing を同時に有効化している場合、`H.Encaps.Red` で内側 IPv6 にカプセル化される際の HbH-PT の扱いは ASIC 実装依存です。経路上のすべての node で MCD が書かれているかを実トラフィックで確認します。

## 障害切り分けの順序

機能を問わず、次の順で潰すと迷いにくくなります。

1. **CONFIG_DB**: 設定が入っているか。
2. **APP_DB / netlink**: FRR / fpmsyncd / bgpcfgd の中継が動いているか。
3. **ASIC_DB**: orchagent が SAI に投げたか。
4. **ASIC counter**: パケットが本当に流れているか。
5. **キャプチャ**: ヘッダ・ラベル・HbH-PT の内容まで降りる。

特に SRv6 と MPLS は、route の入口（FRR vs CONFIG_DB 直書き）が複数あるため、APP_DB をスキップして CONFIG_DB と ASIC_DB だけ見ると「片方の経路が動いていることに気付けない」ことがあります。

## 関連ページ

- [router interface counters](../../routing/router-interface-counters-in-sonic.md)
- [MPLS HLD](../../routing/mpls-for-sonic-high-level-design-document.md)
- [Path Tracing Midpoint](../../routing/path-tracing-midpoint.md)
