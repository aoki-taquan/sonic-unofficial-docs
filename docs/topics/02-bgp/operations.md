---
title: 運用
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 運用

BGP の運用確認は、neighbor の状態確認だけでは足りない。route が FRR で選ばれているか、SONiC に渡っているか、ASIC に入ったか、外部監視に見えているかを分けて確認する。

## 状態確認の入口

| 見たいもの | 入口 |
| --- | --- |
| neighbor、RIB、AF ごとの BGP 状態 | [CLI: show bgp](../../reference/cli/show-bgp.md) |
| policy の適用元 | [CLI: show route-map](../../reference/cli/show-route-map.md) |
| BGP monitor protocol による外部収集 | [BMP](../../routing/bmp-for-monitoring-sonic-bgp-info.md) |
| SNMP CiscoBgp4MIB | [CiscoBgp4MIB の STATE_DB 経由化](../../routing/ciscobgp4mib-implementation-changes.md) |

`show bgp` は FRR 側の BGP 状態を見る。route がそこで best でも、ASIC への install 成功までは保証しない。転送面まで疑う場合は APPL_DB/ASIC_DB、orchagent ログ、syncd/SAI のエラーも見る。

## FIB に入らないときの切り分け

FIB 未導入時は次の順に狭める。

1. `show bgp ...` で peer から route を受け、best path になっているかを見る。
2. zebra/FPM から fpmsyncd へ route が流れているかを確認する。
3. APPL_DB の `ROUTE_TABLE` と `NEXTHOP_GROUP_TABLE` に期待する entry があるかを見る。
4. orchagent が route/nexthop group を処理し、SAI エラーを出していないかを見る。
5. Suppress FIB Pending が有効な構成では、offload 完了まで advertise が抑止されていないか確認する。

歴史的な Route Install Error Handling HLD は `ERROR_ROUTE_TABLE` と `FIB-install pending` 表示を提案しているが、現行実装とは乖離がある扱いで残っている。実運用では [BGP Suppress FIB Pending](../../routing/bgp-suppress-announcements-of-routes-not-installed-in-hw.md) と組み合わせて読む。

## BMP は何を見る機能か

BMP は BGP の Adj-RIB-In/Out や peer state を外部 collector に送るための監視機構である。SONiC では BMP_STATE_DB と FRR 側の BMP 有効化が関わる。Multi-ASIC や gNMI Streaming との接点もあるため、単なる `show bgp` の置き換えではなく、継続監視用の出口として読む。

## CiscoBgp4MIB はなぜ STATE_DB 経由か

CiscoBgp4MIB は SNMP から BGP neighbor 情報を見せるための互換面である。旧設計のように SNMP 実装が FRR の VTY socket に直接依存すると、daemon 間結合が強い。STATE_DB 経由化では `bgpmon` が FRR から情報を収集し、`NEIGH_STATE_TABLE` に書き、SNMP 側は DB を読む。運用上は、SNMP に出ない場合に FRR、bgpmon、STATE_DB、snmp_ax_impl のどこで止まっているかを分けて確認できる。

## 関連ページ

- [CLI: show bgp](../../reference/cli/show-bgp.md)
- [CLI: show route-map](../../reference/cli/show-route-map.md)
- [BMP](../../routing/bmp-for-monitoring-sonic-bgp-info.md)
- [CiscoBgp4MIB の STATE_DB 経由化](../../routing/ciscobgp4mib-implementation-changes.md)
- [BGP Route Install Error Handling](../../routing/bgp-route-install-error-handling.md)
- [BGP Suppress FIB Pending](../../routing/bgp-suppress-announcements-of-routes-not-installed-in-hw.md)
