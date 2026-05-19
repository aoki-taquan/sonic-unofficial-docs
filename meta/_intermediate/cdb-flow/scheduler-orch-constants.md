# SCHEDULER-ORCH — Phase E ハードコード定数 調査メモ

対象ページ: `docs/reference/config-db/scheduler-orch.md`
調査日: 2026-05-19

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/qosorch.h` | フィールド名定数・スケジューラアルゴリズム文字列定数定義 |
| `sonic-swss/orchagent/qosorch.cpp` | `scheduler_meter_map` の値・`handleSchedulerTable()` の型変換ロジック |

## 検出したハードコード定数

### フィールド名定数 (qosorch.h L44–53)

| 定数 | 値 | ソース |
|------|----|--------|
| `scheduler_algo_type_field_name` | `"type"` | `qosorch.h:44` |
| `scheduler_algo_DWRR` | `"DWRR"` | `qosorch.h:45` |
| `scheduler_algo_WRR` | `"WRR"` | `qosorch.h:46` |
| `scheduler_algo_STRICT` | `"STRICT"` | `qosorch.h:47` |
| `scheduler_weight_field_name` | `"weight"` | `qosorch.h:48` |
| `scheduler_meter_type_field_name` | `"meter_type"` | `qosorch.h:49` |
| `scheduler_min_bandwidth_rate_field_name` | `"cir"` (Committed Information Rate) | `qosorch.h:50` |
| `scheduler_min_bandwidth_burst_rate_field_name` | `"cbs"` (Committed Burst Size) | `qosorch.h:51` |
| `scheduler_max_bandwidth_rate_field_name` | `"pir"` (Peak Information Rate) | `qosorch.h:52` |
| `scheduler_max_bandwidth_burst_rate_field_name` | `"pbs"` (Peak Burst Size) | `qosorch.h:53` |

### meter_type 許容値マップ (qosorch.cpp L75–78)

```cpp
map<string, sai_meter_type_t> scheduler_meter_map = {
    {"packets", SAI_METER_TYPE_PACKETS},
    {"bytes",   SAI_METER_TYPE_BYTES}
};
```

- 許容値は **"packets"** と **"bytes"** の 2 値のみ
- `.at()` でアクセスするため、これ以外の値は `std::out_of_range` 例外 → orchagent クラッシュ
- YANG `sonic-scheduler.yang` の enum も同じ 2 値 (`bytes` / `packets`) であり、通常経路ではバリデーション済みの値のみが到達する

### weight フィールドの型変換定数

```cpp
// qosorch.cpp L1402
attr.value.u8 = (uint8_t)stoi(fvValue(*i));
```

- weight は `stoi()` で int 変換後に `uint8_t` にキャスト
- YANG `range "1..100"` は qosorch では未検証（CONFIG_DB のバリデーション層に委ねる）
- `stoi()` が失敗する（数値でない文字列）場合は `std::invalid_argument` 例外 → orchagent クラッシュ
  - 通常経路では YANG バリデーション済みのため発生しないが、直接投入時はリスクあり

### 帯域レートフィールドの型変換定数

```cpp
// qosorch.cpp L1416, 1421, 1426, 1432
attr.value.u64 = stoull(fvValue(*i));
```

- `cir` / `cbs` / `pir` / `pbs` は `stoull()` で `uint64_t` に変換
- 数値以外の文字列が入ると `std::invalid_argument` 例外 → orchagent クラッシュ

## 定数欠如: `priority` フィールド

`sonic-scheduler.yang` に `leaf priority { type uint8 { range "0..9"; } }` が定義されているが、
`qosorch.h` に対応する定数がない（`scheduler_priority_field_name` は存在しない）。
これは「dead field」であり Phase A で詳述。定数が未定義のため、if-else チェーンにも処理分岐がない。
