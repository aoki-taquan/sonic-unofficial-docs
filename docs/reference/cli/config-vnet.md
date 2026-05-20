---
title: config vnet サブコマンド
description: config vnet サブコマンド — config vnet は overlay VNET と VNET route を CONFIG_DB
  に作成・削除する CLI グループ。multi-ASIC では --namespace で対象 namespace を選択できる。
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
  yang:
  - sonic-vnet
---

# config vnet サブコマンド

## 概要

`config vnet` は overlay [VNET](../../reference/glossary.md#term-vnet) と [VNET](../../reference/glossary.md#term-vnet) route を [CONFIG_DB](../../reference/glossary.md#term-config_db) に作成・削除する CLI グループ。multi-[ASIC](../../reference/glossary.md#term-asic) では `--namespace` で対象 namespace を選択できる[^1]。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `config vnet add <vnet_name> <vni> <vxlan_tunnel> [options]` | `VNET|<vnet_name>` を追加/更新 |
| `config vnet del <vnet_name>` | [VNET](../../reference/glossary.md#term-vnet) と関連 interface/route を削除 |
| `config vnet add-route <vnet_name> <prefix> <endpoint> [options]` | tunnel route を追加/更新 |
| `config vnet del-route <vnet_name> [<prefix>]` | route 1件または VNET 配下全 route を削除 |

## 各コマンドの詳細

### `config vnet add`

**用法**:

```bash
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

<!-- cli-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CLI["config vnet"]
  SC["sonic-cfggen<br/>(config CLI のみ)"]
  CLI --> SC
  CDB0[("CONFIG_DB<br/>VNET")]
  SC --> CDB0
  DM0["vrfmgrd"]
  CDB0 --> DM0
  CDB1[("CONFIG_DB<br/>VNET_ROUTE_TUNNEL")]
  SC --> CDB1
  DM1["VNetCfgRouteOrch"]
  CDB1 --> DM1
  CDB2[("CONFIG_DB<br/>VNET_ROUTE")]
  SC --> CDB2
  DM2["VNetCfgRouteOrch"]
  CDB2 --> DM2
```

!!! note "凡例"
    config 系 (CLI → CONFIG_DB → daemon) のミニ図。テーブル → daemon 対応は `docs/reference/config-db-orch-map.md` から機械生成。
<!-- /cli-mermaid -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`VNET`](../config-db/vnet.md) / [`VNET_ROUTE_TUNNEL`](../config-db/vnet.md) / [`VNET_ROUTE`](../config-db/vnet.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `config vnet` グループ定義。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L10057>

[^2]: VNET 名検証は `vnet_name_is_valid()`。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L467>

<!-- ops-hint -->
## 運用ヒント

### 典型的な利用シーン

- [DASH](../../reference/glossary.md#term-dash) / T1 [SmartSwitch](../../reference/glossary.md#term-smartswitch) 向けに VNET ([VRF](../../reference/glossary.md#term-vrf) + VxLAN) を作成する。
- VNET route / VNET neighbor の追加メンテ。

### よくある落とし穴

- VNET に紐付ける VxLAN tunnel が未作成だと [CONFIG_DB](../../reference/glossary.md#term-config_db) に入っても `vnetorch` が起動できない。
- guid / scope を変えると既存 route が無効化される。

### 関連する show / debug

```bash
show vnet brief
show vnet routes all
show vnet endpoint
```
<!-- /ops-hint -->

<!-- cli-sibling -->
### 関連 CLI コマンド

- [`show mclag`](show-mclag.md) — show mclag (mclagdctl) コマンド
- [`config mclag`](config-mclag.md) — config mclag サブコマンド
- [`config vxlan`](config-vxlan.md) — config vxlan サブコマンド

<!-- /cli-sibling -->

<!-- glossary-links-injected: c006405759d8 -->
