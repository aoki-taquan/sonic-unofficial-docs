---
title: Route / Interface / Counter の確認
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/reference/cli/show-ip.md
  - docs/reference/cli/show-interfaces.md
  - docs/routing/router-interface-counters-in-sonic.md
  - docs/routing/sonic-route-flow-counter-design.md
  - docs/architecture/sonic-ip-interface-loopback-action.md
---

# Route / Interface / Counter の確認

L3 の障害調査では、最初に route だけを見ても原因を絞れません。VRF、interface、RIB、FIB、RIF counter、flow counter の順に、control-plane と data-plane の差を分けて確認します。

## 確認コマンドの順番

| 目的 | コマンド / 入口 | 見ること |
|------|----------------|----------|
| Interface 状態 | `show ip interfaces`、`show interfaces status` | L3 interface の IP、admin/oper、VRF bind 前提。 |
| FRR RIB | `show ip route` / `show ipv6 route` | FRR が route を選んでいるか。 |
| ASIC FIB | `show ip fib` | FIB に入っているか。RIB にあり FIB にない場合は orchagent 側を見る。 |
| BGP VRF | `show ip bgp vrf <vrf> ...` | dynamic route の入力側。 |
| RIF 統計 | `show interfaces counters rif` | RIF 単位の RX/TX packet / byte / error。 |
| Route flow | `show flowcnt-route stats` | route pattern に一致する traffic counter。 |
| Loopback action | `show ip interfaces loopback-action` | 同一 RIF 出戻りの drop / forward 設定。 |

`show ip` のコマンド体系は [show ip サブコマンド](../../reference/cli/show-ip.md)、物理 port や RIF counter 表示は [show interfaces サブコマンド](../../reference/cli/show-interfaces.md) を参照してください。

## RIB と FIB の差を分ける

`show ip route` に見える route は FRR RIB の状態です。`show ip fib` は FIB 側を見ます。RIB にあるのに FIB にない場合、次の順で確認します。

1. route の VRF が意図通りか。
2. next hop の interface が同じ VRF にあるか、または `nexthop-vrf` が意図通りか。
3. neighbor が解決しているか。
4. ECMP / NHG の member が作れる状態か。
5. ASIC resource や SAI エラーで route programming が失敗していないか。

BGP 由来 route の FIB 未導入や route install failure は BGP 章の運用ページも関係します。この章では L3 pipeline 側の前提、つまり RIF / NHG / RouteOrch の準備ができているかを見ます。

## RIF counter は L3 interface 単位で見る

port counter は L2 port の統計で、RIF counter は SAI router interface の統計です。L3 forwarding の RX/TX packet、octet、error を確認したい場合は [ルータインタフェース (RIF) カウンタ](../../routing/router-interface-counters-in-sonic.md) を入口にします。

同一 RIF から出戻る packet を drop する設定を使っている場合、drop は RIF counter の error 側に現れます。この挙動は [IP インタフェース ループバックアクション](../../architecture/sonic-ip-interface-loopback-action.md) と合わせて読みます。

## Route flow counter は対象 route を絞って見る

[Route Flow Counter](../../routing/sonic-route-flow-counter-design.md) は、route pattern に一致する route に Generic Counter を bind して hit / byte を見る設計です。全 route の統計を常時見る仕組みではなく、調査したい prefix pattern を指定して観測する機能として読みます。

このページは HLD-only として整理されています。利用可否や CLI の存在は対象ビルドで確認してください。

## Loopback action は誤転送の最後の防波堤

同じ RIF へ出戻る転送は、構成ミスや経路設計の不整合を示すことがあります。`loopback_action=drop` を設定すると ASIC で drop し、帯域消費やループを抑えられます。ただし、これは route 設計を直す代替ではありません。出戻りが見えたら、default route、VRF、next hop、ECMP member の設計も確認します。

## 関連ページ

- [CLI: show ip](../../reference/cli/show-ip.md)
- [CLI: show interfaces](../../reference/cli/show-interfaces.md)
- [ルータインタフェース (RIF) カウンタ](../../routing/router-interface-counters-in-sonic.md)
- [Route Flow Counter](../../routing/sonic-route-flow-counter-design.md)
- [IP インタフェース ループバックアクション](../../architecture/sonic-ip-interface-loopback-action.md)

