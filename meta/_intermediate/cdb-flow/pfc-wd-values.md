# PFC_WD フィールド値分析

## enum フィールド

### `action` (per-port エントリ)
YANG enum: `drop` / `forward` / `alert`
- `drop` (デフォルト実装動作): storm 検出時に対象 queue の ingress/egress を drop
- `forward`: storm 中も通過 (HOL ブロッキングリスクあり)
- `alert`: カウンタ更新のみ、パケットはドロップしない
- `forward` on Cisco 8000: `Unsupported action forward for platform cisco-8000` → SWSS_LOG_ERROR

### `pfc_stat_history` (per-port)
- `enable`: PFC 履歴統計収集開始
- `disable`: 収集停止
- その他: YANG pattern `enable|disable` 違反 → reject

## 数値範囲フィールド

### `detection_time` (per-port、ms)
- 100..5000 かつ ≥ POLL_INTERVAL: 正常
- < POLL_INTERVAL: must 違反 → reject
- 未設定: `PFC_WD_DETECTION_TIME missing` → SWSS_LOG_ERROR

### `restoration_time` (per-port、ms)
- 100..60000 かつ ≥ POLL_INTERVAL: 正常
- < POLL_INTERVAL: must 違反 → reject

### `POLL_INTERVAL` (GLOBAL エントリ、ms)
- 100..1000: 正常

## key 条件制約 (YANG when/must)
- `ifname = 'GLOBAL'` 時: action / detection_time / restoration_time / pfc_stat_history は禁止
- `ifname != 'GLOBAL'` 時: POLL_INTERVAL は禁止

## ソース
- sonic-pfcwd.yang (sonic-buildimage sha 9ea932ec)
- orchagent/pfcwdorch.cpp (sonic-swss)
