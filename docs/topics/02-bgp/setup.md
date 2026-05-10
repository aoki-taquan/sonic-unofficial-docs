---
title: 設定
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 設定

BGP の設定入口は複数ある。運用コマンドで触るなら CLI、宣言的に管理するなら CONFIG_DB、外部 controller から投入するなら YANG/OpenConfig を見る。重要なのは、最終的に FRR に入る設定と CONFIG_DB の状態を分離しないことである。

## どの入口を使うか

| 目的 | 入口 | 詳細 |
| --- | --- | --- |
| 手作業で neighbor や global 設定を入れる | `config bgp ...` | [CLI: config bgp](../../reference/cli/config-bgp.md) |
| 自動化で SONiC native schema を書く | CONFIG_DB | `BGP_GLOBALS`、`BGP_NEIGHBOR`、`BGP_PEER_GROUP` |
| gNMI/REST/OpenConfig を使う | YANG/Management Framework | `sonic-bgp-*`、`sonic-route-map` |
| policy を再利用する | route-map、prefix-list、prefix-set | CONFIG_DB と CLI reference |

## 最小構成で考える

BGP 設定を読むときは、次の順番で追うとよい。

1. `BGP_GLOBALS` で VRF 単位の router-id、ASN、global option を確認する。
2. `BGP_NEIGHBOR` または `BGP_PEER_GROUP` で peer の ASN、peer group 所属、timer、password などを確認する。
3. `BGP_NEIGHBOR_AF` または `BGP_PEER_GROUP_AF` で address family ごとの activate、route-map、prefix-limit などを見る。
4. policy は `ROUTE_MAP`、`PREFIX_LIST`、`PREFIX_SET` を別に確認する。
5. route aggregation を使う場合は `BGP_AGGREGATE_ADDRESS` を確認する。

この順番は FRR CLI の見た目ではなく、CONFIG_DB で依存関係をほどく順番である。peer group を使う構成では、neighbor に直接設定された値と peer group から継承される値を混同しない。

## aggregate address と BBR 連動

aggregate address は単に FRR に summary を入れるだけではなく、BBR awareness や prefix-list 連携を含む設計がある。CONFIG_DB では `BGP_AGGREGATE_ADDRESS` を使い、bgpcfgd が FRR 設定へ反映する。細かいスキーマと挙動は [BBR 連動の BGP ルート集約](../../routing/bgp-route-aggregation-with-bbr-awareness.md) を参照する。

## OpenConfig/Management Framework を使う場合

OpenConfig BGP 経由で広い範囲を扱う場合、`frrcfgd` が有効かどうかが前提になる。`frrcfgd` は CONFIG_DB 差分から FRR vty コマンドを生成する設計で、state/statistics は必要時に FRR から取得する。従来の template ベース運用と混ぜる場合は、同じ設定対象を vtysh 直叩き、CONFIG_DB、OpenConfig の複数入口で更新しない。

## 参照表

| 分類 | ページ |
| --- | --- |
| CLI | [config bgp](../../reference/cli/config-bgp.md) |
| CONFIG_DB global | [BGP_GLOBALS](../../reference/config-db/bgp-globals.md)、[BGP_GLOBALS_AF](../../reference/config-db/bgp-globals-af.md)、[BGP_DEVICE_GLOBAL](../../reference/config-db/bgp-device-global.md) |
| CONFIG_DB neighbor | [BGP_NEIGHBOR](../../reference/config-db/bgp-neighbor.md)、[BGP_NEIGHBOR_AF](../../reference/config-db/bgp-neighbor-af.md) |
| CONFIG_DB peer group | [BGP_PEER_GROUP](../../reference/config-db/bgp-peer-group.md)、[BGP_PEER_GROUP_AF](../../reference/config-db/bgp-peer-group-af.md) |
| CONFIG_DB policy | [ROUTE_MAP](../../reference/config-db/route-map.md)、[PREFIX_LIST](../../reference/config-db/prefix-list.md)、[PREFIX_SET](../../reference/config-db/prefix-set.md) |
| YANG | [sonic-bgp-global](../../reference/yang/sonic-bgp-global.md)、[sonic-bgp-neighbor](../../reference/yang/sonic-bgp-neighbor.md)、[sonic-bgp-peergroup](../../reference/yang/sonic-bgp-peergroup.md)、[sonic-bgp-aggregate-address](../../reference/yang/sonic-bgp-aggregate-address.md)、[sonic-route-map](../../reference/yang/sonic-route-map.md) |

## 関連ページ

- [CLI: config bgp](../../reference/cli/config-bgp.md)
- [CONFIG_DB: BGP_AGGREGATE_ADDRESS](../../reference/config-db/bgp-aggregate-address.md)
- [BBR 連動の BGP ルート集約](../../routing/bgp-route-aggregation-with-bbr-awareness.md)
- [FRR-BGP Unified Mgmt Framework](../../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md)
