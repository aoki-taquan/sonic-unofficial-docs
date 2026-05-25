---
title: Dual-ToR の発展トピック
description: Dual-ToR の発展トピック — Dual-ToR は mux state だけで閉じた機能ではありません。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/overlay/dscp-remapping-for-tunnel-traffic.md
- docs/architecture/dhcpv6-relay-agent.md
related:
  cli:
  - clear
  - config vxlan
  - config bgp
  - show bgp
  - show pfc
  - show bfd
  - show arp
  config_db:
  - VLAN
  - DSCP_TO_TC_MAP
  - TC_TO_QUEUE_MAP
  - MUX_CABLE
  - VXLAN_TUNNEL
  - VXLAN_TUNNEL_MAP
  - VXLAN_EVPN_NVO
  yang:
  - sonic-vxlan
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-global
  - sonic-bgp-bbr
  - sonic-bgp-aggregate-address
---

# Dual-ToR の発展トピック

Dual-ToR は mux state だけで閉じた機能ではありません。standby ToR から peer ToR へ tunnel で戻す経路、DHCPv6 relay の送信元、[CoPP](../../reference/glossary.md#term-copp)、[QoS](../../reference/glossary.md#term-qos)、[PFC](../../reference/glossary.md#term-pfc) watchdog など、周辺機能が Dual-ToR 前提の分岐を持ちます。

このページでは、章の本筋から外れるものの、Dual-ToR を設計・運用するときに境界を理解しておきたい 2 つの機能を扱います。

## tunnel DSCP remap

Active-Standby では、standby ToR が受けたサーバ宛トラフィックを MuxTunnel で active ToR へ戻します。この「バウンスバック」経路が通常トラフィックと同じ queue / priority group を使うと、PFC pause が T1 と ToR の間で固着し、デッドロックを起こす可能性があります。

tunnel [DSCP](../../reference/glossary.md#term-dscp) remap は、encap 時に outer DSCP や queue を別系統へ移し、decap 時に tunnel 用の DSCP / TC / PG map を使うことで、通常経路とバウンスバック経路を分離する仕組みです。

運用上の読みどころは次の 3 つです。

| 観点 | 確認するもの |
|---|---|
| tunnel 設定 | `TUNNEL|MuxTunnel0` に decap / encap 用 QoS map が設定されているか |
| QoS map | `DSCP_TO_TC_MAP`、`TC_TO_PRIORITY_GROUP_MAP`、`TC_TO_QUEUE_MAP`、`TC_TO_DSCP_MAP` の tunnel 用エントリ |
| PFC watchdog | 追加 queue / PG が PFC と watchdog の対象として意図通り分かれているか |

この話は Dual-ToR の tunnel 経路がきっかけですが、詳細は QoS / PFC の設計に深く入ります。この章では「standby から peer へ戻す tunnel が QoS map を変えることがある」と覚えておけば十分です。

## DHCPv6 dual ToR loopback

DHCPv6 relay では、client の link-layer address を Option 79 として relay-forward に入れることが重要です。Dual-ToR ではさらに、relay-forward の送信元を [VLAN](../../reference/glossary.md#term-vlan) SVI ではなく loopback IP に固定するモードが関係します。

Active-Standby では、active ToR が relay-forward を送った後、応答が standby 側に届くような経路が発生し得ます。VLAN SVI を送信元にすると、どちらの ToR 宛の応答なのかが曖昧になります。loopback IP を送信元にすると、peer ToR は loopback 宛 IP を見て相手 ToR へ転送できます。

設定・確認の入口は DHCPv6 relay 側です。

```bash
config dhcp6relay option79 enable
config dhcp6relay use-loopback-address enable
show dhcp6relay_counters
sonic-clear dhcprelay_counters
```

この機能は mux state と隣接しますが、主役は DHCPv6 relay agent です。Dual-ToR 章では「relay の戻り経路が mux / peer ToR に依存するため、loopback source mode がある」と位置付けます。

## 章をまたぐ境界

| トピック | この章で扱う範囲 | 詳細を読む先 |
|---|---|---|
| DSCP remap | standby tunnel 経路が通常 queue と分離される理由 | QoS / PFC、tunnel QoS map |
| DHCPv6 loopback | Dual-ToR で relay 応答の戻り先を安定させる理由 | DHCPv6 relay、CoPP、RADV |
| [BFD](../../reference/glossary.md#term-bfd) | 上流到達性や [BGP](../../reference/glossary.md#term-bgp) 障害検出が mux 判断に影響する点 | Routing / BGP / BFD |
| ICMP offload | link prober の高速化 | Platform / [SAI](../../reference/glossary.md#term-sai) offload |

## 関連ページ

- [トンネルトラフィックの DSCP / TC リマップ](../../overlay/dscp-remapping-for-tunnel-traffic.md)
- [DHCPv6 Relay Agent](../../architecture/dhcpv6-relay-agent.md)

## 発展トピック

- **ICMP / link prober の hardware offload**: link prober は通常ソフトウェアで ICMP echo を送るが、[ASIC](../../reference/glossary.md#term-asic) offload を使うと sub-second の障害検出が可能になる。`linkmgrd` と SAI の検出加速機能の組合せを利用する。
- **Soft Dual-ToR / Active-Active mux**: Active-Standby から、両 ToR が同時に転送する Active-Active モデルへの拡張提案が継続している。[ARP](../../reference/glossary.md#term-arp) / ND の処理、[ECMP](../../reference/glossary.md#term-ecmp) の対称性、ECMP hash の双方向一致が論点。
- **per-VLAN mux state**: 単一 server に複数 VLAN がある場合、VLAN ごとに異なる active ToR を選ぶ拡張。トラフィックを業務単位で振り分ける運用シナリオで役立つ。
- **gRPC ベース peer state 同期**: 旧来の `app_db` 直書きから、明示的な peer 通信プロトコルへの移行が進む。`linkmgrd` のロジック分離と integration test が改善される方向。
- **mux split-brain protection**: peer 連絡不能時に両 ToR が active を主張するのを避けるため、追加判定（uplink BGP 状態、BFD、ICMP）を組み合わせる。

## 既知の制約と回避方法

- **mux toggle 中の transient packet loss**: [linkmgrd](../../reference/glossary.md#term-linkmgrd) が state を変える瞬間に ARP / [FDB](../../reference/glossary.md#term-fdb) の整合が遅れることがある。`config mux mode auto <port>` を試したあと、`show mux status` で両 ToR の見えが揃っているかを確認する。
- **CoPP の icmp rate limiting**: 大規模 link prober は icmp 受信を増やす。CoPP の bucket を `linkmgrd` 想定の rate に合わせないと、prober 自身を drop する。
- **PFC deadlock のリスク**: standby tunnel の outer DSCP を通常データと同じ TC に乗せると、PFC pause が peer ToR まで波及してリングを作る。tunnel DSCP remap で必ず別 PG / queue に逃がす。
- **DHCPv6 relay の loopback source 設定漏れ**: `use-loopback-address` を片側 ToR だけ有効にすると応答が落ちる。両 ToR で揃える運用ガイドが必要。

## 将来計画 / ロードマップ

- Active-Active モデルが進めば、mux state は ToR 間で対称となり、`MUX_CABLE` schema や `linkmgrd` の判定が刷新される。[HLD](../../reference/glossary.md#term-hld) では `dual-tor-active-active` 系の提案が議論段階。
- BFD / BGP unnumbered と link prober の責務統合は中長期テーマで、redundant signaling の冗長性をどう保つかが論点。
- [SmartSwitch](../../reference/glossary.md#term-smartswitch) の [DPU](../../reference/glossary.md#term-dpu) と Dual-ToR が組み合わさる構成 ([13 DASH](../13-dash-smartswitch/index.md)) では、[ENI](../../reference/glossary.md#term-eni) と mux state の同期方式が future work。

## 関連 RFC / 仕様書

- [RFC 3046](https://datatracker.ietf.org/doc/html/rfc3046) — [DHCP Relay](../../reference/glossary.md#term-dhcp-relay) Agent Information Option
- [RFC 6422](https://datatracker.ietf.org/doc/html/rfc6422) — DHCPv6 Relay-Supplied Options
- [RFC 5798](https://datatracker.ietf.org/doc/html/rfc5798) — VRRPv3 (Active/Standby の参考モデル)
- [RFC 7348](https://datatracker.ietf.org/doc/html/rfc7348) — [VXLAN](../../reference/glossary.md#term-vxlan) (tunnel DSCP の outer header 解釈)
- [IEEE 802.1Qbb](https://1.ieee802.org/dcb/) — Priority-based Flow Control

## upstream 開発の最新動向

- `sonic-linkmgrd` 配下では state machine のリファクタリングと test カバレッジ拡張が継続。ログのフォーマット改善 PR が運用負荷を下げる方向で進んでいる。
- DHCPv6 relay agent のループバック source、Option 79、counter export 周辺が community PR で議題に上がる頻度が高い。
- [DASH](../../reference/glossary.md#term-dash) / SmartSwitch との接続を見据え、mux state を外部 controller (NSM / SDN) と同期するインタフェース提案が散見される。

## ハンドオフ

- **概念とアーキテクチャ**は本章の [concept](concept.md) / [internals](internals.md) と、関連 HLD の [tunnel DSCP remap](../../overlay/dscp-remapping-for-tunnel-traffic.md), [DHCPv6 Relay Agent](../../architecture/dhcpv6-relay-agent.md) で完結する。linkmgrd state machine の論理と `APP_DB:MUX_CABLE_TABLE` の遷移は internals で詳細化済み。
- **設定とリファレンス**は [reference/cli](../../reference/cli/index.md) の `config mux`, `show mux`, `show muxcable` 系、および `MUX_CABLE`, `MUX_LINKMGR`, `TUNNEL` の各 [CONFIG_DB スキーマ](../../reference/config-db/index.md)、`sonic-mux*` [YANG](../../reference/glossary.md#term-yang) モジュールで網羅される。
- **本ページ** は tunnel DSCP remap / DHCPv6 loopback / link prober offload など、章境界をまたぐクロスオーバー領域と、Active-Active / SmartSwitch 連携といった発展トピックのみを扱う。

## トラブルシュート観点

- mux state が `unknown` のまま固着するときは、まず `show muxcable status` で peer 側の最新状態と、`linkmgrd` のログ (`/var/log/syslog` の `LINKMGRD` 行) を確認する。peer ToR への gRPC / ICMP 到達性、`LinkProber` の RTT 統計、`MUX_CABLE_RESPONSE_TABLE` の応答有無が決め手になる。
- standby 経由のバウンスバックで packet loss が発生するときは、`show pfc counters` と `show queue counters` で対象 PG / queue が tunnel 用にマップされているかを確認する。`DSCP_TO_TC_MAP|AZURE_TUNNEL` などの専用 map が抜けていると、通常 PG と衝突する。
- DHCPv6 が片側 ToR で取得できない場合は `show dhcp6relay_counters` を両 ToR で見比べる。`use-loopback-address` の片肺設定、または Option 79 の有無で relay-forward が破棄されているケースが多い。

## 検証パスとラボ要件

- linkmgrd の state machine 検証は `sonic-mgmt` の `dualtor` テストグループで実施する。`toggle_mux_status` / `link_flap` / `peer_down` の組合せを minute 単位で連続走行し、`MUX_CABLE_TABLE` の遷移と上流 BGP の収束時間 (target: < 1s) を計測する。
- tunnel DSCP remap の検証では、サーバ→standby ToR→active ToR→上流の経路で `tcpreplay` などにより 0.1〜10Gbps の負荷をかけ、`show queue counters` で tunnel 用 queue が分離されていること、PFC pause が通常経路へ波及しないことを確認する。
- DHCPv6 loopback source mode は両 ToR で同時に `use-loopback-address enable` を設定したうえで、client → relay-forward → server → relay-reply の Wireshark/`tcpdump` キャプチャを取得し、loopback IP が source として一貫しているかを点検する。

## 横断参照 (追補)

- [DSCP remapping for tunnel traffic](../../overlay/dscp-remapping-for-tunnel-traffic.md)
- [DHCPv6 Relay Agent](../../architecture/dhcpv6-relay-agent.md)
- [02 BGP: Dual-ToR の上流到達性と graceful drain](../02-bgp/index.md)
- [13 DASH / SmartSwitch: DPU と mux state の同期](../13-dash-smartswitch/index.md)
- [14 Platform / Port / Optics: link prober の hardware offload](../14-platform-port-optics/index.md)

<!-- glossary-links-injected: c006405759d8 -->
