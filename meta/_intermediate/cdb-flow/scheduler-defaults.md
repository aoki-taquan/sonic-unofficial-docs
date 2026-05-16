# SCHEDULER — Phase A コード由来デフォルト調査

調査日: 2026-05-14  
対象ファイル:
- `sonic-swss/orchagent/qosorch.cpp` (handleSchedulerTable, L1347–1509)
- `sonic-swss/orchagent/qosorch.h` (定数定義 L44–53)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-scheduler.yang`

---

## フィールドごとのデフォルト・挙動分析

### `type`
- **YANG default**: `WRR`
- **コード挙動**: フィールドが CONFIG_DB エントリに存在する場合のみ `SAI_SCHEDULER_ATTR_SCHEDULING_TYPE` を SAI attr リストに追加 (L1378–1397)。フィールドが**省略された場合、SAI 属性は一切送信されない**。
- **SAI 実装依存デフォルト**: SAI 実装（ASIC ベンダー）が `SAI_SCHEDULING_TYPE_WRR` をデフォルトとする保証はない。YANG の `default WRR` は CONFIG_DB バリデーション層の宣言であり、qosorch はこれを読まない。
- **判定**: YANG default ≠ 実装デフォルト。フィールド省略時の ASIC 挙動は SAI ベンダー依存（暗黙 fallback）。

### `weight`
- **YANG default**: `1`
- **コード挙動**: フィールドが存在する場合のみ `SAI_SCHEDULER_ATTR_SCHEDULING_WEIGHT` を設定 (L1399–1403)。`stoi()` + `(uint8_t)` キャスト。範囲 0–255 は`uint8_t`に収まるが YANG の `range "1..100"` はコードで検証されない（silent overflow なし、ただしバリデーション欠如）。
- **フィールド省略時**: SAI デフォルトに委ねられる。YANG の `default 1` は不適用。
- **判定**: YANG default ≠ 実装デフォルト。省略時は SAI ベンダー依存。

### `priority`
- **YANG**: `type uint8 { range "0..9"; }` — デフォルトなし
- **コード挙動**: `qosorch.h` に `scheduler_priority` 定数なし。`handleSchedulerTable` の if-else チェーンに `priority` の処理分岐が**存在しない**。
- **判定**: **完全な dead field**。CONFIG_DB に設定されても SAI には一切反映されない。`else { SWSS_LOG_ERROR("Unknown field:%s") → task_invalid_entry }` により**エントリ全体が破棄される**。

  > **重要**: `priority` フィールドを含むエントリを SET すると `Unknown field:priority` エラーで `task_invalid_entry` が返り、そのエントリの**全フィールドが SAI に反映されない**。

### `meter_type`
- **YANG default**: `bytes`
- **コード挙動**: `scheduler_meter_map.at(fvValue(*i))` を使用 (L1407)。map には `"packets"` → `SAI_METER_TYPE_PACKETS`、`"bytes"` → `SAI_METER_TYPE_BYTES` のみ登録。
- **フィールド省略時**: SAI 属性送信なし → SAI ベンダー依存デフォルト。
- **無効値時**: `std::map::at()` が `std::out_of_range` 例外をスロー → **未キャッチ例外** → `orchagent` プロセスクラッシュ。`type` フィールドの graceful エラーハンドリングと異なる危険な挙動。
- **判定**: YANG default ≠ 実装デフォルト。不正値でクラッシュリスク。

### `cir` (SAI: SAI_SCHEDULER_ATTR_MIN_BANDWIDTH_RATE)
- **YANG default**: なし
- **コード挙動**: フィールド存在時のみ `stoull()` で `uint64_t` に変換して設定 (L1412–1416)。
- **判定**: オプション。省略時は SAI デフォルト (0 相当)。

### `cbs` (SAI: SAI_SCHEDULER_ATTR_MIN_BANDWIDTH_BURST_RATE)
- **YANG default**: なし  
- **コード挙動**: フィールド存在時のみ `stoull()` で設定 (L1418–1422)。
- **判定**: オプション。省略時は SAI デフォルト。

### `pir` (SAI: SAI_SCHEDULER_ATTR_MAX_BANDWIDTH_RATE)
- **YANG default**: なし
- **コード挙動**: フィールド存在時のみ設定 (L1424–1428)。YANG の `must cir > 0` 制約はコードで未検証。
- **判定**: オプション。YANG must 制約はバリデーション層のみ。

### `pbs` (SAI: SAI_SCHEDULER_ATTR_MAX_BANDWIDTH_BURST_RATE)
- **YANG default**: なし
- **コード挙動**: フィールド存在時のみ設定 (L1430–1434)。
- **判定**: オプション。省略時は SAI デフォルト。

---

## 経路依存・書き込み順依存

- **既存オブジェクトの更新 (SET on existing)**: `sai_object != SAI_NULL_OBJECT_ID` の場合は `set_scheduler_attribute()` を属性ごとに個別呼び出し (L1442–1456)。各属性が独立して更新される。
- **新規作成 (SET on new)**: `create_scheduler()` に全属性をまとめて渡す (L1460)。省略フィールドは SAI デフォルトになる。
- **書き込み順依存**: なし（SET 内で完結）。

---

## YANG-実装 Discrepancy サマリー

| フィールド | YANG default | qosorch 実装 | Discrepancy |
|-----------|-------------|-------------|-------------|
| `type` | `WRR` | 省略時 SAI ベンダー依存 | あり（YANG default 不適用） |
| `weight` | `1` | 省略時 SAI ベンダー依存 | あり（YANG default 不適用） |
| `priority` | なし | **dead field** (Unknown field エラー) | あり（YANG 定義あり、実装なし） |
| `meter_type` | `bytes` | 省略時 SAI ベンダー依存 | あり（YANG default 不適用）; 不正値でクラッシュ |
| `cir/cbs/pir/pbs` | なし | 省略時 SAI デフォルト | なし（想定通り） |

---

## ハードコード値

- フィールド名文字列: `qosorch.h` L44–53 でハードコード定義
- SAI enum 値: コード内に直接マッピング（変更不可）
- `scheduler_meter_map`: コンパイル時定数（runtime 変更不可）

---

## evidence

- `qosorch.cpp` L1378–1438: handleSchedulerTable の if-else チェーン
- `qosorch.h` L44–53: 定数定義（`priority` フィールド定数なし）
- `sonic-scheduler.yang`: YANG default 宣言
