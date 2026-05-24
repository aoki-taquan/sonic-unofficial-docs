---
title: sonic-mgmt_port YANG
description: "sonic-mgmt_port YANG — OOB マネジメントポート（eth0 等）の物理パラメータ（速度・MTU・admin status）を保持する YANG モジュール。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-mgmt_port.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [MGMT_PORT]
  cli: ["config interface"]
  yang: [sonic-mgmt_interface, sonic-mgmt_vrf]
---

# sonic-mgmt_port YANG

## 概要

- module: `sonic-mgmt_port`
- namespace: `http://github.com/sonic-net/sonic-mgmt_port`
- revision: `2021-04-07`
- import: `sonic-types`
- top container: `sonic-mgmt_port`

OOB マネジメントポート（`eth0` 等）の物理パラメータ（速度・MTU・admin status）を保持する [YANG](../../reference/glossary.md#term-yang) モジュール[^1]。

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-mgmt_port"]
  C1[("CONFIG_DB<br/>MGMT_PORT")]
  Y --> C1
  D1["mgmt-framework"]
  C1 --> D1
```

!!! note "凡例"
    YANG モジュールから CONFIG_DB テーブル経由で subscribe する daemon/orch までを `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文を参照。
<!-- /yang-mermaid -->

## 関連ページ

<!-- yang-xref -->

本 YANG モジュールに対応する CONFIG_DB / CLI / HLD / Topics への相互リンク。`inject_yang_xref.py` により自動生成されます。

### 対応 CONFIG_DB

- [`MGMT_PORT`](../config-db/mgmt-port.md)

### 関連 CLI

- [`config interface`](../cli/config-interface.md)

<!-- /yang-xref -->

## ツリー

```text
module: sonic-mgmt_port
  +--rw sonic-mgmt_port
     +--rw MGMT_PORT
        +--rw MGMT_PORT_LIST* [name]
           +--rw name           string (pattern eth0..eth3999)
           +--rw speed?         uint16
           +--rw autoneg?       string (on|off)
           +--rw alias?         string
           +--rw description?   string
           +--rw mtu?           uint16
           +--rw admin_status?  stypes:admin_status
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `name` | `sonic-mgmt_port/MGMT_PORT/MGMT_PORT_LIST/name` | `string` | yes |  | pattern `eth([1-3][0-9]{3}\|[1-9][0-9]{2}\|[1-9][0-9]\|[0-9])` (eth0〜eth3999) | マネジメントポート名 |
| `speed` | `sonic-mgmt_port/MGMT_PORT/MGMT_PORT_LIST/speed` | `uint16` |  |  | `10` / `100` / `1000` | リンク速度（Mbps） |
| `autoneg` | `sonic-mgmt_port/MGMT_PORT/MGMT_PORT_LIST/autoneg` | `string` |  |  | `on` / `off` | オートネゴシエーションの有効/無効 |
| `alias` | `sonic-mgmt_port/MGMT_PORT/MGMT_PORT_LIST/alias` | `string` |  |  |  | 別名 |
| `description` | `sonic-mgmt_port/MGMT_PORT/MGMT_PORT_LIST/description` | `string` |  |  |  | 説明文 |
| `mtu` | `sonic-mgmt_port/MGMT_PORT/MGMT_PORT_LIST/mtu` | `uint16` |  | `1500` | range 1500..9216 | MTU（バイト） |
| `admin_status` | `sonic-mgmt_port/MGMT_PORT/MGMT_PORT_LIST/admin_status` | `stypes:admin_status` |  | `up` | up / down | 管理ステータス |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `MGMT_PORT|<name>`
- CLI: `config interface`（管理ポート用 サブセット）

<!-- yang-sibling -->
### 関連 YANG モジュール

意味的に関連する SONiC YANG モジュール (slug prefix / curated group / frontmatter `related.yang` から自動抽出):

- [`sonic-mgmt_interface`](sonic-mgmt_interface.md)
- [`sonic-mgmt_vrf`](sonic-mgmt_vrf.md)
- [`sonic-breakout_cfg`](sonic-breakout_cfg.md)
- [`sonic-fabric-port`](sonic-fabric-port.md)
- [`sonic-interface`](sonic-interface.md)
<!-- /yang-sibling -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`MGMT_PORT`](../config-db/mgmt-port.md)
- CLI: [`config interface`](../cli/config-interface.md)

<!-- ref-triangle:end -->

<!-- ops-hint -->
## 運用ヒント

### 典型的なデプロイ位置

- Management port (eth0) 設定。`MGMT_PORT|eth0` を networking restart / interfacecfgd が処理。

### よくある落とし穴

- `autoneg` を `off` で speed 未設定だとリンクダウンする。ovsdb 等で外部管理する場合に頻発。

### 関連する config / show コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'MGMT_PORT|eth0'
show management_interface
```
<!-- /ops-hint -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-mgmt_port.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

<!-- glossary-links-injected: 20dbc11976b6 -->
