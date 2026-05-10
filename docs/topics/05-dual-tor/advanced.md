---
title: Dual-ToR の発展トピック
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/overlay/dscp-remapping-for-tunnel-traffic.md
  - docs/architecture/dhcpv6-relay-agent.md
---

# Dual-ToR の発展トピック

Dual-ToR は mux state だけで閉じた機能ではありません。standby ToR から peer ToR へ tunnel で戻す経路、DHCPv6 relay の送信元、CoPP、QoS、PFC watchdog など、周辺機能が Dual-ToR 前提の分岐を持ちます。

このページでは、章の本筋から外れるものの、Dual-ToR を設計・運用するときに境界を理解しておきたい 2 つの機能を扱います。

## tunnel DSCP remap

Active-Standby では、standby ToR が受けたサーバ宛トラフィックを MuxTunnel で active ToR へ戻します。この「バウンスバック」経路が通常トラフィックと同じ queue / priority group を使うと、PFC pause が T1 と ToR の間で固着し、デッドロックを起こす可能性があります。

tunnel DSCP remap は、encap 時に outer DSCP や queue を別系統へ移し、decap 時に tunnel 用の DSCP / TC / PG map を使うことで、通常経路とバウンスバック経路を分離する仕組みです。

運用上の読みどころは次の 3 つです。

| 観点 | 確認するもの |
|---|---|
| tunnel 設定 | `TUNNEL|MuxTunnel0` に decap / encap 用 QoS map が設定されているか |
| QoS map | `DSCP_TO_TC_MAP`、`TC_TO_PRIORITY_GROUP_MAP`、`TC_TO_QUEUE_MAP`、`TC_TO_DSCP_MAP` の tunnel 用エントリ |
| PFC watchdog | 追加 queue / PG が PFC と watchdog の対象として意図通り分かれているか |

この話は Dual-ToR の tunnel 経路がきっかけですが、詳細は QoS / PFC の設計に深く入ります。この章では「standby から peer へ戻す tunnel が QoS map を変えることがある」と覚えておけば十分です。

## DHCPv6 dual ToR loopback

DHCPv6 relay では、client の link-layer address を Option 79 として relay-forward に入れることが重要です。Dual-ToR ではさらに、relay-forward の送信元を VLAN SVI ではなく loopback IP に固定するモードが関係します。

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
| BFD | 上流到達性や BGP 障害検出が mux 判断に影響する点 | Routing / BGP / BFD |
| ICMP offload | link prober の高速化 | Platform / SAI offload |

## 関連ページ

- [トンネルトラフィックの DSCP / TC リマップ](../../overlay/dscp-remapping-for-tunnel-traffic.md)
- [DHCPv6 Relay Agent](../../architecture/dhcpv6-relay-agent.md)
