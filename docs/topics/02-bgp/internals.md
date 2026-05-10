---
title: 内部実装
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 内部実装

BGP の内部実装トピックは、同じ「BGP の改善」でも狙っている問題が違う。大量 route 投入を速くするもの、障害時の収束を速くするもの、FIB 未導入 route の advertise を止めるもの、peer 変更を再起動なしで扱うものに分けて読む。

## 改善機能の比較

| 機能 | 改善する問題 | 主な層 | 設定面 |
| --- | --- | --- | --- |
| BGP Loading Optimization | 2M routes 級投入時の fpmsyncd/orchagent/sairedis 処理遅延 | fpmsyncd、orchagent、sairedis | 新規 CLI/CONFIG_DB なし |
| BGP PIC | 障害時に prefix 数 N に比例して再プログラムする遅さ | FRR、NhgOrch、ASIC NHG | HLD は architecture 中心 |
| Suppress FIB Pending | ASIC 未導入 route を先に advertise して traffic loop を起こす問題 | bgpd、zebra、fpmsyncd、orchagent | `DEVICE_METADATA` |
| BGP aggregate with BBR awareness | 集約 route と BBR/prefix-list の連動 | bgpcfgd、FRR | `BGP_AGGREGATE_ADDRESS` |
| dynamic peer modification | dynamic peer range の追加/削除を再起動なしで扱う | bgpcfgd、FRR templates、STATE_DB | `BGP_PEER_RANGE` など |

## 大量 route loading

BGP Loading Optimization は、BGP 自体の best path 計算ではなく、SONiC に route が流れ込んだ後の処理量を減らす。fpmsyncd の Redis pipeline flush、orchagent の ring buffer/assistant thread、sairedis async 化が主な論点である。小規模経路の即時性と大量経路の throughput のバランスが設計上の注意点になる。詳細は [BGP Loading Optimization](../../routing/bgp-loading-optimization-for-sonic.md) を参照する。

## 障害収束と PIC

BGP PIC は、prefix ごとに route を更新するのではなく、共有 nexthop group を更新して多くの prefix をまとめて切り替える発想である。FAST DOWNLOAD は NHG の hardware update、SLOW DOWNLOAD は制御プレーンの通常収束と捉えると読みやすい。NextHop Group 分離や階層 NHG の理解が前提になる。詳細は [BGP PIC](../../routing/bgp-prefix-independent-convergence-architecture-document.md) を参照する。

## FIB pending と advertise 抑止

Suppress FIB Pending は、route が FRR で best になっても ASIC へ入るまで peer に advertise しないための仕組みである。再起動直後や CRM/SAI エラーで FIB が遅れる場面では、control plane の到達性と data plane の到達性が一時的にずれる。これを FRR の `bgp suppress-fib-pending` と SONiC 側 offload feedback で縮める。

注意点は、これは「route install 失敗を完全に解決する」機能ではないこと。一度 install された後に dataplane から消えた route を自動 withdraw する範囲には制約がある。

## dynamic peer はどこが動的か

dynamic peer modification は、peer range や dynamic peer の変更時に FRR container 全体を大きく揺らさず、bgpcfgd が追加/削除用 template を使って反映する設計である。STATE_DB の `BGP_PEER_CONFIGURED_TABLE` により、どの dynamic peer が構成済みかを管理する。頻繁に peer が増減する fabric では、設定反映の粒度と既存 session への影響を確認する。

## 関連ページ

- [BGP Loading Optimization](../../routing/bgp-loading-optimization-for-sonic.md)
- [BGP PIC](../../routing/bgp-prefix-independent-convergence-architecture-document.md)
- [BGP Suppress FIB Pending](../../routing/bgp-suppress-announcements-of-routes-not-installed-in-hw.md)
- [BBR 連動の BGP ルート集約](../../routing/bgp-route-aggregation-with-bbr-awareness.md)
- [bgpcfgd の dynamic BGP peer 動的変更](../../routing/bgpcfgd-dynamic-peer-modification-support.md)
