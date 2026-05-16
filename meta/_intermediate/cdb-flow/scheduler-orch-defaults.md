# SCHEDULER — orchagent QosOrch Phase A コード由来デフォルト (scheduler-orch)

調査日: 2026-05-15
対象ファイル:
- `sonic-swss/orchagent/qosorch.cpp` (handleSchedulerTable, L1347–1509)
- `sonic-swss/orchagent/qosorch.h` (定数定義 L22, 44–53)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-scheduler.yang`

---

## 調査サマリー

`QosOrch::handleSchedulerTable()` が CONFIG_DB `SCHEDULER` テーブルを処理する。
各フィールドは **存在する場合のみ** SAI 属性リストに追加される。省略時は SAI 実装のベンダーデフォルトに委ねられる。

## フィールドごとのデフォルト・挙動分析

### `type` (scheduler_algo_type_field_name)
- **YANG default**: `WRR`
- **コード挙動**: フィールドが CONFIG_DB に存在する場合のみ `SAI_SCHEDULER_ATTR_SCHEDULING_TYPE` を SAI attr リストに追加 (qosorch.cpp L1378–1397)。
  - `"DWRR"` → `SAI_SCHEDULING_TYPE_DWRR`
  - `"WRR"` → `SAI_SCHEDULING_TYPE_WRR`
  - `"STRICT"` → `SAI_SCHEDULING_TYPE_STRICT`
  - 上記以外 → `SWSS_LOG_ERROR("Unknown scheduler type value:%s")` → `task_invalid_entry`（エントリ全体が SAI 未反映）
- **フィールド省略時**: SAI 属性送信なし → SAI ベンダー依存デフォルト
- **discrepancy**: YANG の `default WRR` は qosorch が参照しない

### `weight` (scheduler_weight_field_name)
- **YANG default**: `1`; **YANG range**: `1..100`
- **コード挙動**: フィールド存在時のみ `SAI_SCHEDULER_ATTR_SCHEDULING_WEIGHT` を設定 (L1399–1403)。
  `(uint8_t)stoi(fvValue(*i))` でキャスト。`range "1..100"` はコードで未検証（silent truncation なし、バリデーション欠如）。
- **フィールド省略時**: SAI ベンダー依存デフォルト
- **discrepancy**: YANG default `1` は qosorch が参照しない

### `priority` (定数なし)
- **YANG**: `leaf priority { type uint8 { range "0..9"; } }` — デフォルトなし
- **コード挙動**: `qosorch.h` に `scheduler_priority_field_name` 定数が存在しない。`handleSchedulerTable` の if-else チェーン (L1378–1438) に `priority` 処理分岐が**一切存在しない**。
- **判定**: **完全な dead field**。CONFIG_DB に `priority` を含む SET を行うと `else { SWSS_LOG_ERROR("Unknown field:%s") → task_invalid_entry }` により**そのエントリの全フィールドが SAI に反映されない**。
- **discrepancy**: YANG 定義あり、実装なし → YANG-実装間の重大な乖離

### `meter_type` (scheduler_meter_type_field_name)
- **YANG default**: `bytes`
- **コード挙動**: `scheduler_meter_map.at(fvValue(*i))` (L1407)。map は `"packets"` / `"bytes"` の 2 値のみ。
- **フィールド省略時**: SAI 属性送信なし → SAI ベンダー依存デフォルト
- **無効値時**: `std::map::at()` が `std::out_of_range` 例外 → **未キャッチ → orchagent クラッシュ**（`type` フィールドと異なり graceful エラー処理なし）
- **discrepancy**: YANG default `bytes` は qosorch が参照しない; 不正値でクラッシュリスク

### `cir` (scheduler_min_bandwidth_rate_field_name → SAI_SCHEDULER_ATTR_MIN_BANDWIDTH_RATE)
- **YANG default**: なし
- **コード挙動**: フィールド存在時のみ `stoull()` で `uint64_t` に変換して設定 (L1412–1416)
- **判定**: オプション。省略時は SAI デフォルト相当 (0 = 無制限相当)
- YANG `must cir > 0` (pir/cbs/pbs を設定する際の前提条件) はコードで未検証

### `cbs` (scheduler_min_bandwidth_burst_rate_field_name → SAI_SCHEDULER_ATTR_MIN_BANDWIDTH_BURST_RATE)
- **YANG default**: なし
- **コード挙動**: フィールド存在時のみ設定 (L1418–1422)
- **判定**: オプション。省略時は SAI デフォルト

### `pir` (scheduler_max_bandwidth_rate_field_name → SAI_SCHEDULER_ATTR_MAX_BANDWIDTH_RATE)
- **YANG default**: なし
- **コード挙動**: フィールド存在時のみ設定 (L1424–1428)
- **判定**: オプション。YANG の `must pir >= cir` はコード未検証

### `pbs` (scheduler_max_bandwidth_burst_rate_field_name → SAI_SCHEDULER_ATTR_MAX_BANDWIDTH_BURST_RATE)
- **YANG default**: なし
- **コード挙動**: フィールド存在時のみ設定 (L1430–1434)
- **判定**: オプション。省略時は SAI デフォルト

---

## 経路依存・書き込み順依存

- **既存オブジェクト更新 (SET on existing)**: `sai_object != SAI_NULL_OBJECT_ID` の場合、`set_scheduler_attribute()` を属性ごとに個別呼び出し (L1442–1456)。各属性が独立して更新される。
- **新規作成 (SET on new)**: `create_scheduler()` に全属性をまとめて渡す (L1460)。省略フィールドは SAI ベンダーデフォルト。
- **削除保護**: QUEUE 等から参照中の場合 `isObjectBeingReferenced()` チェックで `task_need_retry` を返し `m_pendingRemove = true` にセット。参照解除後に自動削除。

---

## YANG-実装 Discrepancy サマリー

| フィールド | YANG default | qosorch 実装 | discrepancy |
|-----------|-------------|-------------|-------------|
| `type` | `WRR` | 省略時 SAI ベンダー依存 | あり（YANG default 不適用） |
| `weight` | `1` | 省略時 SAI ベンダー依存 | あり（YANG default 不適用） |
| `priority` | なし | **dead field** (Unknown field エラー、エントリ全破棄) | あり（YANG 定義あり、実装なし） |
| `meter_type` | `bytes` | 省略時 SAI ベンダー依存; 不正値でクラッシュ | あり（YANG default 不適用、危険な例外挙動） |
| `cir/cbs/pir/pbs` | なし | 省略時 SAI デフォルト | なし |

---

## evidence (行番号)

- `qosorch.h` L22: `scheduler_field_name = "scheduler"`
- `qosorch.h` L44–53: フィールド名定数一覧（`priority` 定数なし）
- `qosorch.cpp` L1347–1509: `handleSchedulerTable()` 全体
- `qosorch.cpp` L1378–1438: if-else チェーン（フィールド処理分岐）
- `qosorch.cpp` L1442–1474: 更新 vs 新規作成の分岐
- `qosorch.cpp` L1483–1489: 参照中削除保護ロジック
- `sonic-scheduler.yang`: YANG default/must 宣言
