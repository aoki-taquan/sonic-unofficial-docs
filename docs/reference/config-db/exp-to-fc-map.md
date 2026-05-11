---
title: EXP_TO_FC_MAP テーブル
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-exp-fc-map.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - EXP_TO_FC_MAP
    - PORT_QOS_MAP
  cli:
    - config cbf
  yang:
    - sonic-exp-fc-map
---

# EXP_TO_FC_MAP テーブル

## 概要

Class-Based Forwarding (CBF) で受信 MPLS EXP bit を **Forwarding Class (FC, 0..7)** にマップするテーブル。MPLS フォワーディング時に使われ、`PORT_QOS_MAP` から名前で参照されて port にバインドされる[^1]。

## key 構造

```
EXP_TO_FC_MAP|<name>
```

`<name>` はマップ名 (`[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})`、長さ 1..32)。値部は **EXP → FC のハッシュ**。

## 主要フィールド (entry-level)

| フィールド | 型 | 範囲 | 説明 |
|-----------|----|------|------|
| `<exp>` | string | 0..7 | EXP 値をキーにした FC 値 (`[0-7]?`) を保持 |

例:

```
EXP_TO_FC_MAP|AZURE_MPLS
  "0": "0"
  "1": "1"
  ...
  "7": "7"
```

## 購読者

- `swss`/`orchagent`: `QosOrch` が SAI QOS_MAP (`SAI_QOS_MAP_TYPE_MPLS_EXP_TO_FORWARDING_CLASS`) としてプログラム
- `PORT_QOS_MAP|<port>` の `exp_to_fc_map` フィールドが本テーブルを参照

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `PORT_QOS_MAP`、`DSCP_TO_FC_MAP`
- 関連 YANG: `sonic-exp-fc-map`
- 関連 CLI: `config cbf exp-fc-map` (sonic-utilities `cbf` グループ)

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-exp-fc-map`](../yang/sonic-exp-fc-map.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-exp-fc-map.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-exp-fc-map.yang>
