---
title: LOOPBACK_INTERFACE テーブル
description: "LOOPBACK_INTERFACE テーブル — ルータ ID やサービス IP として使う仮想ループバック IF を定義する。Loopback0 は通常 BGP の router-id / source として使われる。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-loopback-interface.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - LOOPBACK_INTERFACE
    - VRF
  cli:
    - config loopback
  yang:
    - sonic-loopback-interface
---

# LOOPBACK_INTERFACE テーブル

## 概要

ルータ ID やサービス IP として使う仮想ループバック IF を定義する[^1]。`Loopback0` は通常 BGP の router-id / source として使われる。`intfmgrd` が Linux 上の dummy IF を生成し、`orchagent` `IntfsOrch` が SAI ルータ IF を作る。

## key 構造

```
LOOPBACK_INTERFACE|<name>                       # 属性ロウ
LOOPBACK_INTERFACE|<name>|<ip-prefix>           # IP プレフィクス
```

`<name>` は `interface_name` typedef で `Loopback<N>` 形式。

## 属性ロウのフィールド

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `name` (key) | `interface_name` | ✅ | - | ループバック名（例: `Loopback0`） |
| `vrf_name` | leafref `VRF.name` | - | - | バインドする VRF |
| `nat_zone` | uint8 (0..3) | - | `0` | NAT zone |
| `admin_status` | `admin_status` | - | `up` | 管理状態 |

## IP プレフィクスロウ

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `name` (key) | leafref 自テーブル `LOOPBACK_INTERFACE_LIST.name` | ✅ | ループバック名 |
| `ip-prefix` (key) | union (v4/v6 prefix) | ✅ | IP/プレフィクス |
| `scope` | enum `global`/`local` | - | アドレススコープ |
| `family` | `ip-family` | - | family。`ip-prefix` と整合する `must` |

## 購読者

- `intfmgrd`: Linux dummy IF / IP / VRF binding を生成
- `orchagent` `IntfsOrch`: SAI ルータ IF
- `bgpcfgd`: `Loopback0` IPv4 を BGP `bgp router-id` の既定値として参照（`DEVICE_METADATA.bgp_router_id` 未設定時）

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `VRF`、`DEVICE_METADATA` (`bgp_adv_lo_prefix_as_128`)
- 関連 CLI: `config loopback add/del`、`config interface ip add Loopback0 ...`
- 関連 YANG: `sonic-loopback-interface`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-loopback-interface`](../yang/sonic-loopback-interface.md)
- CLI: `config loopback`

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-loopback-interface.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-loopback-interface.yang>
