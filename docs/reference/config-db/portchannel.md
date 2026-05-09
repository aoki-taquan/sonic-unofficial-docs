---
title: PORTCHANNEL テーブル
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-portchannel.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - PORTCHANNEL
    - PORTCHANNEL_MEMBER
    - PORTCHANNEL_INTERFACE
  cli:
    - config portchannel
  yang:
    - sonic-portchannel
---

# PORTCHANNEL テーブル

## 概要

LACP ベースの Link Aggregation Group (LAG) を定義する。`teamd` がこのテーブルから設定を読み、Linux teamd 経由で物理ポートを bond する[^1]。`orchagent` の `PortsOrch` / `LagOrch` が SAI LAG オブジェクトを構成する。

## key 構造

```
PORTCHANNEL|<name>
```

`<name>` は `PortChannel<0-9999>` 形式。

## フィールド一覧

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `name` (key) | string `PortChannel\d{1,4}` | ✅ | - | LAG 名 |
| `min_links` | uint16 (1..1024) | - | - | Operational up に必要な最小メンバ数 |
| `mode` | `switchport_mode` | - | `routed` | スイッチポートモード |
| `description` | string (1..255) | - | - | 説明 |
| `mtu` | uint16 (1..9216) | - | - | MTU |
| `admin_status` | `admin_status` | ✅ | - | 管理状態 |
| `lacp_key` | `auto` \| uint16 (1..65535) | - | - | LACP 集約キー。`auto` で名前末尾から導出 |
| `tpid` | `tpid_type` | - | - | TPID（HW 対応時） |
| `fallback` | boolean | - | - | LACP fallback |
| `fast_rate` | boolean | - | - | LACP fast rate |

## 購読者

- `teammgrd`: PORTCHANNEL を読み、Linux teamd を spawn
- `orchagent` `LagOrch`: SAI LAG を生成、`min_links` でアップ判定
- `intfmgrd`: `mtu`、`admin_status` 変化を Linux カーネルに反映

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `PORTCHANNEL_MEMBER`、`PORTCHANNEL_INTERFACE`、`PORT`
- 関連 CLI: `config portchannel`、[`config portchannel`](../cli/config-portchannel.md)
- 関連 YANG: `sonic-portchannel`

## 引用元

[^1]: YANG 定義: `sonic-portchannel.yang` (sha `9ea932ec`). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-portchannel.yang>
