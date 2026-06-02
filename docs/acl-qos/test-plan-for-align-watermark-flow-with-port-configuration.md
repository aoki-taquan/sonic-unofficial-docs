---
title: counterpoll 種別と watermark / queue / pg-drop マップの整合テストプラン
description: counterpoll 種別と watermark / queue / pg-drop マップの整合テストプラン — SONiC の counterpoll
  CLI は queue / watermark / pg-drop の 3 種を個別に enable/disable できる。
area: acl-qos
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/SONiC
  path: doc/buffer-watermark/align_watermark_flow_with_port_configuration_test_plan.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - FLEX_COUNTER_TABLE
  - PORT
  - QUEUE
  - PORT_QOS_MAP
  - PORT_TABLE
  cli:
  - counterpoll
  - config save
  - config reload
  - show queue
  yang:
  - sonic-port
  - sonic-queue
  - sonic-port-qos-map
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含む。機能の概念・設定・運用を読み物として読みたい場合は [Topics 08 章: QoS / Buffer / PFC](../topics/08-qos-buffer/index.md) を参照。
<!-- /topics-tip -->

!!! success "裏取りステータス: code-verified"
    Verifier 2026-05-09: `sonic-swss/orchagent/flexcounterorch.cpp:76-95` で `QUEUE → QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP`, `QUEUE_WATERMARK → QUEUE_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP`, `PG_WATERMARK → PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP`, `PG_DROP → PG_DROP_STAT_COUNTER_FLEX_COUNTER_GROUP`, `WRED_ECN_QUEUE → WRED_QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP` のマッピングを確認。テストプランの 4 種 counter group が現行 FlexCounterOrch に揃って実装されており、`counterpoll <type> enable/disable` 経路と整合する。

# `counterpoll` 種別と watermark / queue / pg-drop マップの整合テストプラン

## 概要

