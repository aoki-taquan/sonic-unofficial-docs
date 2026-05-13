# DEBUG_COUNTER 値依存挙動分析

## enum フィールド
1. `type`: `PORT_INGRESS_DROPS` / `PORT_EGRESS_DROPS` / `SWITCH_INGRESS_DROPS` / `SWITCH_EGRESS_DROPS`
2. `drop_monitor_status`: `enabled` / `disabled`

## 値依存挙動

### type
- `PORT_INGRESS_DROPS` / `PORT_EGRESS_DROPS`:
  `debugcounterorch` が `CounterType::PORT_DEBUG` として扱い、`installDebugFlexCounters` でポート単位に
  SAI debug counter を作成 (debugcounterorch.cpp:19-20, 90-92)。
  各ポートに紐付くため、ポート削除時にカウンタも削除される。
- `SWITCH_INGRESS_DROPS` / `SWITCH_EGRESS_DROPS`:
  `CounterType::SWITCH_DEBUG` として扱い、switch-wide のグローバルカウンタを作成 (debugcounterorch.cpp:21-22)。
  ポートに依存せず、スイッチ全体のドロップを集計。
- mandatory フィールドのため未設定は YANG エラー。

### drop_monitor_status
- `enabled`: `debug_monitor_enabled=true` がセットされ、ドロップ検知時に syslog アラートを発火する
  (debugcounterorch.cpp:232-234, 649, 708)。
- `disabled` (既定): ドロップモニタリング機能が停止。カウンタの蓄積は続くがアラートは発生しない。
- `enabled`/`disabled` 以外の値は SWSS_LOG_ERROR として拒否される (debugcounterorch.cpp:257)。

## ソース
- `sonic-swss/orchagent/debugcounterorch.cpp:18-22, 87-107, 232-257`
