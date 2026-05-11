---
title: BGP_DEVICE_GLOBAL テーブル
description: "BGP_DEVICE_GLOBAL テーブル — スイッチ全体（VRF 横断）の BGP 動作スイッチを保持する。BGP_GLOBALS が VRF 単位なのに対し、BGP_DEVICE_GLOBAL は装置全体スコープ。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-device-global.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - BGP_DEVICE_GLOBAL
    - BGP_GLOBALS
  cli:
    - config bgp
  yang:
    - sonic-bgp-device-global
---

# BGP_DEVICE_GLOBAL テーブル

## 概要

スイッチ全体（VRF 横断）の BGP 動作スイッチを保持する。`BGP_GLOBALS` が VRF 単位なのに対し、`BGP_DEVICE_GLOBAL` は装置全体スコープ。TSA (Traffic-Shift-Away)、W-ECMP (BGP link-bandwidth ベース重み付き ECMP)、IDF (Inter-DC Fabric) 隔離状態、confederation の代表設定を持つ[^1]。

## key 構造

```
BGP_DEVICE_GLOBAL|STATE
BGP_DEVICE_GLOBAL|CONFED
```

二つの固定キーを持つ container 型。

## STATE のフィールド

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `tsa_enabled` | boolean | `false` | true で外部隣接へ経路広告を停止 (TSA) |
| `wcmp_enabled` | boolean | `false` | BGP link-bandwidth W-ECMP 有効化 |
| `idf_isolation_state` | enum `isolated_no_export` / `isolated_withdraw_all` / `unisolated` | `unisolated` | IDF 隔離状態 |

## CONFED のフィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `asn` | uint32 (1..2^32-1) | confederation AS 番号 |
| `peers` | string | confederation 内の sub-AS をセミコロン区切りで列挙 |

## 購読者

- `bgpcfgd`: STATE / CONFED を読み出し vtysh コマンドに変換
- `frr-mgmt-framework` (`frr_mgmt_framework_config = true` 時)
- TSA / W-ECMP は `bgpcfgd` の `TsaHandler` / `WcmpHandler` が直接担当

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `BGP_GLOBALS`、`DEVICE_METADATA`
- 関連 CLI: [`config bgp device-global tsa`](../cli/config-bgp.md)、`config bgp device-global w-ecmp`
- 関連 YANG: `sonic-bgp-device-global`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-bgp-device-global`](../yang/sonic-bgp-device-global.md)
- CLI: [`config bgp`](../cli/config-bgp.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-bgp-device-global.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-bgp-device-global.yang>