[SONiC](../reference/glossary.md#term-sonic) の `counterpoll` CLI は **queue / watermark / pg-drop** の 3 種を個別に enable/disable できる。それぞれの enable 状態に応じて、`COUNTERS_DB` 上の補助マップ（QUEUE / PG マップ群）と `FLEX_COUNTER_DB` 上の counter group entry が **作成または削除されるべき** という前提で本テストプランは検証する[^1]。

過去に **queue / pg-drop マップ生成のパフォーマンス改善**が入った直後のリグレッション防止が動機で、ポートバッファが設定されていないと統計が両 DB に現れないため、ポートバッファ設定が前提となる[^1]。

## 動作仕様

### counterpoll 種別と期待される DB 状態

| counterpoll | 状態 | 確認すべき counter group |
|-------------|------|------------------------|
| queue | enabled | `FLEX_COUNTER_TABLE:QUEUE_STAT_COUNTER:oid:0x*` |
| watermark | enabled | `FLEX_COUNTER_TABLE:QUEUE_WATERMARK_STAT_COUNTER:oid:0x*` および `PG_WATERMARK_STAT_COUNTER:oid:0x*` |
| pg-drop | enabled | `FLEX_COUNTER_TABLE:PG_DROP_STAT_COUNTER:oid:0x*` |

それ以外は disabled の場合「該当 counter group が **存在しない** こと」を pass criteria とする[^1]。

### COUNTERS_DB 側の補助マップ

| 種別 | 関連マップ |
|------|-----------|
| QUEUE | `COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_QUEUE_INDEX_MAP` / `COUNTERS_QUEUE_PORT_MAP` / `COUNTERS_QUEUE_TYPE_MAP` |
| PG | `COUNTERS_PG_NAME_MAP` / `COUNTERS_PG_PORT_MAP` / `COUNTERS_PG_INDEX_MAP` |
| watermark 値 | `USER_WATERMARKS:oid:*` / `PERIODIC_WATERMARKS:oid:*` / `PERSISTENT_WATERMARKS:oid:*` |

`watermark enable` 時は **PG マップと QUEUE マップの両方** が作成され、両 watermark counter が生成される。`queue enable` 時は QUEUE マップのみ、`pg-drop enable` 時は PG マップのみで、watermark 系 counter は出ない、というのが整合性ルール[^1]。

<!-- evidence:
source: sonic-net/SONiC/doc/buffer-watermark/align_watermark_flow_with_port_configuration_test_plan.md#L70-L88 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  | counterpoll type | state    | counter                                                 | pass criteria  |
  | queue            | enabled  | FLEX_COUNTER_TABLE:QUEUE_STAT_COUNTER:oid:0x*           | present        |
  | watermark        | enabled  | FLEX_COUNTER_TABLE:QUEUE_WATERMARK_STAT_COUNTER:oid:0x* | present        |
  |                  |          | FLEX_COUNTER_TABLE:PG_WATERMARK_STAT_COUNTER:oid:0x*    | present        |
  | pg-drop          | enabled  | FLEX_COUNTER_TABLE:PG_DROP_STAT_COUNTER:oid:0x*         | present        |
reasoning: 本テストの整合性判定基準を直接表化
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/SONiC/doc/buffer-watermark/align_watermark_flow_with_port_configuration_test_plan.md#L70-L88 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)"

    **出典**:

    `sonic-net/SONiC/doc/buffer-watermark/align_watermark_flow_with_port_configuration_test_plan.md#L70-L88 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)`

    **抜粋**:

    ```text
    | counterpoll type | state    | counter                                                 | pass criteria  |
    | queue            | enabled  | FLEX_COUNTER_TABLE:QUEUE_STAT_COUNTER:oid:0x*           | present        |
    | watermark        | enabled  | FLEX_COUNTER_TABLE:QUEUE_WATERMARK_STAT_COUNTER:oid:0x* | present        |
    |                  |          | FLEX_COUNTER_TABLE:PG_WATERMARK_STAT_COUNTER:oid:0x*    | present        |
    | pg-drop          | enabled  | FLEX_COUNTER_TABLE:PG_DROP_STAT_COUNTER:oid:0x*         | present        |
    ```

    **判断根拠**: 本テストの整合性判定基準を直接表化

<!-- evidence-rendered:end -->

## テスト項目

### 単一 counterpoll 有効化（config save → reload）

各種別を 1 つずつ enable し、対応するマップ／counter group のみが存在することを確認[^1]:

1. すべての counterpoll を disable して config save → reload
2. queue / watermark / pg-drop のいずれか 1 つを enable
3. その counter group が `FLEX_COUNTER_DB` に出現
4. 関連する [COUNTERS_DB](../reference/glossary.md#term-counters_db) マップが作成
5. 他種別の counter / マップが存在しないこと

### 全 counterpoll 有効化シーケンス

`queue` → `watermark` → `pg-drop` を順次 enable し、それぞれの直後で **これまで enable した種別の counter のみ** が共存することを確認する[^1]。

### 再起動横断（reboot）

`config save` 後 reboot → fast/warm 後にも同じマップ／counter group が再現される。各種別個別パターンと全部入りパターンを実施[^1]。

## 設定

### 関連 CLI

| Command | 用途 |
|---------|------|
| `counterpoll queue enable\|disable` | queue counter polling 切替 |
| `counterpoll watermark enable\|disable` | queue / PG watermark counter 切替 |
| `counterpoll pg-drop enable\|disable` | priority group drop counter 切替 |
| `config save -y` / `config reload` | 設定永続化と reload |

### 関連する CONFIG_DB

`FLEX_COUNTER_TABLE` の各 group entry。本テストでは [CONFIG_DB](../reference/glossary.md#term-config_db) の参照は限定的で、主に `FLEX_COUNTER_DB` (DB 5) と `COUNTERS_DB` (DB 2) を対象にする。

## 制限事項

- ポートバッファ設定がないと、queue / pg-drop のマップそのものが作成されないため、テスト前提として buffer 設定が必要[^1]
- 本テストは traffic を生成しない。整合性のみ確認

## 干渉する機能

- **buffer config**: ポートバッファ設計変更（dynamic buffer 等）の影響を受ける可能性あり
- **warm/fast-reboot**: counter group / マップの永続化

## 関連 reference

- [HLD: align-watermark-flow-with-port-configuration](align-watermark-flow-with-port-configuration-hld.md)
- [Topics: QoS / Buffer](../topics/08-qos-buffer/index.md)
- [CLI: show buffer-pool](../reference/cli/show-buffer-pool.md)

## 引用元

[^1]: [sonic-net/SONiC doc/buffer-watermark/align_watermark_flow_with_port_configuration_test_plan.md @ 49bab5b](https://github.com/sonic-net/SONiC/blob/49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06/doc/buffer-watermark/align_watermark_flow_with_port_configuration_test_plan.md)

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 8ba32e5aa69d -->
