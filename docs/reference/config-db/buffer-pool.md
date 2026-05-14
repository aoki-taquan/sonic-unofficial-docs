---
title: BUFFER_POOL テーブル
description: "BUFFER_POOL テーブル — ASIC 上の共有 / 専用バッファプールを CONFIG_DB で定義するテーブル。BUFFER_PROFILE.pool から leafref で参照される。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-buffer-pool.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - BUFFER_POOL
    - BUFFER_PROFILE
    - DEVICE_METADATA
  cli:
    - config buffer
  yang:
    - sonic-buffer-pool
hard: 0
---

# BUFFER_POOL テーブル

## 概要

ASIC 上の共有 / 専用バッファプールを [CONFIG_DB](../../reference/glossary.md#term-config_db) で定義するテーブル。`BUFFER_PROFILE.pool` から leafref で参照される。`bufferorch` ([orchagent](../../reference/glossary.md#term-orchagent)) または `buffermgrd` (dynamic buffer model) が [CONFIG_DB](../../reference/glossary.md#term-config_db) を購読し、[SAI](../../reference/glossary.md#term-sai) BUFFER_POOL に変換する[^1]。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>BUFFER_POOL")]
  DM["buffermgrd"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_BUFFER_POOL_TABLE")]
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

```text
BUFFER_POOL|<name>
```

慣用名: `ingress_lossless_pool`、`ingress_lossy_pool`、`egress_lossless_pool`、`egress_lossy_pool`。

## 主要フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `type` | enum `ingress`/`egress`/`both` | yes | プールの方向 |
| `mode` | enum `static`/`dynamic` | yes | 閾値モード |
| `size` | uint64 (bytes) | no | プールサイズ。`percentage` と排他 |
| `xoff` | uint64 (bytes) | no (default 0) | xoff 閾値 (lossless ingress 用) |
| `percentage` | uint8 | no | 利用可能バッファに対する割合 (dynamic buffer model 限定) |

## 制約

- `percentage` は `size` と同時設定できない (`must` 制約)
- `percentage` は `DEVICE_METADATA.localhost.buffer_model = 'dynamic'` のときのみ有効

## 購読者

- **traditional buffer model**: `orchagent` の `BufferOrch`
- **dynamic buffer model**: `buffermgrd` (`docker-swss`) が [CONFIG_DB](../../reference/glossary.md#term-config_db) → [APPL_DB](../../reference/glossary.md#term-appl_db) に展開し、`bufferorch` が [SAI](../../reference/glossary.md#term-sai) 反映
- ベンダ固有のテンプレ (`buffers_*.json.j2`) でハードウェア依存初期値が生成される

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `BUFFER_PROFILE`、`BUFFER_PG`、`BUFFER_QUEUE`、`DEVICE_METADATA`
- 関連 CLI: `config buffer`、`mmuconfig`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-buffer-pool`、`sonic-buffer-profile`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-buffer-pool`](../yang/sonic-buffer-pool.md)
- CLI: [`config buffer`](../cli/config-buffer.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-buffer-pool.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-buffer-pool.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `BUFFER_POOL|<pool-name>` (`ingress_lossless_pool` / `egress_lossless_pool` / `egress_lossy_pool` 等)。
- `size`: ASIC 別の SDK 値（例 100G TOR で `12766208`）。
- `type`: `ingress` / `egress`。
- `mode`: `dynamic` / `static`。

### よくある誤設定

- `size` を ASIC 上限超過で入れると bufferorch が `SAI_STATUS_NO_MEMORY` を返し、すべての buffer 設定が止まる。
- `mode: dynamic` を ASIC 未対応のまま使うと [PFC](../../reference/glossary.md#term-pfc) で head-of-line を起こす。`traditional` プラットフォームでは `static`。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'BUFFER_POOL|ingress_lossless_pool'
show buffer pool
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `type` (enum: `ingress`/`egress`/`both`)

| 値 | SAI 属性 | 備考 |
|----|---------|------|
| `ingress` | `SAI_BUFFER_POOL_TYPE_INGRESS` | ingress 方向のみ。`xoff` 設定は ingress pool でのみ有効 |
| `egress` | `SAI_BUFFER_POOL_TYPE_EGRESS` | egress 方向のみ |
| `both` | `SAI_BUFFER_POOL_TYPE_BOTH` | 双方向プール (一部 ASIC のみ) |

`bufferorch.cpp:443-453` で SAI API に渡される。

### `mode` (enum: `static`/`dynamic`)

| 値 | SAI 属性 | 動作モード | `percentage` フィールド |
|----|---------|-----------|----------------------|
| `static` | `SAI_BUFFER_POOL_THRESHOLD_MODE_STATIC` | `size` (bytes) で固定閾値 | 無効 |
| `dynamic` | `SAI_BUFFER_POOL_THRESHOLD_MODE_DYNAMIC` | Alpha 値で動的閾値 | 有効 (`DEVICE_METADATA.buffer_model=dynamic` のとき) |

`bufferorch.cpp:474-480` で SAI API に渡される。

### `type` × `mode` の組み合わせと `xoff`

| type | mode | `xoff` | 典型 pool 名 |
|------|------|--------|-------------|
| `ingress` | `static` | 有効 (lossless 用) | `ingress_lossless_pool` |
| `ingress` | `dynamic` | 無効 | `ingress_lossy_pool` |
| `egress` | `static` | 無効 | `egress_lossless_pool` |
| `egress` | `dynamic` | 無効 | `egress_lossy_pool` |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| 条件 | 挙動 | ソース |
|------|------|--------|
| `xoff` フィールドが `ingress_lossless_pool` 以外のプールに設定 | `Field xoff is supported for %s only` を LOG_ERROR → xoff は ignored、他フィールドは処理 | `buffermgrdyn.cpp` L2625 |
| `xoff` 値が MMU サイズを超過 | `Invalid xoff %s, exceeding the mmu size` を LOG_ERROR → xoff 無視、pool size は更新 | `buffermgrdyn.cpp` L757 |
| SHP 設定が変化なし | `updated without change, skipped` → APPL_DB への書き込みをスキップ | `buffermgrdyn.cpp` L2614 |
| 同一 pool に複数の zero profile 登録 | `Multiple zero profiles detected for pool %s, takes the former and ignores the latter` を LOG_ERROR | `buffermgrdyn.cpp` L338 |
| Buffer pools が未準備の状態でプロファイル設定 | `pending` → プロファイル適用を遅延 | `buffermgrdyn.cpp` L894 |
| 共有バッファプールが未設定 | headroom 計算をスキップ (`No shared buffer pool configured`) | `buffermgrdyn.cpp` L684 |
| `task_invalid_entry` (static モード main loop) | `Failed to process invalid entry, drop it` → エントリを破棄 | `buffermgr.cpp` L585 |
| 既存プロファイルが存在する場合の pool 作成 | `// check if profile already exists - if yes - skip creation` | `buffermgr.cpp` L246 |
<!-- /cdb-exceptions -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`buffermgrd` / `buffermgrdyn` → `BufferOrch` (APPL_DB 経由) が CONFIG_DB の `BUFFER_POOL` テーブルを購読する。

`BUFFER_POOL` は `ingress_lossless_pool` / `egress_lossy_pool` 等の名前付きプール。

### 段階 2 — CFG→APPL 翻訳

`APP_BUFFER_POOL_TABLE` に書き込み

### 段階 3 — APPL→SAI

`sai_buffer_api` — `sai_create_buffer_pool` でバッファプール (ingress/egress, static/dynamic) を作成/更新

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `buffermgrd(yn)` が検知後 APPL_DB に書き込み。`BufferOrch` が SAI pool オブジェクトを作成/更新。既存プールの size 変更は即時反映。

**副作用**: プールサイズ変更はそのプールを参照するすべてのプロファイルの実効バッファ量に影響。`xoff` 変更は PFC threshold に影響する。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `BUFFER_POOL`

### CLI
- `config buffer pool add/del <name> ...`
  - ソース: `sonic-utilities/config/main.py (buffer グループ)`

### minigraph / sonic-cfggen
- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `buffers_config.j2` テンプレートからプラットフォーム別プールが生成

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- Dynamic buffer model では `buffermgrd` がプールサイズを自動調整
<!-- /entry-points -->


<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 値による他フィールド自動派生

| 条件 | 派生先 | evidence |
|---|---|---|
| DB 移行: 旧 DB の BUFFER_POOL エントリのフィールド区切り文字を更新 | `BUFFER_POOL` のフィールド値を新形式に変換 | `sonic-utilities/scripts/db_migrator.py:447` |
| Dynamic buffer model: `size` フィールドが未指定 | `bufferPool.dynamic_size = true` → buffermgrd がプールサイズを動的計算して APPL_DB へ書き込む | `sonic-swss/cfgmgr/buffermgrdyn.cpp:2525,2534` |

### Phase 7: 条件付き module/manager 登録

| 条件 | 登録 module | evidence |
|---|---|---|
| 常時（条件なし） | `BufferMgrDynamic` が `BUFFER_POOL` を `handleBufferPoolTable` に登録 | `sonic-swss/cfgmgr/buffermgrdyn.cpp:443` |

### grep カバレッジ

- buffermgrdyn.cpp L443: BUFFER_POOL ハンドラ登録（条件なし）
- buffermgrdyn.cpp L2525/2534: dynamic_size フラグ分岐
<!-- /derivation -->
<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Manager / Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `BufferMgrDynamic` | `handleBufferPoolTable()` | `op == SET_COMMAND` かつ `size` フィールドなし | `dynamic_size = true` → プールサイズを動的計算モードで APPL_DB へ書き込む | `sonic-swss/cfgmgr/buffermgrdyn.cpp:2525` |
| `BufferMgrDynamic` | `handleBufferPoolTable()` | `size` フィールドあり | `dynamic_size = false` → 指定サイズをそのまま APPL_DB へ書き込む | `sonic-swss/cfgmgr/buffermgrdyn.cpp:2534` |
| `BufferMgrDynamic` | `handleBufferPoolTable()` | `xoff` フィールドあり（SHP 設定） | Shared Headroom Pool サイズを計算・更新 | `sonic-swss/cfgmgr/buffermgrdyn.cpp:2539` |
| `BufferMgrDynamic` | `handleBufferPoolTable()` | `op == DEL_COMMAND` | プールを APPL_DB から削除し内部キャッシュを更新 | `sonic-swss/cfgmgr/buffermgrdyn.cpp:2634` |

> **スキャン証跡**: `handleBufferPoolTable` L2509-2669 全行読了。dynamic_size フラグと SHP xoff フィールド有無が核心分岐。4 件抽出。
<!-- /handler-branching -->
<!-- glossary-links-injected: 44ea702536a5 -->
