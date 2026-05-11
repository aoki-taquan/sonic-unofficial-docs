---
title: KDUMP テーブル
description: "KDUMP テーブル — Linux kernel crash dump (kdump) の設定。KDUMP|config の単一 container。hostcfgd がこの container を購読し、/etc/default/kdump-tools の生成・kdump-config の起動を実施する。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-kdump.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - KDUMP
  cli:
    - config kdump
  yang:
    - sonic-kdump
---

# KDUMP テーブル

## 概要

Linux kernel crash dump (kdump) の設定。`KDUMP|config` の単一 container[^1]。`hostcfgd` がこの container を購読し、`/etc/default/kdump-tools` の生成・`kdump-config` の起動を実施する。

## key 構造

```
KDUMP|config
```

(list ではなく単一 container)

## 主要フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `enabled` | boolean | kdump メカニズムの有効化 |
| `memory` | string | crash kernel に確保するメモリ。`512M-2G:64M,2G-:128M` 形式または絶対値 (`512M`) |
| `num_dumps` | uint8 (1..9) | 保持する core file 数 |
| `remote` | boolean | リモート (SSH) ダンプ転送の有効化 |
| `ssh_string` | string | リモート ssh 接続文字列 (`user@host` パターン) |
| `ssh_path` | string | リモート ssh 秘密鍵パス |

## 購読者

- `hostcfgd` (`docker-config-engine`): CONFIG_DB → `/etc/default/kdump-tools`

## 関連 CONFIG_DB / YANG / CLI

- 関連 CLI: `config kdump enable/disable/memory/num_dumps/remote/add ssh_string`、`show kdump`
- 関連 YANG: `sonic-kdump`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-kdump`](../yang/sonic-kdump.md)
- CLI: [`config kdump`](../cli/config-kdump.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-kdump.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-kdump.yang>

## 関連ページ
- [HLD: kdump](../../system/kdump.md)
- [CLI: config kdump](../cli/config-kdump.md)
