---
title: sonic-tunnel YANG
description: "sonic-tunnel YANG — DualToR 構成における MuxTunnel (IPinIP encap/decap) のパラメータを保持する。DSCP / ECN / TTL の handling mode、 encap/decap QoS map などを定義する。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-tunnel.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [TUNNEL]
  cli: []
  yang: [sonic-peer-switch, sonic-mux-cable]
---

# sonic-tunnel YANG

## 概要

- module: `sonic-tunnel`
- namespace: `http://github.com/sonic-net/sonic-tunnel`
- revision: `2022-08-23`
- import: `ietf-inet-types`, `sonic-peer-switch`
- top container: `sonic-tunnel`

DualToR 構成における MuxTunnel ([IPinIP](../../reference/glossary.md#term-ipinip) encap/decap) のパラメータを保持する。[DSCP](../../reference/glossary.md#term-dscp) / ECN / TTL の handling mode、 encap/decap [QoS](../../reference/glossary.md#term-qos) map などを定義する[^1]。

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-tunnel"]
  C1[("CONFIG_DB<br/>TUNNEL")]
  Y --> C1
  D1["tunnelmgrd"]
  C1 --> D1
```

!!! note "凡例"
    YANG モジュールから CONFIG_DB テーブル経由で subscribe する daemon/orch までを `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文を参照。
<!-- /yang-mermaid -->

## 関連ページ

<!-- yang-xref -->

本 YANG モジュールに対応する CONFIG_DB / CLI / HLD / Topics への相互リンク。`inject_yang_xref.py` により自動生成されます。

### 対応 CONFIG_DB

- [`TUNNEL`](../config-db/tunnel.md)

### 関連 APPL_DB

- [TUNNEL_DECAP_TABLE (APPL_DB)](../../reference/config-db/tunnel-decap-table.md)

<!-- /yang-xref -->

## ツリー

```text
module: sonic-tunnel
  +--rw sonic-tunnel
     +--rw TUNNEL
        +--rw TUNNEL_LIST* [mux_tunnel]
           +--rw mux_tunnel               string
           +--rw dscp_mode?               string
           +--rw src_ip?                  -> /ps:sonic-peer-switch/PEER_SWITCH/PEER_SWITCH_LIST/address_ipv4
           +--rw dst_ip?                  inet:ipv4-address
           +--rw ecn_mode?                string
           +--rw encap_ecn_mode?          string
           +--rw ttl_mode?                string
           +--rw tunnel_type?             string
           +--rw decap_dscp_to_tc_map?    string
           +--rw decap_tc_to_pg_map?      string
           +--rw encap_tc_to_dscp_map?    string
           +--rw encap_tc_to_queue_map?   string
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `mux_tunnel` | `sonic-tunnel/TUNNEL/TUNNEL_LIST/mux_tunnel` | `string` | yes |  |  | Name of MuxTunnel |
| `dscp_mode` | `sonic-tunnel/TUNNEL/TUNNEL_LIST/dscp_mode` | `string` |  |  | uniform, pipe | [DSCP](../../reference/glossary.md#term-dscp) handling mode (uniform copies outer, pipe preserves inner) |
| `src_ip` | `sonic-tunnel/TUNNEL/TUNNEL_LIST/src_ip` | `leafref` |  |  | /ps:sonic-peer-switch/PEER_SWITCH/PEER_SWITCH_LIST/address_ipv4 | Tunnel source IPv4 (= peer ToR address) |
| `dst_ip` | `sonic-tunnel/TUNNEL/TUNNEL_LIST/dst_ip` | `inet:ipv4-address` |  |  |  | Tunnel destination IPv4 (= this switch address) |
| `ecn_mode` | `sonic-tunnel/TUNNEL/TUNNEL_LIST/ecn_mode` | `string` |  |  | standard, copy_from_outer | ECN handling mode on decapsulation |
| `encap_ecn_mode` | `sonic-tunnel/TUNNEL/TUNNEL_LIST/encap_ecn_mode` | `string` |  |  | standard, copy_from_inner | ECN marking mode on encapsulation |
| `ttl_mode` | `sonic-tunnel/TUNNEL/TUNNEL_LIST/ttl_mode` | `string` |  |  | uniform, pipe | TTL handling mode |
| `tunnel_type` | `sonic-tunnel/TUNNEL/TUNNEL_LIST/tunnel_type` | `string` |  |  | IPINIP | Encapsulation type |
| `decap_dscp_to_tc_map` | `sonic-tunnel/TUNNEL/TUNNEL_LIST/decap_dscp_to_tc_map` | `string` |  |  |  | [DSCP](../../reference/glossary.md#term-dscp)-to-TC map applied on decapsulation |
| `decap_tc_to_pg_map` | `sonic-tunnel/TUNNEL/TUNNEL_LIST/decap_tc_to_pg_map` | `string` |  |  |  | TC-to-PG map applied on decapsulation |
| `encap_tc_to_dscp_map` | `sonic-tunnel/TUNNEL/TUNNEL_LIST/encap_tc_to_dscp_map` | `string` |  |  |  | TC-to-DSCP map applied on encapsulation |
| `encap_tc_to_queue_map` | `sonic-tunnel/TUNNEL/TUNNEL_LIST/encap_tc_to_queue_map` | `string` |  |  |  | TC-to-queue map applied on encapsulation |

## leafref / 依存

- `sonic-tunnel/TUNNEL/TUNNEL_LIST/src_ip` → `/ps:sonic-peer-switch/ps:PEER_SWITCH/ps:PEER_SWITCH_LIST/ps:address_ipv4`

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `TUNNEL`
- CLI: なし（DualToR 構築時に [config_db.json](../../reference/glossary.md#term-config_db.json) で直接設定）

<!-- yang-sibling -->
### 関連 YANG モジュール

意味的に関連する SONiC YANG モジュール (slug prefix / curated group / frontmatter `related.yang` から自動抽出):

- [`sonic-mux-cable`](sonic-mux-cable.md)
- [`sonic-nvgre-tunnel`](sonic-nvgre-tunnel.md)
- [`sonic-srv6`](sonic-srv6.md)
- [`sonic-vnet`](sonic-vnet.md)
- [`sonic-vxlan`](sonic-vxlan.md)
<!-- /yang-sibling -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`TUNNEL`](../config-db/tunnel.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-tunnel.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

<!-- glossary-links-injected: 36ca10160326 -->
