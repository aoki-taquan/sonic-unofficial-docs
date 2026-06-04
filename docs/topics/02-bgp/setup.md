---
title: 設定
description: 設定 — BGP の設定入口は複数ある。運用コマンドで触るなら CLI、宣言的に管理するなら CONFIG_DB、外部 controller
  から投入するなら YANG/OpenConfig を見る。重要なのは、最終的に FRR に入る設定と CONFIG_DB の状態を分離しないことである。
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
related:
  cli:
  - config bgp
  - show ip
  - config interface
  - show bgp
  - clear
  - config vrf
  - show acl
  config_db:
  - BGP_GLOBALS
  - BGP_NEIGHBOR
  - BGP_PEER_GROUP
  - BGP_AGGREGATE_ADDRESS
  - BGP_NEIGHBOR_AF
  - BGP_PEER_GROUP_AF
  - ROUTE_MAP
  yang:
  - sonic-route-map
  - sonic-bgp-global
  - sonic-bgp-neighbor
  - sonic-bgp-peergroup
  - sonic-bgp-aggregate-address
  - sonic-bgp-monitor
  - sonic-bgp-peerrange
---

# 設定

[BGP](../../reference/glossary.md#term-bgp) の設定入口は複数ある。運用コマンドで触るなら CLI、宣言的に管理するなら [CONFIG_DB](../../reference/glossary.md#term-config_db)、外部 controller から投入するなら [YANG](../../reference/glossary.md#term-yang)/OpenConfig を見る。重要なのは、最終的に [FRR](../../reference/glossary.md#term-frr) に入る設定と CONFIG_DB の状態を分離しないことである。

## どの入口を使うか

| 目的 | 入口 | 詳細 |
| --- | --- | --- |
| 手作業で neighbor や global 設定を入れる | `config bgp ...` | [CLI: config bgp](../../reference/cli/config-bgp.md) |
| 自動化で [SONiC](../../reference/glossary.md#term-sonic) native schema を書く | CONFIG_DB | `BGP_GLOBALS`、`BGP_NEIGHBOR`、`BGP_PEER_GROUP` |
| [gNMI](../../reference/glossary.md#term-gnmi)/REST/OpenConfig を使う | YANG/Management Framework | `sonic-bgp-*`、`sonic-route-map` |
| policy を再利用する | route-map、prefix-list、prefix-set | CONFIG_DB と CLI reference |

## 最小構成で考える

BGP 設定を読むときは、次の順番で追うとよい。

1. `BGP_GLOBALS` で [VRF](../../reference/glossary.md#term-vrf) 単位の router-id、ASN、global option を確認する。
2. `BGP_NEIGHBOR` または `BGP_PEER_GROUP` で peer の ASN、peer group 所属、timer、password などを確認する。
3. `BGP_NEIGHBOR_AF` または `BGP_PEER_GROUP_AF` で address family ごとの activate、route-map、prefix-limit などを見る。
4. policy は `ROUTE_MAP`、`PREFIX_LIST`、`PREFIX_SET` を別に確認する。
5. route aggregation を使う場合は `BGP_AGGREGATE_ADDRESS` を確認する。

この順番は FRR CLI の見た目ではなく、CONFIG_DB で依存関係をほどく順番である。peer group を使う構成では、neighbor に直接設定された値と peer group から継承される値を混同しない。

## 典型シナリオ 1: ToR 上で leaf-spine eBGP を立ち上げる

「新しい ToR を箱出しして、上位 spine 2 台と eBGP unnumbered を張りたい」という最頻出シナリオである。読み手の質問は (1) 何を順に打つか、(2) CONFIG_DB に何が落ちるか、(3) どの show で確認するか、の 3 つに集約される。

### CLI で打つ場合

```bash
# 1. 自 AS と router-id を入れる
sudo config bgp autonomous-system 65001
sudo config interface ip add Loopback0 10.1.0.1/32

# 2. spine 2 台と eBGP を張る (numbered)
sudo config bgp neighbor add 10.0.0.0 65000
sudo config bgp neighbor add 10.0.0.2 65000

# 3. peer group を使う場合 (推奨)
sudo config bgp peer-group add SPINE 65000
sudo config bgp neighbor add 10.0.0.0 --peer-group SPINE
sudo config bgp neighbor add 10.0.0.2 --peer-group SPINE
```

引数や `--peer-group` などのオプション展開は SONiC バージョンによって差分がある。実コマンドは [CLI: config bgp](../../reference/cli/config-bgp.md) を正にすること。実機では [vtysh](../../reference/glossary.md#term-vtysh) 直叩きで FRR 側を触る運用も残っているが、CONFIG_DB と vtysh を混ぜると `frrcfgd` 再描画時に上書きが起きるので避ける。

### CONFIG_DB JSON で投入する場合

`/etc/sonic/config_db.json` に書き込み `config reload -y` で反映するか、`sonic-cfggen` で部分パッチを当てる。

```json
{
  "DEVICE_METADATA": {
    "localhost": {
      "bgp_asn": "65001"
    }
  },
  "BGP_GLOBALS": {
    "default": {
      "router_id": "10.1.0.1",
      "local_asn": "65001",
      "load_balance_mp_relax": "true",
      "always_compare_med": "false"
    }
  },
  "BGP_PEER_GROUP": {
    "default|SPINE": {
      "asn": "65000",
      "ebgp_multihop_ttl": "1",
      "keepalive": "3",
      "holdtime": "9"
    }
  },
  "BGP_NEIGHBOR": {
    "default|10.0.0.0": {
      "peer_group_name": "SPINE",
      "asn": "65000",
      "local_addr": "10.0.0.1",
      "admin_status": "up"
    },
    "default|10.0.0.2": {
      "peer_group_name": "SPINE",
      "asn": "65000",
      "local_addr": "10.0.0.3",
      "admin_status": "up"
    }
  },
  "BGP_PEER_GROUP_AF": {
    "default|SPINE|ipv4_unicast": {
      "admin_status": "true",
      "soft_reconfiguration_in": "true"
    }
  }
}
```

`sonic-cfggen` で部分パッチを当てる場合は次の形になる。

```bash
sonic-cfggen -a "$(cat patch.json)" --write-to-db
config save -y
```

`config save -y` を忘れると reboot で消える。本番はこの 2 段が要る。

### show コマンドで設定確認

```bash
show ip bgp summary
show ip bgp neighbors 10.0.0.0
show ip route bgp
show running-configuration bgp
```

`show ip bgp summary` の典型出力:

```text
IPv4 Unicast Summary:
BGP router identifier 10.1.0.1, local AS number 65001 vrf-id 0
BGP table version 12
RIB entries 23, using 4 KiB of memory
Peers 2, using 1 KiB of memory

Neighbor        V    AS   MsgRcvd   MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd
10.0.0.0        4 65000        15        18        0    0    0 00:00:42           10
10.0.0.2        4 65000        15        18        0    0    0 00:00:42           10
```

`State/PfxRcd` が数字でなく `Idle` / `Active` / `Connect` のままなら confederation か router-id 不一致を疑う。

## 典型シナリオ 2: route-map で受信 prefix を絞る

「上位から送られてくる default 以外を全部捨てたい」というケース。

```bash
sudo config bgp route-map add ONLY_DEFAULT 10 permit \
  --match-prefix-list DEFAULT_ONLY
```

CONFIG_DB では次のような形になる。

```json
{
  "PREFIX_LIST": {
    "DEFAULT_ONLY|10": {
      "action": "permit",
      "prefix": "0.0.0.0/0"
    }
  },
  "ROUTE_MAP": {
    "ONLY_DEFAULT|10": {
      "route_operation": "permit",
      "match_prefix_set": "DEFAULT_ONLY"
    }
  },
  "BGP_NEIGHBOR_AF": {
    "default|10.0.0.0|ipv4_unicast": {
      "admin_status": "true",
      "route_map_in": "ONLY_DEFAULT"
    }
  }
}
```

`soft_reconfiguration_in` が無いと `clear ip bgp 10.0.0.0 soft in` で再評価できない。policy 変更時は必ず確認する。

## 典型シナリオ 3: aggregate address で /24 を /16 に集約

```bash
sudo config bgp aggregate-address add default 10.10.0.0/16 \
  --as-set --summary-only
```

```json
{
  "BGP_AGGREGATE_ADDRESS": {
    "default|10.10.0.0/16|ipv4_unicast": {
      "as_set": "true",
      "summary_only": "true"
    }
  }
}
```

`as_set` は集約に含まれる AS_PATH を merge する。`summary_only` は contributing route を広告しない。BBR 連動の挙動は別ページで扱う。

## aggregate address と BBR 連動

aggregate address は単に FRR に summary を入れるだけではなく、BBR awareness や prefix-list 連携を含む設計がある。CONFIG_DB では `BGP_AGGREGATE_ADDRESS` を使い、[bgpcfgd](../../reference/glossary.md#term-bgpcfgd) が FRR 設定へ反映する。細かいスキーマと挙動は [BBR 連動の BGP ルート集約](../../routing/bgp-route-aggregation-with-bbr-awareness.md) を参照する。

## OpenConfig/Management Framework を使う場合

OpenConfig BGP 経由で広い範囲を扱う場合、`frrcfgd` が有効かどうかが前提になる。`frrcfgd` は CONFIG_DB 差分から FRR vty コマンドを生成する設計で、state/statistics は必要時に FRR から取得する。従来の template ベース運用と混ぜる場合は、同じ設定対象を vtysh 直叩き、CONFIG_DB、OpenConfig の複数入口で更新しない。

## よくある設定エラーと対処

| 症状 | 原因 | 対処 |
|---|---|---|
| neighbor 追加で `Peer does not exist` 等 | local_addr の interface に IP 未設定 | 先に `config interface ip add` を済ませる |
| `State/PfxRcd` が `Active` のまま | TCP 179 が片道 [ACL](../../reference/glossary.md#term-acl) で drop / route-map で reject | `show ip route <peer>` と [CoPP](../../reference/glossary.md#term-copp) / data ACL を確認 |
| `Connect` で止まる | router-id 重複、両 ToR が同じ loopback IP | `BGP_GLOBALS.router_id` を確認 |
| MD5 password mismatch | `BGP_NEIGHBOR.auth_password` 不一致 | 両側で同じ平文を入れる (vtysh 表示は encrypted) |
| `OpenSent` のまま | ASN 不一致 (eBGP 期待だが iBGP 設定) | `BGP_NEIGHBOR.asn` を確認 |
| 設定したのに FRR に入らない | `frrcfgd` 未起動 / template モードと混在 | `docker exec bgp supervisorctl status` |

CONFIG_DB の値は文字列であって boolean ではない (`"true"` / `"false"` のクオート必須)。`sonic-cfggen` で生成するとき numeric / boolean を入れると schema validation で弾かれる。

## 参照表

| 分類 | ページ |
| --- | --- |
| CLI | [config bgp](../../reference/cli/config-bgp.md)、[show bgp](../../reference/cli/show-bgp.md) |
| CONFIG_DB global | [BGP_GLOBALS](../../reference/config-db/bgp-globals.md)、[BGP_GLOBALS_AF](../../reference/config-db/bgp-globals-af.md)、[BGP_DEVICE_GLOBAL](../../reference/config-db/bgp-device-global.md) |
| CONFIG_DB neighbor | [BGP_NEIGHBOR](../../reference/config-db/bgp-neighbor.md)、[BGP_NEIGHBOR_AF](../../reference/config-db/bgp-neighbor-af.md) |
| CONFIG_DB peer group | [BGP_PEER_GROUP](../../reference/config-db/bgp-peer-group.md)、[BGP_PEER_GROUP_AF](../../reference/config-db/bgp-peer-group-af.md) |
| CONFIG_DB policy | [ROUTE_MAP](../../reference/config-db/route-map.md)、[PREFIX_LIST](../../reference/config-db/prefix-list.md)、[PREFIX_SET](../../reference/config-db/prefix-set.md) |
| CONFIG_DB aggregate | [BGP_AGGREGATE_ADDRESS](../../reference/config-db/bgp-aggregate-address.md) |
| YANG | [sonic-bgp-global](../../reference/yang/sonic-bgp-global.md)、[sonic-bgp-neighbor](../../reference/yang/sonic-bgp-neighbor.md)、[sonic-bgp-peergroup](../../reference/yang/sonic-bgp-peergroup.md)、[sonic-bgp-aggregate-address](../../reference/yang/sonic-bgp-aggregate-address.md)、[sonic-route-map](../../reference/yang/sonic-route-map.md) |

## 関連ページ

- [CLI: config bgp](../../reference/cli/config-bgp.md)
- [CLI: show bgp](../../reference/cli/show-bgp.md)
- [CONFIG_DB: BGP_AGGREGATE_ADDRESS](../../reference/config-db/bgp-aggregate-address.md)
- [BBR 連動の BGP ルート集約](../../routing/bgp-route-aggregation-with-bbr-awareness.md)
- [FRR-BGP Unified Mgmt Framework](../../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md)

<!-- glossary-links-injected: 7ac8e66e1af3 -->
