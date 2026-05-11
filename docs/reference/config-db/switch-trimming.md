---
title: SWITCH_TRIMMING テーブル
description: "SWITCH_TRIMMING テーブル — 輻輳テレメトリ向けの パケットトリミング (packet trimming) を全スイッチに対して設定するテーブル。 ドロップ予定のパケットを「短縮コピー」して別の DSCP / TC / queue で送り出すことで、輻輳発生を末端まで伝える。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-trimming.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - SWITCH_TRIMMING
  yang:
    - sonic-trimming
---

# SWITCH_TRIMMING テーブル

## 概要

輻輳テレメトリ向けの **パケットトリミング (packet trimming)** を全スイッチに対して設定するテーブル[^1]。
ドロップ予定のパケットを「短縮コピー」して別の DSCP / TC / queue で送り出すことで、輻輳発生を末端まで伝える。

## key 構造

```
SWITCH_TRIMMING|GLOBAL
```

シングルトン。

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `size` | uint32 | トリミング後のパケットサイズ [bytes] |
| `dscp_value` | uint8 (0..63) または `from-tc` | トリミング後パケットに付ける DSCP。`from-tc` で `tc_value` から DSCP_TO_TC マッピング逆引きで導出 |
| `tc_value`  | uint8 | トリミング後パケットに付ける Traffic Class |
| `queue_index` | uint8 または `dynamic` | トリミング後パケットの送信キュー。`dynamic` で `dscp_value` から導出 |

`dscp_value=from-tc` と `queue_index=dynamic` の組み合わせは矛盾するので、どちらか一方だけを使う想定。

## 購読者

- `orchagent` (SwitchOrch trimming 拡張)。SAI の switch-level trimming 属性に push

## 関連 YANG

- `sonic-trimming`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-trimming`](../yang/sonic-trimming.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-trimming.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-trimming.yang>

## 関連ページ
- [CONFIG_DB index](index.md)
