# pfcwd-state — Phase E ハードコード定数調査メモ

## 調査対象

- `sonic-net/sonic-swss` `orchagent/pfcwdorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-net/sonic-swss` `orchagent/pfcactionhandler.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 発見した定数

### pfcwdorch.cpp

| 定数名 | 値 | 行 | 用途 |
|--------|----|----|------|
| `PFC_WD_TC_MAX` | `8` | L28 | lossless TC スキャン上限（queue index 0–7）。ハードウェア最大 TC 数と一致 |
| `PFC_WD_DETECTION_TIME_MIN` | `100` (ms) | L23 | `detection_time` の下限値。`to_uint<uint32_t>()` の min 引数に渡される |
| `PFC_WD_DETECTION_TIME_MAX` | `5000` (ms) (= 5 × 1000) | L22 | `detection_time` の上限値。5 秒 |
| `PFC_WD_RESTORATION_TIME_MIN` | `100` (ms) | L25 | `restoration_time` の下限値 |
| `PFC_WD_RESTORATION_TIME_MAX` | `60000` (ms) (= 60 × 1000) | L24 | `restoration_time` の上限値。60 秒 |
| `PFC_WD_POLL_TIMEOUT` | `5000` (ms) | L26 | flex-counter ポーリングタイムアウト |
| `PFC_WD_GLOBAL` | `"GLOBAL"` | L14 | CONFIG_DB `PFC_WD|GLOBAL` キーのリテラル（グローバル設定エントリ） |
| `PFC_WD_IN_STORM` | `"storm"` | L20 | APPL_DB `PFC_WD_TABLE_INSTORM` に書き込まれる storm 中状態値 |

### pfcactionhandler.cpp

| 定数名 | 値 | 行 | 用途 |
|--------|----|----|------|
| `PFC_WD_QUEUE_STATUS` | `"PFC_WD_STATUS"` | L9 | COUNTERS_DB フィールド名リテラル |
| `PFC_WD_QUEUE_STATUS_OPERATIONAL` | `"operational"` | L10 | `PFC_WD_STATUS` の stable 状態値 |
| `PFC_WD_QUEUE_STATUS_STORMED` | `"stormed"` | L11 | `PFC_WD_STATUS` の storm 検知状態値 |

## COUNTERS_DB への影響

- `PFC_WD_TC_MAX=8` により per-port の登録は queue index 0–7 の最大 8 エントリ。PFC 有効 TC のみ実際に書き込まれる
- `DETECTION_TIME` の `[100, 5000]` ms 範囲を外れた値は `task_invalid_entry` となり COUNTERS_DB に書き込まれない
- `RESTORATION_TIME` の `[100, 60000]` ms 範囲を外れた値も同様
- `PFC_WD_STATUS` のフィールド名・値は C++ マクロリテラルであり YANG スキーマによる検証外
