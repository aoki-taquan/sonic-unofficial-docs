---
title: BUFFER_PROFILE テーブル
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-buffer-profile.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - BUFFER_PROFILE
    - BUFFER_POOL
    - BUFFER_PG
    - BUFFER_QUEUE
  cli: []
  yang:
    - sonic-buffer-profile
---

# BUFFER_PROFILE テーブル

## 概要

バッファプロファイル（プール参照、reserved size、admission threshold、PFC xon/xoff など）を名前付きで定義する[^1]。`buffermgrd` がこのテーブルを APPL_DB の `BUFFER_PROFILE_TABLE` に転送し、`orchagent` `BufferOrch` が SAI buffer profile を生成する。`BUFFER_PG` / `BUFFER_QUEUE` から leafref で参照される。

## key 構造

```
BUFFER_PROFILE|<name>
```

## フィールド一覧

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `name` (key) | string | ✅ | - | プロファイル名 |
| `pool` | leafref `BUFFER_POOL.name` | ✅ | - | バインドする buffer pool |
| `size` | uint64 | ✅ | - | 予約バッファサイズ [byte] |
| `static_th` | uint64 | - | - | static threshold [byte]（最大占有量） |
| `dynamic_th` | int32 (-8..7) | - | - | dynamic threshold alpha 値 |
| `xon` | uint64 | - | `0` | PFC xon 閾値 [byte] |
| `xon_offset` | uint64 | - | `0` | xon offset [byte]（resume を `max(xon, limit-offset)` で発火） |
| `xoff` | uint64 | - | `0` | PFC xoff 閾値 [byte]（pause 生成） |
| `headroom_type` | enum `static`/`dynamic` | - | `static` | headroom 動的計算かどうか |
| `packet_discard_action` | enum `drop`/`trim` | - | - | shared buffer に admit できないときの動作 |

## 購読者

- `buffermgrd`: dynamic buffer model のとき、ポート速度・ケーブル長・MTU から `headroom_type=dynamic` のサイズを計算
- `orchagent` `BufferOrch`: SAI buffer profile を生成
- `pfcwd`: profile の xon/xoff を参照

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `BUFFER_POOL`、`BUFFER_PG`、`BUFFER_QUEUE`、`DEVICE_METADATA` (`buffer_model`)
- 関連 CLI: 通常は `config_db.json` からロード。CLI 直接編集は限定的
- 関連 YANG: `sonic-buffer-profile`

## 引用元

[^1]: YANG 定義: `sonic-buffer-profile.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-buffer-profile.yang>
