---
title: TC_TO_DSCP_MAP テーブル
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-tc-dscp-map.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - TC_TO_DSCP_MAP
    - PORT_QOS_MAP
  cli:
    - config qos
  yang:
    - sonic-tc-dscp-map
---

# TC_TO_DSCP_MAP テーブル

## 概要

egress 側で **内部 TC を DSCP に remark** するマップ。`PORT_QOS_MAP|<port>` の `tc_to_dscp_map` フィールドから名前で参照され、ASIC の egress remarking テーブルに反映される[^1]。

## key 構造

```
TC_TO_DSCP_MAP|<name>
```

`<name>` はマップ名 (`[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})`、長さ 1..32)。値部は **TC → DSCP のハッシュ**。

## 主要フィールド (entry-level)

| フィールド | 型 | 範囲 | 説明 |
|-----------|----|------|------|
| `<tc>` | `stypes:tc_type` | 0..7 | TC 値をキーにした DSCP 値 (0..63) を保持 |

例:

```
TC_TO_DSCP_MAP|AZURE
  "0": "0"
  "1": "8"
  ...
  "7": "56"
```

## 購読者

- `swss`/`orchagent`: `QosOrch` が SAI QOS_MAP (`SAI_QOS_MAP_TYPE_TC_AND_COLOR_TO_DSCP` 系) として ASIC にプログラム
- `PORT_QOS_MAP|<port>` の `tc_to_dscp_map` フィールドが本テーブルを参照

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `PORT_QOS_MAP`、`DSCP_TO_TC_MAP` (ingress 側)、`TC_TO_QUEUE_MAP`
- 関連 YANG: `sonic-tc-dscp-map`
- 関連 CLI: `config qos remap` 系 (sonic-utilities `qos` グループ)

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-tc-dscp-map`](../yang/sonic-tc-dscp-map.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-tc-dscp-map.yang` (`revision 2025-01-10`). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-tc-dscp-map.yang>
