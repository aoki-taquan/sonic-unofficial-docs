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

<!-- glossary-links-injected: efbc9015e957 -->
