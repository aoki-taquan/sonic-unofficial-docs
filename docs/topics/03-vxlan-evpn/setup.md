---
title: Overlay 設定
description: Overlay 設定 — Overlay の設定は、最初に「L2 VLAN-VNI を作るのか」「VNET route を作るのか」「EVPN
  の NVO を作るのか」を決めると整理できる。どの場合も、VTEP となる VXLAN tunnel が先に必要となる。
area: topics
verification: code-verified
last_verified: 2026-06-04
sources:
- repo: sonic-net/sonic-utilities
  path: config/vxlan.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
- repo: sonic-net/sonic-utilities
  path: config/main.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  cli:
  - config vxlan
  - config vnet
  - config vlan
  - config interface
  - show bgp
  - config vrf
  - config bgp
  config_db:
  - VNET
  - VXLAN_TUNNEL_MAP
  - TUNNEL
  - VXLAN_TUNNEL
  - VXLAN_EVPN_NVO
  - VLAN
  yang:
  - sonic-vxlan
  - sonic-vnet
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-global
  - sonic-bgp-bbr
---

# Overlay 設定

Overlay の設定は、最初に「L2 [VLAN](../../reference/glossary.md#term-vlan)-VNI を作るのか」「[VNET](../../reference/glossary.md#term-vnet) route を作るのか」「[EVPN](../../reference/glossary.md#term-evpn) の NVO を作るのか」を決めると整理できます。どの場合も、[VTEP](../../reference/glossary.md#term-vtep) となる [VXLAN](../../reference/glossary.md#term-vxlan) tunnel が先に必要です。

## 最小構成の順番

1. Underlay IP reachability を作る。
2. 自 VTEP loopback を決め、`VXLAN_TUNNEL` を作る。
3. L2 overlay なら `VXLAN_TUNNEL_MAP` で VLAN と VNI を対応させる。
4. L3 / tenant overlay なら `VNET` を作り、VNI と VXLAN tunnel を対応させる。
5. remote prefix は `VNET_ROUTE_TUNNEL` または controller / EVPN 経由で入れる。
6. EVPN を使う場合は `VXLAN_EVPN_NVO` と [FRR](../../reference/glossary.md#term-frr) [BGP](../../reference/glossary.md#term-bgp)-EVPN 側の設定を揃える。

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

## 典型シナリオ 1: EVPN VXLAN を有効化する (leaf として参加)

「underlay BGP は既に動いている。leaf として L2VPN EVPN family を有効化し、VLAN100 を VNI 100100 で広告したい」というケース。

### CLI で打つ

```bash
# 1. loopback を VTEP source として使う
sudo config interface ip add Loopback1 10.1.0.1/32

# 2. VTEP を作成
sudo config vxlan add vtep1 10.1.0.1

# 3. EVPN NVO を有効化
sudo config vxlan evpn_nvo add nvo1 vtep1

# 4. VLAN を作る
sudo config vlan add 100
sudo config vlan member add 100 Ethernet0 -u

# 5. VLAN-VNI map を作る
sudo config vxlan map add vtep1 100 100100
```

`vtep1` という名前はインスタンス名で、内部的に `VXLAN_TUNNEL|vtep1` になります。同一 box で複数 VTEP を持つことは想定されないため通常は単一です。

### CONFIG_DB で投入する

`config_db.json` 抜粋:

```json
{
  "VXLAN_TUNNEL": {
    "vtep1": {
      "src_ip": "10.1.0.1"
    }
  },
  "VXLAN_EVPN_NVO": {
    "nvo1": {
      "source_vtep": "vtep1"
    }
  },
  "VXLAN_TUNNEL_MAP": {
    "vtep1|map_100_Vlan100": {
      "vni": "100100",
      "vlan": "Vlan100"
    }
  },
  "VLAN": {
    "Vlan100": {
      "vlanid": "100"
    }
  },
  "VLAN_MEMBER": {
    "Vlan100|Ethernet0": {
      "tagging_mode": "untagged"
    }
  }
}
```

`VXLAN_TUNNEL_MAP` のキーは `<tunnel>|<map_name>` で、`config vxlan map add` 経由の場合 `map_name` は `map_<vni>_Vlan<id>` 形式が `vxlan.py` 側でハードコードされる (慣例ではなくコード生成)[^vxlan-map-name]。`vlan` フィールドも `Vlan<id>` 形式で書く必要がある (数字単独ではエラー)。

`sonic-cfggen` で部分パッチを当てる場合:

```bash
sonic-cfggen -a "$(cat vxlan_patch.json)" --write-to-db
config save -y
```

### show コマンドで確認

```bash
show vxlan tunnel
show vxlan vlanvnimap
show vxlan name vtep1
show vxlan remotevtep
show vxlan remotemac all
```

`show vxlan tunnel` の典型出力:

```text
vxlan tunnel name    source ip    destination ip    tunnel map name    tunnel map mapping(s)
-------------------  -----------  ----------------  -----------------  --------------------
vtep1                10.1.0.1                       map_100_Vlan100    Vlan100 -> 100100
```

`destination ip` 列は EVPN モードでは空欄になります (動的学習)。EVPN BGP neighbor 確認は `show bgp l2vpn evpn summary` で別経路です。

## 典型シナリオ 2: VNET (controller driven overlay) を設定する

[DASH](../../reference/glossary.md#term-dash) 系や Mellanox [SmartNIC](../../reference/glossary.md#term-smartnic) 系の controller が VNET route を流し込むケース。EVPN を使わず、controller が `VNET_ROUTE_TUNNEL` を直接 [APPL_DB](../../reference/glossary.md#term-appl_db) / [CONFIG_DB](../../reference/glossary.md#term-config_db) に書きます。

```bash
sudo config vxlan add vtep1 10.1.0.1
sudo config vnet add Vnet1000 1000 vtep1
sudo config vnet add-route Vnet1000 192.0.2.10/32 203.0.113.10 --vni 1000 \
  --mac 00:11:22:33:44:55
```

CONFIG_DB:

```json
{
  "VNET": {
    "Vnet1000": {
      "vxlan_tunnel": "vtep1",
      "vni": "1000",
      "peer_list": ""
    }
  },
  "VNET_ROUTE_TUNNEL": {
    "Vnet1000|192.0.2.10/32": {
      "endpoint": "203.0.113.10",
      "vni": "1000",
      "mac_address": "00:11:22:33:44:55"
    }
  }
}
```

確認:

```bash
show vnet brief
show vnet routes all
show vnet endpoint
```

## 典型シナリオ 3: IPinIP decap を Dual-ToR 用に設定する

`TUNNEL` テーブルは [IPinIP](../../reference/glossary.md#term-ipinip) decap term を表現します。Dual-ToR の standby → active 折り返しに使われる構成例:

```json
{
  "TUNNEL": {
    "MuxTunnel0": {
      "tunnel_type": "IPINIP",
      "src_ip": "10.1.0.32",
      "dst_ip": "10.1.0.33",
      "dscp_mode": "uniform",
      "encap_ecn_mode": "standard",
      "ecn_mode": "copy_from_outer",
      "ttl_mode": "pipe"
    }
  }
}
```

`TUNNEL_DECAP_TABLE` は APPL_DB に書かれる ephemeral state で、CONFIG_DB から書く対象ではありません。[orchagent](../../reference/glossary.md#term-orchagent) が `TUNNEL` を見て APPL_DB に派生する流れです。

## CONFIG_DB / APPL_DB の見方

| 目的 | 主なテーブル | 読み方 |
| --- | --- | --- |
| VTEP 作成 | `VXLAN_TUNNEL` | `src_ip` が自 VTEP。P2P では `dst_ip` も使う |
| VLAN-VNI map | `VXLAN_TUNNEL_MAP` | tunnel 配下で VLAN と VNI を対応させる |
| VNET 作成 | `VNET` | `vxlan_tunnel` と `vni` が必須 |
| local route | `VNET_ROUTE` / `VNET_ROUTE_TABLE` | VNET 内の subnet / local nexthop |
| tunnel route | `VNET_ROUTE_TUNNEL` / `VNET_ROUTE_TUNNEL_TABLE` | remote endpoint、VNI、MAC、monitoring 情報 |
| IPinIP decap | `TUNNEL` → `TUNNEL_DECAP_TABLE` | Dual-ToR や subnet decap の tunnel term |

Reference の `config-db` ページは、CLI で触る table と orchagent が見る table の違いを確認する場所です。特に `TUNNEL_DECAP_TABLE` は CONFIG_DB ではなく APPL_DB / [STATE_DB](../../reference/glossary.md#term-state_db) の table なので、直接設定ファイルへ書く対象ではありません。

## EVPN NVO と FRR の境界

`VXLAN_EVPN_NVO` は EVPN NVO インスタンスと source VTEP を結びます。ただし、BGP neighbor、address-family l2vpn evpn、route-target、[VRF](../../reference/glossary.md#term-vrf) などの control plane 設定は FRR 側の領域です。[SONiC](../../reference/glossary.md#term-sonic) 側で VXLAN tunnel と map が存在していても、FRR EVPN が Type-2 / Type-5 を交換していなければ remote MAC / prefix は学習されません。

## PBH inner hash

VXLAN / NVGRE の外側 header だけで [ECMP](../../reference/glossary.md#term-ecmp) / [LAG](../../reference/glossary.md#term-lag) hash すると、複数 flow が同じ tunnel endpoint へ偏ることがあります。Policy Based Hashing は [ACL](../../reference/glossary.md#term-acl) match した encapsulated packet に対して inner 5-tuple ベースの hash を適用する機能です。設定単位は `PBH_TABLE`、`PBH_RULE`、`PBH_HASH`、`PBH_HASH_FIELD` で、VXLAN/VNET そのものの設定とは別です。

## よくある設定エラーと対処

`sonic-utilities/config/vxlan.py` の `ctx.fail()` から抜粋した実エラーメッセージ[^vxlan-ctx-fail]:

| エラーメッセージ | 原因 | 対処 |
|---|---|---|
| `VTEP already configured.` | 既に別名で VTEP が存在 | `show vxlan tunnel` で確認し、不要なら削除 |
| `EVPN NVO already configured` | NVO は 1 box 1 個 | 既存 NVO を削除してから再作成 |
| `VTEP <name> not configured` | map / NVO の追加で VTEP 未作成 | 先に `config vxlan add` |
| `Please delete the EVPN NVO configuration.` | VTEP 削除で NVO 残存 | `config vxlan evpn_nvo del` 先行 |
| `Please delete all VLAN VNI mappings.` | VTEP 削除で map 残存 | `config vxlan map del` 先行 |
| `Vlan Id already mapped` | 同一 VLAN を別 VNI に二重 map | 既存 map を確認して削除 |
| `VNI Id already mapped` | 同一 VNI を別 VLAN に二重 map | 同上 |
| `Invalid Vlan Id , Valid Range : 1 to 4094` | VLAN ID 範囲外 | 入力値を見直す |
| `Invalid VNI <vni>. Valid range [1 to 16777215].` | VNI 範囲外 | 24bit 範囲に収める |
| `VNI mapped to vrf <vrf>, Please remove VRF VNI mapping` | VRF-VNI 結びつきあり | `config vrf del_vrf_vni_map` 先行 |

削除順序は **add の逆順** が原則: `(rule) → map → NVO → VTEP`。途中に VLAN_MEMBER / VLAN が残っていると VTEP 削除はできますが VLAN 側の clean-up は別途必要です。

## 関連ページ

- [config vxlan](../../reference/cli/config-vxlan.md)
- [config vnet](../../reference/cli/config-vnet.md)
- [VXLAN_TUNNEL テーブル](../../reference/config-db/vxlan-tunnel.md)
- [VXLAN_TUNNEL_MAP テーブル](../../reference/config-db/vxlan-tunnel-map.md)
- [VXLAN_EVPN_NVO テーブル](../../reference/config-db/vxlan-evpn-nvo.md)
- [VNET / VNET_ROUTE テーブル](../../reference/config-db/vnet.md)
- [TUNNEL テーブル](../../reference/config-db/tunnel.md)
- [TUNNEL_DECAP_TABLE](../../reference/config-db/tunnel-decap-table.md)
- [sonic-vxlan YANG](../../reference/yang/sonic-vxlan.md)
- [sonic-vnet YANG](../../reference/yang/sonic-vnet.md)
- [Policy Based Hashing](../../architecture/sonic-policy-based-hashing.md)

[^vxlan-map-name]: `sonic-net/sonic-utilities/config/vxlan.py` の `add_vxlan_map` (L167-L208) では `vlan_name = "Vlan" + vlan` を組み立てた上で `mapname = vxlan_name + '|' + 'map_' + vni + '_' + vlan_name` でキーを生成しており、形式は固定。`del_vxlan_map` (L215-L253) と `add_vxlan_map_range` (L313) も同じ形式。`sonic-net/sonic-utilities/config/vxlan.py#L204` (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)。

[^vxlan-ctx-fail]: 列挙したエラーメッセージは `sonic-net/sonic-utilities/config/vxlan.py` 内の `ctx.fail()` 呼び出しと一致 (`VTEP already configured.` L45 / `Please delete the EVPN NVO configuration.` L76 / `Please delete all VLAN VNI mappings.` L85 / `EVPN NVO already configured` L122 / `VTEP {} not configured` L125, L188, L234 / `Invalid Vlan Id , Valid Range : 1 to 4094` L179 / `Invalid VNI {}. Valid range [1 to 16777215].` L183 / `Vlan Id already mapped` L198 / `VNI Id already mapped` L200 / `VNI mapped to vrf {}, Please remove VRF VNI mapping` L245)。`sonic-net/sonic-utilities/config/vxlan.py` (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)。

<!-- glossary-links-injected: c5c8b661ae7e -->
