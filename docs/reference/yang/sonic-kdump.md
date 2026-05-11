---
title: sonic-kdump YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-kdump.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [KDUMP]
  cli: ["config kdump"]
  yang: []
---

# sonic-kdump YANG

## 概要

- module: `sonic-kdump`
- namespace: `http://github.com/sonic-net/sonic-kdump`
- revision: `2022-05-09`
- import: なし
- top container: `sonic-kdump`

Linux Kernel crash dumping (Kdump) mechanism configuration. Kdump はカーネルクラッシュ時のメモリダンプを取得する。[^1]

## ツリー

```
module: sonic-kdump
  +--rw sonic-kdump
     +--rw KDUMP
        +--rw config
           +--rw enabled?       boolean
           +--rw memory?        string
           +--rw num_dumps?     uint8
           +--rw remote?        boolean
           +--rw ssh_string?    string
           +--rw ssh_path?      string
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `enabled` | `sonic-kdump/KDUMP/config/enabled` | `boolean` |  |  |  | Enable or Disable the Kdump mechanism. |
| `memory` | `sonic-kdump/KDUMP/config/memory` | `string` |  |  | pattern `(((([0-9]+[MG]?)?(-([0-9]+[MG])?):)?[0-9]+[MG],?)+)` | Memory reserved for loading the crash handler kernel. 可変メモリ予約構文 `<range1>:<size1>,<range2>:<size2>`（例: `512M-2G:64M,2G-:128M`）または絶対値 `512M` `1G`。 |
| `num_dumps` | `sonic-kdump/KDUMP/config/num_dumps` | `uint8` |  |  | range 1..9 | Maximum number of Kernel Core files Stored. |
| `remote` | `sonic-kdump/KDUMP/config/remote` | `boolean` |  |  |  | Enable or Disable the Kdump remote ssh mechanism. |
| `ssh_string` | `sonic-kdump/KDUMP/config/ssh_string` | `string` |  |  | pattern `([a-zA-Z0-9._%+-]+@(host\|IPv4))` | Remote ssh connection string. |
| `ssh_path` | `sonic-kdump/KDUMP/config/ssh_path` | `string` |  |  | pattern `(/[a-zA-Z0-9._-]+)+` | Remote ssh private key path. |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `KDUMP|config`
- CLI: `config kdump`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`KDUMP`](../config-db/kdump.md)
- CLI: [`config kdump`](../cli/config-kdump.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-kdump.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
