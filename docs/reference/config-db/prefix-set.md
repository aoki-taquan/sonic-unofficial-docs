---
title: PREFIX_SET テーブル
description: "PREFIX_SET テーブル — sonic-routing-policy-sets モジュールが定義する 汎用 prefix set の宣言テーブル。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-routing-policy-sets.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - PREFIX_SET
    - PREFIX
    - ROUTE_MAP
  cli: []
  yang:
    - sonic-routing-policy-sets
---

# PREFIX_SET テーブル

## 概要

`sonic-routing-policy-sets` モジュールが定義する **汎用 prefix set** の宣言テーブル[^1]。実際のメンバ prefix は `PREFIX` (`PREFIX_LIST` / `PREFIX_NOSEQ_LIST`) 側に格納し、`PREFIX_SET_LIST.name` を leafref で参照する。`frr-mgmt-framework` 経路のルーティングポリシで route-map `match ip address prefix-list` に展開される。

## key 構造

```
PREFIX_SET|<name>
```

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `name` | string | prefix set 名（key） |
| `mode` | enum `IPv4` / `IPv6` | アドレスファミリ。デフォルト `IPv4` |

## メンバ prefix（派生テーブル）

メンバは同モジュール内 `PREFIX` コンテナに格納される:

- `PREFIX_LIST` (key: `name sequence_number ip_prefix masklength_range`): シーケンス番号付き
  - `sequence_number` (uint32 1..4294967295)
  - `ip_prefix` (inet:ip-prefix)
  - `masklength_range` (string、`exact` または `lo..hi`)
  - `action` (enum `permit`/`deny`)
- `PREFIX_NOSEQ_LIST` (key: `name ip_prefix masklength_range`): シーケンス番号なし

`grouping prefix-common-fields` で `name` が `../../../PREFIX_SET/PREFIX_SET_LIST/name` への leafref になる。

## 制約

- `PREFIX_LIST` の `sequence_number` は `must "count(... = 1) <= 1"` で同一 set 内ユニーク
- `mode` と実プレフィクスの family の整合チェックは TODO コメントで未実装

## 購読者

- `frr-mgmt-framework`: ルーティングポリシ管理（`DEVICE_METADATA.frr_mgmt_framework_config = true` 環境）
- 一部 sonic-mgmt-common transformer がここから FRR vtysh コマンドへ変換

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `PREFIX_LIST` / `PREFIX_NOSEQ_LIST`、[`COMMUNITY_SET`](./community-set.md)、[`AS_PATH_SET`](./as-path-set.md)、`ROUTE_MAP`
- 関連 YANG: `sonic-routing-policy-sets`
- 関連 CLI: なし（`config_db.json` 投入。FRR 側の `ip prefix-list` 等に最終的に変換される）

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: `sonic-routing-policy-sets`

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-routing-policy-sets.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-routing-policy-sets.yang>

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `PREFIX_SET|<name>`。
- `mode`: `IPv4` / `IPv6`、`prefix`: CIDR 列。route-map から `match ip address prefix-list` で参照。

### よくある誤設定

- IPv6 entry を IPv4 set に混在させて FRR が syntax エラーで読み込めない。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'PREFIX_SET|*'
vtysh -c 'show ip prefix-list'
```
<!-- /ops-hint -->
