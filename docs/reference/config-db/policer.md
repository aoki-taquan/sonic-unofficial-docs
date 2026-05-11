---
title: POLICER テーブル
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/policerorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
related:
  config_db:
    - POLICER
    - ACL_RULE
    - COPP_GROUP
    - PORT_STORM_CONTROL
  cli: []
  yang: []
---

# POLICER テーブル

!!! warning "YANG 未定義"
    `POLICER` 単独の YANG モジュールは `sonic-yang-models` に存在しない。`COPP_GROUP` (sonic-copp.yang)、`ACL_RULE` (sonic-acl.yang)、`PORT_STORM_CONTROL` (sonic-storm-control.yang)、`SCHEDULER` (sonic-scheduler.yang)、`MIRROR_SESSION` (sonic-mirror-session.yang) 等から「policer 名」あるいは個別フィールドが参照される形でのみ規定される。本ページは `policerorch.cpp` の実装を一次情報とする。

## 概要

SAI policer (sai_policer) を CONFIG_DB から作成・更新するためのテーブル。`policerorch` (orchagent) が CONFIG_DB の `POLICER` を読み出し、CIR/PIR の更新は SET、その他属性は create-only として扱う[^1]。実利用は ACL ルール、COPP、ストーム制御、ミラーセッション、ポートスケジューラ等の指し先として参照される。

## key 構造

```
POLICER|<name>
```

- `<name>`: 任意の文字列（COPP / ACL の policer 名と一致させる）

## フィールド

`policerorch.cpp` の field 定数および参照される SAI 属性は以下:

| フィールド | 値 | SAI 属性 / 説明 |
|-----------|---|------|
| `METER_TYPE` | `PACKETS` / `BYTES` | `SAI_POLICER_ATTR_METER_TYPE`。create に必須 |
| `MODE` | `SR_TCM` / `TR_TCM` / `STORM_CONTROL` | `SAI_POLICER_ATTR_MODE`。create に必須 |
| `COLOR_SOURCE` | `AWARE` / `BLIND` | `SAI_POLICER_ATTR_COLOR_SOURCE` |
| `CIR` | uint64 (bytes/sec or packets/sec) | `SAI_POLICER_ATTR_CIR`。SET 可 |
| `CBS` | uint64 | `SAI_POLICER_ATTR_CBS`。SET 可 |
| `PIR` | uint64 | `SAI_POLICER_ATTR_PIR`。SET 可 |
| `PBS` | uint64 | `SAI_POLICER_ATTR_PBS`。SET 可 |
| `GREEN_PACKET_ACTION` | `FORWARD`/`DROP`/... | `SAI_POLICER_ATTR_GREEN_PACKET_ACTION`。create-only |
| `YELLOW_PACKET_ACTION` | 同上 | `SAI_POLICER_ATTR_YELLOW_PACKET_ACTION`。create-only |
| `RED_PACKET_ACTION` | 同上 | `SAI_POLICER_ATTR_RED_PACKET_ACTION`。create-only |

## 制約

- `METER_TYPE` と `MODE` の両方が無いエントリは create でエラー (`policerorch.cpp` の `if (!meter_type || !mode)` 判定)
- `*_PACKET_ACTION`、`METER_TYPE`、`MODE`、`COLOR_SOURCE` は **create-only**。生成済み policer に対する SET は反映されない（再作成が必要）
- `CIR` 単独でも create 可能（storm-control が暗黙の `STORM_CONTROL` モード, BYTES として作成する経路を持つ）

## 購読者

- `policerorch` (orchagent): SAI policer オブジェクトを作成・更新

## 利用先（参照テーブル例）

- `ACL_RULE`: `POLICER` を action として指定
- `COPP_GROUP`: control plane 制限に利用
- `PORT_STORM_CONTROL`: ストーム制御
- `MIRROR_SESSION`: span/erspan の policer

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `ACL_RULE`、`COPP_GROUP`、`PORT_STORM_CONTROL`、`MIRROR_SESSION`
- 関連 YANG: 直接の YANG モジュールは無し（参照側 YANG が個別フィールドを持つ）
- 関連 CLI: なし（`config_db.json` で投入）

<!-- ref-triangle:start -->

## 関連リファレンス

- (関連リンクなし)

<!-- ref-triangle:end -->

## 引用元

[^1]: policerorch 実装: `policerorch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/policerorch.cpp>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: ACL / CoPP / Mirror / Packet Action](../../topics/07-acl-copp-mirror/index.md)

<!-- /topics-back-ref -->
