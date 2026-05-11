---
title: MPLS_TC_TO_TC_MAP テーブル
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-mpls-tc-map.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - MPLS_TC_TO_TC_MAP
    - PORT_QOS_MAP
  cli:
    - config qos
  yang:
    - sonic-mpls-tc-map
---

# MPLS_TC_TO_TC_MAP テーブル

## 概要

ingress 側で **MPLS TC bit を内部 Traffic Class (TC, 0..7)** にマップするテーブル。MPLS パケットの QoS classification に使用される[^1]。

## key 構造

```
MPLS_TC_TO_TC_MAP|<name>
```

`<name>` はマップ名 (`[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})`、長さ 1..32)。値部は **MPLS TC → TC のハッシュ**。

## 主要フィールド (entry-level)

| フィールド | 型 | 範囲 | 説明 |
|-----------|----|------|------|
| `<mpls>` | string | 0..7 | MPLS TC 値をキーにした TC 値 (`stypes:tc_type`) を保持 |

例:

```
MPLS_TC_TO_TC_MAP|AZURE_MPLS
  "0": "0"
  "1": "1"
  ...
  "7": "7"
```

## 購読者

- `swss`/`orchagent`: `QosOrch` が SAI QOS_MAP (`SAI_QOS_MAP_TYPE_MPLS_EXP_TO_TC` 相当) としてプログラム
- `PORT_QOS_MAP|<port>` の `mpls_tc_to_tc_map` フィールドが本テーブルを参照

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `PORT_QOS_MAP`、`DSCP_TO_TC_MAP`、`EXP_TO_FC_MAP`
- 関連 YANG: `sonic-mpls-tc-map`
- 関連 CLI: `config qos` 系 (sonic-utilities `qos` グループ)

<!-- ref-triangle:start -->

## 関連リファレンス

- (関連 YANG ページなし)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-mpls-tc-map.yang` (`revision 2021-04-15`). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-mpls-tc-map.yang>
