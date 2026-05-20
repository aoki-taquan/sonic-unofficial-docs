---
title: sonic-bgp-sentinel YANG
description: sonic-bgp-sentinel YANG — SONiC BGP Sentinel 機能の YANG モデル。ToR 配下の特定 IP 範囲に対する Sentinel BGP セッション設定。
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
- repo: sonic-net/sonic-buildimage
  path: src/sonic-yang-models/yang-models/sonic-bgp-sentinel.yang
  ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
  - BGP_SENTINELS
  cli: []
  yang:
  - sonic-bgp-common
  - sonic-bgp-neighbor
  - sonic-bgp-peergroup
---

# sonic-bgp-sentinel YANG

## 概要

- module: `sonic-bgp-sentinel`
- namespace: `http://github.com/Azure/sonic-bgp-sentinel`
- revision: `2023-06-06`
- import: `ietf-inet-types`, `sonic-types`
- top container: `sonic-bgp-sentinel`

[SONiC](../../reference/glossary.md#term-sonic) [BGP](../../reference/glossary.md#term-bgp) Sentinel 機能の [YANG](../../reference/glossary.md#term-yang) モデル。ToR 配下の特定 IP 範囲に対する Sentinel [BGP](../../reference/glossary.md#term-bgp) セッション設定[^1]。

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-bgp-sentinel"]
  C1[("CONFIG_DB<br/>BGP_SENTINELS")]
  Y --> C1
  D1["bgpcfgd"]
  C1 --> D1
```

!!! note "凡例"
    YANG モジュールから CONFIG_DB テーブル経由で subscribe する daemon/orch までを `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文を参照。
<!-- /yang-mermaid -->

## ツリー

```text
module: sonic-bgp-sentinel
  +--rw sonic-bgp-sentinel
     +--rw BGP_SENTINELS
        +--rw BGP_SENTINELS_LIST* [sentinel_name]
           +--rw sentinel_name    string
           +--rw name?            string
           +--rw src_address?     inet:ip-address
           +--rw ip_range*        stypes:sonic-ip-prefix
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `sentinel_name` | `sonic-bgp-sentinel/BGP_SENTINELS/BGP_SENTINELS_LIST/sentinel_name` | `string` | yes |  |  | [BGP](../../reference/glossary.md#term-bgp) Sentinel 名（リストキー） |
| `name` | `sonic-bgp-sentinel/BGP_SENTINELS/BGP_SENTINELS_LIST/name` | `string` |  |  | must `current() = sentinel_name` | BGP Sentinel 名（`sentinel_name` と一致必須） |
| `src_address` | `sonic-bgp-sentinel/BGP_SENTINELS/BGP_SENTINELS_LIST/src_address` | `inet:ip-address` |  |  |  | 接続に使うソースアドレス |
| `ip_range` | `sonic-bgp-sentinel/BGP_SENTINELS/BGP_SENTINELS_LIST/ip_range` | `leaf-list stypes:sonic-ip-prefix` |  |  | ordered-by user | 受け入れるアドレスレンジ |

## leafref / 依存

- なし（must 制約 `name = sentinel_name` のみ）

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `BGP_SENTINELS|<sentinel_name>`
- CLI: なし（[CONFIG_DB](../../reference/glossary.md#term-config_db) 直接設定）

<!-- yang-sibling -->
### 関連 YANG モジュール

意味的に関連する SONiC YANG モジュール (slug prefix / curated group / frontmatter `related.yang` から自動抽出):

- [`sonic-bgp-neighbor`](sonic-bgp-neighbor.md)
- [`sonic-bgp-peergroup`](sonic-bgp-peergroup.md)
- [`sonic-bgp-aggregate-address`](sonic-bgp-aggregate-address.md)
- [`sonic-bgp-bbr`](sonic-bgp-bbr.md)
- [`sonic-bgp-device-global`](sonic-bgp-device-global.md)
<!-- /yang-sibling -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `BGP_SENTINELS`

<!-- ref-triangle:end -->

<!-- ops-hint -->
## 運用ヒント

### 典型的なデプロイ位置

- BGP Sentinel (route monitor) 用 neighbor 定義。BMP 系と独立した経路で `BGP_SENTINELS` テーブルに書かれる。

### よくある落とし穴

- 通常の BGP neighbor と key 空間が異なるため `show bgp neighbors` には現れない。[bgpcfgd](../../reference/glossary.md#term-bgpcfgd) のテンプレ確認が必要。

### 関連する config / show コマンド

```bash
sonic-db-cli CONFIG_DB keys 'BGP_SENTINELS|*'
show runningconfiguration bgp
```
<!-- /ops-hint -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-bgp-sentinel.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

<!-- glossary-links-injected: 8ba32e5aa69d -->
