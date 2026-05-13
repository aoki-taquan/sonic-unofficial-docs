# CRM 値依存挙動分析

## enum フィールド
1. `<resource>_threshold_type`: `percentage` / `used` / `free`（全リソース共通）

## 値依存挙動

### threshold_type
- `percentage` (既定: `CRM_THRESHOLD_TYPE_DEFAULT`): high/low 閾値を使用率 % として解釈。
  `high_threshold > 100` または `low_threshold > 100` の場合 YANG/crmorch が拒否（crmorch.cpp:428）。
  `THRESHOLD_EXCEEDED` アラートは `used/total * 100 >= high_threshold` で発火。
- `used`: high/low 閾値を「使用中エントリ数」の絶対値として解釈。ASIC の total 数に依存しない。
  大きなハードウェアでは percent より細かく制御可能。
- `free`: high/low 閾値を「空きエントリ数」として解釈。残り少なくなったら alert するパターン。
  `free < low_threshold` で THRESHOLD_CLEAR が発火する（超過/クリアの向きが逆になる）。

### DASH 系リソース (when 条件)
- `DEVICE_METADATA.localhost.switch_type = 'dpu'` のときのみ `dash_*_threshold_type` が有効 (YANG `when` 制約)。
  通常スイッチに設定しても YANG validator で拒否される。

## ソース
- `sonic-swss/orchagent/crmorch.cpp:13, 299-303, 428, 1152-1162`
