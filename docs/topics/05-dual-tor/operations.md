---
title: Dual-ToR の運用
description: Dual-ToR の運用 — Dual-ToR の障害対応では、最初に「mux がどちらを向いているか」だけを見ると誤ります。サーバ側リンク、ICMP
  prober、Y-cable / SoC 制御、default route、MuxOrch の route programming が別々に壊れ得るためです。
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
related:
  cli:
  - show muxcable
  - config muxcable
  - show interfaces
  - show ip
  - clear
  - show feature
  - show bfd
  config_db:
  - MUX_LINKMGR
  - VLAN
  - MUX_CABLE
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_NETWORK
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  - BGP_AGGREGATE_ADDRESS
  yang:
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-global
  - sonic-bgp-bbr
  - sonic-bgp-aggregate-address
  - sonic-bgp-sentinel
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

Active-Standby で複数 nexthop route が mux port をまたぐ場合、standby nexthop を含む [ECMP](../../reference/glossary.md#term-ecmp) がループを作る可能性があります。`MuxOrch` は active nexthop がある場合は単一 nexthop に絞り、全て standby なら tunnel に向ける設計です。

運用上は、問題の prefix がどの nexthop を持ち、それぞれがどの mux state の port に属するかを確認します。prefix-based neighbor を使っている場合、neighbor entry の有無だけでなく、サーバ `/32` / `/128` route の nexthop が直接 neighbor なのか tunnel なのかを見る必要があります。

## ICMP hardware offload

ICMP hardware offload は、Dual-ToR の link prober を [NPU](../../reference/glossary.md#term-npu) 側へ寄せ、検出時間を短縮するための仕組みです。software prober では raw socket とユーザ空間処理が入るため、数百 ms 程度の検出が下限になります。hardware prober では ICMP echo session を [ASIC](../../reference/glossary.md#term-asic) に作り、状態通知を `IcmpOrch` 経由で受けます。

運用者目線では、`prober_type` が hardware か software か、offload session が作成されているか、TLV 入り ICMP などソフトウェア処理に残る部分があるかを分けて見ます。高速検出を期待するなら、単に `MUX_CABLE` を入れるだけでなく、対象 ASIC / [SAI](../../reference/glossary.md#term-sai) / ICMP offload 機能の対応も前提です。

## BFD との関係

[BFD](../../reference/glossary.md#term-bfd) hardware offload は Dual-ToR 専用機能ではありませんが、上流 [BGP](../../reference/glossary.md#term-bgp) や peer 到達性の高速検出と組み合わせて、mux の安全な切替条件に影響します。BGP セッション向け BFD offload では [FRR](../../reference/glossary.md#term-frr) `bfdd`、`bfdsyncd`、`BfdOrch`、ASIC BFD engine の経路が関係します。

ここでの注意点は、BFD が下げるのは主に routing adjacency であり、mux state そのものではないことです。default route が消える、BGP が落ちる、上流到達性が無い、という結果が `linkmgrd` の default route 連動や route programming にどう反映されるかを見る必要があります。

## show muxcable の出力サンプル

`show muxcable grpc muxdirection Ethernet12` は gRPC 経由で NIC / peer 側の状態を取り、`Direction`、`Presence`、`PeerDirection`、`ConnectivityState` の 4 カラムを出します。

```text
Port        Direction    Presence    PeerDirection    ConnectivityState
----------  -----------  ----------  ---------------  -------------------
Ethernet12  active       True        active           READY
```

両側が `active` なのは split-brain の可能性があります。`active/standby` の組み合わせが正常で、`unknown` / `not_applicable` は Y-cable へのアクセス失敗を疑います。

`show muxcable hwmode muxdirection` は ASIC / Y-cable HW から取得した実状態のみを示します。

```text
Port        Direction    Presence
----------  -----------  ----------
Ethernet12  active       True
```

`show muxcable metrics Ethernet0` は [linkmgrd](../../reference/glossary.md#term-linkmgrd) / xcvrd の状態遷移タイムスタンプを並べます。

```text
PORT       EVENT                         TIME
---------  ----------------------------  ---------------------------
Ethernet0  linkmgrd_switch_active_start  2021-May-13 10:00:21.420898
Ethernet0  xcvrd_switch_standby_start    2021-May-13 10:01:15.690835
Ethernet0  xcvrd_switch_standby_end      2021-May-13 10:01:15.696051
Ethernet0  linkmgrd_switch_standby_end   2021-May-13 10:01:15.696728
```

`switch_*_start` と `switch_*_end` の差が切替遅延（数 ms〜数 100 ms）です。1 秒を超えるなら Y-cable / xcvrd を疑います。

`show muxcable packetloss Ethernet0` は link prober の連続失敗を集計します。

```text
PORT       COUNT                 VALUE
---------  ------------------  -------
Ethernet0  pck_loss_count          612
Ethernet0  pck_expected_count      840
PORT       EVENT                      TIME
---------  -------------------------  ---------------------------
Ethernet0  link_prober_unknown_start  2022-Jan-26 03:13:05.366900
Ethernet0  link_prober_unknown_end    2022-Jan-26 03:17:35.446580
```

`pck_loss_count / pck_expected_count` が 1 に近い場合、prober が完全に失敗していて切替判断が止まっています。

`show muxcable tunnel_route Ethernet0` は MuxOrch が tunnel に向けた server 向け `/32` route を kernel / asic 別に表示します。

```text
PORT        DEST_TYPE    DEST_ADDRESS    kernel    asic
----------  -----------  --------------  --------  ------
Ethernet0   server_ipv4  10.2.1.1        added     added
Ethernet4   server_ipv4  10.3.1.1        added     -
```

`asic=-` は ASIC への投入が完了していないか standby 側として意図的に空のケースです。kernel が added で asic が `-` なら SAI / route programming 失敗を疑います。

## 異常検出パターン

| 観測 | 疑う状態 | 一次切り分け |
|---|---|---|
| 両側 `Direction=active` | split-brain（peer 通信断 + 自律 active 化） | peer-link、ICCP-like、SoC link、`linkmgrd` 状態 |
| `state=auto` だが切替が起きない | link prober 停止、または `state` が実は manual | `show muxcable status`、`config muxcable mode auto` |
| `metrics` で `switch_*` 差が 1s 以上 | Y-cable / xcvrd 遅延、SoC busy | `xcvrd` ログ、firmware 不一致 |
| `pck_loss_count` が連続増加 | server-facing link / NIC firmware / ICMP filter | NIC 側 counter、`show interfaces counters` の Ethernet |
| `tunnel_route` の `asic=-` | MuxOrch SAI 失敗、tunnel object 不在 | [orchagent](../../reference/glossary.md#term-orchagent) / [muxorch](../../reference/glossary.md#term-muxorch) ログ、`show vxlan tunnel` |
| default route が消えても切替しない | linkmgrd の default-route 連動未設定 | `linkmgrd` config、BFD/BGP 上流連動 |
| ICMP offload 期待だが prober_type=software | ASIC / SAI 未対応、または `MUX_LINKMGR` 設定漏れ | `MUX_LINKMGR` table、`show muxcable status` の prober |
| `prefix-based mux neighbors` 構成で `/32` が neighbor でなく tunnel | mux state が standby、または neighbor 学習失敗 | `show muxcable status`、`show ip neighbor` |

## 典型的なログサンプル

linkmgrd / muxorch / xcvrd / IcmpOrch の代表ログ:

```text
linkmgrd: Mux port Ethernet0 transitioning to active due to LinkProberStateActive
linkmgrd: Mux port Ethernet0 transitioning to standby due to PeerWaitTimeout
linkmgrd: Default route nexthop went unreachable, forcing standby
xcvrd: Y-cable switch to active for port Ethernet0
xcvrd: Y-cable read NIC failed for port Ethernet0
muxorch: :- doTask: switch port Ethernet0 to active, install neigh and route to nexthop
muxorch: :- removeNextHopTunnel: delete NH tunnel for ip '10.2.1.1' failed
IcmpOrch: ICMP offload session create failed for port Ethernet0, SAI status -2
```

split-brain や fast-fail の検出に使う syslog 文字列:

```text
linkmgrd: Detected dual active on Ethernet0, forcing standby on local
linkmgrd: BFD session for upstream peer 10.0.0.1 went down
```

## 対応コマンド早見表

| 目的 | コマンド |
|---|---|
| 設定確認 | `show muxcable config [<port>]` |
| 論理状態 | `show muxcable status [<port>]` |
| gRPC 状態 | `show muxcable grpc muxdirection [<port>\|all]` |
| HW 状態 | `show muxcable hwmode muxdirection [<port>\|all]` |
| Tunnel route | `show muxcable tunnel_route [<port>]` |
| Cable health | `show muxcable health [<port>]` |
| Metric | `show muxcable metrics [<port>]` |
| Packetloss | `show muxcable packetloss [<port>]` |
| Cable info | `show muxcable cableinfo [<port>]` |
| Firmware | `show muxcable firmware version [<port>]` |
| 手動切替 | `config muxcable mode active\|standby \| auto\|manual <port>` |
| HW mode override | `config muxcable hwmode state active\|standby <port>` |
| Counter clear | `sonic-clear muxcable packetloss <port>` |
| ICMP offload | `show feature status \| grep icmp`、`MUX_LINKMGR` の `prober_type` |
| BFD HW offload | `show bfd summary`、`BFD_SESSION` の `hardware` フィールド |

## 関連 CONFIG_DB / STATE_DB / counter

- `CONFIG_DB:MUX_CABLE|<port>` — `state`（auto / active / standby / manual）、`server_ipv4`、`server_ipv6`、`soc_ipv4`、`soc_ipv6`、`cable_type`。
- `CONFIG_DB:MUX_LINKMGR|LINK_PROBER` — `interval_v4`、`interval_v6`、`positive_signal_count`、`negative_signal_count`、`prober_type`（software / hardware）。
- `APPL_DB:MUX_CABLE_TABLE:<port>` — linkmgrd 出力の現在 state（active / standby / unknown）。
- `STATE_DB:MUX_CABLE_TABLE|<port>` — `state`、`peer_state`、gRPC connectivity。
- `STATE_DB:HW_MUX_CABLE_TABLE|<port>` — HW 実状態。
- `STATE_DB:MUX_LINKMGR_TABLE|<port>` — link prober の現在値。
- `STATE_DB:LINK_PROBE_STATS|<port>` — `pck_loss_count`、`pck_expected_count`、unknown event タイムスタンプ。
- `APPL_DB:TUNNEL_ROUTE_TABLE:<port>` — server / soc 向け `/32` / `/128` の install 状態。
- `APPL_DB:NEIGH_TABLE` — mux active 時に再 install される neighbor。
- `COUNTERS_DB:COUNTERS_TUNNEL_NAME_MAP` — Dual-ToR tunnel encap counter。

## 横断参照

- 上流 BGP / BFD が落ちたときの mux 連動: [BGP 章 運用](../02-bgp/operations.md) と [VRF / ECMP 章 運用](../04-vrf-ecmp/operations.md) の default route / FIB 確認。
- Bounce-back 経路の [DSCP](../../reference/glossary.md#term-dscp) / [PFC](../../reference/glossary.md#term-pfc) は [Overlay 章 運用](../03-vxlan-evpn/operations.md) の DSCP remap。
- mux 配下 server の [VLAN](../../reference/glossary.md#term-vlan) / [FDB](../../reference/glossary.md#term-fdb) / Proxy [ARP](../../reference/glossary.md#term-arp) は [L2 章 運用](../06-l2-vlan-lag/operations.md)。
- mux / icmp / linkmgrd feature 自体が落ちている場合: [運用入口](../01-overview/operations.md) の feature 切り分け。

## 関連ページ

- [show muxcable サブコマンド](../../reference/cli/show-muxcable.md)
- [config muxcable サブコマンド](../../reference/cli/config-muxcable.md)
- [ICMP Hardware Offload](../../platform/icmp-hardware-offload.md)
- [BFD ハードウェアオフロード](../../routing/bfd-hw-offload.md)
- [BGP セッション向け BFD ハードウェアオフロード](../../routing/bfd-hw-offload-for-bgp-session.md)
- [linkmgrd のデフォルトルート連動](../../routing/default-route.md)
- [プレフィックスルート方式の Mux ネイバ](../../routing/prefix-based-mux-neighbors.md)
- [multi-nexthop route ループ回避](../../routing/multiple-nexthop-route-hld.md)

<!-- glossary-links-injected: 3baf0ec03624 -->
