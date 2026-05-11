---
title: SYSTEM_DEFAULTS テーブル
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-system-defaults.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - SYSTEM_DEFAULTS
    - FEATURE
  yang:
    - sonic-system-defaults
---

# SYSTEM_DEFAULTS テーブル

## 概要

システム共通の機能既定値 (デフォルトの enable / disable 状態) を定義する。`init_cfg.json` 由来の値を保持し、`db_migrator` が初期化時にエントリの有無を確認する[^1]。具体的なキーは `tunnel_qos_remap`、`synchronous_mode`、`dhcp_server` など (時期により異なる) で、各機能の起動前提として参照される。

## key 構造

```
SYSTEM_DEFAULTS|<name>
```

`<name>` は string (1..32)。

## 主要フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `status` | enum `enabled`/`disabled` (`admin_mode`) | 機能既定状態 |

## 設計上の位置づけ

- 単一の "ツマミ" として ON/OFF を保持し、より詳細な動作は対応する機能の設定テーブル (`FEATURE` 含む) で行う
- `db_migrator.py` が古い image からアップグレードした際にデフォルト値を補完する

## 購読者

- 各 daemon が起動時に該当 `<name>` を読み、自身の動作を切替

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `FEATURE`、`DEVICE_METADATA`
- 関連 YANG: `sonic-system-defaults`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-system-defaults`](../yang/sonic-system-defaults.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-system-defaults.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-system-defaults.yang>
