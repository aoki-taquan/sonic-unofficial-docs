---
title: FABRIC_PORT テーブル
description: "FABRIC_PORT テーブル — FABRIC_PORT テーブルは VOQ chassis におけるラインカード間ファブリックリンクの設定を CONFIG_DB に保持する。portsyncd / orchagent がファブリックポートの isolate / unisolate 状態を SAI 側に反映する。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-fabric-port.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - FABRIC_PORT
    - FABRIC_MONITOR
  cli:
    - config fabric
  yang:
    - sonic-fabric-port
---

# FABRIC_PORT テーブル

## 概要

`FABRIC_PORT` テーブルは VOQ chassis におけるラインカード間ファブリックリンクの設定を CONFIG_DB に保持する[^1]。`portsyncd` / `orchagent` がファブリックポートの isolate / unisolate 状態を SAI 側に反映する。

## key 構造

```
FABRIC_PORT|<name>
```

| キー | 型 | 説明 |
|------|----|------|
| `name` | string (1..128) | ファブリックポート名 |

## フィールド

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `isolateStatus` | `boolean_type` | False | ポートのアイソレーション状態 |
| `alias` | string (1..128) | — | ファブリックポートのエイリアス |
| `lanes` | string (1..128) | — (mandatory) | レーン番号文字列 |
| `forceUnisolateStatus` | uint32 | 0 | 強制 unisolate のステータス値 |

## 制約

- `lanes` は mandatory
- `isolateStatus` の値は `sonic-types:boolean_type`（`True`/`False` 文字列）

## 購読者

- `orchagent` の FabricPortOrch / ファブリック関連ロジック
- `fabricmgrd` 系 daemon（プラットフォーム実装による）

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `FABRIC_MONITOR`、`SYSTEM_PORT`、`CHASSIS_MODULE`
- 関連 YANG: `sonic-fabric-port`、`sonic-fabric-monitor`
- 関連 CLI: `config fabric`、`show fabric`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-fabric-port`](../yang/sonic-fabric-port.md)
- CLI: `config fabric`

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-fabric-port.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-fabric-port.yang>

## 関連ページ
- 関連 CONFIG_DB ページ: `FABRIC_MONITOR`（本バッチで追加）
