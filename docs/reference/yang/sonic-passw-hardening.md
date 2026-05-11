---
title: sonic-passwh YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-passwh.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [PASSW_HARDENING]
  cli: ["config passwd-hardening"]
  yang: []
---

# sonic-passwh YANG

## 概要

- module: `sonic-passwh`
- namespace: `http://github.com/sonic-net/sonic-passwh`
- revision: `2022-05-03`
- import: なし
- top container: `sonic-passwh`

Password hardening policy YANG module for SONiC OS. ローカルユーザーパスワードの複雑さ・有効期限・履歴ポリシーを定義する。[^1]

## ツリー

```
module: sonic-passwh
  +--rw sonic-passwh
     +--rw PASSW_HARDENING
        +--rw POLICIES
           +--rw state?                     feature_state
           +--rw expiration?                int16
           +--rw expiration_warning?        int8
           +--rw history_cnt?               uint8
           +--rw len_min?                   uint8
           +--rw reject_user_passw_match?   boolean
           +--rw lower_class?               boolean
           +--rw upper_class?               boolean
           +--rw digits_class?              boolean
           +--rw special_class?             boolean
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `state` | `sonic-passwh/PASSW_HARDENING/POLICIES/state` | `feature_state` |  | `disabled` | `enabled`, `disabled` | Enable or disable password hardening enforcement. |
| `expiration` | `sonic-passwh/PASSW_HARDENING/POLICIES/expiration` | `int16` |  |  | range -1..365 | Password expiration period in days; -1 disables expiration. |
| `expiration_warning` | `sonic-passwh/PASSW_HARDENING/POLICIES/expiration_warning` | `int8` |  |  | range -1..30 | Number of days before expiration to warn the user; -1 disables the warning. |
| `history_cnt` | `sonic-passwh/PASSW_HARDENING/POLICIES/history_cnt` | `uint8` |  |  | range 1..100 | Number of previous passwords remembered to prevent reuse. |
| `len_min` | `sonic-passwh/PASSW_HARDENING/POLICIES/len_min` | `uint8` |  |  | range 1..32 | Minimum required password length in characters. |
| `reject_user_passw_match` | `sonic-passwh/PASSW_HARDENING/POLICIES/reject_user_passw_match` | `boolean` |  |  |  | When true, reject passwords that match the username. |
| `lower_class` | `sonic-passwh/PASSW_HARDENING/POLICIES/lower_class` | `boolean` |  |  |  | When true, require at least one lowercase letter (a-z). |
| `upper_class` | `sonic-passwh/PASSW_HARDENING/POLICIES/upper_class` | `boolean` |  |  |  | When true, require at least one uppercase letter (A-Z). |
| `digits_class` | `sonic-passwh/PASSW_HARDENING/POLICIES/digits_class` | `boolean` |  |  |  | When true, require at least one digit (0-9). |
| `special_class` | `sonic-passwh/PASSW_HARDENING/POLICIES/special_class` | `boolean` |  |  |  | When true, require at least one special character. |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `PASSW_HARDENING|POLICIES`
- CLI: `config passwd-hardening`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: `PASSW_HARDENING`
- CLI: `config passwd-hardening`

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-passwh.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
