---
title: VXLAN / VNet 設定と運用（CONFIG_DB / APP_DB / CLI）
description: VXLAN / VNet の設定経路。CONFIG_DB / APP_DB スキーマ、CLI 一覧、VNet ピアリングの設定例、運用時のトラブルシューティング手順を扱う。
area: overlay
verification: code-verified
last_verified: 2026-06-06
page_kind: split-child
sources:
- repo: sonic-net/SONiC
  path: doc/vxlan/Vxlan_hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
- repo: sonic-net/sonic-utilities
  path: show/vxlan.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
- repo: sonic-net/sonic-utilities
  path: config/vxlan.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
- repo: sonic-net/sonic-swss-common
  path: common/schema.h
  ref: master
- repo: sonic-net/sonic-swss
  path: neighsyncd/neighsync.cpp
  ref: master
- repo: sonic-net/sonic-swss
  path: cfgmgr/intfmgr.cpp
  ref: master
related:
  config_db:
  - VXLAN_TUNNEL
  - VXLAN_TUNNEL_MAP
  - VNET
  - INTERFACE
  - VLAN_INTERFACE
  - VLAN
  cli:
  - config vxlan
  - show vxlan
  yang:
  - sonic-vxlan
  - sonic-vnet
  - sonic-vrf
---

# VXLAN / VNet 設定と運用

このページは [VXLAN / VNet 全体設計（概要ハブ）](vxlan-sonic.md) の派生ページで、**設定経路・CLI・運用** に絞って整理する。概念は [vxlan-sonic-concepts.md](vxlan-sonic-concepts.md)、内部実装は [vxlan-sonic-internals.md](vxlan-sonic-internals.md)、制限事項は [vxlan-sonic-limitations.md](vxlan-sonic-limitations.md) を参照。

## 1. CONFIG_DB スキーマ

```text
VXLAN_TUNNEL|<tunnel_name>
    src_ip : <ipv4>
    dst_ip : <ipv4>  (OPTIONAL, P2P 用)

VXLAN_TUNNEL_MAP|<tunnel_name>|<map_name>
    vni  : <int>
    vlan : <vlan_id>

VNET|<vnet_name>
    vxlan_tunnel : <tunnel_name>
    vni          : <int>
    scope        : "default"     (OPTIONAL)
    peer_list    : <vnet_name,...> (OPTIONAL)

INTERFACE|<intf>
    vnet_name : <vnet_name>

INTERFACE|<intf>|<prefix>
    {}

VLAN_INTERFACE|<vlan_intf>
    vnet_name : <vnet_name>

VLAN_INTERFACE|<vlan_intf>|<prefix>
    {}
```

