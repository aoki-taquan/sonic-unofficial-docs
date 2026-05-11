---
title: TUNNEL テーブル
description: "TUNNEL テーブル — SONiC Dual-ToR (Active-Standby) 構成で、ToR スイッチ間に張る IPinIP トンネルを定義するテーブル。tunnelmgrd が CONFIG_DB の本テーブルを購読し、APPL_DB TUNNEL_DECAP_TABLE を生成。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-tunnel.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-swss
    path: orchagent/tunneldecaporch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db:
    - TUNNEL
    - PEER_SWITCH
    - MUX_CABLE
  cli: []
  yang:
    - sonic-tunnel
    - sonic-peer-switch
---

# TUNNEL テーブル

## 概要

SONiC Dual-ToR (Active-Standby) 構成で、ToR スイッチ間に張る IPinIP トンネルを定義するテーブル[^1]。`tunnelmgrd` が CONFIG_DB の本テーブルを購読し、APPL_DB `TUNNEL_DECAP_TABLE` を生成。`tunneldecaporch` (orchagent) が SAI tunnel オブジェクトを作成する。

## key 構造

```
TUNNEL|<mux_tunnel>
```

- `<mux_tunnel>`: `MuxTunnel<n>` の文字列パターン（YANG `pattern "MuxTunnel[0-9]+"`）

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `tunnel_type` | enum `IPINIP` | カプセル化方式。Dual-ToR では IPinIP 固定 |
| `src_ip` | leafref → `PEER_SWITCH.address_ipv4` | トンネル送信元 (= peer ToR の IPv4) |
| `dst_ip` | inet:ipv4-address | トンネル宛先 (自スイッチの IPv4) |
| `dscp_mode` | string `uniform`/`pipe` | DSCP 継承モード |
| `ecn_mode` | string `copy_from_outer`/`standard` | デカプセル時 ECN 処理 |
| `encap_ecn_mode` | string `standard` | カプセル時 ECN マーキング |
| `ttl_mode` | string `uniform`/`pipe` | TTL 継承モード |
| `decap_dscp_to_tc_map` | string | デカプセル時 DSCP→TC マップ名 |
| `decap_tc_to_pg_map` | string | デカプセル時 TC→PG マップ名 |
| `encap_tc_to_dscp_map` | string | カプセル時 TC→DSCP マップ名 |
| `encap_tc_to_queue_map` | string | カプセル時 TC→Queue マップ名 |

## 制約

- `src_ip` は `PEER_SWITCH_LIST.address_ipv4` への leafref で、PEER_SWITCH に登録された IPv4 のみ使える
- `tunnel_type` は IPINIP のみ。`tunneldecaporch.cpp` も `tunnel_type != "IPINIP"` をエラーとする

## 購読者

- `tunnelmgrd` (cfgmgr): CONFIG_DB→APPL_DB へ橋渡し
- `tunneldecaporch` (orchagent): APPL_DB `TUNNEL_DECAP_TABLE` 経由で SAI へ反映

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `PEER_SWITCH`、`MUX_CABLE`、`TUNNEL_DECAP_TABLE` (派生は `docs/reference/config-db/tunnel-decap-table.md`)
- 関連 CLI: 直接の CLI は無く `config_db.json` で投入
- 関連 YANG: `sonic-tunnel`、`sonic-peer-switch`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-tunnel`](../yang/sonic-tunnel.md) / `sonic-peer-switch`

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-tunnel.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-tunnel.yang>; orchagent 側パース: `tunneldecaporch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/tunneldecaporch.cpp>
