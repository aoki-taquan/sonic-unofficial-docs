---
title: sonic-trimming YANG
description: "sonic-trimming YANG — パケットトリミング（輻輳テレメトリ用にパケットを縮小して送信）のグローバル設定を保持する YANG モジュール。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-trimming.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [SWITCH_TRIMMING]
  cli: ["config switch-trimming"]
  yang: [sonic-buffer-profile, sonic-queue, sonic-dscp-tc-map]
---

# sonic-trimming YANG

## 概要

- module: `sonic-trimming`
- namespace: `http://github.com/sonic-net/sonic-trimming`
- revision: `2024-11-01`
- import: なし
- top container: `sonic-trimming`

パケットトリミング（輻輳テレメトリ用にパケットを縮小して送信）のグローバル設定を保持する [YANG](../../reference/glossary.md#term-yang) モジュール[^1]。

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-trimming"]
  C1[("CONFIG_DB<br/>SWITCH_TRIMMING")]
  Y --> C1
  D1["SwitchOrch"]
  C1 --> D1
```

!!! note "凡例"
    YANG モジュールから CONFIG_DB テーブル経由で subscribe する daemon/orch までを `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文を参照。
<!-- /yang-mermaid -->

## 関連ページ

<!-- yang-xref -->

本 [YANG](../../reference/glossary.md#term-yang) モジュールに対応する [CONFIG_DB](../../reference/glossary.md#term-config_db) / CLI / [HLD](../../reference/glossary.md#term-hld) / Topics への相互リンク。`inject_yang_xref.py` により自動生成されます。

### 対応 CONFIG_DB

- [`SWITCH_TRIMMING`](../config-db/switch-trimming.md)

<!-- /yang-xref -->

## ツリー

```
module: sonic-trimming
  +--rw sonic-trimming
     +--rw SWITCH_TRIMMING
        +--rw GLOBAL
           +--rw size?          uint32
           +--rw dscp_value?    union(uint8 0..63, "from-tc")
           +--rw tc_value?      uint8
           +--rw queue_index?   union(uint8, "dynamic")
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `size` | `sonic-trimming/SWITCH_TRIMMING/GLOBAL/size` | `uint32` |  |  | bytes | トリミング後のパケットサイズ |
| `dscp_value` | `.../dscp_value` | `union(uint8, string)` |  |  | uint8 0..63 または `from-tc` | トリミング後の [DSCP](../../reference/glossary.md#term-dscp) 値。`from-tc` で `tc_value` 経由マッピングを使用 |
| `tc_value` | `.../tc_value` | `uint8` |  |  |  | トリミング後の TC 値 |
| `queue_index` | `.../queue_index` | `union(uint8, string)` |  |  | uint8 または `dynamic` | トリミング後の送信キュー。`dynamic` で `dscp_value` 経由マッピング |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `SWITCH_TRIMMING|GLOBAL`
- CLI: `config switch-trimming`

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`SWITCH_TRIMMING`](../config-db/switch-trimming.md)
- CLI: `config switch-trimming`

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-trimming.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

<!-- glossary-links-injected: bdcdeec1d5aa -->
