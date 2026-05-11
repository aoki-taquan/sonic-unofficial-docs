---
title: BUFFER_PORT_EGRESS_PROFILE_LIST テーブル
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-buffer-port-egress-profile-list.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - BUFFER_PORT_EGRESS_PROFILE_LIST
    - BUFFER_PORT_INGRESS_PROFILE_LIST
    - BUFFER_PROFILE
    - PORT
  cli:
    - config buffer
  yang:
    - sonic-buffer-port-egress-profile-list
---

# BUFFER_PORT_EGRESS_PROFILE_LIST テーブル

## 概要

`BUFFER_PORT_EGRESS_PROFILE_LIST` テーブルはポートに **egress** 側バッファプロファイルを順序付きでバインドする[^1]。`buffermgrd` が CONFIG_DB を読み出し、SAI 経由でポート単位の egress バッファプール / プロファイル割当を反映する。

## key 構造

```
BUFFER_PORT_EGRESS_PROFILE_LIST|<port>
```

| キー | 型 | 説明 |
|------|----|------|
| `port` | leafref → `PORT.name` | バインド対象の物理ポート |

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `profile_list` | leaf-list leafref → `BUFFER_PROFILE.name` (`ordered-by user`) | このポートに適用する egress バッファプロファイルの順序付きリスト |

## 制約

- `port` は `PORT` への leafref
- `profile_list` 各要素は `BUFFER_PROFILE` への leafref
- 順序はユーザー指定（`ordered-by user`）

## 購読者

- `buffermgrd` (sonic-swss)
- 間接的に `orchagent` の `BufferOrch`

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `BUFFER_PROFILE`、`BUFFER_PORT_INGRESS_PROFILE_LIST`、`BUFFER_QUEUE`、`BUFFER_POOL`、`PORT`
- 関連 YANG: `sonic-buffer-port-egress-profile-list`、`sonic-buffer-profile`
- 関連 CLI: `config buffer`

## 引用元

[^1]: YANG 定義: `sonic-buffer-port-egress-profile-list.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-buffer-port-egress-profile-list.yang>

## 関連ページ
- [CONFIG_DB: BUFFER_PROFILE](buffer-profile.md)
- [CONFIG_DB: BUFFER_QUEUE](buffer-queue.md)
- 関連 CONFIG_DB ページ: `BUFFER_PORT_INGRESS_PROFILE_LIST`（本バッチで追加）
