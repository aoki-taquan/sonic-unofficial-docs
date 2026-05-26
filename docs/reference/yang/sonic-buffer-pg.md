---
title: sonic-buffer-pg YANG
description: "sonic-buffer-pg YANG — Ingress buffer priority group configuration for SONiC ports."
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-buffer-pg.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [BUFFER_PG]
  cli: []
  yang: [sonic-port, sonic-buffer-profile]
---

# sonic-buffer-pg YANG

## 概要

- module: `sonic-buffer-pg`
- namespace: `http://github.com/sonic-net/sonic-buffer-pg`
- revision: `2021-07-01`
- import: `sonic-port`, `sonic-buffer-profile`
- top container: `sonic-buffer-pg`

[SONiC](../../reference/glossary.md#term-sonic) ポートの Ingress バッファ優先グループ ([Priority Group](../../reference/glossary.md#term-priority-group)) 設定を管理する [YANG](../../reference/glossary.md#term-yang) モジュール。[^1]

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-buffer-pg"]
  C1[("CONFIG_DB<br/>BUFFER_PG")]
  Y --> C1
  D1["buffermgrd"]
  C1 --> D1
```

!!! note "凡例"
    YANG モジュールから CONFIG_DB テーブル経由で subscribe する daemon/orch までを `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文を参照。
<!-- /yang-mermaid -->

## 関連ページ

<!-- yang-xref -->

本 YANG モジュールに対応する CONFIG_DB / CLI / HLD / Topics への相互リンク。`inject_yang_xref.py` により自動生成されます。

### 対応 CONFIG_DB

- [`BUFFER_PG`](../config-db/buffer-pg.md)

### 関連 HLD

- [sonic-buffer-pool YANG](../../reference/yang/sonic-buffer-pool.md)

<!-- /yang-xref -->

## ツリー

```text
module: sonic-buffer-pg
  +--rw sonic-buffer-pg
     +--rw BUFFER_PG
        +--rw BUFFER_PG_LIST* [port pg_num]
           +--rw port       -> /prt:sonic-port/PORT/PORT_LIST/name
           +--rw pg_num     string
           +--rw profile?   union
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `port` | `sonic-buffer-pg/BUFFER_PG/BUFFER_PG_LIST/port` | `leafref` | yes |  | /prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name | Port on which the buffer priority group is configured. |
| `pg_num` | `sonic-buffer-pg/BUFFER_PG/BUFFER_PG_LIST/pg_num` | `string` | yes |  | pattern `[0-7]((-)[0-7])?` | [Priority Group](../../reference/glossary.md#term-priority-group) number |
| `profile` | `sonic-buffer-pg/BUFFER_PG/BUFFER_PG_LIST/profile` | `union` |  | 0 | union(leafref, string) | [Buffer Profile](../../reference/glossary.md#term-buffer-profile) associated with [Priority Group](../../reference/glossary.md#term-priority-group) number for a port |

## leafref / 依存

- `sonic-buffer-pg/BUFFER_PG/BUFFER_PG_LIST/port` → `/prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name`

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `BUFFER_PG`

<!-- yang-sibling -->
### 関連 YANG モジュール

意味的に関連する SONiC YANG モジュール (slug prefix / curated group / frontmatter `related.yang` から自動抽出):

- [`sonic-port`](sonic-port.md)
- [`sonic-buffer-profile`](sonic-buffer-profile.md)
- [`sonic-buffer-pool`](sonic-buffer-pool.md)
- [`sonic-buffer-queue`](sonic-buffer-queue.md)
- [`sonic-dot1p-tc-map`](sonic-dot1p-tc-map.md)
<!-- /yang-sibling -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`BUFFER_PG`](../config-db/buffer-pg.md)

<!-- ref-triangle:end -->

<!-- ops-hint -->
## 運用ヒント

### 典型的なデプロイ位置

- [QoS](../../reference/glossary.md#term-qos) priority-group のバッファ割り当て。`BUFFER_PG|<port>|<pg-index>` を `swss/orchagent` の bufferorch が [SAI](../../reference/glossary.md#term-sai) へ反映する。

### よくある落とし穴

- `profile` leafref で BUFFER_PROFILE を参照。先に profile を消すと leafref エラーで [CONFIG_DB](../../reference/glossary.md#term-config_db) 書き込みが失敗する。

### 関連する config / show コマンド

```bash
sonic-db-cli CONFIG_DB keys 'BUFFER_PG|*'
show priority-group persistent-watermark headroom
```
<!-- /ops-hint -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-buffer-pg.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`


<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 8ba32e5aa69d -->
