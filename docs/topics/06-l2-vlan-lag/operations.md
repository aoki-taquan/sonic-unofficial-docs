---
title: L2 運用確認
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
---

# L2 運用確認

L2 障害は「VLAN に入っていない」「LAG が期待通り up していない」「MAC 学習が古い」「MC-LAG peer と状態がずれている」「BUM traffic や link flap が制御面を壊している」に分けると追いやすくなります。

## VLAN の状態を見る

まず VLAN と member の見え方を確認します。

```bash
show vlan brief
show vlan config
```

`show vlan brief` は VLAN ID、IP Address、Ports、Port Tagging、Proxy ARP を一覧します。`show vlan config` は 1 行 1 member で VLAN と member port を展開します。multi-ASIC 環境では namespace 指定の有無に注意します。

見るべき点は次の順です。

| 確認 | 観点 |
|---|---|
| VLAN が存在するか | `VLAN|Vlan<id>` が作られているか |
| member がいるか | `VLAN_MEMBER` に port / PortChannel が入っているか |
| tagged / untagged が期待通りか | access なら untagged、trunk なら tagged の組み合わせ |
| SVI が必要か | L3 gateway が必要なら `VLAN_INTERFACE` と IP があるか |

## LAG の状態を見る

PortChannel の設定は `config portchannel` と CONFIG_DB の `PORTCHANNEL` / `PORTCHANNEL_MEMBER` が入口です。運用時は LACP、member の admin / oper、`min_links` の条件、VLAN member への参加有無を分けて確認します。

削除や変更が失敗する場合は、PortChannel が VLAN member、L3 interface、DHCP relay 対象、または member を残した状態ではないかを先に確認します。

## MC-LAG の状態を見る

SONiC では `show mclag` という Click サブコマンドではなく、実体は `mclagdctl` です。

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
| VLAN member 変更後に古い MAC が残る | FDB flush の対象と static / dynamic の違い |
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

Link event damping は、ポート up/down が短時間に繰り返される場合に、SyncD 側でイベント通知を抑制する設計です。現行ページでは swss 側の実装は確認されている一方、HLD に書かれた CLI は未実装とされています。

運用手順としては、まず通常の interface state と transceiver / cable 健全性を確認し、damping を使う場合は [リンクイベントダンピング](../../switching/link-event-damping-hld.md) の実装との乖離を確認してください。

## 関連ページ

- [CLI: show vlan](../../reference/cli/show-vlan.md)
- [CLI: show mclag](../../reference/cli/show-mclag.md)
- [BUM ストームコントロール](../../switching/sonic-bum-storm-control.md)
- [リンクイベントダンピング](../../switching/link-event-damping-hld.md)
- [MCLAG Enhancements](../../switching/mclag-enhancements.md)
