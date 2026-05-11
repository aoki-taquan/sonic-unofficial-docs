---
title: sonic-buffer-pool YANG
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-buffer-pool.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [BUFFER_POOL]
  cli: []
  yang: []
---

# sonic-buffer-pool YANG

## 概要

- module: `sonic-buffer-pool`
- namespace: `http://github.com/sonic-net/sonic-buffer-pool`
- revision: `2021-07-01`
- import: `sonic-device_metadata`
- top container: `sonic-buffer-pool`

Shared and dedicated memory pool configuration for packet buffering.[^1]

## ツリー

```
module: sonic-buffer-pool
  +--rw sonic-buffer-pool
     +--rw BUFFER_POOL
        +--rw BUFFER_POOL_LIST* [name]
           +--rw name          string
           +--rw type          enumeration
           +--rw mode          enumeration
           +--rw size?         uint64
           +--rw xoff?         uint64
           +--rw percentage?   uint8
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `name` | `sonic-buffer-pool/BUFFER_POOL/BUFFER_POOL_LIST/name` | `string` | yes |  |  | Buffer Pool name |
| `type` | `sonic-buffer-pool/BUFFER_POOL/BUFFER_POOL_LIST/type` | `enumeration` | yes |  | ingress, egress, both | Buffer Pool Type |
| `mode` | `sonic-buffer-pool/BUFFER_POOL/BUFFER_POOL_LIST/mode` | `enumeration` | yes |  | static, dynamic | Buffer Pool Mode |
| `size` | `sonic-buffer-pool/BUFFER_POOL/BUFFER_POOL_LIST/size` | `uint64` |  |  |  | Buffer Pool Size (in Bytes) |
| `xoff` | `sonic-buffer-pool/BUFFER_POOL/BUFFER_POOL_LIST/xoff` | `uint64` |  | 0 |  | Buffer Pool Xoff Threshold (in Bytes) |
| `percentage` | `sonic-buffer-pool/BUFFER_POOL/BUFFER_POOL_LIST/percentage` | `uint8` |  |  |  | Buffer Pool percentage. The buffer pool size will be available_buffer * percentage / 100 if percentage is provided. It is valid in dynamic buffer model only. |

## leafref / 依存

- なし（このモジュール内で直接 leafref を持つ leaf はない）

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `BUFFER_POOL`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`BUFFER_POOL`](../config-db/buffer-pool.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-buffer-pool.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

