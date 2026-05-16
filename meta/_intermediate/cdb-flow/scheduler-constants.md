# SCHEDULER — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/orchagent/qosorch.h` (フィールド名定数・enum 文字列)
- `sonic-swss/orchagent/qosorch.cpp` (SAI 属性マッピング・meter_type マップ)

---

## 1. type enum 文字列 (qosorch.h L44-47)

| 定数名 | 値 | SAI 変換先 | ソース |
|--------|----|-----------|--------|
| `scheduler_algo_type_field_name` | `"type"` | — (フィールドキー) | qosorch.h L44 |
| `scheduler_algo_DWRR` | `"DWRR"` | `SAI_SCHEDULING_TYPE_DWRR` | qosorch.h L45, qosorch.cpp L1381-1383 |
| `scheduler_algo_WRR` | `"WRR"` | `SAI_SCHEDULING_TYPE_WRR` | qosorch.h L46, qosorch.cpp L1385-1387 |
| `scheduler_algo_STRICT` | `"STRICT"` | `SAI_SCHEDULING_TYPE_STRICT` | qosorch.h L47, qosorch.cpp L1389-1391 |

未知の値は `SWSS_LOG_ERROR("Unknown scheduler type value:%s")` → `task_invalid_entry` でエントリ全破棄。

---

## 2. weight フィールド (qosorch.h L48)

| 定数名 | 値 | SAI 属性 | ソース |
|--------|----|---------|--------|
| `scheduler_weight_field_name` | `"weight"` | `SAI_SCHEDULER_ATTR_SCHEDULING_WEIGHT` | qosorch.h L48, qosorch.cpp L1399-1404 |

- `stoi()` で int 変換後 `(uint8_t)` キャスト。YANG range `"1..100"` はコードで未検証。
- 0-255 の範囲外は暗黙に切り捨て（バリデーションなし）。

---

## 3. meter_type enum 文字列 (qosorch.cpp L75-78)

| 定数名 | 値 | SAI 変換先 | ソース |
|--------|----|-----------|--------|
| `scheduler_meter_type_field_name` | `"meter_type"` | — (フィールドキー) | qosorch.h L49 |
| `scheduler_meter_map["packets"]` | `"packets"` | `SAI_METER_TYPE_PACKETS` | qosorch.cpp L76 |
| `scheduler_meter_map["bytes"]` | `"bytes"` | `SAI_METER_TYPE_BYTES` | qosorch.cpp L77 |

`scheduler_meter_map.at()` は例外非キャッチ。未知値で `std::out_of_range` → orchagent クラッシュ。

---

## 4. bandwidth rate/burst フィールド名 (qosorch.h L50-53)

| 定数名 | 値 | SAI 属性 | コメント | ソース |
|--------|----|---------|---------|--------|
| `scheduler_min_bandwidth_rate_field_name` | `"cir"` | `SAI_SCHEDULER_ATTR_MIN_BANDWIDTH_RATE` | Committed Information Rate | qosorch.h L50 |
| `scheduler_min_bandwidth_burst_rate_field_name` | `"cbs"` | `SAI_SCHEDULER_ATTR_MIN_BANDWIDTH_BURST_RATE` | Committed Burst Size | qosorch.h L51 |
| `scheduler_max_bandwidth_rate_field_name` | `"pir"` | `SAI_SCHEDULER_ATTR_MAX_BANDWIDTH_RATE` | Peak Information Rate | qosorch.h L52 |
| `scheduler_max_bandwidth_burst_rate_field_name` | `"pbs"` | `SAI_SCHEDULER_ATTR_MAX_BANDWIDTH_BURST_RATE` | Peak Burst Size | qosorch.h L53 |

各フィールドは存在するときのみ SAI 属性を設定。省略時は SAI デフォルト（0 相当）。

---

## 5. SAI API 呼び出し

| 操作 | SAI 関数 | エラー時 |
|------|---------|---------|
| 作成 | `sai_scheduler_api->create_scheduler()` | `SWSS_LOG_ERROR("Failed to create scheduler profile")` → 処理中断 |
| 更新 | `sai_scheduler_api->set_scheduler_attribute()` | `SWSS_LOG_ERROR("fail to set scheduler attribute, id:%d")` |
| 削除 | `sai_scheduler_api->remove_scheduler()` | `SWSS_LOG_ERROR("Failed to remove scheduler profile")` |

---

## 特記事項

1. **`priority` フィールドは dead field**: `qosorch.h` に対応定数なし。`handleSchedulerTable` の if-else チェーン (L1378-1438) に分岐なし。SET で `priority` を含めると `Unknown field:priority` → `task_invalid_entry` で全フィールド SAI 未反映。
2. **`scheduler_field_name`** (= `"scheduler"`) は QUEUE テーブルから SCHEDULER を参照する leafref フィールド名 (qosorch.h L22)。SCHEDULER テーブル自体のフィールドではない。
3. **weight の有効範囲**: YANG `range "1..100"` はコードで強制されない。SAI 実装依存でベンダーによる。

---

## 出典

- `sonic-net/sonic-swss/orchagent/qosorch.h` L22, L44-53
- `sonic-net/sonic-swss/orchagent/qosorch.cpp` L75-78, L1378-1494
