---
title: config vnet サブコマンド
area: reference
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/sonic-utilities
    path: config/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - VNET
    - VNET_ROUTE_TUNNEL
    - VNET_ROUTE
  cli:
    - config vnet
    - show vnet
  yang: []
---

# config vnet サブコマンド

## 概要

`config vnet` は overlay VNET と VNET route を CONFIG_DB に作成・削除する CLI グループ。multi-ASIC では `--namespace` で対象 namespace を選択できる[^1]。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `config vnet add <vnet_name> <vni> <vxlan_tunnel> [options]` | `VNET|<vnet_name>` を追加/更新 |
| `config vnet del <vnet_name>` | VNET と関連 interface/route を削除 |
| `config vnet add-route <vnet_name> <prefix> <endpoint> [options]` | tunnel route を追加/更新 |
| `config vnet del-route <vnet_name> [<prefix>]` | route 1件または VNET 配下全 route を削除 |

## 各コマンドの詳細

### `config vnet add`

**用法**:

```
config vnet add <vnet_name> <vni> <vxlan_tunnel>
    [--peer_list <list>]
    [--guid <guid>]
    [--scope default|...]
    [--advertise_prefix true|false]
    [--overlay_dmac <mac>]
    [--src_mac <mac>]
```

`<vnet_name>` は `Vnet` で始まり、最大 15 文字。`VNET|<vnet_name>` に `vni`, `vxlan_tunnel` と指定オプションを書き込む。`peer_list` の各 peer も同じ VNET 名検証を受ける[^2]。

### `config vnet del`

`VNET|<vnet_name>` が存在することを確認し、関連 interface の `vnet_name` と `VNET_ROUTE_TUNNEL` / `VNET_ROUTE` を削除してから VNET entry を削除する。

### `config vnet add-route`

`VNET_ROUTE_TUNNEL|<vnet_name>|<prefix>` に endpoint, vni, mac address, monitoring/profile 系の属性を書き込む。対象 VNET が無い場合はエラー。

### `config vnet del-route`

`<prefix>` 指定時は該当 route だけを削除する。省略時は対象 VNET に紐づく route をまとめて削除する。

## 引用元

[^1]: `config vnet` グループ定義。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L10057>

[^2]: VNET 名検証は `vnet_name_is_valid()`。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L467>
