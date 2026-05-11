---
title: PFC_PRIORITY_TO_PRIORITY_GROUP_MAP テーブル
area: reference
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-pfc-priority-priority-group-map.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
related:
  config_db:
    - PFC_PRIORITY_TO_PRIORITY_GROUP_MAP
  cli:
    - config qos
  yang:
    - sonic-pfc-priority-priority-group-map
---

# PFC_PRIORITY_TO_PRIORITY_GROUP_MAP テーブル

## 概要

`PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` は PFC priority 0..7 を ingress priority group 0..7 に対応付ける named QoS map テーブル[^1]。`PORT_QOS_MAP.pfc_to_pg_map` から参照され、lossless traffic の buffer priority group 選択に使われる。`schema.h` では APPL_DB 側の `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_TABLE` 定数が定義されている[^2]。

## key 構造

```text
PFC_PRIORITY_TO_PRIORITY_GROUP_MAP|<name>|<pfc_priority>
```

YANG 上は map 名を key にする outer list と、`pfc_priority` を key にする inner list の 2 階層。

## 主要フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `name` | string | map 名。`PORT_QOS_MAP.pfc_to_pg_map` から参照される |
| `pfc_priority` | string pattern `[0-7]?` | 入力 PFC priority |
| `pg` | string pattern `[0-7]?` | 対応する ingress priority group |

## 制約

- `name` は 1..32 文字、英数字で始まり、英数字 / `-` / `_` を利用可能。
- `pfc_priority` と `pg` は 0..7 の 1 桁値、または空文字を許す pattern。
- `PORT_QOS_MAP.pfc_to_pg_map` から leafref 参照されるため、port に適用する前に map entry が存在する必要がある。

## 購読者

- `orchagent` の `QosOrch` (`sonic-swss/orchagent/qosorch.cpp`): CONFIG_DB の QoS map を直接 subscribe し、SAI QoS map (`SAI_QOS_MAP_TYPE_PFC_PRIORITY_TO_PRIORITY_GROUP`) として作成、port QoS binding に利用する（master には独立した `qosmgrd` プロセスは存在しない）。

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `PORT_QOS_MAP`、`BUFFER_PG`、`PFC_WD`
- 関連 CLI: `config qos`
- 関連 YANG: `sonic-pfc-priority-priority-group-map`、`sonic-port-qos-map`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-pfc-priority-priority-group-map`](../yang/sonic-pfc-priority-priority-group-map.md)
- CLI: [`config qos`](../cli/config-qos.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-pfc-priority-priority-group-map.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-pfc-priority-priority-group-map.yang>
[^2]: テーブル名定数: `schema.h`. <https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/schema.h>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->
