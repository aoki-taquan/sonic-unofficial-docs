# QUEUE — 値依存挙動分析

## Phase 1: YANG フィールド全列挙

非 VOQ (`QUEUE_LIST`):
- `ifname` (key): leafref `PORT.name` または文字列 `CPU`
- `qindex` (key): 文字列（数値または範囲）
- `scheduler`: leafref `SCHEDULER.name`（省略可）
- `wred_profile`: leafref `WRED_PROFILE.name`（省略可）

VOQ (`VOQ_QUEUE_LIST`):
- `hostname` / `asic_name` / `ifname` / `qindex` (key)
- `scheduler` / `wred_profile`（省略可）

## Phase 2: per-value 挙動

### `ifname` 値別挙動
| 値 | 挙動 |
|----|------|
| `PORT.name` に存在する値 | 正常処理。SAI queue scheduler / WRED 適用。 |
| `CPU` | CPU queue 用。専用処理パス。 |
| 存在しないポート名 | `SWSS_LOG_ERROR("Port with alias:%s not found")` → `task_invalid_entry` でスキップ。 |

### `scheduler` フィールド
| 状態 | 挙動 |
|------|------|
| 省略 | スケジューラなし。ASIC デフォルト動作。 |
| 存在する SCHEDULER 名 | `qosorch` が SAI scheduler を queue に適用。 |
| 存在しない SCHEDULER 名 | `task_need_retry`（後で再試行）。解決不可なら `task_failed`。 |

### `wred_profile` フィールド
| 状態 | 挙動 |
|------|------|
| 省略 | WRED なし。 |
| 存在する WRED_PROFILE 名 | SAI WRED を queue に適用。 |
| 存在しない WRED_PROFILE 名 | `task_need_retry`。解決不可なら `task_failed`。 |

## Phase 3: ソース確認

- `sonic-swss/orchagent/qosorch.cpp`: key トークン数チェック、queue index 範囲検証、SAI scheduler group 検索。

## enum 有無

- `ifname`: enum なし（leafref / 文字列 `CPU`）
- `scheduler` / `wred_profile`: enum なし（leafref）
