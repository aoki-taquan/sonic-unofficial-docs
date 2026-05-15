---
title: APPL_DB BUFFER_* テーブル群
description: "APPL_DB の BUFFER_POOL_TABLE / BUFFER_PROFILE_TABLE / BUFFER_PG_TABLE / BUFFER_QUEUE_TABLE / BUFFER_PORT_*_PROFILE_LIST_TABLE — buffermgrd が CONFIG_DB から変換して書き込み、bufferorch が SAI へ反映するバッファ関連テーブル群。"
area: reference
verification: code-verified
last_verified: 2026-05-15
hard: 0
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/bufferorch.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/bufferorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: cfgmgr/buffermgrdyn.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
related:
  config_db:
    - BUFFER_POOL
    - BUFFER_PROFILE
    - BUFFER_PG
    - BUFFER_QUEUE
    - BUFFER_PORT_INGRESS_PROFILE_LIST
    - BUFFER_PORT_EGRESS_PROFILE_LIST
  cli:
    - config buffer
    - show buffer
  yang:
    - sonic-buffer-pool
    - sonic-buffer-profile
---

# APPL_DB BUFFER_* テーブル群

## 概要

[APPL_DB](../../reference/glossary.md#term-appl_db) 上のバッファ関連テーブル群。[CONFIG_DB](../../reference/glossary.md#term-config_db) の `BUFFER_POOL` / `BUFFER_PROFILE` / `BUFFER_PG` / `BUFFER_QUEUE` / `BUFFER_PORT_*_PROFILE_LIST` テーブルを `buffermgrd`（`buffermgrdyn` または `buffermgr`）が変換・展開して書き込む。`orchagent` の `BufferOrch` がこれを購読し、[SAI](../../reference/glossary.md#term-sai) `sai_buffer_api` を通じてハードウェアに反映する[^buforch]。

テーブル名定数は `sonic-swss-common/common/schema.h` に定義される[^schema]。

## テーブル一覧

| APPL_DB テーブル名 | 定数名 | 対応 CONFIG_DB テーブル |
|-------------------|--------|------------------------|
| `BUFFER_POOL_TABLE` | `APP_BUFFER_POOL_TABLE_NAME` | `BUFFER_POOL` |
| `BUFFER_PROFILE_TABLE` | `APP_BUFFER_PROFILE_TABLE_NAME` | `BUFFER_PROFILE` |
| `BUFFER_PG_TABLE` | `APP_BUFFER_PG_TABLE_NAME` | `BUFFER_PG` |
| `BUFFER_QUEUE_TABLE` | `APP_BUFFER_QUEUE_TABLE_NAME` | `BUFFER_QUEUE` |
| `BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE` | `APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME` | `BUFFER_PORT_INGRESS_PROFILE_LIST` |
| `BUFFER_PORT_EGRESS_PROFILE_LIST_TABLE` | `APP_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME` | `BUFFER_PORT_EGRESS_PROFILE_LIST` |

## データフロー

```mermaid
flowchart LR
  CFGDB[("CONFIG_DB\nBUFFER_*")]
  MGRD["buffermgrd\n(buffermgrdyn/buffermgr)"]
  CFGDB --> MGRD
  APPLDB[("APPL_DB\nBUFFER_*_TABLE")]
  MGRD --> APPLDB
  ORCH["bufferorch"]
  APPLDB --> ORCH
  SAI["SAI\nsai_buffer_api"]
  ORCH --> SAI
```

## key 構造

```text
BUFFER_POOL_TABLE|<pool-name>
BUFFER_PROFILE_TABLE|<profile-name>
BUFFER_PG_TABLE|<port-name>|<pg-range>
BUFFER_QUEUE_TABLE|<port-name>|<queue-range>
BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE|<port-name>
BUFFER_PORT_EGRESS_PROFILE_LIST_TABLE|<port-name>
```

VoQ スイッチ環境では `BUFFER_PG_TABLE` / `BUFFER_QUEUE_TABLE` のキーが 4 トークン形式になる（`<hostname>|<asic>|<port>|<range>`）。

## 主要フィールド

### BUFFER_POOL_TABLE

| フィールド | 型 | 省略条件 | 説明 |
|-----------|---|---------|------|
| `type` | enum `ingress`/`egress` | 常に書き込み | プールの方向。`both` は `BUFFER_EGRESS` に折り畳まれる（後述） |
| `mode` | enum `static`/`dynamic` | 常に書き込み | 閾値モード |
| `size` | uint64 (bytes) | dynamic_size 条件成立時スキップ | プールサイズ。Lua plugin が後から書き込む場合がある |
| `xoff` | uint64 (bytes) | SHP 未設定時省略 | Shared Headroom Pool サイズ |

### BUFFER_PROFILE_TABLE

| フィールド | 型 | 省略条件 | 説明 |
|-----------|---|---------|------|
| `pool` | string | 常に書き込み | 参照プール名 |
| `size` | uint64 (bytes) | 常に書き込み | reserved バッファサイズ |
| `xon` | uint64 (bytes) | lossy profile は省略 | XON 閾値 |
| `xon_offset` | uint64 (bytes) | 値が空のとき省略 | XON オフセット |
| `xoff` | uint64 (bytes) | lossy profile は省略 | XOFF 閾値 |
| `dynamic_th` | int8 | `static_th` と排他 | dynamic threshold (alpha 値) |
| `static_th` | uint64 (bytes) | `dynamic_th` と排他 | static threshold |
| `headroom_type` | string | CONFIG_DB からの転写時のみ | bufferorch で無視（SAI 非反映） |
| `packet_discard_action` | string `drop`/`trim` | 値が空のとき省略 | パケット廃棄アクション |

### BUFFER_PG_TABLE / BUFFER_QUEUE_TABLE

| フィールド | 型 | 省略条件 | 説明 |
|-----------|---|---------|------|
| `profile` | string (profile 名) | 常に書き込み | 参照プロファイル名 |

### BUFFER_PORT_INGRESS/EGRESS_PROFILE_LIST_TABLE

| フィールド | 型 | 省略条件 | 説明 |
|-----------|---|---------|------|
| `profile_list` | string (カンマ区切り) | 常に書き込み | 適用プロファイルリスト |

## 購読者

- **`buffermgrdyn`** (`docker-swss`): dynamic buffer model 時に CONFIG_DB を変換して APPL_DB に書き込む
- **`buffermgr`** (`docker-swss`): static buffer model 時（pass-through に近い）
- **`BufferOrch`** (`orchagent`): APPL_DB を購読して SAI に反映

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `BUFFER_POOL`、`BUFFER_PROFILE`、`BUFFER_PG`、`BUFFER_QUEUE`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-buffer-pool`、`sonic-buffer-profile`
- 関連 CLI: `config buffer`、`show buffer pool`、`show buffer profile`

<!-- defaults -->
## コード由来の暗黙デフォルト / 実装乖離 (Phase A)

### `type=both` — buffermgrdyn が内部で `BUFFER_EGRESS` に折り畳む (乖離)

`buffermgrdyn.cpp` L2544-2549:

```cpp
if (value == buffer_value_ingress)
    bufferPool.direction = BUFFER_INGRESS;
else
    bufferPool.direction = BUFFER_EGRESS;  // "both" はここに落ちる
```

APPL_DB に書き込まれる `type` フィールドは raw 文字列（`"both"`）をそのまま転写するため [SAI](../../reference/glossary.md#term-sai) 側には `SAI_BUFFER_POOL_TYPE_BOTH` が届く。しかし buffermgrdyn の内部キャッシュは `BUFFER_EGRESS` として扱うため、headroom 計算では ingress 側プールとして参照されない可能性がある。

### `size` (BUFFER_POOL_TABLE) — dynamic_size 時は Lua plugin へサイレント委譲

`buffermgrdyn.cpp` L2525/2534: `size` フィールドが CONFIG_DB に存在しない場合、`bufferPool.dynamic_size = true` を立て APPL_DB への書き込みを遅延する。実効サイズは Mellanox/Barefoot の Lua plugin (`buffer_pool_<platform>.lua`) が MMU 使用量から逆算して書き込む。さらに `ingress_lossless_pool` において `overSubscribeRatio` 非ゼロかつ SHP が size で有効でない場合、`dontUpdatePoolToDb=true` となり直接書き込みが完全にスキップされる (`buffermgrdyn.cpp` L2555-2628)。

### `xoff` (BUFFER_POOL_TABLE) — 省略 = 0 相当

`updateBufferPoolToDb()` (L878-879): `pool.xoff.empty()` のとき `xoff` フィールドを APPL_DB に書き込まない。`bufferorch.cpp` はフィールド不在を SHP なしと解釈し、`publishSHPSize()` を呼ばない (L549-554)。

### `xon` / `xoff` (BUFFER_PROFILE_TABLE) — lossy profile では APPL_DB に存在しない

`updateBufferProfileToDb()` (L903-910): `profile.lossless == false` のとき `xon`、`xon_offset`、`xoff` フィールドを書き込まない。bufferorch は `xoff` フィールドの有無でロスレス判定を行う (L851)。

### `xon_offset` (BUFFER_PROFILE_TABLE) — 省略 = ASIC デフォルト

`xon_offset` が空文字列のとき APPL_DB に書き込まれない (L906-908)。bufferorch はフィールド不在を無視するため SAI の `SAI_BUFFER_PROFILE_ATTR_XON_OFFSET_TH` は設定されない。

### `headroom_type` (BUFFER_PROFILE_TABLE) — bufferorch で dead field (乖離)

`bufferorch.cpp` L748-752:

```cpp
else {
    SWSS_LOG_ERROR("Unknown buffer profile field specified:%s, ignoring", field.c_str());
    continue;
}
```

`headroom_type` は `else` 分岐に落ちて `LOG_ERROR` + skip される。CONFIG_DB / YANG には定義があるが SAI 経路では完全に無視される。

### `dynamic_th` / `static_th` — threshold type が create-only (乖離)

`bufferorch.cpp` L692-713: SAI オブジェクトが既存の場合（プロファイル更新時）、`SAI_BUFFER_PROFILE_ATTR_THRESHOLD_MODE` の書き込みをスキップする（LOG_INFO のみ）。threshold 値 (`SHARED_DYNAMIC_TH` / `SHARED_STATIC_TH`) 自体は更新されるが、モード切り替え（`dynamic_th` → `static_th` の変更など）は SAI に反映されない。

### threshold_mode 自動決定

`updateBufferProfileToDb()` L901:

```cpp
const string &&mode = profile.threshold_mode.empty() ? getPgPoolMode() + "_th" : profile.threshold_mode;
```

threshold_mode が未設定のとき、ingress_lossless_pool の `mode` フィールド (`"dynamic"` / `"static"`) に `"_th"` を付加した値 (`"dynamic_th"` / `"static_th"`) を自動採用する。CONFIG_DB に `dynamic_th` / `static_th` フィールドを明示していない場合でも、APPL_DB にはどちらかが必ず書き込まれる。

### `packet_discard_action` (BUFFER_PROFILE_TABLE) — 省略 = drop 相当

フィールドが APPL_DB に存在しない場合、bufferorch は SAI 属性を設定しない（= ASIC デフォルト動作 = パケット DROP）。`"trim"` を設定した場合のみ `SAI_BUFFER_PROFILE_PACKET_ADMISSION_FAIL_ACTION_DROP_AND_TRIM` が渡る (L730-744)。

### `profile` (BUFFER_PG_TABLE / BUFFER_QUEUE_TABLE) — 不在時は retry

`bufferorch.cpp:processPriorityGroup()` / `processQueue()`: `profile` フィールドが不在または参照先プロファイルが未登録の場合 `task_need_retry` を返す。ゼロプロファイル（名前に `_zero_` を含む）は flex counter の追加をスキップする (L995)。

### 書き込みルート別フィールド扱い早見表

| フィールド | buffermgrdyn (dynamic) | buffermgr (static) | bufferorch (SAI) |
|-----------|----------------------|-------------------|-----------------|
| BUFFER_POOL: `type` | raw 転写 (`both`→内部 EGRESS) | pass-through | SAI create-only |
| BUFFER_POOL: `mode` | raw 転写 | pass-through | SAI create-only |
| BUFFER_POOL: `size` | dynamic_size フラグ制御 | pass-through | `SAI_BUFFER_POOL_ATTR_SIZE` |
| BUFFER_POOL: `xoff` | SHP 計算結果 (空なら省略) | pass-through | `SAI_BUFFER_POOL_ATTR_XOFF_SIZE` |
| BUFFER_PROFILE: `pool` | `pool_name` から転写 | pass-through | SAI create-only |
| BUFFER_PROFILE: `size` | Lua 計算値 or 指定値 | pass-through | `SAI_BUFFER_PROFILE_ATTR_BUFFER_SIZE` |
| BUFFER_PROFILE: `xon` | lossless のみ | pass-through | `SAI_BUFFER_PROFILE_ATTR_XON_TH` |
| BUFFER_PROFILE: `xoff` | lossless のみ | pass-through | `SAI_BUFFER_PROFILE_ATTR_XOFF_TH` |
| BUFFER_PROFILE: `headroom_type` | 転写のみ | pass-through | LOG_ERROR + skip |
| BUFFER_PROFILE: `dynamic_th` | 自動決定 or 指定値 | pass-through | mode は create-only、値は更新可 |

> **証跡**: `bufferorch.h` L18-35 全行読了、`bufferorch.cpp` L391-1000 全行読了、`buffermgrdyn.cpp` L870-960 全行読了、`schema.h` BUFFER 定数確認済み。
<!-- /defaults -->

<!-- failure -->
## 失敗・retry 挙動 (Phase D)

`BufferOrch::doTask()` (`bufferorch.cpp` L2096-2129) は per-table handler が返す `task_process_status` を一括処理する。ステータスごとの最終挙動は以下のとおり[^buforch]。

| ステータス | doTask の動作 | 残タスク処理 | ログ |
|---|---|---|---|
| `task_success` / `task_ignore` | `m_toSync` から該当エントリを erase | 次タスクへ継続 | なし |
| `task_invalid_entry` | erase | 次タスクへ継続 | `LOG_ERROR ("Failed to process invalid buffer task")` |
| `task_failed` | erase | **その回の doTask を `return` で打ち切り** | `LOG_ERROR ("Failed to process buffer task, drop it")` |
| `task_need_retry` | erase せず `it++` で次回まで保留 | 次タスクへ継続 | `LOG_INFO ("Failed to process buffer task, retry it")` |
| handler 未登録 | erase | 次タスクへ継続 | `LOG_ERROR ("No handler for key:%s found")` |

> `task_failed` のみ doTask 関数全体を return で抜けるため、後続のキューイング済みタスクは次回ディスパッチまで処理されない。`task_invalid_entry` は LOG レベルが ERROR でも処理続行する点に注意。

### 主要 handler ごとの retry / failed 条件

| handler | retry になる条件 (`task_need_retry`) | failed になる条件 (`task_failed`) |
|---|---|---|
| `processBufferPool()` (L391-596) | 削除対象 pool が pending-remove / 削除対象 pool が他オブジェクト参照中 / SAI 一時エラー (`handleSaiSetStatus` 経由) | — (SAI 致命系のみ) |
| `processBufferProfile()` (L602-888) | 削除対象 profile が pending-remove / `pool` 参照が `not_resolved` (= pool 未登録) / PG・Queue から参照中 | `pool` 参照 resolve その他失敗 / 数値フィールドのパース失敗 / `packet_discard_action` が `drop`/`trim` 以外 |
| `processQueue()` (L914-1233) | `profile` 参照 `not_resolved` (= profile 未登録) / queue がロック中 (`LOG_WARN "...is locked, will retry"`, L1068-1070) | `profile` 参照 resolve その他失敗 |
| `processPriorityGroup()` (L1305-1495) | `profile` 参照 `not_resolved` | `profile` resolve その他失敗 / 参照 profile が **trimming-eligible** (`SAI_BUFFER_PROFILE_PACKET_ADMISSION_FAIL_ACTION_DROP_AND_TRIM` を持つ profile を PG に貼ろうとした場合、L1382-1388) |
| `processIngressBufferProfileList()` (L1663-) / `processEgressBufferProfileList()` (L1845-) | profile-list 内のいずれかの profile が `not_resolved` | profile-list resolve その他失敗 / list 内に trimming-eligible profile 混在 |

### handler 内の特殊な 2 段 retry (profile only)

`processBufferProfile()` L778-797 では、`sai_set_buffer_profile_attribute()` が失敗した場合に **bufferorch 自身が同じ attr で SAI をもう一度呼ぶ**:

```cpp
SWSS_LOG_NOTICE("Unable to modify buffer profile, ... will retry one more time", ...);
sai_status = sai_buffer_api->set_buffer_profile_attribute(sai_object, &attribute);
if (SAI_STATUS_SUCCESS != sai_status) {
    SWSS_LOG_ERROR("Failed to modify buffer profile, ... will retry once", ...);
    handle_status = handleSaiSetStatus(SAI_API_BUFFER, sai_status);
    ...
}
```

これは `task_need_retry` での次回 doTask 待ちとは別のループ内 retry で、SAI ベンダ実装の transient エラー吸収用。`processBufferPool()` 側にはこの即時 retry はなく、初回失敗で即 `handleSaiSetStatus()` に委譲する (L513-521)。

### SAI 失敗の共通変換: `handleSaiSetStatus` / `handleSaiCreateStatus` / `handleSaiRemoveStatus`

bufferorch は SAI 戻り値を直接 enum 化せず、`orch.cpp` 共通の `handleSai*Status()` を経由する。これらは `SAI_STATUS_SUCCESS` 以外を retry/failed/ignore/abort のいずれかに翻訳する。`SAI_STATUS_ATTR_NOT_IMPLEMENTED_0` のみ bufferorch 側で先取りして `task_ignore` を返す (L508-512 / L773-777)。

### 致命的でないが LOG_WARN を出す経路

| 条件 | 挙動 | evidence |
|---|---|---|
| queue ロック中 | `task_need_retry` + `LOG_WARN ("Queue %zd on port %s is locked, will retry")` | `bufferorch.cpp:1068-1070` |
| port link-up 後に queue/PG プロファイルを適用 | handler は処理続行 (警告のみ) | `bufferorch.cpp:1220-1227` |

### 入力検証で `task_invalid_entry` になる主なケース

- `type` が `ingress`/`egress` 以外 (`processBufferPool`, L457)
- `mode` が `static`/`dynamic` 以外 (`processBufferPool`, L484)
- key トークン数違反 (queue: 2 or 4, PG: 2, L920/L944/L1322)
- port alias 未登録 (`processQueue` L1035 / profile-list L1113)
- voq/queue index 範囲外 (L1053-1064)
- op が SET/DEL 以外 (L593, L885, L1013, L1188)

### 詳細マトリクス

handler ごと・行番号付きの完全な失敗・retry 分岐マトリクス、ディスパッチャ挙動表、grep カバレッジは中間ファイル参照:

- `meta/_intermediate/cdb-flow/appl-buffer-failure.md`

> **証跡**: `bufferorch.cpp` 全 2138 行のうち、`task_need_retry` × 12 / `task_failed` × 10 / `task_invalid_entry` × 17 / `task_ignore` × 3 / `handleSai*Status` × 9 hit を全件確認。`doTask()` の switch 句 (L2107-2128) も精読。

<!-- /failure -->

## 引用元

[^buforch]: `bufferorch.cpp` — `processBufferPool()` / `processBufferProfile()` / `processPriorityGroup()` / `processQueue()`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/bufferorch.cpp>

[^schema]: `sonic-swss-common/common/schema.h` — `APP_BUFFER_*_TABLE_NAME` 定数. <https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/schema.h>
