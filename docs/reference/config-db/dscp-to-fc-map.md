---
title: DSCP_TO_FC_MAP テーブル
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dscp-fc-map.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - DSCP_TO_FC_MAP
    - PORT_QOS_MAP
  cli:
    - config cbf
  yang:
    - sonic-dscp-fc-map
---

# DSCP_TO_FC_MAP テーブル

## 概要

Class-Based Forwarding (CBF) で受信 DSCP を **Forwarding Class (FC, 0..7)** にマップするテーブル。`PORT_QOS_MAP` から名前で参照されて port にバインドされる[^1]。

## key 構造

```
DSCP_TO_FC_MAP|<name>
```

`<name>` はマップ名 (`[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})`、長さ 1..32)。値部は **DSCP → FC のハッシュ**。

## 主要フィールド (entry-level)

| フィールド | 型 | 範囲 | 説明 |
|-----------|----|------|------|
| `<dscp>` | string | 0..63 | DSCP 値をキーにした FC 値 (`[0-7]?`) を保持 |

例:

```
DSCP_TO_FC_MAP|AZURE
  "0": "0"
  "8": "1"
  "16": "2"
  ...
```

## 購読者

- `swss`/`orchagent`: `QosOrch` が CBF map を SAI `SAI_OBJECT_TYPE_QOS_MAP` (`SAI_QOS_MAP_TYPE_DSCP_TO_FORWARDING_CLASS`) に変換して ASIC へ
- `PORT_QOS_MAP|<port>` の `dscp_to_fc_map` フィールドが本テーブルを参照

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `PORT_QOS_MAP`、`EXP_TO_FC_MAP` (MPLS 側)
- 関連 YANG: `sonic-dscp-fc-map`
- 関連 CLI: `config cbf dscp-fc-map` (sonic-utilities `cbf` グループ)

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-dscp-fc-map`](../yang/sonic-dscp-fc-map.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-dscp-fc-map.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-dscp-fc-map.yang>
