# SCHEDULER — 値依存挙動分析

## Phase 1: YANG フィールド全列挙

- `name` (key): 文字列
- `type`: enum `DWRR` / `WRR` / `STRICT`。デフォルト `WRR`（実装側は未省略時 WRR 相当）。
- `weight`: uint8 (1..100)
- `priority`: uint8 (0..9)
- `meter_type`: enum `packets` / `bytes`。デフォルト `bytes`。
- `cir`: uint64
- `pir`: uint64（`cir > 0` 必須、`pir >= cir`）
- `cbs`: uint32（`cir > 0` 必須）
- `pbs`: uint32（`pir > 0` 必須、`pbs >= cbs`）

## Phase 2: per-value 挙動

### `type` 値別挙動
| 値 | SAI 変換 | 挙動 |
|----|----------|------|
| `DWRR` | `SAI_SCHEDULING_TYPE_DWRR` | 重み付きデフキュー方式。`weight` フィールドを使用。 |
| `WRR` | `SAI_SCHEDULING_TYPE_WRR` | 重み付きラウンドロビン。`weight` フィールドを使用。 |
| `STRICT` | `SAI_SCHEDULING_TYPE_STRICT` | 厳格優先。weight は無視。上位優先度 queue が常に先処理。 |
| その他 | なし | `SWSS_LOG_ERROR("Unknown scheduler type value:%s")` → `task_invalid_entry`。エントリ破棄。 |

### `meter_type` 値別挙動
| 値 | SAI 変換 | 挙動 |
|----|----------|------|
| `packets` | `SAI_METER_TYPE_PACKETS` | CIR/PIR の単位をパケット数として解釈。 |
| `bytes` | `SAI_METER_TYPE_BYTES` | CIR/PIR の単位をバイト数として解釈（デフォルト）。 |

### `weight` 値別挙動
| 値 | 挙動 |
|----|------|
| 1..100 | DWRR/WRR で使用。比率で帯域分配。 |
| 0 | YANG 制約外。uint8 として 0 は渡せるが YANG `range "1..100"` で拒否。 |

## Phase 3: ソース確認

- `sonic-swss/orchagent/qosorch.cpp:75-77`: `scheduler_meter_map = {"packets": SAI_METER_TYPE_PACKETS, "bytes": SAI_METER_TYPE_BYTES}` で 2 値のみ。
- `qosorch.cpp:1381-1396`: type が DWRR/WRR/STRICT 以外の場合 `task_invalid_entry`。
- `qosorch.cpp:1407`: `scheduler_meter_map.at()` — map に存在しない値は `std::out_of_range` 例外（実質 bytes/packets のみ）。

## enum 有無

- `type`: YANG enum `DWRR` / `WRR` / `STRICT`
- `meter_type`: YANG enum `packets` / `bytes`
