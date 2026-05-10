---
title: Dual-ToR の考え方
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/overlay/active-active-dual-tor.md
  - docs/overlay/active-standby-dual-tor.md
  - docs/categories/dual-tor.md
---

# Dual-ToR の考え方

Dual-ToR は、1 台のサーバを 2 台の ToR に接続し、ToR / リンク / ケーブルの障害でもサーバ到達性を維持するための構成です。SONiC ではこの冗長性を `MUX_CABLE`、`linkmgrd`、`MuxOrch`、Y-cable または SoC NIC との制御経路で実現します。

まず分けて考えるべき点は、サーバに向かう下り方向を「片側だけが受け持つ」のか「両側が同時に受け持つ」のかです。これが Active-Standby と Active-Active の違いです。

## Active-Standby は何を解くか

Active-Standby では、サーバ NIC と 2 台の ToR の間に smart Y-cable があり、mux の向きが active ToR を決めます。standby ToR は通常、サーバ宛の下りトラフィックを直接サーバへ送らず、peer ToR へ IPinIP tunnel で戻します。障害時には standby 側が active へ昇格し、サーバ側リンクを生かしたまま転送面を切り替えます。

この方式の中心は「どちらが active か」を明確に 1 つに決めることです。`linkmgrd` は ICMP heartbeat、物理リンク、mux 方向を見て状態遷移を決めます。`MuxOrch` は active / standby に応じて neighbor や route の nexthop を直接サーバ向けまたは tunnel 向けに切り替えます。

## Active-Active は何を変えるか

Active-Active では、両 ToR が常時トラフィックを処理します。サーバ NIC は 2 本のリンクを使い、northbound は 5-tuple などで分散し、必要な制御パケットは両リンクへ複製します。従来の I2C ベースの Y-cable 制御ではなく、ToR と SoC NIC の間で gRPC による forwarding state 制御を使う点が大きな違いです。

Active-Active でも `linkmgrd` はリンク健全性を見ますが、状態判断は各 ToR がより独立に行います。障害を検知した側だけが standby 相当の forwarding state に倒れ、復旧後に active へ戻る、という整理になります。

## どちらを選ぶか

| 観点 | Active-Standby | Active-Active |
|---|---|---|
| 通常時の帯域 | 片側リンク分 | 両リンク分 |
| ケーブル / NIC 制御 | smart Y-cable、I2C、ycabled | SoC NIC、gRPC |
| 障害時の基本動作 | standby が active へ昇格 | 不健全な側だけ forwarding を止める |
| 下りの standby 経路 | IPinIP tunnel で peer へ戻す | NIC 側の分散 / forwarding state が中心 |
| 設計上の注意 | tunnel、neighbor、route 更新の整合 | gRPC channel、SoC state、peer link state |

既存の Active-Standby は「片側 active」を前提にした経路制御が多く、tunnel、prefix-based neighbor、multi-nexthop route のループ回避が重要です。Active-Active は帯域効率を上げますが、NIC / SoC 側の制御と観測点が増えるため、gRPC client と forwarding state の切り分けが必要になります。

## まず押さえる用語

| 用語 | 意味 |
|---|---|
| `MUX_CABLE` | server-facing port ごとの Dual-ToR 設定。`cable_type`、`state`、サーバ IP、SoC IP、neighbor mode を持つ |
| mux state | active / standby / auto / manual / detach などの論理状態 |
| link prober | サーバ NIC への ICMP heartbeat で self / peer の到達性を見る `linkmgrd` の機能 |
| MuxTunnel | standby ToR がサーバ宛トラフィックを peer ToR へ戻す IPinIP tunnel |
| prefix-based neighbor | neighbor を残したまま `/32` / `/128` route の nexthop だけを切り替える方式 |

## 関連ページ

- [Active-Standby Dual ToR](../../overlay/active-standby-dual-tor.md)
- [Active-Active Dual ToR](../../overlay/active-active-dual-tor.md)
- [Dual-ToR 関連](../../categories/dual-tor.md)
