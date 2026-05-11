---
title: FABRIC_MONITOR テーブル
description: "FABRIC_MONITOR テーブル — FABRIC_MONITOR テーブルは VOQ chassis のファブリックリンク監視 (FABRIC_PORT の自動 isolate/include) 用パラメータを CONFIG_DB に保持する。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-fabric-monitor.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - FABRIC_MONITOR
    - FABRIC_PORT
  cli:
    - config fabric
  yang:
    - sonic-fabric-monitor
---

# FABRIC_MONITOR テーブル

## 概要

`FABRIC_MONITOR` テーブルは VOQ chassis のファブリックリンク監視 (`FABRIC_PORT` の自動 isolate/include) 用パラメータを CONFIG_DB に保持する[^1]。単一エントリ `FABRIC_MONITOR_DATA` を持ち、CRC エラー閾値や検出/復旧ポーリング数を定義する。

## key 構造

```
FABRIC_MONITOR|FABRIC_MONITOR_DATA
```

YANG では `container FABRIC_MONITOR_DATA` の直下にスカラー leaf が並ぶ単一インスタンス構造。

## フィールド

| フィールド | 型 | 範囲 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `monErrThreshCrcCells` | uint32 | — | 1 | エラー検出閾値となる CRC エラーセル数 |
| `monErrThreshRxCells` | uint32 | — | 61035156 | 受信セル総数の閾値。`monErrThreshRxCells` 中 `monErrThreshCrcCells` を超えるエラーで isolate |
| `monPollThreshIsolation` | uint8 | 1..10 | 1 | 連続して閾値超過と判定された場合に isolate するポーリング回数 |
| `monPollThreshRecovery` | uint8 | 1..10 | 8 | 連続して閾値以下に戻った場合に include するポーリング回数 |
| `monCapacityThreshWarn` | uint8 | 5..100 | 10 | up 状態ファブリックリンクの割合 (%) 警告閾値 |
| `monState` | `mode-status` (enable/disable) | — | disable | 監視機能のオン/オフ |

## 制約

- `monPollThreshIsolation` / `monPollThreshRecovery` は 1..10
- `monCapacityThreshWarn` は 5..100 (%)
- `monState` は `enable` または `disable`

## 購読者

- ファブリックモニタ daemon（プラットフォーム / orchagent の FabricPortOrch 拡張）

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `FABRIC_PORT`、`CHASSIS_MODULE`
- 関連 YANG: `sonic-fabric-monitor`、`sonic-fabric-port`
- 関連 CLI: `config fabric`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-fabric-monitor`](../yang/sonic-fabric-monitor.md)
- CLI: `config fabric`

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-fabric-monitor.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-fabric-monitor.yang>

## 関連ページ
- 関連 CONFIG_DB ページ: `FABRIC_PORT`（本バッチで追加）
