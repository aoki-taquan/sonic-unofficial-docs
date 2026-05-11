---
title: sonic-system-defaults YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-system-defaults.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [SYSTEM_DEFAULTS]
  cli: []
  yang: [sonic-types]
---

# sonic-system-defaults YANG

## 概要

- module: `sonic-system-defaults`
- namespace: `http://github.com/Azure/system-defaults`
- import: `sonic-types`
- top container: `sonic-system-defaults`

System-wide default feature settings YANG module for SONiC OS[^1]。プラットフォーム/イメージレベルでオプション機能のデフォルト admin 状態を表す `SYSTEM_DEFAULTS` テーブルを保持する。

## ツリー

```
module: sonic-system-defaults
  +--rw sonic-system-defaults
     +--rw SYSTEM_DEFAULTS
        +--rw SYSTEM_DEFAULTS_LIST* [name]
           +--rw name      string
           +--rw status?   stypes:admin_mode
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `name` | `sonic-system-defaults/SYSTEM_DEFAULTS/SYSTEM_DEFAULTS_LIST/name` | `string` | yes |  |  | Name of the system feature |
| `status` | `sonic-system-defaults/SYSTEM_DEFAULTS/SYSTEM_DEFAULTS_LIST/status` | `stypes:admin_mode` |  |  | enabled, disabled | Default administrative state of the feature |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `SYSTEM_DEFAULTS`
- CLI: なし（init_cfg / image 由来の不変設定として参照）

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-system-defaults.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
