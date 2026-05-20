---
title: sonic-pfc-priority-queue-map YANG
description: "sonic-pfc-priority-queue-map YANG — PFC_PRIORITY_TO_QUEUE_MAP yang Module for SONiC OS. PFC 優先度 (0-7) を egress queue index にマッピングする。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-pfc-priority-queue-map.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [MAP_PFC_PRIORITY_TO_QUEUE]
  cli: []
  yang: [sonic-port-qos-map, sonic-queue]
---

# sonic-pfc-priority-queue-map YANG

## 概要

- module: `sonic-pfc-priority-queue-map`
- namespace: `http://github.com/sonic-net/sonic-pfc-priority-queue-map`
- revision: `2021-04-15`
- import: なし
- top container: `sonic-pfc-priority-queue-map`

PFC_PRIORITY_TO_QUEUE_MAP yang Module for SONiC OS. [PFC](../../reference/glossary.md#term-pfc) 優先度 (0-7) を egress queue index にマッピングする。[^1]

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-pfc-priority-queue-map"]
  C1[("CONFIG_DB<br/>MAP_PFC_PRIORITY_TO_QUEUE")]
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

- [`MAP_PFC_PRIORITY_TO_QUEUE`](../config-db/map-pfc-priority-to-queue.md)

<!-- /yang-xref -->

## ツリー

```text
module: sonic-pfc-priority-queue-map
  +--rw sonic-pfc-priority-queue-map
     +--rw MAP_PFC_PRIORITY_TO_QUEUE
        +--rw MAP_PFC_PRIORITY_TO_QUEUE_LIST* [name]
           +--rw name    string
           +--rw MAP_PFC_PRIORITY_TO_QUEUE* [pfc_priority]
              +--rw pfc_priority    string
              +--rw qindex?         string
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `name` | `sonic-pfc-priority-queue-map/MAP_PFC_PRIORITY_TO_QUEUE/MAP_PFC_PRIORITY_TO_QUEUE_LIST/name` | `string` | yes |  | pattern `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})`, length 1..32 | Name of the [PFC](../../reference/glossary.md#term-pfc) priority to queue map. |
| `pfc_priority` | `.../MAP_PFC_PRIORITY_TO_QUEUE/pfc_priority` | `string` | yes |  | pattern `[0-7]?` | [PFC](../../reference/glossary.md#term-pfc) priority value (0-7). |
| `qindex` | `.../MAP_PFC_PRIORITY_TO_QUEUE/qindex` | `string` |  |  | pattern `[0-7]?` | Target egress queue index (0-7). |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `MAP_PFC_PRIORITY_TO_QUEUE|<name>` でマップ本体、`PORT_QOS_MAP|<port>/pfc_to_queue_map` から参照
- CLI: マップ名は `config qos reload` / minigraph 経由で投入

<!-- yang-sibling -->
### 関連 YANG モジュール

意味的に関連する SONiC YANG モジュール (slug prefix / curated group / frontmatter `related.yang` から自動抽出):

- [`sonic-port-qos-map`](sonic-port-qos-map.md)
- [`sonic-queue`](sonic-queue.md)
- [`sonic-buffer-pg`](sonic-buffer-pg.md)
- [`sonic-buffer-pool`](sonic-buffer-pool.md)
- [`sonic-buffer-profile`](sonic-buffer-profile.md)
<!-- /yang-sibling -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`MAP_PFC_PRIORITY_TO_QUEUE`](../config-db/map-pfc-priority-to-queue.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-pfc-priority-queue-map.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

<!-- glossary-links-injected: 20dbc11976b6 -->
