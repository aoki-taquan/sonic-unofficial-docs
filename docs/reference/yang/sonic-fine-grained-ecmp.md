---
title: sonic-fine-grained-ecmp YANG
description: "sonic-fine-grained-ecmp YANG — Fine-Grained ECMP (FG_NHG) のグループ・対象プレフィックス・メンバの 3 テーブルを保持する。bucket-size と match_mode により flow-to-nexthop の固定マッピングを記述する。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-fine-grained-ecmp.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [FG_NHG, FG_NHG_PREFIX, FG_NHG_MEMBER]
  cli: []
  yang: [sonic-portchannel, sonic-port, sonic-types]
  _no_related_cli: true
---

# sonic-fine-grained-ecmp YANG

## 概要

- module: `sonic-fine-grained-ecmp`
- namespace: `http://github.com/sonic-net/sonic-fine-grained-ecmp`
- revision: `2024-09-15` (Added support for dynamic nexthop group), `2023-01-19` (initial)
- import: `ietf-inet-types`, `sonic-portchannel`, `sonic-port`, `sonic-types`
- top container: `sonic-fine-grained-ecmp`

Fine-Grained [ECMP](../../reference/glossary.md#term-ecmp) (FG_NHG) のグループ・対象プレフィックス・メンバの 3 テーブルを保持する。bucket-size と match_mode により flow-to-nexthop の固定マッピングを記述する[^1]。

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-fine-grained-ecmp"]
  C1[("CONFIG_DB<br/>FG_NHG")]
  Y --> C1
  D1["FgNhgOrch"]
  C1 --> D1
  C2[("CONFIG_DB<br/>FG_NHG_PREFIX")]
  Y --> C2
  C2 --> D1
  C3[("CONFIG_DB<br/>FG_NHG_MEMBER")]
  Y --> C3
  C3 --> D1
```

!!! note "凡例"
    YANG モジュールから CONFIG_DB テーブル経由で subscribe する daemon/orch までを `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文を参照。
<!-- /yang-mermaid -->

## 関連ページ

<!-- yang-xref -->

本 YANG モジュールに対応する CONFIG_DB / CLI / HLD / Topics への相互リンク。`inject_yang_xref.py` により自動生成されます。

### 対応 CONFIG_DB

- [`FG_NHG`](../config-db/fg-nhg.md)
- [`FG_NHG_PREFIX`](../config-db/fg-nhg.md)
- [`FG_NHG_MEMBER`](../config-db/fg-nhg.md)

### 関連 Topics

- [VRF / ECMP / RIB-FIB パイプライン](../../topics/04-vrf-ecmp/index.md)

<!-- /yang-xref -->

## ツリー

```text
module: sonic-fine-grained-ecmp
  +--rw sonic-fine-grained-ecmp
     +--rw FG_NHG
     |  +--rw FG_NHG_LIST* [name]
     |     +--rw name             string
     |     +--rw bucket_size      uint16
     |     +--rw match_mode       match-mode-name
     |     +--rw max_next_hops?   uint16     // when match_mode='prefix-based'; range 1..128
     +--rw FG_NHG_PREFIX
     |  +--rw FG_NHG_PREFIX_LIST* [ip_prefix]
     |     +--rw ip_prefix    stypes:sonic-ip-prefix
     |     +--rw FG_NHG       -> /sonic-fine-grained-ecmp/FG_NHG/FG_NHG_LIST/name
     +--rw FG_NHG_MEMBER
        +--rw FG_NHG_MEMBER_LIST* [next_hop_ip]
           +--rw next_hop_ip    inet:ip-address
           +--rw FG_NHG         -> /sonic-fine-grained-ecmp/FG_NHG/FG_NHG_LIST/name
           +--rw bank           uint16
           +--rw link?          union
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `name` | `sonic-fine-grained-ecmp/FG_NHG/FG_NHG_LIST/name` | `string` | yes |  |  | FG_NHG group name |
| `bucket_size` | `sonic-fine-grained-ecmp/FG_NHG/FG_NHG_LIST/bucket_size` | `uint16` | yes |  |  | Total hash bucket size (recommended LCM of 1..max nexthops) |
| `match_mode` | `sonic-fine-grained-ecmp/FG_NHG/FG_NHG_LIST/match_mode` | `match-mode-name` | yes |  | nexthop-based, route-based, prefix-based | Filtering method to identify when to use Fine Grained handling |
| `max_next_hops` | `sonic-fine-grained-ecmp/FG_NHG/FG_NHG_LIST/max_next_hops` | `uint16` | conditional[^2] |  | range `1..128`, `must "current() > 0"` | `match_mode = prefix-based` のときのみ適用される最大 nexthop 数。`when` により他モードでは存在不可、`prefix-based` 時は mandatory[^2] |
| `ip_prefix` | `sonic-fine-grained-ecmp/FG_NHG_PREFIX/FG_NHG_PREFIX_LIST/ip_prefix` | `stypes:sonic-ip-prefix` | yes |  |  | Prefix for which FG behavior is desired |
| `FG_NHG` | `sonic-fine-grained-ecmp/FG_NHG_PREFIX/FG_NHG_PREFIX_LIST/FG_NHG` | `leafref` | yes |  | /sonic-fine-grained-ecmp/FG_NHG/FG_NHG_LIST/name | Fine Grained nexthop group name |
| `next_hop_ip` | `sonic-fine-grained-ecmp/FG_NHG_MEMBER/FG_NHG_MEMBER_LIST/next_hop_ip` | `inet:ip-address` | yes |  |  | Member nexthop IP associated with the prefix |
| `FG_NHG` | `sonic-fine-grained-ecmp/FG_NHG_MEMBER/FG_NHG_MEMBER_LIST/FG_NHG` | `leafref` | yes |  | /sonic-fine-grained-ecmp/FG_NHG/FG_NHG_LIST/name | Fine Grained nexthop group name |
| `bank` | `sonic-fine-grained-ecmp/FG_NHG_MEMBER/FG_NHG_MEMBER_LIST/bank` | `uint16` | yes |  |  | Index of bank/group for redistribution |
| `link` | `sonic-fine-grained-ecmp/FG_NHG_MEMBER/FG_NHG_MEMBER_LIST/link` | `union` |  |  | union(port leafref, portchannel leafref) | Local link associated with the nexthop |

## leafref / 依存

- `sonic-fine-grained-ecmp/FG_NHG_PREFIX/FG_NHG_PREFIX_LIST/FG_NHG` → `/sonic-fine-grained-ecmp/FG_NHG/FG_NHG_LIST/name`
- `sonic-fine-grained-ecmp/FG_NHG_MEMBER/FG_NHG_MEMBER_LIST/FG_NHG` → `/sonic-fine-grained-ecmp/FG_NHG/FG_NHG_LIST/name`
- `sonic-fine-grained-ecmp/FG_NHG_MEMBER/FG_NHG_MEMBER_LIST/link` → port または portchannel leafref

## 制約 (when / must / range)

- `max_next_hops` には次の 3 つの制約が同時に課される[^2]:
    - `when "current()/../match_mode = 'prefix-based'"`: `match_mode` が `prefix-based` 以外のとき本 leaf は存在不可。データツリー上に出現すると validation エラー
    - `mandatory true`: `when` が成立するケース (= `prefix-based` モード) では必須
    - `type uint16 { range 1..128; }`: コメントに *"Adjust based on platform support"* とあり、上限はプラットフォーム能力に応じて調整される前提の YANG 既定値
    - `must "current() > 0"`: `range 1..128` で 0 は既に排除されるが、意味的な dynamic-nhg モードの非ゼロ要件を redundancy として明示。違反時メッセージは `"max_next_hops needs to be a positive value in dynamic-nhg mode"`
- 上記により、`route-based` / `nexthop-based` の従来モードでは `max_next_hops` を設定してはならず、`prefix-based` モードでは必ず 1..128 の値を設定する必要がある

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `FG_NHG`, `FG_NHG_PREFIX`, `FG_NHG_MEMBER`
- CLI: なし（[config_db.json](../../reference/glossary.md#term-config_db.json) で直接設定）

<!-- yang-sibling -->
### 関連 YANG モジュール

意味的に関連する SONiC YANG モジュール (slug prefix / curated group / frontmatter `related.yang` から自動抽出):

- [`sonic-portchannel`](sonic-portchannel.md)
- [`sonic-port`](sonic-port.md)
- [`sonic-hash`](sonic-hash.md)
- [`sonic-route-common`](sonic-route-common.md)
- [`sonic-trimming`](sonic-trimming.md)
<!-- /yang-sibling -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`FG_NHG`](../config-db/fg-nhg.md) / [`FG_NHG_PREFIX`](../config-db/fg-nhg.md) / [`FG_NHG_MEMBER`](../config-db/fg-nhg.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-fine-grained-ecmp.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
[^2]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-fine-grained-ecmp.yang` L98-L109 @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd` (`leaf max_next_hops` の `when` / `mandatory true` / `type uint16 { range 1..128; }` / `must "current() > 0"`)

<!-- glossary-links-injected: 20dbc11976b6 -->
