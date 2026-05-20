---
title: sonic-tc-priority-group-map YANG
description: "sonic-tc-priority-group-map YANG — TC_TO_PRIORITY_GROUP_MAP yang Module for SONiC OS. Traffic Class を ingress priority group へマップしバッファ受入制御に使う。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-tc-priority-group-map.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [TC_TO_PRIORITY_GROUP_MAP]
  cli: []
  yang: [sonic-port-qos-map, sonic-buffer-pg]
---

# sonic-tc-priority-group-map YANG

## 概要

- module: `sonic-tc-priority-group-map`
- namespace: `http://github.com/sonic-net/sonic-tc-priority-group-map`
- revision: `2021-04-15`
- import: `sonic-types`
- top container: `sonic-tc-priority-group-map`

TC_TO_PRIORITY_GROUP_MAP yang Module for [SONiC](../../reference/glossary.md#term-sonic) OS. Traffic Class を ingress priority group へマップしバッファ受入制御に使う。[^1]

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-tc-priority-group-map"]
  C1[("CONFIG_DB<br/>TC_TO_PRIORITY_GROUP_MAP")]
  Y --> C1
  D1["QosOrch"]
  C1 --> D1
```

!!! note "凡例"
    YANG モジュールから CONFIG_DB テーブル経由で subscribe する daemon/orch までを `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文を参照。
<!-- /yang-mermaid -->

## 関連ページ

<!-- yang-xref -->

本 YANG モジュールに対応する CONFIG_DB / CLI / HLD / Topics への相互リンク。`inject_yang_xref.py` により自動生成されます。

### 対応 CONFIG_DB

- [`TC_TO_PRIORITY_GROUP_MAP`](../config-db/tc-to-priority-group-map.md)

<!-- /yang-xref -->

## ツリー

```text
module: sonic-tc-priority-group-map
  +--rw sonic-tc-priority-group-map
     +--rw TC_TO_PRIORITY_GROUP_MAP
        +--rw TC_TO_PRIORITY_GROUP_MAP_LIST* [name]
           +--rw name    string
           +--rw TC_TO_PRIORITY_GROUP_MAP* [tc]
              +--rw tc    stypes:tc_type
              +--rw pg?   string
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `name` | `sonic-tc-priority-group-map/TC_TO_PRIORITY_GROUP_MAP/TC_TO_PRIORITY_GROUP_MAP_LIST/name` | `string` | yes |  | pattern `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})`, length 1..32 | Name of the TC to priority group map. |
| `tc` | `.../TC_TO_PRIORITY_GROUP_MAP/tc` | `stypes:tc_type` | yes |  |  | Source traffic class. |
| `pg` | `.../TC_TO_PRIORITY_GROUP_MAP/pg` | `string` |  |  | pattern `[0-7]?` | Target ingress priority group (0-7). |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `TC_TO_PRIORITY_GROUP_MAP|<name>`、`PORT_QOS_MAP|<port>/tc_to_pg_map` から参照

<!-- yang-sibling -->
### 関連 YANG モジュール

意味的に関連する SONiC YANG モジュール (slug prefix / curated group / frontmatter `related.yang` から自動抽出):

- [`sonic-port-qos-map`](sonic-port-qos-map.md)
- [`sonic-buffer-pg`](sonic-buffer-pg.md)
- [`sonic-buffer-pool`](sonic-buffer-pool.md)
- [`sonic-buffer-profile`](sonic-buffer-profile.md)
- [`sonic-buffer-queue`](sonic-buffer-queue.md)
<!-- /yang-sibling -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `TC_TO_PRIORITY_GROUP_MAP`

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-tc-priority-group-map.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

<!-- glossary-links-injected: 8ba32e5aa69d -->