`VXLAN_TUNNEL` に `src_ip` 必須、`dst_ip` は P2P 用にオプション。`VXLAN_TUNNEL_MAP` で [VLAN](../reference/glossary.md#term-vlan) ↔ VNI を関連付ける[^1]。`VNET.peer_list` は空文字列 `""` で「ピアなし」を表す（HLD `2.1.3 ConfigDB Schemas` の `PEER_LIST` 注記が明示）[^1]。

!!! note "HLD と master の乖離: `NEIGH_TABLE`"
    元の HLD `2.1.2 VNET/Interface Table` は `NEIGH_TABLE|<intf>|<ip>` を CONFIG_DB のテーブルとして列挙している[^1]が、master の実装では `NEIGH_TABLE` は APP_DB のテーブル名であり、CONFIG_DB 用の `CFG_NEIGH_TABLE_NAME` マクロは定義されていない（`APP_NEIGH_TABLE_NAME = "NEIGH_TABLE"` のみ存在）[^4]。`intfmgrd` / `neighsyncd` 等の producer はいずれも APP_DB に対して書き込む[^5]。本ページでは混乱を避けるため、`NEIGH_TABLE` を CONFIG_DB スキーマから除外した。

## 2. APP_DB スキーマ

```yaml
VNET_ROUTE_TABLE:<vnet>:<prefix>
    nexthop : <ip>      (OPTIONAL)
    ifname  : <intf>

VNET_ROUTE_TUNNEL_TABLE:<vnet>:<prefix>
    endpoint    : <vtep ip>
    mac_address : <mac>     (OPTIONAL: inner DST MAC)
    vni         : <int>     (OPTIONAL)

VXLAN_FDB_TABLE:<tunnel>:<vni>:<mac>
    remote_vtep : <ip>

VNET_TABLE:<vnet>
    vxlan_tunnel : <tunnel>
    vni          : <int>
    scope        : "default"
    peer_list    : <vnet,...>

NEIGH_TABLE:<intf>:<ip>
    family : IPv4 | IPv6
```

`VNET_ROUTE_TABLE` は **同 VNet 内の直接到達**、`VNET_ROUTE_TUNNEL_TABLE` は **tunnel nexthop 経由のリモート経路**[^1]。`NEIGH_TABLE` は APP_DB 側のテーブルで、kernel neighbor を `neighsyncd` が同期し、`intfmgrd` も VNet neighbor を APP_DB に書く[^4][^5]。

## 3. CLI

| Command | 用途 |
|---------|------|
| `config vxlan add <vxlan_name> <src_ip>` | [VTEP](../reference/glossary.md#term-vtep) tunnel エントリの追加（`VXLAN_TUNNEL` を書く）[^3] |
| `config vxlan del <vxlan_name>` | tunnel エントリの削除[^3] |
| `config vxlan map add <vxlan_name> <vlan_id> <vni>` | VLAN ↔ VNI のマップ追加（`VXLAN_TUNNEL_MAP` を書く）[^3] |
| `config vxlan map del <vxlan_name> <vlan_id> <vni>` | VLAN ↔ VNI マップ削除[^3] |
| `config vxlan map_range add <vxlan_name> <vlan_start> <vlan_end> <vni_start>` | VLAN レンジ ↔ VNI レンジの一括マップ[^3] |
| `config vxlan map_range del <vxlan_name> <vlan_start> <vlan_end> <vni_start>` | VLAN レンジ ↔ VNI レンジの一括マップ削除[^3] |
| `config vxlan evpn_nvo add <nvo_name> <vxlan_name>` | EVPN NVO エントリ追加[^3] |
| `config vxlan evpn_nvo del <nvo_name>` | EVPN NVO エントリ削除[^3] |
| `show vxlan name <vxlan_name>` | 個別 [VXLAN](../reference/glossary.md#term-vxlan) tunnel 情報[^2] |
| `show vxlan tunnel` | 全 VTEP tunnel と src/dst を一覧[^2] |
| `show vxlan interface` | VTEP 情報（src IP・status）[^2] |
| `show vxlan remotevni all` / `show vxlan remotevni <vtep_ip>` | リモート VTEP から学習した VNI 一覧（`all` は sentinel）[^2] |
| `show vxlan remotevtep` | リモート VTEP 一覧（[FDB](../reference/glossary.md#term-fdb) / VNI 経由で発見）[^2] |
| `show vxlan vlanvnimap` / `show vxlan vrfvnimap` | VLAN ↔ VNI / VRF ↔ VNI マッピング[^2] |
| `show vxlan remotemac all` / `show vxlan remotemac <vtep_ip>` | リモート VTEP 経由の MAC 一覧[^2] |
| `show vxlan counters [tunnel]` | tunnel カウンタ[^2] |

VNet ピアリングの CLI は無く、[CONFIG_DB](../reference/glossary.md#term-config_db) を直接編集する想定[^1]。

## 4. 設定例（VNet ピアリング）

`Vnet_2000`（VNI 2000、ベアメタル `Ethernet1`）と `Vnet_3000`（VNI 3000、`Vlan2000`、`Vnet_2000` をピア）:

```json
{
  "VXLAN_TUNNEL": { "tunnel1": { "src_ip": "10.10.10.10" } },
  "VNET": {
    "Vnet_2000": { "vxlan_tunnel": "tunnel1", "vni": "2000", "peer_list": "" },
    "Vnet_3000": { "vxlan_tunnel": "tunnel1", "vni": "3000", "peer_list": "Vnet_2000" }
  },
  "INTERFACE": {
    "Ethernet1": { "vnet_name": "Vnet_2000" },
    "Ethernet1|100.100.3.1/24": {}
  },
  "VLAN_INTERFACE": {
    "Vlan2000": { "vnet_name": "Vnet_3000" },
    "Vlan2000|100.100.4.1/24": {}
  }
}
```

APP_DB に `VNET_ROUTE_TABLE` / `VNET_ROUTE_TUNNEL_TABLE` を投入してベアメタル subnet 経路と VM tunnel nexthop 経路を作る[^1]。

## 5. トラブルシューティング

| 症状 | 最初に見る場所 |
|------|---------------|
| VTEP が上がらない | `VXLAN_TUNNEL.src_ip` が実在 IF（Loopback 等）の IP か |
| L2 VXLAN で MAC が伝搬しない | `VXLAN_FDB_TABLE`（APP_DB）に `remote_vtep` |
| L3 VXLAN で経路が乗らない | `VNET_ROUTE_TUNNEL_TABLE.endpoint` が remote VTEP IP と一致 |
| [VRF](../reference/glossary.md#term-vrf) が [SAI](../reference/glossary.md#term-sai) に作られない | `VrfMgrD` の [STATE_DB](../reference/glossary.md#term-state_db) 更新が間に合っているか |

### コマンド例

VXLAN トンネルと [EVPN](../reference/glossary.md#term-evpn) ピアの状態を確認する。

```bash
# VXLAN tunnel / VNI / EVPN
show vxlan tunnel
show vxlan remotevni all
redis-cli -n 4 keys 'VXLAN_TUNNEL|*'
docker exec bgp vtysh -c 'show evpn vni'
docker exec bgp vtysh -c 'show bgp l2vpn evpn summary'
```

## 関連ページ

- [VXLAN / VNet 全体設計（概要ハブ）](vxlan-sonic.md) — 元 [HLD](../reference/glossary.md#term-hld) ページ
- [vxlan-sonic-concepts.md](vxlan-sonic-concepts.md) — 概念・用語
- [vxlan-sonic-internals.md](vxlan-sonic-internals.md) — Orch 内部実装
- [vxlan-sonic-limitations.md](vxlan-sonic-limitations.md) — 制限事項
- [CLI: config vxlan](../reference/cli/config-vxlan.md)
- [CONFIG_DB: VXLAN_TUNNEL](../reference/config-db/vxlan-tunnel.md)
- [CONFIG_DB: VXLAN_TUNNEL_MAP](../reference/config-db/vxlan-tunnel-map.md)

## 引用元

[^1]: `sonic-net/SONiC` `doc/vxlan/Vxlan_hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
[^2]: `sonic-net/sonic-utilities` `show/vxlan.py` (`vxlan` click group) L12-L392 @ `39732bceb8bdefe706518ab40623bbbba6ff33b9`
[^3]: `sonic-net/sonic-utilities` `config/vxlan.py` (`vxlan` click group, `add/del/map/map_range/evpn_nvo` subcommands) L14-L325 @ `39732bceb8bdefe706518ab40623bbbba6ff33b9`
[^4]: `sonic-net/sonic-swss-common` `common/schema.h` L46 (`APP_NEIGH_TABLE_NAME = "NEIGH_TABLE"`、CONFIG_DB 用 `CFG_NEIGH_TABLE_NAME` は未定義) @ master
[^5]: `sonic-net/sonic-swss` `neighsyncd/neighsync.cpp` L23, L33, L179 / `cfgmgr/intfmgr.cpp` L43 (いずれも `APP_NEIGH_TABLE_NAME` を APP_DB に対して open) @ master

<!-- glossary-links-injected: 302f3d074477 -->
