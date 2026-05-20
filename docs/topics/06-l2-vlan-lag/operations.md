---
title: L2 運用確認
description: L2 運用確認 — L2 障害は「VLAN に入っていない」「LAG が期待通り up していない」「MAC 学習が古い」「MC-LAG
  peer と状態がずれている」「BUM traffic や link flap が制御面を壊している」に分けると追いやすくなります。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/reference/cli/show-vlan.md
- docs/reference/cli/show-mclag.md
- docs/switching/sonic-bum-storm-control.md
- docs/switching/link-event-damping-hld.md
- docs/switching/layer-2-forwarding-enhancements.md
- docs/switching/mclag-enhancements.md
related:
  cli:
  - show vlan
  - show interfaces
  - config vlan
  - config portchannel
  - config interface
  - show mclag
  - clear
  config_db:
  - VLAN_MEMBER
  - VLAN
  - VLAN_INTERFACE
  - PORTCHANNEL
  - PORTCHANNEL_MEMBER
  - PORT_STORM_CONTROL
  - PORTCHANNEL_INTERFACE
  yang:
  - sonic-portchannel
  - sonic-vlan
  - sonic-vlan-sub-interface
---

# L2 運用確認

L2 障害は「[VLAN](../../reference/glossary.md#term-vlan) に入っていない」「[LAG](../../reference/glossary.md#term-lag) が期待通り up していない」「MAC 学習が古い」「MC-LAG peer と状態がずれている」「BUM traffic や link flap が制御面を壊している」に分けると追いやすくなります。

## VLAN の状態を見る

まず VLAN と member の見え方を確認します。

```bash
show vlan brief
show vlan config
```

`show vlan brief` は VLAN ID、IP Address、Ports、Port Tagging、Proxy [ARP](../../reference/glossary.md#term-arp) を一覧します。`show vlan config` は 1 行 1 member で VLAN と member port を展開します。multi-[ASIC](../../reference/glossary.md#term-asic) 環境では namespace 指定の有無に注意します。

見るべき点は次の順です。

| 確認 | 観点 |
|---|---|
| VLAN が存在するか | `VLAN|Vlan<id>` が作られているか |
| member がいるか | `VLAN_MEMBER` に port / [PortChannel](../../reference/glossary.md#term-portchannel) が入っているか |
| tagged / untagged が期待通りか | access なら untagged、trunk なら tagged の組み合わせ |
| SVI が必要か | L3 gateway が必要なら `VLAN_INTERFACE` と IP があるか |

## LAG の状態を見る

PortChannel の設定は `config portchannel` と [CONFIG_DB](../../reference/glossary.md#term-config_db) の `PORTCHANNEL` / `PORTCHANNEL_MEMBER` が入口です。運用時は [LACP](../../reference/glossary.md#term-lacp)、member の admin / oper、`min_links` の条件、VLAN member への参加有無を分けて確認します。

削除や変更が失敗する場合は、PortChannel が VLAN member、L3 interface、DHCP relay 対象、または member を残した状態ではないかを先に確認します。

## MC-LAG の状態を見る

[SONiC](../../reference/glossary.md#term-sonic) では `show mclag` という Click サブコマンドではなく、実体は `mclagdctl` です。

```bash
mclagdctl dump state
mclagdctl dump portlist local
mclagdctl dump portlist peer
mclagdctl dump mac
mclagdctl dump arp
mclagdctl dump nd
mclagdctl dump unique_ip
```

単一 domain であれば `-i <domain_id>` を省略できます。複数 domain や明示確認が必要な場合は `mclagdctl -i <domain_id> ...` を使います。

確認順は、ICCP session、peer-link、local / peer portlist、remote MAC / ARP / ND、unique IP の順が実用的です。peer 側の情報は ICCP セッション断中に stale になる可能性があるため、`dump state` の結果を先に見ます。

## FDB の問題を切り分ける

MAC が期待と違う port に出る場合は、次を確認します。

| 症状 | 見る場所 |
|---|---|
| VLAN member 変更後に古い MAC が残る | [FDB](../../reference/glossary.md#term-fdb) flush の対象と static / dynamic の違い |
| PortChannel down 後に誤転送する | PortChannel 単位の dynamic FDB flush |
| STP topology change 後に片側へ流れ続ける | STP と FDB flush の連動 |
| MC-LAG で片側だけ MAC を知っている | `mclagdctl dump mac` と APP_MCLAG_FDB_TABLE の同期 |

詳細な flush 粒度と現行 CLI との差分は [L2 Forwarding 強化](../../switching/layer-2-forwarding-enhancements.md) を参照してください。

## BUM storm を抑える

Broadcast、Unknown-unicast、Unknown-multicast が多い場合は、物理ポート単位の storm control を使います。

```bash
config interface storm-control broadcast add Ethernet0 1000
config interface storm-control unknown-unicast add Ethernet0 2000
show storm-control interface Ethernet0
```

制限は物理ポートに対して設定します。VLAN や PortChannel interface に直接設定する機能として読まないことが重要です。

## Link flap を抑える

Link event damping は、ポート up/down が短時間に繰り返される場合に、SyncD 側でイベント通知を抑制する設計です。現行ページでは swss 側の実装は確認されている一方、[HLD](../../reference/glossary.md#term-hld) に書かれた CLI は未実装とされています。

運用手順としては、まず通常の interface state と transceiver / cable 健全性を確認し、damping を使う場合は [リンクイベントダンピング](../../switching/link-event-damping-hld.md) の実装との乖離を確認してください。

## show vlan / show interfaces の出力サンプル

`show vlan brief` は CONFIG_DB の `VLAN`、`VLAN_MEMBER`、`VLAN_INTERFACE` を結合したテーブル表示です。

```text
+-----------+-----------------+-----------------+----------------+-------------+
|   VLAN ID | IP Address      | Ports           | Port Tagging   | Proxy ARP   |
+===========+=================+=================+================+=============+
|      1000 | 192.168.0.1/21  | Ethernet4       | untagged       | disabled    |
|           | fc02:1000::1/64 | Ethernet8       | untagged       |             |
|           |                 | Ethernet12      | untagged       |             |
|           |                 | Ethernet16      | untagged       |             |
+-----------+-----------------+-----------------+----------------+-------------+
|      2000 | 192.168.0.10/21 | Ethernet24      | untagged       | enabled     |
|           | fc02:1011::1/64 | Ethernet28      | untagged       |             |
+-----------+-----------------+-----------------+----------------+-------------+
|      3000 |                 |                 |                | disabled    |
+-----------+-----------------+-----------------+----------------+-------------+
|      4000 |                 | PortChannel1001 | tagged         | disabled    |
+-----------+-----------------+-----------------+----------------+-------------+
```

`SONIC_CLI_IFACE_MODE=alias` のときは `Ethernet0` が `etp1` のような alias で出ます。VLAN ID 列が空の行（VLAN 3000）は member も IP も無い未使用 VLAN を示します。

`show interfaces portchannel` は PortChannel の状態を一覧します。

```text
  No.  Team Dev         Protocol     Ports
-----  ---------------  -----------  ---------------------------
 0001  PortChannel0001  LACP(A)(Up)  Ethernet112(S) Ethernet116(S)
 0002  PortChannel0002  LACP(A)(Up)  Ethernet108(S) Ethernet104(S)
```

`(A)` は active LACP、`(S)` は selected、`(D)` は disabled / down。`(P)` は LACP unsel / not bundled です。

## 異常検出パターン

| 観測 | 疑う状態 | 一次切り分け |
|---|---|---|
| `show vlan brief` に member が出ない | `VLAN_MEMBER` 未登録、または port が PortChannel の中で隠れている | `redis-cli -n 4 keys 'VLAN_MEMBER*'`、`config vlan member add` |
| Port が `tagged` 想定だが `untagged` で出る | `tagging_mode` 設定漏れ | `config vlan member add -u\|--tag-mode` |
| PortChannel が `(D)` のまま | LACP unmatched、speed/duplex 不一致、`min_links` 未達 | `teamdctl <pc> state`、`show interfaces status` |
| `mclagdctl dump state` で `Session Status=DOWN` | ICCP peer-link 断、peer IP 不到達、MD5 不一致 | peer-link の `show interfaces portchannel`、`ping <peer>` |
| `peer state=ERROR` / `mclag_remote_system_id` 取れない | ICCP capability mismatch | `mclagsyncd` ログ |
| 片側だけ MAC を知っている | ICCP MAC sync 失敗、または対向 PortChannel 不一致 | `mclagdctl dump mac` 両側比較、`APP_MCLAG_FDB_TABLE` |
| MAC が古い port に残る | FDB flush 未発火、または STP/PortChannel down の通知欠落 | `fdbshow`、`sonic-clear fdb` |
| `storm-control` 設定後も flooding 続く | unit が pps か bps か、対象が unknown unicast か broadcast か取り違え | `show storm-control all`、CONFIG_DB:`PORT_STORM_CONTROL` |
| Link が短周期 flap | cable / transceiver / autoneg / damping 未設定 | `show interfaces transceiver eeprom`、syslog の `Link is Up\|Down` |

## 典型的なログサンプル

```text
swss: :- doTask: VLAN 1000 was added
swss: :- doTask: Failed to add member Ethernet4 to Vlan1000: not in any port
teamd: PortChannel0001: bond carrier changed to UP
teamd: PortChannel0001: state changed: down -> up
kernel: 8021q: adding VLAN 0 to HW filter on device Ethernet0
mclagsyncd: ICCP session UP with peer 12.1.1.2
mclagsyncd: ICCP session DOWN with peer 12.1.1.2: KeepaliveTimeout
mclagsyncd: Failed to sync MAC 00:aa:bb:cc:dd:ee on Vlan1000 from peer
fdbsyncd: FDB entry MAC 00:11:22:33:44:55 on Vlan1000 learned on Ethernet4
fdbsyncd: FDB flush triggered for Ethernet4 due to port down
orchagent: :- doTask: SAI_API_FDB FDB age out for 00:11:22:33:44:55
orchagent: :- doTask: Failed to add FDB entry, SAI status SAI_STATUS_TABLE_FULL
linkmgrd: Storm control packet drop on Ethernet0 broadcast
```

## 対応コマンド早見表

| 目的 | コマンド |
|---|---|
| VLAN 一覧 | `show vlan brief`、`show vlan config` |
| VLAN 追加 / 削除 | `config vlan add <id>` / `config vlan del <id>` |
| VLAN member | `config vlan member add [-u] <id> <port>` |
| PortChannel 一覧 | `show interfaces portchannel` |
| PortChannel 追加 | `config portchannel add PortChannel<id> [--min-links N] [--fallback]` |
| Member 追加 | `config portchannel member add <pc> <port>` |
| MC-LAG 状態 | `mclagdctl dump state` |
| MC-LAG local / peer 一覧 | `mclagdctl dump portlist local\|peer` |
| MC-LAG MAC | `mclagdctl dump mac` |
| MC-LAG ARP / ND | `mclagdctl dump arp\|nd` |
| FDB 一覧 | `fdbshow` |
| FDB flush | `sonic-clear fdb all\|port <p>\|vlan <id>` |
| Storm control | `config interface storm-control broadcast\|unknown-unicast\|unknown-multicast add <port> <kbps>` |
| Storm 状態 | `show storm-control all\|interface <port>` |
| L1 状態 | `show interfaces status` |
| Transceiver | `show interfaces transceiver eeprom\|status\|info` |
| Counters | `show interfaces counters`、`sonic-clear counters` |
| Proxy ARP | `config vlan proxy_arp <vid> enable\|disable`、`show vlan brief` の Proxy ARP 列 |

## 関連 CONFIG_DB / APPL_DB / STATE_DB / counter

- `CONFIG_DB:VLAN|Vlan<id>` — `vlanid`、`mtu`、`mac`、`description`、`proxy_arp`、`autostate`。
- `CONFIG_DB:VLAN_MEMBER|Vlan<id>|<port>` — `tagging_mode`。
- `CONFIG_DB:VLAN_INTERFACE|Vlan<id>` / `|Vlan<id>|<ip>` — SVI 定義と IP。
- `CONFIG_DB:PORTCHANNEL|PortChannel<id>` — `admin_status`、`mtu`、`min_links`、`fallback`、`lacp_key`。
- `CONFIG_DB:PORTCHANNEL_MEMBER|PortChannel<id>|<port>` — member 関係。
- `CONFIG_DB:MCLAG_DOMAIN|<id>` — `source_ip`、`peer_ip`、`peer_link`、`keepalive_interval`、`session_timeout`。
- `APPL_DB:FDB_TABLE:Vlan<id>:<mac>` — dynamic / static FDB。
- `APPL_DB:LAG_TABLE:<pc>` — admin / oper、active member。
- `APPL_DB:STORM_CONTROL_TABLE:<port>:<type>` — storm control の現在値。
- `STATE_DB:FDB_TABLE` — FDB sync 後の sniffer 出力（fdbshow が読む）。
- `STATE_DB:PORT_TABLE\|<port>` — `oper_status`、`speed`、`admin_status`。
- `COUNTERS_DB:COUNTERS_LAG_NAME_MAP` / `COUNTERS_PORT_NAME_MAP` — port / LAG の counter OID。
- `STATE_DB` の MC-LAG 同期テーブル（`MCLAG_*`、`APP_MCLAG_FDB_TABLE`）。

## 横断参照

- VLAN_INTERFACE で出す SVI が L3 で動かない: [VRF / ECMP 章 運用](../04-vrf-ecmp/operations.md)。
- MC-LAG over Dual-ToR / Active-Active 構成: [Dual-ToR 章 運用](../05-dual-tor/operations.md)。
- VLAN ↔ VNI 紐付けや [EVPN](../../reference/glossary.md#term-evpn) 由来 FDB の差分: [Overlay 章 運用](../03-vxlan-evpn/operations.md)。
- [teamd](../../reference/glossary.md#term-teamd-teamsyncd-teammgrd) / swss が起動しない場合の前提: [運用入口](../01-overview/operations.md) の feature / [hostcfgd](../../reference/glossary.md#term-hostcfgd) セクション。

## 関連ページ

- [CLI: show vlan](../../reference/cli/show-vlan.md)
- [CLI: show mclag](../../reference/cli/show-mclag.md)
- [BUM ストームコントロール](../../switching/sonic-bum-storm-control.md)
- [リンクイベントダンピング](../../switching/link-event-damping-hld.md)
- [MCLAG Enhancements](../../switching/mclag-enhancements.md)

<!-- glossary-links-injected: ec18b66e3507 -->
