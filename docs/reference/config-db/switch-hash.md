---
title: SWITCH_HASH テーブル
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-hash.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
related:
  config_db:
    - SWITCH_HASH
  cli:
    - config switch-hash
  yang:
    - sonic-hash
---

# SWITCH_HASH テーブル

## 概要

ECMP / LAG ハッシュに使うフィールド集合とハッシュアルゴリズムをスイッチ全体で設定する Generic Hash 設定テーブル[^1]。
`orchagent` が CONFIG_DB から読んで SAI `SAI_SWITCH_ATTR_ECMP_DEFAULT_HASH_*` / `SAI_SWITCH_ATTR_LAG_DEFAULT_HASH_*` 系属性として SAI に push する。

## key 構造

```
SWITCH_HASH|GLOBAL
```

シングルトン (`GLOBAL` の 1 行のみ)。

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `ecmp_hash` | leaf-list of `hash-field` enum | ECMP パケットを分散させるためのハッシュフィールド集合 |
| `lag_hash`  | leaf-list of `hash-field` enum | LAG メンバ間分散用のハッシュフィールド集合 |
| `ecmp_hash_algorithm` | `hash-algorithm` enum | ECMP に使うハッシュアルゴリズム (CRC / XOR / Random / CRC_32LO 等、`sonic-types`) |
| `lag_hash_algorithm` | `hash-algorithm` enum | LAG に使うハッシュアルゴリズム |

`hash-field` enum (`sonic-hash.yang`):

`IN_PORT` / `DST_MAC` / `SRC_MAC` / `ETHERTYPE` / `VLAN_ID` / `IP_PROTOCOL` / `DST_IP` / `SRC_IP` / `L4_DST_PORT` / `L4_SRC_PORT` / `INNER_*` 同等 / `IPV6_FLOW_LABEL`

`ordered-by user` が付くため、ユーザー設定順が保たれる (実装上はベンダーによっては順序を無視するが、YANG 上の意味は保存される)。

## 購読者

- `orchagent`（`SwitchOrch` の Generic Hash 拡張）

## 関連 CONFIG_DB / YANG / CLI

- 関連 CLI: `config switch-hash global ecmp` / `config switch-hash global lag`
- 関連 YANG: `sonic-hash`
- 関連: `FG_NHG`（fine-grained ECMP）, `PORT.lag_hash` 等の per-port ハッシュは別経路

## 引用元

[^1]: YANG 定義: `sonic-hash.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-hash.yang>

## 関連ページ
- [CONFIG_DB index](index.md)
