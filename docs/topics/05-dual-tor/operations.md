---
title: Dual-ToR の運用
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/reference/cli/show-muxcable.md
  - docs/reference/cli/config-muxcable.md
  - docs/platform/icmp-hardware-offload.md
  - docs/routing/bfd-hw-offload.md
  - docs/routing/bfd-hw-offload-for-bgp-session.md
  - docs/routing/default-route.md
  - docs/routing/prefix-based-mux-neighbors.md
  - docs/routing/multiple-nexthop-route-hld.md
---

# Dual-ToR の運用

Dual-ToR の障害対応では、最初に「mux がどちらを向いているか」だけを見ると誤ります。サーバ側リンク、ICMP prober、Y-cable / SoC 制御、default route、MuxOrch の route programming が別々に壊れ得るためです。

## まず確認する順番

| 順番 | 確認 | 代表コマンド |
|---|---|---|
| 1 | 設定が対象 port に入っているか | `show muxcable config Ethernet0` |
| 2 | 論理 mux state と動的状態 | `show muxcable status Ethernet0` |
| 3 | HW / gRPC 側の実状態 | `show muxcable hwmode muxdirection Ethernet0`、`show muxcable grpc muxdirection Ethernet0` |
| 4 | tunnel 経路 | `show muxcable tunnel_route Ethernet0` |
| 5 | probe / cable health | `show muxcable health Ethernet0`、`show muxcable metrics Ethernet0` |
| 6 | packet loss / low-level error | `show muxcable packetloss Ethernet0`、BER / FEC 系 |

Active-Standby では `status` と HW mux direction の不一致が切り分けの入口になります。Active-Active では gRPC で見える forwarding state と、NIC / SoC 側の実転送状態が一致しているかが重要です。

## フェイルオーバー確認

自動フェイルオーバーを確認するときは、事前に `state` が `auto` であることを見ます。`manual` や明示的な `active` / `standby` で固定していると、default route 連動や link prober の結果が転送状態へ反映されないことがあります。

確認の流れは次のようになります。

1. 正常時の `show muxcable status`、`show muxcable tunnel_route`、サーバ到達性を記録する。
2. 片側の server-facing link、peer reachability、または default route を意図的に変化させる。
3. `status` の active / standby、tunnel route、packet loss counter、上流到達性を見る。
4. 復旧後に `auto` 状態へ戻り、prefix route の nexthop が直接 neighbor に戻ることを見る。

`config muxcable mode active|standby` は手動切替の確認に使えますが、障害注入テストと混ぜると原因が曖昧になります。テストケースごとに「自動制御を見ているのか、手動制御を見ているのか」を分けてください。

## ループ回避を見る

Active-Standby で複数 nexthop route が mux port をまたぐ場合、standby nexthop を含む ECMP がループを作る可能性があります。`MuxOrch` は active nexthop がある場合は単一 nexthop に絞り、全て standby なら tunnel に向ける設計です。

運用上は、問題の prefix がどの nexthop を持ち、それぞれがどの mux state の port に属するかを確認します。prefix-based neighbor を使っている場合、neighbor entry の有無だけでなく、サーバ `/32` / `/128` route の nexthop が直接 neighbor なのか tunnel なのかを見る必要があります。

## ICMP hardware offload

ICMP hardware offload は、Dual-ToR の link prober を NPU 側へ寄せ、検出時間を短縮するための仕組みです。software prober では raw socket とユーザ空間処理が入るため、数百 ms 程度の検出が下限になります。hardware prober では ICMP echo session を ASIC に作り、状態通知を `IcmpOrch` 経由で受けます。

運用者目線では、`prober_type` が hardware か software か、offload session が作成されているか、TLV 入り ICMP などソフトウェア処理に残る部分があるかを分けて見ます。高速検出を期待するなら、単に `MUX_CABLE` を入れるだけでなく、対象 ASIC / SAI / ICMP offload 機能の対応も前提です。

## BFD との関係

BFD hardware offload は Dual-ToR 専用機能ではありませんが、上流 BGP や peer 到達性の高速検出と組み合わせて、mux の安全な切替条件に影響します。BGP セッション向け BFD offload では FRR `bfdd`、`bfdsyncd`、`BfdOrch`、ASIC BFD engine の経路が関係します。

ここでの注意点は、BFD が下げるのは主に routing adjacency であり、mux state そのものではないことです。default route が消える、BGP が落ちる、上流到達性が無い、という結果が `linkmgrd` の default route 連動や route programming にどう反映されるかを見る必要があります。

## 関連ページ

- [show muxcable サブコマンド](../../reference/cli/show-muxcable.md)
- [config muxcable サブコマンド](../../reference/cli/config-muxcable.md)
- [ICMP Hardware Offload](../../platform/icmp-hardware-offload.md)
- [BFD ハードウェアオフロード](../../routing/bfd-hw-offload.md)
- [BGP セッション向け BFD ハードウェアオフロード](../../routing/bfd-hw-offload-for-bgp-session.md)
- [linkmgrd のデフォルトルート連動](../../routing/default-route.md)
- [プレフィックスルート方式の Mux ネイバ](../../routing/prefix-based-mux-neighbors.md)
- [multi-nexthop route ループ回避](../../routing/multiple-nexthop-route-hld.md)
