---
title: MGMT_PORT テーブル
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-mgmt_port.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - MGMT_PORT
    - MGMT_INTERFACE
  cli:
    - config interface
  yang:
    - sonic-mgmt_port
---

# MGMT_PORT テーブル

## 概要

帯域外管理 (out-of-band) ポート (`eth0`, `eth1`, ...) の物理プロパティを保持する[^1]。`hostcfgd` が読み出して Linux 側の `/etc/network/interfaces` を更新する。

## key 構造

```
MGMT_PORT|<name>
```

`<name>` は正規表現 `eth([1-3][0-9]{3}|[1-9][0-9]{2}|[1-9][0-9]|[0-9])` に合致する管理 IF 名（例: `eth0`）。

## フィールド一覧

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `name` (key) | string `eth\d+` | ✅ | - | 管理 IF 名 |
| `speed` | uint16 (`10`/`100`/`1000`) | - | - | 速度 [Mbps] |
| `autoneg` | string `on`/`off` | - | - | 自動ネゴシエーション |
| `alias` | string | - | - | 別名 |
| `description` | string | - | - | 説明 |
| `mtu` | uint16 (1500..9216) | - | `1500` | MTU |
| `admin_status` | `admin_status` | - | `up` | 管理状態 |

## 購読者

- `hostcfgd`: `/etc/network/interfaces` への展開、`ifconfig` / `ethtool` 系操作
- `sonic-host-services`

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `MGMT_INTERFACE`（IP 設定）、`MGMT_VRF_CONFIG`（mgmt VRF）
- 関連 CLI: `config interface speed/mtu eth0 ...`
- 関連 YANG: `sonic-mgmt_port`

## 引用元

[^1]: YANG 定義: `sonic-mgmt_port.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-mgmt_port.yang>
