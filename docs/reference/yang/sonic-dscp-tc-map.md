---
title: sonic-dscp-tc-map YANG
description: sonic-dscp-tc-map YANG — DSCP_TO_TC_MAP yang Module for SONiC OS
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/sonic-buildimage
  path: src/sonic-yang-models/yang-models/sonic-dscp-tc-map.yang
  ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
  - DSCP_TO_TC_MAP
  cli: []
  yang:
  - sonic-tc-queue-map
  - sonic-tc-dscp-map
  - sonic-port-qos-map
---

# sonic-dscp-tc-map YANG

## 概要

- module: `sonic-dscp-tc-map`
- namespace: `http://github.com/sonic-net/sonic-dscp-tc-map`
- revision: `2021-04-15`
- import: `sonic-types`
- top container: `sonic-dscp-tc-map`

DSCP_TO_TC_MAP yang Module for SONiC OS[^1]

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-dscp-tc-map"]
  C1[("CONFIG_DB<br/>DSCP_TO_TC_MAP")]
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

- [`DSCP_TO_TC_MAP`](../config-db/dscp-to-tc-map.md)

<!-- /yang-xref -->

## ツリー

```text
module: sonic-dscp-tc-map
  +--rw sonic-dscp-tc-map
     +--rw DSCP_TO_TC_MAP
        +--rw DSCP_TO_TC_MAP_LIST* [name]
           +--rw name              string
           +--rw DSCP_TO_TC_MAP* [dscp]
              +--rw dscp    string
              +--rw tc?     stypes:tc_type
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `name` | `sonic-dscp-tc-map/DSCP_TO_TC_MAP/DSCP_TO_TC_MAP_LIST/name` | `string` | yes |  | pattern `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})` | Name of the [DSCP](../../reference/glossary.md#term-dscp) to TC map. |
| `dscp` | `sonic-dscp-tc-map/DSCP_TO_TC_MAP/DSCP_TO_TC_MAP_LIST/DSCP_TO_TC_MAP/dscp` | `string` | yes |  | pattern `6[0-3]|[1-5][0-9]?|[0-9]?` | [DSCP](../../reference/glossary.md#term-dscp) value (0-63). |
| `tc` | `sonic-dscp-tc-map/DSCP_TO_TC_MAP/DSCP_TO_TC_MAP_LIST/DSCP_TO_TC_MAP/tc` | `stypes:tc_type` |  |  |  | Target traffic class. |

## leafref / 依存

- なし（このモジュール内で直接 leafref を持つ leaf はない）

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `DSCP_TO_TC_MAP`

<!-- yang-sibling -->
### 関連 YANG モジュール

意味的に関連する SONiC YANG モジュール (slug prefix / curated group / frontmatter `related.yang` から自動抽出):

- [`sonic-tc-queue-map`](sonic-tc-queue-map.md)
- [`sonic-port-qos-map`](sonic-port-qos-map.md)
- [`sonic-buffer-pg`](sonic-buffer-pg.md)
- [`sonic-buffer-pool`](sonic-buffer-pool.md)
- [`sonic-buffer-profile`](sonic-buffer-profile.md)
<!-- /yang-sibling -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`DSCP_TO_TC_MAP`](../config-db/dscp-to-tc-map.md)

<!-- ref-triangle:end -->

<!-- ops-hint -->
## 運用ヒント

### 典型的なデプロイ位置

- [DSCP](../../reference/glossary.md#term-dscp) → TC マッピング。`DSCP_TO_TC_MAP|<name>` を qosorch が [SAI](../../reference/glossary.md#term-sai) qos map に反映。

### よくある落とし穴

- key は 0-63 の string。leading zero 表記 (e.g. `07`) を入れると別エントリ扱いになる。

### 関連する config / show コマンド

```bash
sonic-db-cli CONFIG_DB keys 'DSCP_TO_TC_MAP|*'
show qos map dscp-tc
```
<!-- /ops-hint -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-dscp-tc-map.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

<!-- glossary-links-injected: 36ca10160326 -->
