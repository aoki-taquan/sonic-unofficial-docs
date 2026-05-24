---
title: BUFFER_PG テーブル
description: "BUFFER_PG テーブル — ポートの ingress バッファ Priority Group (PG) ごとにどの BUFFER_PROFILE を割り当てるかを保持する。lossless トラフィックの xon/xoff 閾値、PFC 動作の根本となる設定。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-buffer-pg.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - BUFFER_PG
    - BUFFER_PROFILE
    - PORT
  cli: []
  yang:
    - sonic-buffer-pg
hard: 0
---

# BUFFER_PG テーブル

## 概要

ポートの ingress バッファ [Priority Group](../../reference/glossary.md#term-priority-group) (PG) ごとにどの BUFFER_PROFILE を割り当てるかを保持する[^1]。lossless トラフィックの xon/xoff 閾値、[PFC](../../reference/glossary.md#term-pfc) 動作の根本となる設定。`buffermgrd` が [APPL_DB](../../reference/glossary.md#term-appl_db) に転送、`orchagent` `BufferOrch` が [SAI](../../reference/glossary.md#term-sai) ingress PG buffer profile を設定する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>BUFFER_PG")]
  DM["buffermgrd"]
  CDB --> DM
  APPDB[("APPL_DB<br/>APP_BUFFER_PG_TABLE")]
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
BUFFER_PG|<port>|<pg_num>
```

`<pg_num>` は `0..7` または `0-3` のような範囲表現を許す。

## フィールド一覧

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `port` (key) | leafref `PORT.name` | ✅ | - | 対象ポート |
| `pg_num` (key) | string `[0-7]((-)[0-7])?` | ✅ | - | PG 番号または範囲 |
| `profile` | leafref `BUFFER_PROFILE.name` または `NULL` | - | `0` (YANG 定義値、**実装上は dead field**。実効デフォルトは経路依存: Jinja2 静的=`ingress_lossy_profile`、Jinja2 動的=`NULL`、buffermgr=`pg_lossless_*_profile`) | 関連付ける buffer profile。`NULL` で削除扱い |

## 購読者

- `buffermgrd`: [APPL_DB](../../reference/glossary.md#term-appl_db) へ転送
- `orchagent` `BufferOrch`: [SAI](../../reference/glossary.md#term-sai) に PG buffer profile を反映

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `BUFFER_PROFILE`、`BUFFER_POOL`、`PORT`、`PFC_WD`
- 関連 CLI: なし（`config_db.json` でロード）
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-buffer-pg`

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

### フィールド別デフォルト・fallback 一覧

| フィールド | YANG default | 実装上の実効デフォルト | 経路 | evidence |
|-----------|-------------|----------------------|------|---------|
| `profile` | `0` (numeric) | **dead field** — 実装上一切使われない | — | `sonic-buffer-pg.yang:59` |
| `profile` (Jinja2 静的モード, PG 0) | — | `"ingress_lossy_profile"` | `buffers_config.j2` フォールバック分岐 | `buffers_config.j2:271-272` |
| `profile` (Jinja2 動的モード, PG 3-4) | — | `"NULL"` → pureDynamic fallback | `buffers_config.j2` + `buffermgrdyn.cpp` | `buffers_config.j2:266-268` |
| `profile` (buffermgr 静的モード, PG 3-4) | — | `"pg_lossless_<speed>_<cable>_profile"` (速度・ケーブル長から自動生成) | `buffermgr.cpp doSpeedUpdateTask()` | `buffermgr.cpp:183-184` |
| `dynamic_calculated` (pureDynamic) | — | `true` (profile 未指定時に暗黙設定) | `buffermgrdyn.cpp handleSingleBufferPgEntry()` | `buffermgrdyn.cpp:3194` |
| `lossless` (pureDynamic) | — | `true` (固定値) | 同上 | `buffermgrdyn.cpp:3195` |
| threshold (動的計算) | — | `m_defaultThreshold` = `DEFAULT_LOSSLESS_BUFFER_PARAMETER.default_dynamic_th` (Jinja2 デフォルト `"0"`) | `buffermgrdyn.cpp refreshPgsForPort()` | `buffermgrdyn.cpp:1521` |
| `admin_status` (暗黙) | — | `"down"` (PORT テーブルに無ければ `down` 扱い → PG 書き込み抑制) | `buffermgr.cpp doTask()` | `buffermgr.cpp:565` |

### 主要乖離・silent パターン

| パターン | 内容 | evidence |
|---------|------|---------|
| **dead field** | YANG `profile default 0` は実装で一切参照されない | `sonic-buffer-pg.yang:59` |
| **書き込み経路依存乖離** | Jinja2 静的: PG 0 → `ingress_lossy_profile`; Jinja2 動的: PG 3-4 → `NULL`; buffermgr 静的: `pg_lossless_*_profile` | 各経路 |
| **silent fallback** (動的 threshold) | profile 未指定の lossless PG は `default_dynamic_th` を threshold に使用 | `buffermgrdyn.cpp:1521` |
| **silent drop** (cable=0m) | ケーブル長 `0m` の lossless PG は [APPL_DB](../../reference/glossary.md#term-appl_db) から削除。WARN なし | `buffermgrdyn.cpp:1492-1509` |
| **silent skip** (PFC 未設定) | `PORT_QOS_MAP.pfc_enable` が未設定のポートは [BUFFER_PG](../../reference/glossary.md#term-buffer-pg) を書かずに `task_success` 返却 | `buffermgr.cpp:173-179` |
| **consumer 乖離** (egress reject) | egress profile を PG に設定すると `task_failed` drop — YANG 無制約、実装のみで enforcement | `buffermgrdyn.cpp:3156-3163` |
| **db_migrator silent overwrite** | 動的モード移行時に `profile` を `NULL` に強制書き換え | `db_migrator.py:398` |
| **admin down 書き込み抑制** | PORT admin down 時は APPL_DB 書き込みをスキップし内部状態のみ保持 | `buffermgrdyn.cpp:3198-3202` |

> 中間調査ファイル: `meta/_intermediate/cdb-flow/buffer-pg-defaults.md`

<!-- /defaults -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-buffer-pg`](../yang/sonic-buffer-pg.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-buffer-pg.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-buffer-pg.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `BUFFER_PG|<port>|<pg-range>` (例 `BUFFER_PG|Ethernet0|3-4`)。
- `profile`: `pg_lossless_100000_5m_profile` 等。

### よくある誤設定

- [PFC](../../reference/glossary.md#term-pfc) 対象 PG (`3-4`) に `lossy` profile を当てると [PFC](../../reference/glossary.md#term-pfc) が機能しない。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'BUFFER_PG|Ethernet0|*'
show buffer pg
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

このテーブルには enum フィールドはない。

### `profile` (leafref または `NULL`)

| 値 | 挙動 |
|----|------|
| `[BUFFER_PROFILE\|<name>]` | `buffermgrd` が対応プロファイルの xon/xoff/dynamic_th で PG を設定し APPL_DB に書く |
| `NULL` | PG の削除扱い。APPL_DB から該当エントリを削除し [SAI](../../reference/glossary.md#term-sai) が PG バッファを解放 |

### `pg_num` (key、範囲対応)

| 形式 | 挙動 |
|------|------|
| `0`〜`7` (単一値) | その PG 番号のみに適用 |
| `0-3` (範囲) | `buffermgrd` が範囲をパースして各 PG (0, 1, 2, 3) に個別に適用 |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| 条件 | 挙動 | ソース |
|------|------|--------|
| `profile` フィールドの参照形式が `[BUFFER_PROFILE\|name]` でない | `BUFFER_PG: Invalid format of reference to profile` → `task_invalid_entry` (drop) | `buffermgrdyn.cpp` L3133 |
| 参照プロファイルが未設定 | `Profile %s hasn't been configured yet, skip` → `task_need_retry` (再試行) | `buffermgrdyn.cpp` L3150 |
| `profile` 以外の不正フィールドが SET で到達 | `BUFFER_PG: Invalid field %s` → `task_invalid_entry` (drop) | `buffermgrdyn.cpp` L3180 |
| PG ID が `uint8_t` に変換不可 (std::invalid_argument) | その PG ID を silently skip | `buffermgr.cpp` L197 |
| speed / cable_length 組み合わせが lookup table に未定義 | `Unable to create/update PG profile` → `task_invalid_entry` | `buffermgr.cpp` L238 |
| admin down ポートでデフォルト以外のプロファイル設定時 | [BUFFER_PG](../../reference/glossary.md#term-buffer-pg) エントリを削除しない (`won't reclaim buffer`) | `buffermgr.cpp` L228 |
| ポートの `admin_status` が取得不可 | `assuming default down` として扱う | `buffermgr.cpp` L565 |
| zero buffer profile が pool に未設定でバッファ回収不可 | `Zero profile is not provided for pool %s` を LOG_ERROR | `buffermgrdyn.cpp` L381 |
| admin down ポートへの SET | APPL_DB 書き込みをスキップし内部状態のみ保持。ポート up 時に APPL_DB に反映 | `buffermgrdyn.cpp` L3202 |
<!-- /cdb-exceptions -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`buffermgrd` / `buffermgrdyn` → `BufferOrch` (APPL_DB 経由) が [CONFIG_DB](../../reference/glossary.md#term-config_db) の `BUFFER_PG` テーブルを購読する。

`BUFFER_PG` の key は `<port>|<pg_range>` (例: `Ethernet0|3-4`)。

### 段階 2 — CFG→APPL 翻訳

`APP_BUFFER_PG_TABLE` (`BUFFER_PG_TABLE`) に書き込み

### 段階 3 — APPL→SAI

`sai_buffer_api` — `sai_create_ingress_priority_group_attr` でポート毎の [PG (Priority Group)](../../reference/glossary.md#term-pg) バッファプロファイルを設定

### 段階 4 — タイミングと副作用

**適用タイミング**: [CONFIG_DB](../../reference/glossary.md#term-config_db) 変化を `buffermgrd(yn)` が検知後 APPL_DB に書き込み。`BufferOrch` が APPL_DB を購読して SAI call を発行。動的モードでは cable length / speed から自動計算。

**副作用**: PG バッファ変更は ingress traffic の一時的な pause/drop に影響する可能性がある。warm-reboot では既存バッファ設定が保持される。
<!-- /runtime-trace -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

`BUFFER_PG` テーブルの SET/DEL が CONFIG_DB に届くと、`buffermgrdyn` (cfgmgr) と `BufferOrch` ([orchagent](../../reference/glossary.md#term-orchagent)) は APPL_DB 以外に計 3 DB へ副次書き込みを行う。

### APPL_DB / `BUFFER_PROFILE_TABLE`

動的算出プロファイルが [BUFFER_PG](../../reference/glossary.md#term-buffer-pg) 参照により新規生成される場合に書き込む。

| トリガ | 操作 | evidence |
|--------|------|---------|
| `buffermgrdyn` が headroom 計算で新プロファイルを生成 (動的モード) | `m_applBufferProfileTable.set(name, fvVector)` | `buffermgrdyn.cpp:919` |
| 動的プロファイルが不要になった場合 (DEL) | `m_applBufferProfileTable.del(profileName)` | `buffermgrdyn.cpp:1047` |

### STATE_DB / `BUFFER_PROFILE_TABLE`

APPL_DB への書き込みと常に同時に発生する。

| トリガ | 操作 | evidence |
|--------|------|---------|
| 動的プロファイル生成 (SET) | `m_stateBufferProfileTable.set(name, fvVector)` | `buffermgrdyn.cpp:920` |
| 動的プロファイル削除 (DEL) | `m_stateBufferProfileTable.del(profileName)` | `buffermgrdyn.cpp:1049` |

!!! note "静的モード"
    `buffermgr.cpp`（静的バッファモード）は STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB への書き込みを行わない（走査結果 0 件）。

### COUNTERS_DB / `COUNTERS_PG_NAME_MAP` · `COUNTERS_PG_PORT_MAP` · `COUNTERS_PG_INDEX_MAP`

`BufferOrch::processPriorityGroupPost()` が SAI 適用成功後に `createPortBufferPgCounters()` を呼び出し、PG の OID マッピングを [COUNTERS_DB](../../reference/glossary.md#term-counters_db) に書き込む。

| トリガ | テーブル | 操作 | 条件 | evidence |
|--------|---------|------|------|---------|
| BUFFER_PG SET 成功（新規 PG） | `COUNTERS_PG_NAME_MAP` | `m_pgCounterNameMapUpdater->setCounterNameMap()` alias:index→OID | `isCreateOnlyConfigDbBuffers=true` かつ `getPgCountersState() \|\| getPgWatermarkCountersState()` | `portsorch.cpp:8937` |
| 同上 | `COUNTERS_PG_PORT_MAP` | `m_pgPortTable->set("", pgPortVector)` PG OID→port OID | 同上 | `portsorch.cpp:8938` |
| 同上 | `COUNTERS_PG_INDEX_MAP` | `m_pgIndexTable->set("", pgIndexVector)` PG OID→index | 同上 | `portsorch.cpp:8939` |
| BUFFER_PG DEL 成功 | 上記 3 テーブル | `delCounterNameMap` / `hdel` | 同上（旧 counter が存在した場合） | `portsorch.cpp:9081-9083` |

### FLEX_COUNTER_DB / PG drop・watermark stat グループ

`addPortBufferPgCounters()` からさらに flex counter ポーリング設定が [FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) に書き込まれる。

| トリガ | グループキー | 操作 | 条件 | evidence |
|--------|------------|------|------|---------|
| BUFFER_PG SET 成功（新規 PG） | `PG_DROP_STAT_COUNTER_FLEX_COUNTER_GROUP:<pg_oid>` | `pg_drop_stat_manager.setCounterIdList()` | `FlexCounterOrch::getPgCountersState()=true` | `portsorch.cpp:8995` |
| BUFFER_PG SET 成功（新規 PG） | `PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP:<pg_oid>` | `pg_watermark_manager.setCounterIdList()` | `FlexCounterOrch::getPgWatermarkCountersState()=true` | `portsorch.cpp:9051` |
| BUFFER_PG DEL 成功 | 上記グループ | `pg_drop_stat_manager.clearCounterIdList()` / `pg_watermark_manager.clearCounterIdList()` | 対応 counter が存在した場合 | `portsorch.cpp:9089,9095` |

> 中間調査ファイル: `meta/_intermediate/cdb-flow/buffer-pg-side.md`

<!-- /side-effects -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `BUFFER_PG`

### CLI
- `config interface buffer priority-group set <port> <pg-range> <profile>`
- `config interface buffer priority-group remove <port> <pg-range>`
  - ソース: `sonic-utilities/config/main.py (buffer グループ)`

### minigraph / sonic-cfggen
- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/[SONiC](../../reference/glossary.md#term-sonic) YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `sonic-cfggen` が `buffers_config.j2` テンプレートから初期バッファ PG マッピングを生成

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- Dynamic buffer model: `buffermgrd` が LOSSLESS_TRAFFIC_PATTERN を参照してポートごとに自動再計算・書き込み
<!-- /entry-points -->


<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 値による他フィールド自動派生

| 条件 | 派生先 | evidence |
|---|---|---|
| DB 移行: 旧 DB で `profile` が `pg_lossless_<speed>_<cable>_profile` 形式 | `profile = 'NULL'` に変換（Dynamic buffer model 移行） | `sonic-utilities/scripts/db_migrator.py:347-398` |
| Dynamic buffer model: `buffermgrd` が速度・ケーブル長から headroom を計算 | `BUFFER_PG.profile` を自動生成プロファイル名で書き込む | `sonic-swss/cfgmgr/buffermgrdyn.cpp:1483-1528` |

### Phase 7: 条件付き module/manager 登録

| 条件 | 登録 module | evidence |
|---|---|---|
| 常時（条件なし） | `BufferMgrDynamic` が `BUFFER_PG` を `handleBufferPgTable` に登録 | `sonic-swss/cfgmgr/buffermgrdyn.cpp:446` |

### grep カバレッジ

- buffermgrdyn.cpp L446: BUFFER_PG ハンドラ登録（条件なし）
- db_migrator.py L364-398: BUFFER_PG profile='NULL' 移行
<!-- /derivation -->
<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Manager / Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `BufferMgrDynamic` | `handleBufferObjectTables()` | キー形式 `port:ids` が不正 | `task_invalid_entry` 返却（早期リジェクト） | `sonic-swss/cfgmgr/buffermgrdyn.cpp:3514` |
| `BufferMgrDynamic` | `handleBufferObjectTables()` | カンマ区切りポートリスト（複数ポート） | ポートごとにシングルポートハンドラを繰り返し呼び出し | `sonic-swss/cfgmgr/buffermgrdyn.cpp:3536-3547` |
| `BufferMgrDynamic` | BUFFER_PG シングルポートハンドラ | `portPg.dynamic_calculated == true` | headroom を自動計算してプロファイル名を決定 | `sonic-swss/cfgmgr/buffermgrdyn.cpp:1483` |
| `BufferMgrDynamic` | BUFFER_PG シングルポートハンドラ | `portPg.dynamic_calculated == false` | 静的プロファイル参照として APPL_DB に直接書き込む | `sonic-swss/cfgmgr/buffermgrdyn.cpp:1515` |

> **スキャン証跡**: `handleBufferObjectTables` L3502-3553 全行読了。`handleBufferPgTable` は共通ルーターを経由。4 件分岐抽出。
<!-- /handler-branching -->
<!-- constants -->
## ハードコード定数 (Phase E)

### PG インデックス範囲

| 定数 | 値 | 根拠 |
|------|----|------|
| 最大 PG 数 (per port) | **8**（インデックス `0`–`7`）| `buffermgrdyn.cpp` L1336: `(1 << maximum_buffer_objects[BUFFER_PG]) - 1`; [STATE_DB](../../reference/glossary.md#term-state_db) `BUFFER_MAX_PARAM` が 8 を報告 |
| key の `pg_num` 許容パターン | `[0-7]((-)[0-7])?` | `sonic-buffer-pg.yang` pg_num leaf |
| `pg_num` 内部型 | `uint8_t` にキャスト | `buffermgr.cpp` L197 |

### プロファイル名パターン (動的モード)

`buffermgrdyn.cpp` L481–525 `getDynamicProfileName()` が生成する命名規則:

```
pg_lossless_<speed>_<cable>_profile               # MTU=9100 (デフォルト)
pg_lossless_<speed>_<cable>_mtu<mtu>_profile      # 非デフォルト MTU
pg_lossless_<speed>_<cable>_th<threshold>_profile # カスタム threshold
pg_lossless_<speed>_<cable>_<gearbox>_profile     # gearbox モデル付き
pg_lossless_<speed>_<cable>_8lane_profile         # Mellanox 8-lane ポート
```

デフォルト MTU ハードコード: `DEFAULT_MTU_STR = "9100"` (`buffermgrdyn.h` L15)。MTU がこの値に一致する場合は `_mtu` サフィックスが付かない。

静的モード (`buffermgr.cpp` L183–184): `pg_lossless_<speed>_<cable>_profile` のみ。

### pool 名定数

| マクロ | 値 | 定義 |
|--------|----|------|
| `INGRESS_LOSSLESS_PG_POOL_NAME` | `"ingress_lossless_pool"` | `buffermgrdyn.h` L14 / `buffermgr.h` L13 |

### DB テーブル名

| 定数 | 値 | 定義 |
|------|----|------|
| `APP_BUFFER_PG_TABLE_NAME` | `"BUFFER_PG_TABLE"` | `sonic-swss-common/common/schema.h` L161 |
| `CFG_BUFFER_PG_TABLE_NAME` | `"BUFFER_PG"` | `buffermgr.cpp` L140 (文字列参照) |

### SAI 識別子

| SAI ID | 用途 | evidence |
|--------|------|---------|
| `SAI_INGRESS_PRIORITY_GROUP_ATTR_BUFFER_PROFILE` | PG へのバッファプロファイル設定 | `bufferorch.cpp` L1425 |
| `SAI_OBJECT_TYPE_INGRESS_PRIORITY_GROUP` | PG オブジェクト型識別子 | `bufferorch.cpp` L1458 |
| `SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES` | xoff 使用量 watermark 統計 | `portsorch.cpp` L412 |
| `SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES` | shared buffer watermark 統計 | `portsorch.cpp` L413 |
| `SAI_INGRESS_PRIORITY_GROUP_STAT_DROPPED_PACKETS` | PG drop counter 統計 | `portsorch.cpp` L418 |

### FlexCounter グループ名

`portsorch.h` L36–40 で定義。

| マクロ | 値 | ポーリング間隔 |
|--------|----|----|
| `PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"PG_WATERMARK_STAT_COUNTER"` | 60,000 ms |
| `PG_DROP_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"PG_DROP_STAT_COUNTER"` | 10,000 ms |

CONFIG_DB `FLEX_COUNTER_TABLE` キー: `PG_WATERMARK` / `PG_DROP` (`flexcounterorch.cpp` L53–54)。

> 中間調査ファイル: `meta/_intermediate/cdb-flow/buffer-pg-constants.md`

<!-- /constants -->
<!-- platform -->
## プラットフォーム差異 (Phase H)

### 1. Dynamic / Static バッファモデル

`DEVICE_METADATA.localhost.buffer_model` または環境変数 `ASIC_VENDOR` の有無ではなく、Jinja2 テンプレート変数 `dynamic_mode` の定義有無でモデルが決まる。

| モデル | PG 3-4 の初期 profile 値 | PG 0 の初期 profile 値 | 担当デーモン |
|--------|--------------------------|------------------------|-------------|
| **Dynamic** (`dynamic_mode` 定義あり) | `"NULL"` → `buffermgrdyn` が速度・ケーブル長から自動計算 | `"ingress_lossy_profile"` | `buffermgrdyn` |
| **Static** (`dynamic_mode` 未定義) | `"pg_lossless_<speed>_<cable>_profile"` (Jinja2 が直接埋め込み) | `"ingress_lossy_profile"` | `buffermgr` |

- Jinja2 テンプレート: `sonic-buildimage/files/build_templates/buffers_config.j2:263-275`
- Dynamic モードでは `buffermgrdyn` が `getDynamicProfileName()` で `pg_lossless_<speed>_<cable>_profile` を生成し APPL_DB に書く

### 2. ASIC ベンダー別 PG プロファイル名サフィックス (Mellanox)

環境変数 `ASIC_VENDOR=mellanox` が設定された場合、`buffermgrdyn` は Mellanox SN シリーズのモデル番号を `DEVICE_METADATA.localhost.platform` から抽出し、8 レーンポートに対して特別なプロファイル名サフィックスを付与する。

| 条件 | プロファイル名サフィックス | 例 |
|------|--------------------------|-----|
| Mellanox SN4xxx: 8 レーンかつ速度 ≠ 400G | `_8lane` | `pg_lossless_100000_5m_8lane_profile` |
| Mellanox SN5xxx: 8 レーンかつ速度 ≠ 800G | `_8lane` | `pg_lossless_400000_5m_8lane_profile` |
| 上記以外 / 非 Mellanox | サフィックスなし | `pg_lossless_100000_5m_profile` |

- ソース: `sonic-swss/cfgmgr/buffermgrdyn.cpp:504-522` (`getDynamicProfileName`)
- 理由: 8 レーンポートは xon 値が 2 倍になるため、4 レーンポートとプロファイルを共有できない

### 3. Gearbox 付きプラットフォーム

外部 Gearbox が存在するプラットフォーム (PHY チップ挿入構成) では、`gearbox_model` 文字列がプロファイル名に挿入される。

| 条件 | プロファイル名形式 |
|------|--------------------|
| `gearbox_model` 未設定 | `pg_lossless_<speed>_<cable>_profile` |
| `gearbox_model` 設定あり | `pg_lossless_<speed>_<cable>_<gearbox_model>_profile` |

- ソース: `sonic-swss/cfgmgr/buffermgrdyn.cpp:499-501` (`getDynamicProfileName`)
- Gearbox 情報は `PORT_PERIPHERAL_TABLE` から取得 (`buffermgrdyn.cpp:174-226`)

### 4. VOQ Chassis (仮想出力キューシャーシ)

`DEVICE_METADATA.localhost.switch_type == "voq"` の場合、`BufferOrch` の BUFFER_PG 処理は通常スイッチと異なる。

| 項目 | 通常スイッチ | [VOQ](../../reference/glossary.md#term-voq) Chassis |
|------|-------------|-------------|
| BUFFER_PG key 形式 | `<port>\|<pg_range>` (2 トークン) | `<hostname>\|<asic>\|<port>\|<pg_range>` (4 トークン) |
| バッファ適用対象 | フロントパネルポートの PG | [VOQ](../../reference/glossary.md#term-voq) (Virtual Output Queue、システムポートに紐づく) |
| 初期化ゲート | `isConfigDone()` | `isInitDone()` |
| ポート参照カウント | `increasePortRefCount()` で増減 | スキップ（システムポートは動的生成されない） |
| Warm reboot ready list | `initBufferReadyList(pg_table)` | `initBufferReadyList(pg_table)` (PG は通常通り) + `initVoqBufferReadyList(queue_table)` |

- ソース: `sonic-swss/orchagent/bufferorch.cpp:116-136, 916-938, 1166-1168, 2079-2086`
- [VOQ](../../reference/glossary.md#term-voq) モードでは BUFFER_PG は引き続き CONFIG_DB に存在するが、[orchagent](../../reference/glossary.md#term-orchagent) 側で key を 4 トークンとしてパースしローカル/リモートポートを判別する

### 5. プラットフォーム別 PG 範囲割り当て

プラットフォームが独自の `buffers.json.j2` を持つ場合、PG 範囲割り当てが異なる。

| プラットフォーム | Lossless PG | Lossy PG | 備考 |
|---------------|-------------|----------|------|
| 汎用 (buffers_config.j2) | `3-4` | `0` | Dynamic モードのみ 3-4 を NULL で登録 |
| Supermicro SSE-T7132S (400G固定) | `3-4` | `0`, `1-2`, `5-7` | 速度固定のため `pg_lossless_400000_<cable>_profile` を直接埋め込み |
| Marvell Falcon / ARM 系 | プラットフォーム独自 `buffers_config.j2` を使用 | 同左 | `device/marvell/` 配下に独自テンプレート |
| Arista (全機種) | `3-4` (汎用テンプレートに委譲) | `0`, `5-6` | `buffers.json.j2` が `buffers_config.j2` を include するのみ |

- ソース: `sonic-buildimage/device/supermicro/.../buffers.json.j2:124-146`
- ソース: `sonic-buildimage/files/build_templates/buffers_config.j2:263-275`
- ソース: `sonic-buildimage/device/marvell/*/buffers_config.j2`

> 中間調査ファイル: `meta/_intermediate/cdb-flow/buffer-pg-platform.md`

<!-- /platform -->

<!-- ordering -->
## 書込順依存 (Phase B)

BUFFER_PG エントリが正常に SAI まで到達するには、以下の順序制約を満たす必要がある。

| # | 先行必須リソース | 依存先処理 | 違反時の挙動 | evidence |
|---|----------------|-----------|-------------|---------|
| 1 | **BUFFER_POOL** が APPL_DB に存在すること | `buffermgrdyn` が PG を APPL_DB に書き込む | `m_bufferObjectsPending = true` に設定、書き込みデファー | `buffermgrdyn.cpp:935` |
| 2 | **BUFFER_PROFILE** が APPL_DB に存在すること | `BufferOrch::processPriorityGroup()` がプロファイル参照を解決する | `task_need_retry`（[orchagent](../../reference/glossary.md#term-orchagent) が再試行） | `bufferorch.cpp:1345-1348` |
| 3 | **PORT** speed + cable_length が設定済みであること（動的モード） | `buffermgrdyn` が headroom を計算して PG を書き込む | `"Nothing to be done for %s since port is not ready"` → スキップ | `buffermgrdyn.cpp:1485-1487` |
| 4 | **PORT** admin_status + PORT_QOS_MAP.pfc_enable が設定済みであること（静的モード） | `buffermgr.doSpeedUpdateTask()` が PG を作成する | `task_need_retry` または silent skip | `buffermgr.cpp:155,167,175-179` |
| 5 | **BUFFER_PG** は PORT admin up **前**に設定すること | `BufferOrch` が SAI に PG プロファイルを適用する | PORT up 後の設定は `SWSS_LOG_WARN` を発行（SAI 適用自体は行われるが運用上 unsafe） | `bufferorch.cpp:1576-1589` |

### 確定 SAI call 順序

```
1. sai_create_buffer_pool()              ← BUFFER_POOL
2. sai_create_buffer_profile()           ← BUFFER_PROFILE (pool 依存)
3. sai_set_port_attribute(PORT_UP=false) ← PORT admin down のまま保持
4. set_ingress_priority_groups_attribute(SAI_INGRESS_PRIORITY_GROUP_ATTR_BUFFER_PROFILE)
                                         ← BUFFER_PG (pool + profile + port 依存)
5. sai_set_port_attribute(PORT_UP=true)  ← PORT を up にする (BUFFER_PG 設定後)
```

> 中間調査ファイル: `meta/_intermediate/cdb-flow/buffer-pg-ordering.md`

<!-- /ordering -->

<!-- failure -->
## 失敗挙動マトリクス (Phase D)

### buffermgrdyn.cpp — handleSingleBufferPgEntry / refreshPgsForPort

| 失敗条件 | 結果 | ログ | evidence |
|---|---|---|---|
| `profile` 参照が空文字（`profileName.empty()`） | `task_invalid_entry`（エントリ drop、ルックアップもクリア） | `SWSS_LOG_ERROR("BUFFER_PG: Invalid format of reference to profile: %s")` | `buffermgrdyn.cpp:3133` |
| 参照 BUFFER_PROFILE が未登録（`m_bufferProfileLookup` に存在しない） | `task_need_retry`（次イベントで再試行） | `SWSS_LOG_INFO("Profile %s hasn't been configured yet, skip")` | `buffermgrdyn.cpp:3144-3151` |
| 参照 BUFFER_PROFILE の direction が egress | `task_failed`（永続 drop） | `SWSS_LOG_ERROR("Egress buffer profile configured on PG %s")` | `buffermgrdyn.cpp:3156-3163` |
| lossy PG の累積 headroom がリソース上限超過 | `task_failed` | `SWSS_LOG_ERROR("Unable to configure lossy PG %s, accumulative headroom size exceeds the limit")` | `buffermgrdyn.cpp:3170-3171` |
| `profile` 以外の不明フィールドが SET で到達 | `task_invalid_entry` | `SWSS_LOG_ERROR("BUFFER_PG: Invalid field %s")` | `buffermgrdyn.cpp:3180` |
| PORT が `PORT_READY` でない（speed/cable_length 未設定）— 動的計算時 | 対象 PG をスキップ（silent skip、retry なし） | `SWSS_LOG_INFO("Nothing to be done for %s since port is not ready")` | `buffermgrdyn.cpp:1485-1487` |
| cable_length = `"0m"` かつ lossless PG | APPL_DB から lossless PG を削除（バッファ回収） | `SWSS_LOG_INFO("No lossless profile found for port %s when cable length is set to '0m'.")` | `buffermgrdyn.cpp:1492-1509` |
| 動的 headroom 計算（`allocateProfile()`）失敗 | `task_failed` | `allocateProfile()` 内部で `SWSS_LOG_ERROR` | `buffermgrdyn.cpp:1530-1534` |
| 動的計算後の累積 headroom がリソース上限超過 | `task_failed`（profile を release） | `SWSS_LOG_ERROR("Update speed (%s) and cable length (%s) for port %s failed, accumulative headroom size exceeds the limit")` | `buffermgrdyn.cpp:1541-1546` |
| PORT admin down 時の SET | APPL_DB 書き込みをスキップし内部状態のみ保持。PORT up 時に再適用（silent defer） | なし | `buffermgrdyn.cpp:3198-3202` |
| zero profile が pool に未設定 | LOG_ERROR のみ・処理継続（SAI call なし） | `SWSS_LOG_ERROR("Zero profile is not provided for pool %s ...")` | `buffermgrdyn.cpp:384` |

### buffermgr.cpp — doSpeedUpdateTask

| 失敗条件 | 結果 | ログ | evidence |
|---|---|---|---|
| cable_length 未設定 | `task_need_retry` | `SWSS_LOG_INFO("...Cable length is not set")` | `buffermgr.cpp:155` |
| `admin_status` 未取得 | `task_need_retry` | `SWSS_LOG_INFO("pfc_enable status is not available for port %s")` | `buffermgr.cpp:170` |
| `PORT_QOS_MAP.pfc_enable` 未設定 | `task_success`（silent skip、pfc_enable 設定時に再ハンドル） | `SWSS_LOG_INFO("pfc_enable status is not available for port %s")` | `buffermgr.cpp:175-179` |
| speed + cable_length が lookup table に未定義 | `task_invalid_entry`（永続 drop） | `SWSS_LOG_ERROR("No PG profile configured for speed %s and cable length %s")` | `buffermgr.cpp:240` |
| lossless pool が未作成 | `task_need_retry` | `SWSS_LOG_INFO("PG lossless pool is not yet created")` | `buffermgr.cpp:258` |
| PORT admin down（mellanox/barefoot）かつデフォルトプロファイル | CONFIG_DB の BUFFER_PG を削除（バッファ回収） | `SWSS_LOG_NOTICE("Removing PG %s from port %s which is administrative down")` | `buffermgr.cpp:228` |
| PORT admin down かつ非デフォルトプロファイル | 削除せず silent skip | `SWSS_LOG_NOTICE("won't reclaim buffer")` | `buffermgr.cpp:231` |
| PG ID が `uint8_t` に変換不可 | 該当 PG ID を silent skip・ループ継続 | なし | `buffermgr.cpp:197` |

### bufferorch.cpp — processPriorityGroup / processPriorityGroupPost

| 失敗条件 | 結果 | ログ | evidence |
|---|---|---|---|
| key が 2 トークンでない | `task_invalid_entry` | `SWSS_LOG_ERROR("malformed key:%s. Must contain 2 tokens")` | `bufferorch.cpp:1324` |
| pg_range パース失敗 | `task_invalid_entry` | `SWSS_LOG_ERROR("Failed to obtain pg range values")` | `bufferorch.cpp:1330` |
| BUFFER_PROFILE 参照が未解決 | `task_need_retry` | `SWSS_LOG_INFO("Missing or invalid pg profile reference specified")` | `bufferorch.cpp:1347` |
| BUFFER_PROFILE 参照がその他エラーで解決失敗 | `task_failed` | `SWSS_LOG_ERROR("Resolving pg profile reference failed")` | `bufferorch.cpp:1350-1351` |
| BUFFER_PROFILE が trimming eligible | `task_failed` | `SWSS_LOG_ERROR("...buffer profile(%s) is trimming eligible")` | `bufferorch.cpp:759-763` |
| ポート名が PortsOrch に未登録 | `task_invalid_entry` | `SWSS_LOG_ERROR("Port with alias:%s not found")` | `bufferorch.cpp:1035` |
| PG インデックスがポートの PG 数超過 | `task_invalid_entry` | `SWSS_LOG_ERROR("Invalid pg index specified:%zd")` | `bufferorch.cpp:1063` |
| SAI `set_attribute` が非 SUCCESS を返却 | `handleSaiSetStatus()` に委譲（retry 可能か判定） | `SWSS_LOG_ERROR("Failed to set port:%s pg:%zd buffer profile attribute, status:%d")` | `bufferorch.cpp:1507-1512` |
| DEL 対象が APPL_DB に存在しない | SAI call をスキップして `task_success` | `SWSS_LOG_INFO("...doesn't not exist, don't need to notfiy SAI")` | `bufferorch.cpp:1409-1413` |

> 中間調査ファイル: `meta/_intermediate/cdb-flow/buffer-pg-failure.md`

<!-- /failure -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

`BUFFER_PG` テーブルの変更が CONFIG_DB から SAI へ到達するまでに経由する subscribe 方式を示す。

### CONFIG_DB → buffermgr / buffermgrdyn（Orch subscribe）

| consumer | 購読方式 | 購読 DB / テーブル | ハンドラ | evidence |
|---|---|---|---|---|
| `BufferMgrDynamic` (動的モード) | `Orch` コンストラクタ経由 `TableConnector` subscribe | `CONFIG_DB / BUFFER_PG` (`CFG_BUFFER_PG_TABLE_NAME`) | `handleBufferPgTable()` → `handleBufferObjectTables()` | `buffermgrd.cpp:179`, `buffermgrdyn.cpp:446` |
| `BufferMgr` (静的モード) | `Orch(cfgDb, tableNames)` コンストラクタ経由 subscribe | `CONFIG_DB / BUFFER_PG` (`CFG_BUFFER_PG_TABLE_NAME`) | `doTask()` 内 `table_name == CFG_BUFFER_PG_TABLE_NAME` 分岐 | `buffermgrd.cpp:196`, `buffermgr.cpp:22,493` |

`Orch` 基底クラスは各 `TableConnector` に対して内部的に `SubscriberStateTable` を生成し、[Redis](../../reference/glossary.md#term-redis) Keyspace Notification を SELECT loop で受信する。`buffermgrd.cpp` の `main()` が `cfgOrchList` を構築し、動的/静的モードを `-a`/`-l` フラグで切り替える。

### APPL_DB → BufferOrch（ConsumerStateTable）

| consumer | 購読方式 | 購読 DB / テーブル | ハンドラ | evidence |
|---|---|---|---|---|
| `BufferOrch` | `Orch(applDb, tableNames)` コンストラクタ経由 `ConsumerStateTable` | `APPL_DB / BUFFER_PG_TABLE` (`APP_BUFFER_PG_TABLE_NAME`) | `processPriorityGroup()` / `processPriorityGroupBulk()` | `bufferorch.cpp:54`, `orchdaemon.cpp:390,394` |

`orchdaemon.cpp` は `buffer_tables` ベクタに `APP_BUFFER_PG_TABLE_NAME` を含めて `BufferOrch` を生成する。`Orch` 基底クラスが `ConsumerStateTable` を介して APPL_DB の BUFFER_PG_TABLE 変更を受信し、`doTask()` が `m_bufferHandlerMap[APP_BUFFER_PG_TABLE_NAME]` → `processPriorityGroup()` を呼び出す。

### データフロー概要

```
CONFIG_DB / BUFFER_PG
  │  (SubscriberStateTable via Orch)
  ▼
buffermgrdyn.cpp::handleBufferPgTable()          ← 動的モード
buffermgr.cpp::doTask() / CFG_BUFFER_PG 分岐     ← 静的モード
  │  (ProducerStateTable.set/del → APPL_DB)
  ▼
APPL_DB / BUFFER_PG_TABLE
  │  (ConsumerStateTable via Orch)
  ▼
bufferorch.cpp::processPriorityGroup()
  │  (SAI API)
  ▼
syncd → SAI sai_buffer_api
```

> 中間調査ファイル: `meta/_intermediate/cdb-flow/buffer-pg-pubsub.md`

<!-- /pubsub -->
<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

YANG leafref は `profile → BUFFER_PROFILE.name` の 1 件のみ定義。以下はすべて実装レベルの暗黙参照。

| 参照先テーブル / リソース | YANG leafref | 参照方向 | 条件 | 参照元 evidence |
|--------------------------|:------------:|---------|------|----------------|
| `BUFFER_PROFILE\|<name>` | ✅ | 存在確認 + 属性取得（`dynamic_calculated`, `lossless`, `direction`） | `profile` フィールドが非 NULL のとき。未設定 → `task_need_retry`、egress 方向 → `task_failed` | `buffermgrdyn.cpp` L3141–3168 (`handleSingleBufferPgEntry()`) |
| `BUFFER_POOL` | ✗ | ブロッキング（`m_bufferPoolReady` フラグ） | 常時。BUFFER_POOL が確立するまで全 PG 書き込みをデファー | `buffermgrdyn.cpp` L933–935 / `buffermgr.cpp` L118 |
| `PORT` (speed / mtu / admin_status / lanes) | ✗ | 読み取り（内部キャッシュ `m_portInfoLookup`） | 常時。speed + mtu が揃わない限り headroom 計算をスキップ | `buffermgrdyn.cpp` L1485–1487 / `buffermgr.cpp` L155–179 / `bufferorch.cpp` L1431 |
| `CABLE_LENGTH` (ポートごとのケーブル長) | ✗ | 読み取り（`handleCableLenTable` 購読） | dynamic モードの lossless PG headroom 計算時。`0m` → lossless PG を APPL_DB から silent delete | `buffermgrdyn.cpp` L2142–2148, L1492–1523 / `buffermgr.cpp` L101–106 |
| `DEFAULT_LOSSLESS_BUFFER_PARAMETER` (`default_dynamic_th`) | ✗ | 読み取り（起動時 + 動的更新） | dynamic モードで lossless PG の threshold を決定。未設定なら BUFFER_POOL ready 後もデファー | `buffermgrdyn.cpp` L150–153, L1460, L1521 |
| `LOSSLESS_TRAFFIC_PATTERN` (Lua 経由) | ✗ | 間接読み取り（`buffer_headroom_<platform>.lua` 内 [Redis](../../reference/glossary.md#term-redis) KEYS） | Mellanox / Barefoot プラットフォームでの headroom 計算時のみ有効 | `cfgmgr/buffer_headroom_mellanox.lua` L91 / `buffermgrdyn.cpp` L76–78 |

!!! note "BUFFER_POOL と DEFAULT_LOSSLESS_BUFFER_PARAMETER の二重ゲート"
    dynamic モードでは `m_bufferPoolReady == true` かつ `m_defaultThreshold.empty() == false` の両条件が揃わない限り、lossless BUFFER_PG の APPL_DB 書き込みは開始されない（`buffermgrdyn.cpp` L1460, L3645）。CONFIG_DB への BUFFER_PG 設定だけでは不十分で、BUFFER_POOL と DEFAULT_LOSSLESS_BUFFER_PARAMETER の先行設定が必須。

!!! note "LOSSLESS_TRAFFIC_PATTERN の適用範囲"
    `buffermgrdyn.cpp` 本体は `LOSSLESS_TRAFFIC_PATTERN` を直接購読しない。参照は `buffer_headroom_mellanox.lua` / `buffer_headroom_barefoot.lua` の Lua スクリプト内のみで行われる。汎用（`buffer_headroom_generic.lua`）では参照しない。

> 中間調査ファイル: `meta/_intermediate/cdb-flow/buffer-pg-cross-refs.md`

<!-- /cross-refs -->

<!-- glossary-links-injected: 19092d470ffc -->
