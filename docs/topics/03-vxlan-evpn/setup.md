---
title: Overlay 設定
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/reference/cli/config-vxlan.md
  - docs/reference/cli/config-vnet.md
  - docs/reference/config-db/vxlan-tunnel.md
  - docs/reference/config-db/vxlan-tunnel-map.md
  - docs/reference/config-db/vnet.md
  - docs/reference/config-db/tunnel.md
  - docs/reference/config-db/tunnel-decap-table.md
  - docs/reference/yang/sonic-vxlan.md
  - docs/reference/yang/sonic-vnet.md
  - docs/architecture/sonic-policy-based-hashing.md
---

# Overlay 設定

Overlay の設定は、最初に「L2 VLAN-VNI を作るのか」「VNET route を作るのか」「EVPN の NVO を作るのか」を決めると整理できます。どの場合も、VTEP となる VXLAN tunnel が先に必要です。

## 最小構成の順番

1. Underlay IP reachability を作る。
2. 自 VTEP loopback を決め、`VXLAN_TUNNEL` を作る。
3. L2 overlay なら `VXLAN_TUNNEL_MAP` で VLAN と VNI を対応させる。
4. L3 / tenant overlay なら `VNET` を作り、VNI と VXLAN tunnel を対応させる。
5. remote prefix は `VNET_ROUTE_TUNNEL` または controller / EVPN 経由で入れる。
6. EVPN を使う場合は `VXLAN_EVPN_NVO` と FRR BGP-EVPN 側の設定を揃える。

## CLI 入口

`config vxlan` は VTEP、EVPN NVO、VLAN-VNI map を扱います。

```text
config vxlan add vtep1 10.0.0.1
config vxlan map add vtep1 100 100100
config vxlan evpn_nvo add nvo1 vtep1
```

`config vnet` は VNET と VNET route を扱います。

```text
config vnet add Vnet1000 1000 vtep1
config vnet add-route Vnet1000 192.0.2.10/32 203.0.113.10 --vni 1000
```

実際の引数、依存チェック、削除時の順序は [config vxlan](../../reference/cli/config-vxlan.md) と [config vnet](../../reference/cli/config-vnet.md) を確認してください。

## CONFIG_DB / APPL_DB の見方

| 目的 | 主なテーブル | 読み方 |
| --- | --- | --- |
| VTEP 作成 | `VXLAN_TUNNEL` | `src_ip` が自 VTEP。P2P では `dst_ip` も使う |
| VLAN-VNI map | `VXLAN_TUNNEL_MAP` | tunnel 配下で VLAN と VNI を対応させる |
| VNET 作成 | `VNET` | `vxlan_tunnel` と `vni` が必須 |
| local route | `VNET_ROUTE` / `VNET_ROUTE_TABLE` | VNET 内の subnet / local nexthop |
| tunnel route | `VNET_ROUTE_TUNNEL` / `VNET_ROUTE_TUNNEL_TABLE` | remote endpoint、VNI、MAC、monitoring 情報 |
| IPinIP decap | `TUNNEL` → `TUNNEL_DECAP_TABLE` | Dual-ToR や subnet decap の tunnel term |

Reference の `config-db` ページは、CLI で触る table と orchagent が見る table の違いを確認する場所です。特に `TUNNEL_DECAP_TABLE` は CONFIG_DB ではなく APPL_DB / STATE_DB の table なので、直接設定ファイルへ書く対象ではありません。

## EVPN NVO と FRR の境界

`VXLAN_EVPN_NVO` は EVPN NVO インスタンスと source VTEP を結びます。ただし、BGP neighbor、address-family l2vpn evpn、route-target、VRF などの control plane 設定は FRR 側の領域です。SONiC 側で VXLAN tunnel と map が存在していても、FRR EVPN が Type-2 / Type-5 を交換していなければ remote MAC / prefix は学習されません。

## PBH inner hash

VXLAN / NVGRE の外側 header だけで ECMP / LAG hash すると、複数 flow が同じ tunnel endpoint へ偏ることがあります。Policy Based Hashing は ACL match した encapsulated packet に対して inner 5-tuple ベースの hash を適用する機能です。設定単位は `PBH_TABLE`、`PBH_RULE`、`PBH_HASH`、`PBH_HASH_FIELD` で、VXLAN/VNET そのものの設定とは別です。

## 関連ページ

- [config vxlan](../../reference/cli/config-vxlan.md)
- [config vnet](../../reference/cli/config-vnet.md)
- [VXLAN_TUNNEL テーブル](../../reference/config-db/vxlan-tunnel.md)
- [VXLAN_TUNNEL_MAP テーブル](../../reference/config-db/vxlan-tunnel-map.md)
- [VNET / VNET_ROUTE テーブル](../../reference/config-db/vnet.md)
- [TUNNEL テーブル](../../reference/config-db/tunnel.md)
- [TUNNEL_DECAP_TABLE](../../reference/config-db/tunnel-decap-table.md)
- [sonic-vxlan YANG](../../reference/yang/sonic-vxlan.md)
- [sonic-vnet YANG](../../reference/yang/sonic-vnet.md)
- [Policy Based Hashing](../../architecture/sonic-policy-based-hashing.md)
