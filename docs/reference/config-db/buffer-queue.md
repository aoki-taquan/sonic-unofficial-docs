---
title: BUFFER_QUEUE テーブル
description: "BUFFER_QUEUE テーブル — ポートの egress queue ごとにバッファプロファイルを割り当てる。non-VOQ 用と VOQ シャーシ用で list が分かれる。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-buffer-queue.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - BUFFER_QUEUE
    - BUFFER_PROFILE
    - PORT
  cli: []
  yang:
    - sonic-buffer-queue
hard: 0
---

# BUFFER_QUEUE テーブル

## 概要

ポートの egress queue ごとにバッファプロファイルを割り当てる[^1]。non-[VOQ](../../reference/glossary.md#term-voq) 用と [VOQ](../../reference/glossary.md#term-voq) シャーシ用で list が分かれる。`buffermgrd` が [APPL_DB](../../reference/glossary.md#term-appl_db) に転送、`orchagent` `BufferOrch` が [SAI](../../reference/glossary.md#term-sai) egress queue buffer profile を反映する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>BUFFER_QUEUE")]
  DM["buffermgrd"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_BUFFER_QUEUE_TABLE")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_buffer_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

非 [VOQ](../../reference/glossary.md#term-voq):
```text
BUFFER_QUEUE|<port>|<qindex>
```

VOQ chassis:
```text
BUFFER_QUEUE|<hostname>|<asic_name>|<port>|<qindex>
```

`<qindex>` は `0..15` または範囲表現 (`0-3` 等)。

## フィールド一覧 (非 VOQ: `BUFFER_QUEUE_LIST`)

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `port` (key) | leafref `PORT.name` | ✅ | - | 対象ポート |
| `qindex` (key) | string `(1[0-5]|[0-9])((-)(1[0-5]|[0-9]))?` | ✅ | - | Q-index または範囲 |
| `profile` | leafref `BUFFER_PROFILE.name` | - | `0` | 関連付ける buffer profile |

`when` 条件: `DEVICE_METADATA.localhost.switch_type` が `voq` 以外、または未指定。

## フィールド一覧 (VOQ: `VOQ_BUFFER_QUEUE_LIST`)

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `hostname` (key) | `hostname` | ✅ | VOQ シャーシのホスト名 |
| `asic_name` (key) | `asic_name` | ✅ | ASIC インスタンス名 |
| `port` (key) | string (1..128) | ✅ | リニアカード上のポート名 |
| `qindex` (key) | string | ✅ | Q-index |
| `profile` | leafref `BUFFER_PROFILE.name` | - | buffer profile |

`when` 条件: `switch_type = voq`。

<!-- defaults -->
## コード由来暗黙デフォルト (Phase A)

このテーブルの有効フィールドは `profile` 1 つのみ。以下はコード精読から得た暗黙挙動。

| 種別 | フィールド | 内容 | evidence |
|------|-----------|------|----------|
| YANG-実装 discrepancy | `profile` | YANG は `default 0` を宣言するが実装 (`buffermgrdyn`) は `profile` フィールドのない SET を `task_failed` で拒否する。実質必須。 | `sonic-swss/cfgmgr/buffermgrdyn.cpp:3337-3341` |
| 方向制約（YANG になし） | `profile` | 参照プロファイルが `BUFFER_EGRESS` 以外（ingress pool 参照）の場合 `task_failed`。YANG に方向制約の記述なし。 | `buffermgrdyn.cpp:3318-3325` |
| silent substitution (admin-down) | `profile` | ポートが admin-down になると `reclaimReservedBufferForPort` が設定プロファイルを zero profile（`_zero_` 含む名前）に自動差し替えて APPL_DB に書き込む。CONFIG_DB 値は変わらないが SAI 反映値は異なる。 | `buffermgrdyn.cpp:1319-1383` |
| platform 依存（zero profile） | `profile` | vendor 提供 JSON に `queues_to_apply_zero_profile` / `egress_zero_profile` が定義されない場合、admin-down 時に各 queue が APPL_DB から削除される（zero profile 適用なし）。platform によって admin-down 挙動が異なる。 | `buffermgrdyn.cpp:285-289`, `1332` |
| dead field 相当（removal 非対応） | DEL 操作 | `support_removing_buffer_items: no` の platform では DEL が `task_failed`。削除自体をサポートしないプラットフォームが存在する。 | `buffermgrdyn.cpp:3355-3358` |
| flexcounter 暗黙スキップ | `profile` | プロファイル名に `_zero_` を含む場合、flex counter の追加・削除を行わない。YANG に規定なく、命名慣習による暗黙ルール。 | `bufferorch.cpp:995, 1017` |
| retry（書込み順依存） | `profile` | BUFFER_PROFILE が APPL_DB に未到達の時点で BUFFER_QUEUE SET が届くと `task_need_retry` ループになる。CONFIG_DB 書き込み順が重要。 | `bufferorch.cpp:961-974` |

> **運用上の注意**: YANG `default 0` を信頼して `profile` を省略した場合、`buffermgrd` 起動直後のリプレイで `task_failed` が発生しエントリが消失する。テンプレート生成時は必ず `profile` フィールドを明示する。
<!-- /defaults -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

- **key フォーマット不正 → スキップ**: key が `<port>|<queue_range>` の 2 トークンでない場合、初期化時にエラーログを出力しそのエントリをスキップする。<!-- evidence: bufferorch.cpp L158-162 initBufferReadyList -->
- **プロファイル参照未解決 → retry**: `profile` フィールドに参照する `BUFFER_PROFILE` が未存在の場合、`orchagent` は `task_need_retry` を返す。<!-- evidence: bufferorch.cpp L966-970 -->
- **プロファイル変更なし → SAI 呼び出しスキップ**: プロファイルが変更なく `m_partiallyAppliedQueues` にもキーがない場合はスキップ (冪等)。<!-- evidence: bufferorch.cpp L975-985 -->
- **queue インデックス範囲外 → task_invalid_entry**: 指定インデックスがポートのキュー数を超える場合 `task_invalid_entry` を返す。VoQ も同様。<!-- evidence: bufferorch.cpp L1060-1065 -->
- **queue ロック中 → retry + partiallyApplied**: `port.m_queue_lock[ind] == true` の場合 `task_need_retry` を返し `m_partiallyAppliedQueues` に登録。ロック解除後に再適用される。<!-- evidence: bufferorch.cpp L1066-1070 -->
- **zero profile (`_zero_` 含む名前) → flexcounter 登録スキップ**: プロファイル名に `_zero_` が含まれる場合、カウンタの追加・削除は行わない。zero profile はトラフィックなしを意味する。<!-- evidence: bufferorch.cpp L1017, L1020 -->

<!-- value-behavior -->
## 値依存挙動マトリクス

このテーブルに enum フィールドはない。ただし `DEVICE_METADATA.switch_type` および参照プロファイルの値によって挙動が変わる。

| 条件 | 挙動 |
|------|------|
| `switch_type` が `voq` 以外（未設定含む） | `BUFFER_QUEUE_LIST` が有効。key は `<port>\|<qindex>` の 2 トークン形式。 |
| `switch_type = voq` | `VOQ_BUFFER_QUEUE_LIST` が有効。key に `<hostname>\|<asic_name>` が付加される。 |
| 参照プロファイルの `packet_discard_action = drop` | egress queue buffer profile として制限なく適用可能。 |
| プロファイル名に `_zero_` を含む | flex counter の追加・削除をスキップ（traffic なしを意味する zero profile 扱い）（`bufferorch.cpp:1017, 1020`）。 |
<!-- /value-behavior -->

## 購読者

- `buffermgrd`: [APPL_DB](../../reference/glossary.md#term-appl_db) へ転送
- `orchagent` `BufferOrch`: [SAI](../../reference/glossary.md#term-sai) egress queue buffer profile を反映

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `BUFFER_PROFILE`、`BUFFER_POOL`、`PORT`、`DEVICE_METADATA`、`QUEUE`、`SCHEDULER`
- 関連 CLI: なし
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-buffer-queue`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-buffer-queue`](../yang/sonic-buffer-queue.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-buffer-queue.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-buffer-queue.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `BUFFER_QUEUE|<port>|<queue-range>` (例 `0-2`, `3-4`, `5-6`)。
- `profile`: `q_lossy_profile` 等。

### よくある誤設定

- queue 範囲が抜けると当該 queue が default profile になり、計画値と乖離。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'BUFFER_QUEUE|Ethernet0|*'
show buffer queue
```
<!-- /ops-hint -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`buffermgrd` → `BufferOrch` (APPL_DB 経由) が CONFIG_DB の `BUFFER_QUEUE` テーブルを購読する。

`BUFFER_QUEUE` の key は `<port>|<queue_range>` (例: `Ethernet0|0-2`)。

### 段階 2 — CFG→APPL 翻訳

`APP_BUFFER_QUEUE_TABLE` に書き込み

### 段階 3 — APPL→SAI

`sai_buffer_api` — キューのバッファプロファイルをバインド

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `buffermgrd` が検知後 APPL_DB に書き込み。`BufferOrch` が SAI queue buffer attribute を更新。

**副作用**: 対象キューの egress バッファ割り当てが変更される。キューの動作中変更は一時的な traffic 影響を伴う可能性がある。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `BUFFER_QUEUE`

### CLI
- `config interface buffer queue set <port> <q-range> <profile>`
- `config interface buffer queue remove <port> <q-range>`
  - ソース: `sonic-utilities/config/main.py (buffer グループ)`

### minigraph / sonic-cfggen
- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `qos_config.j2` から QoS マッピングと共に生成

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
<!-- /entry-points -->


<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 値による他フィールド自動派生

| 条件 | 派生先 | evidence |
|---|---|---|
| DB 移行: `profile` フィールドの区切り文字を新形式に更新 | `BUFFER_QUEUE.profile` を変換 | `sonic-utilities/scripts/db_migrator.py:450` |

### Phase 7: 条件付き module/manager 登録

| 条件 | 登録 module | evidence |
|---|---|---|
| 常時（条件なし） | `BufferMgrDynamic` が `BUFFER_QUEUE` を `handleBufferQueueTable` に登録 | `sonic-swss/cfgmgr/buffermgrdyn.cpp:445` |

### grep カバレッジ

- buffermgrdyn.cpp L445: BUFFER_QUEUE ハンドラ登録（条件なし）
- db_migrator.py L450: profile フィールド区切り文字変換
<!-- /derivation -->
<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Manager / Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `BufferMgrDynamic` | `handleBufferObjectTables()` | キー形式 `port:ids` が不正 | `task_invalid_entry` 返却（`keyWithIds=true` のためキュー番号必須） | `sonic-swss/cfgmgr/buffermgrdyn.cpp:3521` |
| `BufferMgrDynamic` | `handleBufferObjectTables()` | カンマ区切りポートリスト（複数ポート） | ポートごとにシングルポートハンドラを繰り返し呼び出し | `sonic-swss/cfgmgr/buffermgrdyn.cpp:3536-3547` |

> **スキャン証跡**: `handleBufferQueueTable` は `handleBufferObjectTables(tuple, CFG_BUFFER_QUEUE_TABLE_NAME, true)` に委譲（`keyWithIds=true`）。BUFFER_PG と同一パスを共有。2 件分岐抽出。
<!-- /handler-branching -->
<!-- glossary-links-injected: efbc9015e957 -->
