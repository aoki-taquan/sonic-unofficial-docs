---
title: VOQ_INBAND_INTERFACE テーブル
description: "VOQ_INBAND_INTERFACE テーブル — VOQ_INBAND_INTERFACE テーブルは VOQ chassis におけるラインカード間のインバンド通信用論理インターフェース (Ethernet-IB) を CONFIG_DB に定義する。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-voq-inband-interface.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - VOQ_INBAND_INTERFACE
    - SYSTEM_PORT
  cli:
    - config interface
  yang:
    - sonic-voq-inband-interface
---

# VOQ_INBAND_INTERFACE テーブル

## 概要

`VOQ_INBAND_INTERFACE` テーブルは VOQ chassis におけるラインカード間のインバンド通信用論理インターフェース (`Ethernet-IB<n>`) を CONFIG_DB に定義する[^1]。BGP internal-neighbor などのコントロールプレーン通信に使われる。テーブルは 2 段構造:

- `VOQ_INBAND_INTERFACE_LIST` (key: name)
- `VOQ_INBAND_INTERFACE_IPPREFIX_LIST` (key: name, ip-prefix)

## key 構造

```
VOQ_INBAND_INTERFACE|<name>
VOQ_INBAND_INTERFACE|<name>|<ip-prefix>
```

## VOQ_INBAND_INTERFACE_LIST フィールド

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `name` (key) | string パターン `Ethernet-IB[0-9]+` | — | インバンド IF 名 |
| `inband_type` | string パターン `port\|Port` | `port` | インバンドタイプ |

## VOQ_INBAND_INTERFACE_IPPREFIX_LIST フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `name` (key) | leafref → `VOQ_INBAND_INTERFACE_LIST.name` | 親インターフェース |
| `ip-prefix` (key) | `sonic-ip-prefix` | アサイン IP プレフィックス |

## 制約

- `name` は `Ethernet-IB<数値>` パターン
- `inband_type` は `port` または `Port`

## 購読者

- `intfmgrd` / `intfsyncd` (sonic-swss)
- `bgpcfgd` / `bgpd` — BGP internal neighbor のソース interface として使う場合

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `SYSTEM_PORT`、`BGP_INTERNAL_NEIGHBOR`、`BGP_VOQ_CHASSIS_NEIGHBOR`、`CHASSIS_MODULE`
- 関連 YANG: `sonic-voq-inband-interface`、`sonic-bgp-internal-neighbor`、`sonic-bgp-voq-chassis-neighbor`
- 関連 CLI: `config interface`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: `sonic-voq-inband-interface`
- CLI: [`config interface`](../cli/config-interface.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-voq-inband-interface.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-voq-inband-interface.yang>

## 関連ページ
- [CONFIG_DB: INTERFACE](interface.md)
