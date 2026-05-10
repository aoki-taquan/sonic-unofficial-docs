---
title: EVPN VXLAN Multihoming（ESI / DF election / split-horizon）
area: routing
verification: discrepancy-found
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/vxlan/EVPN/EVPN_VxLAN_Multihoming.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - PORTCHANNEL
    - VXLAN_TUNNEL
    - EVPN_ETHERNET_SEGMENT
  cli:
    - config evpn ethernet-segment
    - show evpn ethernet-segment
  yang:
    - sonic-evpn
---

!!! warning "裏取りステータス: discrepancy-found / 大規模 HLD"
    HLD は 80KB。本ページは EVPN MH の中核（ESI / Type-1 / Type-4 / DF election / split-horizon）に絞る。基本の EVPN VXLAN は同 area の `evpn-vxlan-hld.md` を参照。

!!! note "Verifier 注記（2026-05-10）"
    実コード裏取り: 現行 master の `sonic-swss/orchagent/`、`sonic-buildimage/src/sonic-yang-models/yang-models/`、`sonic-utilities/` を grep した範囲では **`EVPN_ETHERNET_SEGMENT` テーブル / `EthernetSegment` orch / `config evpn ethernet-segment` CLI / EVPN-MH 用 yang は確認できない**。HLD は提案レベルで、sonic-net のメインリポジトリには未取り込みの可能性が高い。利用可否は upstream FRR の EVPN-MH と vendor SAI の ESI label / split-horizon サポートに依存する。

# EVPN VXLAN Multihoming（ESI / DF election / split-horizon）

## 概要

EVPN multihoming（MH）は **MC-LAG / vPC を使わず、BGP-EVPN だけで host を複数 leaf にマルチホーム接続する** RFC 7432 / RFC 8365 の仕組み[^1]。SONiC は FRR の EVPN-MH と SAI レイヤを組合せる。

主要な構成:

- **Ethernet Segment (ES)**: 複数 leaf が共有する論理 link を表す。**ESI（Ethernet Segment Identifier）** で一意化
- **Type-1 (Auto-Discovery / per-ES, per-EVI)**: ES の到達性と aliasing 用 next-hop を広告
- **Type-4 (ES Route)**: 同一 ES のメンバ leaf を相互に発見し、**Designated Forwarder（DF）election** を行う
- **Split-horizon**: ES に向かうトラフィックがその ES の他メンバに重複ループしないよう、ESI label を付けてフィルタする

## 動作仕様

```mermaid
flowchart LR
    H[Multi-homed Host\nLAG bond] --- L1[Leaf 1\nESI 0xAA]
    H --- L2[Leaf 2\nESI 0xAA]
    L1 -. Type-4 .- L2
    L1 --- SP[(Spine)]
    L2 --- SP
    SP --- L3[Leaf 3\n(remote)]
    L1 -.Type-2 (MAC) ＋ Aliasing Type-1.-> L3
```

主要動作[^1]:

- **DF election**: ES メンバ間で BUM の **forwarder を 1 つに選ぶ**（VLAN 単位）。Type-4 で見つかったメンバ群を IP / DF algo で並べる
- **Aliasing (Type-1)**: remote leaf は ES 全メンバを ECMP next-hop として使い、トラフィックを load-balance
- **Split-horizon (ESI label)**: ingress leaf が ESI label を付与、egress leaf は同 ESI 受信なら local ES に出さない
- **Single-Active vs All-Active**: ES が All-Active か Single-Active かを ESI / config で区別

## 設定

### 関連 CONFIG_DB

| Table | 説明 |
|-------|------|
| `EVPN_ETHERNET_SEGMENT` | ESI、関連する LAG / interface、type (single-active / all-active)、DF preference |
| `PORTCHANNEL` | ES に紐づく LAG |
| `VXLAN_TUNNEL` | VTEP loopback（前提） |

### 関連 CLI

| Command | 用途 |
|---------|------|
| `config evpn ethernet-segment add <name> esi <id>` | ES 定義 |
| `config evpn ethernet-segment <name> interface <portchannel>` | LAG 紐付け |
| `show evpn ethernet-segment` | DF / メンバ一覧 |
| `show evpn vni <vni> mh` | MH 視点 |

## 制限事項

- **対応 ASIC のみ**: ESI label / split-horizon を SAI で扱える NPU が必要
- **DF election timer**: 起動直後の不安定期に BUM が断する可能性。`hold timer` で対処
- **VLAN ↔ ES の整合**: ES に紐づく VLAN は両 leaf で同一定義であること
- **MAC mobility**: host が ES 内で移動した時の MAC mobility extended community 処理に依存

## 干渉する機能

- **EVPN VXLAN HLD**: 上位の Type-2 / Type-5 流通の前提
- **MC-LAG**: 同じ目的を別アプローチで解く。両者の違いを理解した上で選択
- **port-channel / LACP**: ES の物理リンク基盤
- **fpmsyncd / nexthop group**: aliasing による ECMP next-hop インストール

## トラブルシューティング

- BUM ループ → ESI label / split-horizon フィルタが ASIC で効いているか
- DF が両側で active → Type-4 受信の確認、`show evpn ethernet-segment` の DF 状態
- aliasing で trafic が偏る → ECMP hash 設定、remote leaf の Type-1 受信状況

## 引用元

[^1]: `sonic-net/SONiC` `doc/vxlan/EVPN/EVPN_VxLAN_Multihoming.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- VxlanOrch / EvpnOrch の MH 拡張（ESI / DF / Type-1/Type-4）の現行実装存在確認
- CONFIG_DB EVPN_ETHERNET_SEGMENT スキーマと sonic-yang-models 取り込み確認
- FRR EVPN-MH（bgpd / zebra）の SONiC ビルド取り込み version 確認
- SAI ESI label / split-horizon サポート（SAI_TUNNEL_ATTR / SAI_TUNNEL_TERM_TABLE_ENTRY 拡張）の community SAI 取り込み確認
- show evpn ethernet-segment / config evpn ethernet-segment CLI の sonic-utilities 取り込み確認
- DF election timer / hold timer の現行既定値と挙動確認
-->
