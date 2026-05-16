# BUFFER_PROFILE — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/buffer-profile.md` Phase C 追加分。
YANG leafref として `BUFFER_PROFILE.pool → BUFFER_POOL.name` が明示されているが、
実装上は他に BUFFER_POOL・PORT・DEVICE_METADATA への暗黙的な依存が複数存在する。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/cfgmgr/buffermgrdyn.cpp` | `BufferMgrDynamic` — dynamic buffer model のメインハンドラ |
| `sonic-swss/cfgmgr/buffermgr.cpp` | `BufferMgr` — static buffer model のメインハンドラ |
| `sonic-swss/orchagent/bufferorch.cpp` | `BufferOrch` — APPL_DB → SAI 変換 |

## YANG leafref（明示参照）

| フィールド | leafref 先 | 備考 |
|-----------|-----------|------|
| `pool` | `BUFFER_POOL.name` | YANG で明示。APPL_DB 転送・SAI 生成でも同様に解決 |

## 暗黙参照 (実装レベル)

### 1. BUFFER_POOL (CONFIG_DB → APPL_DB)

- **参照先テーブル**: `BUFFER_POOL`
- **参照方向**: 購読 + 内部 lookup
- **条件**: dynamic buffer model（`buffermgrdyn`）常時
- **参照元**:
  - `buffermgrdyn.cpp:443` — `handleBufferPoolTable` ハンドラを `m_bufferTableHandlerMap` に登録（`CFG_BUFFER_POOL_TABLE_NAME`）
  - `buffermgrdyn.cpp:2707-2716` — `handleBufferProfileTable()` 内で `m_bufferPoolLookup.find(poolName)` → 未登録なら `task_need_retry`
  - `buffermgrdyn.cpp:2718-2736` — pool の `mode`（dynamic/static）を取り出して `threshold_mode` と照合。不一致なら `task_failed`
  - `buffermgrdyn.cpp:892-896` — `updateBufferProfileToDb()` 冒頭: `m_bufferPoolReady == false` ならば APPL_DB への書き込みをデファー
  - `bufferorch.cpp:641-652` — `processBufferProfile()` 内で `resolveFieldRefValue()` が APPL_DB の `BUFFER_POOL_TABLE` を参照解決。`not_resolved` → `task_need_retry`
- **読み取りフィールド**: `mode`（dynamic/static）、`direction`（ingress/egress）、`m_bufferPoolReady` フラグ
- **意味**:
  - BUFFER_POOL が CONFIG_DB/APPL_DB に存在しないと BUFFER_PROFILE は APPL_DB に書き込まれない（サイレント保留または `task_need_retry`）。
  - pool の `mode` が profile の `threshold_mode`（`dynamic_th` / `static_th`）と不一致の場合は `task_failed` でリジェクト。
  - pool の `direction` が ingress でない場合、`lossless=true` のプロファイルは `task_failed`（`buffermgrdyn.cpp:2807-2814`）。

### 2. PORT (CONFIG_DB)

- **参照先テーブル**: `PORT`
- **参照方向**: 購読 + 読み取り
- **条件**: dynamic buffer model（`buffermgrdyn`）、`headroom_type=dynamic` のプロファイルが存在するとき
- **参照元**:
  - `buffermgrdyn.cpp:449` — `handlePortTable` を `CFG_PORT_TABLE_NAME` に登録
  - `buffermgrdyn.cpp:451` — `handlePortStateTable` を `STATE_PORT_TABLE_NAME` に登録
  - `buffermgrdyn.cpp:2266-2344` — `handlePortTable()` 実装: `speed`・`mtu`・`admin_status`・`adv_speeds`・`autoneg`・`lanes` フィールドを読み取り内部 `m_portInfoLookup` に保持
  - `buffermgrdyn.cpp:1799-1833` — `doUpdateBufferProfileForDynamicTh()`: `headroom_type=dynamic` プロファイル変更時に、当該プロファイルを参照している全ポートの `effective_speed`・`cable_length`・`mtu` を用いて headroom を再計算
  - `buffermgrdyn.cpp:1822` — `refreshPgsForPort(portName, port.effective_speed, port.cable_length, port.mtu)` 呼び出し
- **読み取りフィールド**: `speed`、`mtu`、`admin_status`、`adv_speeds`、`autoneg`、`lanes`（lane_count 計算）
- **意味**:
  - `headroom_type=dynamic` のプロファイルは PORT の `speed`（または `adv_speeds` のmax、`supported_speeds` のmax）と `cable_length`（`CABLE_LENGTH` テーブル経由）・`mtu` から headroom を Lua plugin で自動計算する。
  - PORT が未到達（`PORT_READY` でない）のときはヘッドルーム計算をスキップし、到着後に再計算する。
  - Mellanox SN4k/SN5k では `lanes` フィールドから `lane_count` を算出し、8-lane ポートで xon を 2 倍にする（`buffermgrdyn.cpp:504-523`）。

### 3. DEVICE_METADATA (CONFIG_DB)

- **参照先テーブル**: `DEVICE_METADATA`
- **参照方向**: 起動時読み取り（購読なし）
- **条件**: dynamic buffer model（`buffermgrdyn`）かつ Mellanox プラットフォームのとき
- **参照元**:
  - `buffermgrdyn.cpp:41` — コンストラクタ初期化: `m_cfgDeviceMetaDataTable(cfgDb, CFG_DEVICE_METADATA_TABLE_NAME)`
  - `buffermgrdyn.cpp:87` — `m_cfgDeviceMetaDataTable.hget("localhost", "platform", m_specific_platform)` — Mellanox 限定で起動時 1 回読み取り
- **読み取りフィールド**: `platform`（`localhost` キー）
- **意味**:
  - `platform` の値（例: `x86_64-mlnx_sn4600c-r0`）からモデル番号を抽出し `m_model_number` に保持。
  - SN4xxx で 8-lane かつ非 400G、SN5xxx で 8-lane かつ非 800G の場合に `pg_lossless_<speed>_<cable>_8lane_profile` を生成し xon を 2 倍にする。
  - Mellanox 以外のプラットフォームではこの読み取りはスキップされ（`buffermgrdyn.cpp:85-104`）、BUFFER_PROFILE 処理に影響しない。
  - static buffer model（`buffermgr`）では `DEVICE_METADATA.buffer_model` フィールドを読み取り dynamic/static の切り替えを行う（`buffermgr.cpp:390-407`）。

## 参照関係サマリ

```
BUFFER_PROFILE
  ├─ [YANG leafref / 常時]         CONFIG_DB.BUFFER_POOL
  │     pool.mode    → threshold_mode 照合（不一致で task_failed）
  │     pool.direction → lossless プロファイルは ingress 必須（egress で task_failed）
  │     m_bufferPoolReady → false 時は APPL_DB 書き込みをサイレントデファー
  │     APPL_DB 参照解決 → not_resolved で task_need_retry (bufferorch)
  ├─ [暗黙/dynamic-only]           CONFIG_DB.PORT
  │     speed / adv_speeds / supported_speeds → effective_speed → Lua headroom 計算
  │     mtu → headroom 計算パラメータ
  │     lanes → lane_count → Mellanox 8-lane xon 2倍判定
  │     admin_status → down 時 lossless PG 削除トリガ
  └─ [暗黙/Mellanox-startup-only]  CONFIG_DB.DEVICE_METADATA
        platform → m_model_number → SN4k/SN5k 8-lane 判定
        buffer_model → dynamic/static モデル選択 (static model)
```

## evidence

- `buffermgrdyn.cpp`: L41 (DEVICE_METADATA 初期化), L85-104 (platform 読み取り), L443 (BUFFER_POOL ハンドラ登録), L449/L451 (PORT ハンドラ登録), L892-896 (m_bufferPoolReady ガード), L1799-1833 (doUpdateBufferProfileForDynamicTh), L1822 (refreshPgsForPort 呼び出し), L2266-2344 (handlePortTable 実装), L2707-2736 (BUFFER_POOL lookup + threshold_mode 照合), L2807-2814 (lossless+egress task_failed)
- `buffermgr.cpp`: L390-407 (DEVICE_METADATA.buffer_model 読み取り)
- `bufferorch.cpp`: L641-652 (APPL_DB BUFFER_POOL 参照解決)
