---
title: SCHEDULER テーブル
description: "SCHEDULER テーブル — キュー / ポートに適用するスケジューラ（DWRR / WRR / STRICT）と dual-rate token bucket policer (CIR / PIR / CBS / PBS) のプロファイルを保持する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-scheduler.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - SCHEDULER
    - QUEUE
    - PORT_QOS_MAP
  cli: []
  yang:
    - sonic-scheduler
---

# SCHEDULER テーブル

## 概要

キュー / ポートに適用するスケジューラ（[DWRR](../../reference/glossary.md#term-dwrr) / WRR / STRICT）と dual-rate token bucket policer (CIR / PIR / CBS / PBS) のプロファイルを保持する[^1]。`qosorch` が [SAI](../../reference/glossary.md#term-sai) scheduler を生成、`QUEUE.scheduler` から leafref で参照される。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>SCHEDULER")]
  DM["QosOrch"]
  CDB --> DM
  SAI["SAI<br/>sai_scheduler_api"]
  DM --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
SCHEDULER|<name>
```

## フィールド一覧

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `name` (key) | string | ✅ | - | スケジューラ名 |
| `type` | enum `DWRR`/`WRR`/`STRICT` | - | `WRR` | スケジューリングアルゴリズム |
| `weight` | uint8 (1..100) | - | `1` | 重み（[DWRR](../../reference/glossary.md#term-dwrr)/WRR で使用） |
| `priority` | uint8 (0..9) | - | - | 優先度 |
| `meter_type` | enum `packets`/`bytes` | - | `bytes` | meter 単位 |
| `cir` | uint64 | - | - | committed information rate（Bps or Pps） |
| `pir` | uint64 | - | - | peak information rate。`cir > 0` 必須、`pir >= cir` |
| `cbs` | uint32 | - | - | committed burst size。`cir > 0` 必須 |
| `pbs` | uint32 | - | - | excess/peak burst size。`pir > 0` 必須、`pbs >= cbs` |

## 制約 (must)

- `pir` 単独設定禁止（`cir` 必須・`cir > 0`）
- `pir >= cir`
- `cbs` 単独設定禁止（`cir` 必須）
- `pbs` 単独設定禁止（`pir` 必須）、`pbs >= cbs`

## 購読者

- `qosorch`: [SAI](../../reference/glossary.md#term-sai) scheduler を生成

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `QUEUE`、`PORT_QOS_MAP`
- 関連 CLI: なし
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-scheduler`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-scheduler`](../yang/sonic-scheduler.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-scheduler.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-scheduler.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `SCHEDULER|<name>` (例 `scheduler.0`)。
- `type`: `STRICT` / `DWRR` / `WRR`。
- `weight`: 1..100。
- `meter_type` / `pir` (shaping 用)。

### よくある誤設定

- `type: STRICT` を全 queue に設定すると低優先 queue が永遠に starve。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'SCHEDULER|*'
show queue counters
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `type` 値別挙動
| 値 | [SAI](../../reference/glossary.md#term-sai) 変換 | 挙動 |
|----|----------|------|
| `DWRR` | `SAI_SCHEDULING_TYPE_DWRR` | 重み付きデフキュー方式。`weight` フィールドを帯域比率として使用。 |
| `WRR` | `SAI_SCHEDULING_TYPE_WRR` | 重み付きラウンドロビン。`weight` フィールドを使用。 |
| `STRICT` | `SAI_SCHEDULING_TYPE_STRICT` | 厳格優先。weight は無視。上位優先度 queue が常に先処理。全 queue に設定すると低優先が starve。 |
| その他 | なし | `SWSS_LOG_ERROR("Unknown scheduler type value:%s")` → `task_invalid_entry`。エントリ破棄、SAI 非反映。 |

### `meter_type` 値別挙動
| 値 | SAI 変換 | 挙動 |
|----|----------|------|
| `packets` | `SAI_METER_TYPE_PACKETS` | CIR/PIR の単位をパケット数として解釈。 |
| `bytes` | `SAI_METER_TYPE_BYTES` | CIR/PIR の単位をバイト数として解釈（デフォルト）。 |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

- **type フィールドが未知の値**: `type` が `DWRR` / `WRR` / `STRICT` 以外の場合 `SWSS_LOG_ERROR("Unknown scheduler type value:%s")` を出して `task_invalid_entry` を返す。エントリは破棄されて SAI には反映されない。[^2]
- **SAI scheduler profile 作成失敗**: `sai_scheduler_api->create_scheduler()` が失敗した場合 `SWSS_LOG_ERROR("Failed to create scheduler profile")` で処理中断。[^2]
- **SAI scheduler profile 削除失敗**: QUEUE から参照されている SCHEDULER プロファイルを削除しようとすると SAI が EBUSY 等を返し `SWSS_LOG_ERROR("Failed to remove scheduler profile")` となる。[CONFIG_DB](../../reference/glossary.md#term-config_db) からは削除されても ASIC には古いプロファイルが残留する。[^2]
- **weight のオーバーフロー**: `weight` フィールドは `uint8` にキャストされるため 0-255 の範囲外は暗黙に切り捨てられる（バリデーションなし）。[^2]
- **QUEUE 参照がある間は削除不可**: QUEUE が参照している SCHEDULER を削除すると SAI レイヤで失敗する。QUEUE の参照を先に外してから削除する必要がある。[^2]

[^2]: qosorch 実装: `sonic-swss/orchagent/qosorch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/qosorch.cpp>


<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

QosOrch が `SCHEDULER.type` の値から SAI scheduling type を自動決定する。`STRICT` → `SAI_SCHEDULING_TYPE_STRICT`、`DWRR` → `SAI_SCHEDULING_TYPE_DWRR`、`WRR` → `SAI_SCHEDULING_TYPE_WRR`。`meter_type` も同様に SAI enum に変換される。

### Phase 7: 条件付き登録 (add_manager 条件)

QosOrch は常時登録し `SCHEDULER` テーブルを無条件購読する。`SCHEDULER` が `QUEUE.scheduler` から参照されている場合のみ SAI キューオブジェクトに scheduler profile が bind される。

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `QosOrch` | `type==STRICT` | `SAI_SCHEDULING_TYPE_STRICT` + weight 属性なし | `qosorch.cpp` |
| `QosOrch` | `type==DWRR` | `SAI_SCHEDULING_TYPE_DWRR` + weight 属性設定 | `qosorch.cpp` |
| `QosOrch` | `type==WRR` | `SAI_SCHEDULING_TYPE_WRR` + weight 属性設定 | `qosorch.cpp` |
| `QosOrch` | `meter_type==bytes` | `SAI_METER_TYPE_BYTES` | `qosorch.cpp` |
| `QosOrch` | `meter_type==packets` | `SAI_METER_TYPE_PACKETS` | `qosorch.cpp` |
| `QosOrch` | `cir` / `cbs` / `pir` / `pbs` フィールドあり | SAI rate/burst 属性を設定 | `qosorch.cpp` |
| `QosOrch` | del_handler | SAI scheduler profile を削除、QUEUE 参照を解除してから削除 | `qosorch.cpp` |

> **スキャン証跡**: `SCHEDULER` は SAI scheduler profile の属性マッピング。`type` フィールドで SAI enum を決定する主要分岐あり。CONFIG_DB 内フィールド間の自動付与はなし。

<!-- /handler-branching -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **orchagent / QosOrch**: `SCHEDULER` テーブルを `SubscriberStateTable` で購読。

### 段階 2: CFG → APPL 翻訳

- QosOrch がスケジューラタイプ (`STRICT`, `WRR`, `DWRR`) と重み/優先度を解析。
- APP_DB への書き込みなし。

### 段階 3: APPL → SAI

- QosOrch が `sai_scheduler_api->create_scheduler()` を呼び出して SAI スケジューラオブジェクトを作成。
- QUEUE テーブルからの参照で各キューに適用。

### 段階 4: タイミング + 副作用

- スケジューラ作成後、QUEUE テーブルが参照するときに即時キューに適用。
- 副作用: STRICT スケジューラが高優先度キューを飽和させると低優先度が枯渇 (starvation)。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

SCHEDULER テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config qos reload` — sonic-cfggen が `files/build_templates/qos_config.j2` を展開し SCHEDULER エントリを生成 (sonic-buildimage/files/build_templates/qos_config.j2)

### minigraph / sonic-cfggen

minigraph.py に SCHEDULER 直接生成なし — `qos_config.j2` テンプレート経由

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での SCHEDULER マイグレーションなし

### ビルド時デフォルト (build-time default)

各プラットフォームの `qos.json.j2` に SCHEDULER エントリが定義され、ビルド時に投入

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`SCHEDULER` プロファイルは CONFIG_DB 上では独立したエントリだが、`QosOrch` の
`resolveFieldRefValue` 機構を通じて以下のテーブルから**暗黙的に leafref 参照**される。
YANG leafref として明示されていない参照もコードレベルで強制される。

### SCHEDULER を参照するテーブル (被参照)

| 参照元テーブル | 参照元フィールド | 参照先キー形式 | SAI 効果 | 参照箇所 |
|---|---|---|---|---|
| `QUEUE` | `scheduler` | `SCHEDULER\|<name>` | `SAI_QUEUE_ATTR_SCHEDULER_PROFILE_ID` バインド | `qosorch.cpp:1822-1853` |
| `PORT_QOS_MAP` | `scheduler` | `SCHEDULER\|<name>` | `SAI_PORT_ATTR_QOS_SCHEDULER_PROFILE_ID` バインド | `qosorch.cpp:2124-2133` |

### 解決タイミングと retry 挙動

- `QUEUE.scheduler` または `PORT_QOS_MAP.scheduler` が SET された時点で `SCHEDULER|<name>` が
  未存在の場合、`task_need_retry` が返され参照が解決されるまで SAI バインドは保留される。
- 参照が解決された後、`setObjectReference()` で参照カウントが増加し、被参照中の SCHEDULER は
  DEL ハンドラで削除保留 (`m_pendingRemove = true`) となる。

### WRED_PROFILE との連携

- `QUEUE` は `scheduler` と `wred_profile` フィールドを並列に解決する (`qosorch.cpp:1857-1886`)。
  SCHEDULER (帯域制御) と WRED_PROFILE (ドロップ確率制御) は互いに独立だが、同一 QUEUE に
  同時適用することで帯域制御と輻輳回避を組み合わせることができる。
- SCHEDULER と WRED_PROFILE の間に直接の参照関係はない。

### 削除順序制約

```
QUEUE の scheduler / PORT_QOS_MAP の scheduler 参照を解除
  ↓
SCHEDULER|<name> を DEL
```

参照が残っている間は SAI レベルで EBUSY となり `Failed to remove scheduler profile` エラーが発生する。
<!-- /cross-refs -->

<!-- glossary-links-injected: 96667c52d98d -->
