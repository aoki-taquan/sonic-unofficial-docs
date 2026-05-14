---
title: QUEUE テーブル
description: "QUEUE テーブル — ポートの egress queue ごとに SCHEDULER (WRR/DWRR/STRICT) と WRED_PROFILE を割り当てる。qosorch が SAI queue scheduler / WRED を設定する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-queue.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - QUEUE
    - SCHEDULER
    - WRED_PROFILE
    - PORT
  cli: []
  yang:
    - sonic-queue
---

# QUEUE テーブル

## 概要

ポートの egress queue ごとに `SCHEDULER` (WRR/[DWRR](../../reference/glossary.md#term-dwrr)/STRICT) と `WRED_PROFILE` を割り当てる[^1]。`qosorch` が [SAI](../../reference/glossary.md#term-sai) queue scheduler / [WRED](../../reference/glossary.md#term-wred) を設定する。[VOQ](../../reference/glossary.md#term-voq) シャーシでは `QUEUE_LIST` ではなく `VOQ_QUEUE_LIST` を使う。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>QUEUE")]
  DM["QosOrch"]
  CDB --> DM
  SAI["SAI<br/>sai_queue_api"]
  DM --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

非 [VOQ](../../reference/glossary.md#term-voq):
```text
QUEUE|<ifname>|<qindex>
```

[VOQ](../../reference/glossary.md#term-voq) chassis:
```text
QUEUE|<hostname>|<asic_name>|<ifname>|<qindex>
```

`<ifname>` は `PORT.name` への leafref または文字列 `CPU`。`<qindex>` はプラットフォーム依存（物理 0-7、CPU 0-48 等）、範囲表現も可。

## フィールド一覧 (非 VOQ: `QUEUE_LIST`)

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `ifname` (key) | leafref `PORT.name` または `CPU` | ✅ | IF 名 |
| `qindex` (key) | string | ✅ | Q-index または範囲 |
| `scheduler` | leafref `SCHEDULER.name` | - | スケジューラ参照 |
| `wred_profile` | leafref `WRED_PROFILE.name` | - | [WRED](../../reference/glossary.md#term-wred) プロファイル参照 |

`when` 条件: `switch_type` が `voq` でないか未指定。

## フィールド一覧 (VOQ: `VOQ_QUEUE_LIST`)

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `hostname` (key) | `hostname` | ✅ | シャーシホスト名 |
| `asic_name` (key) | `asic_name` | ✅ | ASIC 名 |
| `ifname` (key) | string (1..128) | ✅ | IF 名 |
| `qindex` (key) | string | ✅ | Q-index |
| `scheduler` | leafref `SCHEDULER.name` | - | スケジューラ |
| `wred_profile` | leafref `WRED_PROFILE.name` | - | [WRED](../../reference/glossary.md#term-wred) プロファイル |

`when` 条件: `switch_type = voq`。

## 購読者

- `qosorch`: [SAI](../../reference/glossary.md#term-sai) queue scheduler / WRED を生成
- `bufferorch` と協調

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `SCHEDULER`、`WRED_PROFILE`、`PORT`、`BUFFER_QUEUE`、`TC_TO_QUEUE_MAP`
- 関連 CLI: なし（`config_db.json` ロード）
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-queue`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-queue`](../yang/sonic-queue.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-queue.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-queue.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `QUEUE|<port>|<queue-range>` (例 `QUEUE|Ethernet0|3-4`)。
- `scheduler`: `scheduler.0` 等。
- `wred_profile`: `AZURE_LOSSY` 等。

### よくある誤設定

- [PFC](../../reference/glossary.md#term-pfc) 対応 queue に `wred_profile` を当てて ECN を有効にしないと、輻輳時に [PFC](../../reference/glossary.md#term-pfc) が連続発火する。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'QUEUE|Ethernet0|*'
show queue counters
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `ifname` 値別挙動
| 値 | 挙動 |
|----|------|
| `PORT.name` に存在する値 | 正常処理。[SAI](../../reference/glossary.md#term-sai) queue scheduler / WRED 適用。 |
| `CPU` | CPU queue 用の専用処理パス。 |
| 存在しないポート名 | `SWSS_LOG_ERROR("Port with alias:%s not found")` → `task_invalid_entry` でスキップ。 |

### `scheduler` フィールド挙動
| 状態 | 挙動 |
|------|------|
| 省略 | スケジューラなし。ASIC デフォルト動作。 |
| 存在する SCHEDULER 名 | `qosorch` が SAI scheduler を queue に適用。 |
| 存在しない SCHEDULER 名 | `task_need_retry`（後で再試行）。解決不可なら `task_failed`。 |

### `wred_profile` フィールド挙動
| 状態 | 挙動 |
|------|------|
| 省略 | WRED なし。 |
| 存在する WRED_PROFILE 名 | SAI WRED を queue に適用。 |
| 存在しない WRED_PROFILE 名 | `task_need_retry`。解決不可なら `task_failed`。 |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

- **key トークン数不正**: 非 VOQ 環境では `<ifname>|<qindex>` の 2 トークン必須。VOQ 環境では `<hostname>|<asic_name>|<ifname>|<qindex>` の 4 トークン必須。違反時は `task_invalid_entry` で処理中断。[^2]
- **queue index 範囲外**: `<qindex>` が SAI の queue 数を超えた場合 `SWSS_LOG_ERROR("Invalid queue index specified")` でエントリがスキップされる。[^2]
- **SCHEDULER 参照未解決 (リトライ)**: `scheduler` フィールドの参照先 SCHEDULER エントリがまだ存在しない場合は `task_need_retry` で後で再試行される。解決できない恒久エラーの場合は `task_failed`。[^2]
- **WRED_PROFILE 参照未解決 (リトライ)**: `wred_profile` も同様に未解決なら `task_need_retry`、恒久エラーは `task_failed`。[^2]
- **port 未検出**: `<ifname>` が PORT テーブルに存在しない場合 `SWSS_LOG_ERROR("Port with alias:%s not found")` でスキップ。[^2]
- **scheduler group 未検出**: ポートは存在しても queue index に対応する SAI scheduler group が見つからない場合 `task_failed`。[^2]

[^2]: qosorch 実装: `sonic-swss/orchagent/qosorch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/qosorch.cpp>


<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

QosOrch が `QUEUE.wred_profile` / `QUEUE.scheduler` / `QUEUE.dscp_to_tc_map` フィールドを参照して各テーブルの OID を解決し、SAI キューオブジェクトに bind する。参照先テーブルが未作成の場合は設定がペンディング状態になる（待機派生）。

### Phase 7: 条件付き登録 (add_manager 条件)

QosOrch は常時登録し `QUEUE` テーブルを無条件購読する。ただし `SCHEDULER` / `WRED_PROFILE` が未作成の場合は対応 OID が未解決でペンディングとなる。port が未初期化の場合はエラーログ + スキップ。

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `QosOrch` | `wred_profile` フィールドあり | `WRED_PROFILE` OID 参照 → `SAI_QUEUE_ATTR_WRED_PROFILE_ID` 設定 | `qosorch.cpp` |
| `QosOrch` | `scheduler` フィールドあり | `SCHEDULER` OID 参照 → `SAI_QUEUE_ATTR_SCHEDULER_PROFILE_ID` 設定 | `qosorch.cpp` |
| `QosOrch` | port のキュー番号が範囲外 | ERROR ログ + スキップ | `qosorch.cpp` |
| `QosOrch` | del_handler: `wred_profile` あり | SAI attribute を NULL OID に設定して解除 | `qosorch.cpp` |

> **スキャン証跡**: QUEUE は SAI キューオブジェクトの属性 (scheduler, wred_profile) を束ねる。Phase 6 派生はフィールドから OID 解決への変換。自動付与はなし。

<!-- /handler-branching -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **orchagent / QosOrch** (`sonic-swss/orchagent/qosorch.cpp`): `QUEUE` テーブルを `SubscriberStateTable` で購読。

### 段階 2: CFG → APPL 翻訳

- QosOrch がキューのスケジューラマップ (`scheduler`) と WRED プロファイル (`wred_profile`) を解析。
- APP_DB への書き込みなし。

### 段階 3: APPL → SAI

- QosOrch が `sai_scheduler_api` / `sai_wred_api` を呼び出し、キュー OID に対してスケジューラと WRED を適用。

### 段階 4: タイミング + 副作用

- 参照するスケジューラ/WRED が未作成の場合は `task_need_retry`。
- 副作用: キューの WRED 変更は既存フロー中のパケットからリアルタイムに適用される。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

QUEUE テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config qos reload` — sonic-cfggen が `files/build_templates/qos_config.j2` を展開し QUEUE エントリを生成 (sonic-buildimage/files/build_templates/qos_config.j2)

### minigraph / sonic-cfggen

minigraph.py に QUEUE 直接生成なし — `qos_config.j2` テンプレート経由

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

**db_migrator.py** が QUEUE テーブルのマイグレーション処理を実装 (sonic-utilities/scripts/db_migrator.py)

### ビルド時デフォルト (build-time default)

各プラットフォームの `qos.json.j2` に QUEUE エントリが定義され、ビルド時に投入

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- glossary-links-injected: f9445b5b4106 -->
