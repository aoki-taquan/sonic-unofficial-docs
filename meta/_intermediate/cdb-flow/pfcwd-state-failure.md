# pfcwd-state failure behavior 調査ノート

対象ファイル: `docs/reference/config-db/pfcwd-state.md`
Phase: D (failure-behavior)
調査日: 2026-05-18

## 調査ソース

- `sonic-net/sonic-swss` orchagent/pfcwdorch.cpp (master)
- `sonic-net/sonic-swss` orchagent/pfcactionhandler.cpp (master)

## doTask タスクステータス管理

`PfcWdOrch::doTask()` (pfcwdorch.cpp:64-120) はエントリごとに `task_process_status` を評価し、
`task_need_retry` のみキューに残留（再試行）、それ以外はキューから除去する。

```
task_success        → erase(it++)
task_need_retry     → ++it (残留・再試行)
task_invalid_entry  → erase(it++) (永久破棄)
task_failed         → erase(it++) (永久破棄)
```

## createEntry 失敗パス (pfcwdorch.cpp:182-319)

1. getPort 失敗 → task_invalid_entry (L195-196)
2. 物理ポートでない → task_invalid_entry (L201-202)
3. action 不明 → task_invalid_entry (L230-231)
4. Cisco 8000 + forward → task_invalid_entry (L234-235)
5. Broadcom DLR + action 不一致 → task_invalid_entry (L260-262)
6. Broadcom DLR + SAI set_switch_attribute 失敗 → task_invalid_entry (L250-251)
7. 不明フィールド → task_invalid_entry (L273-277)
8. 例外 (パース失敗) → task_invalid_entry (L282-295)
9. detection_time 欠如 → task_invalid_entry (L302-303)
10. pfc_stat_history 値不正 → task_invalid_entry (L307-308)
11. startWdOnPort 失敗 → task_need_retry (L313-314)

## deleteEntry 失敗パス (pfcwdorch.cpp:323-338)

- stopWdOnPort 失敗 → task_failed (L332-333)
  - SAI エラーまたは COUNTERS_DB 操作失敗時に発生
  - DEL 側は retry なし

## allPortsReady ガード

doTask 冒頭 (L66-69) で `gPortsOrch->allPortsReady()` チェック。
未 ready の場合は doTask 全体を即時 return。ポート初期化完了まで全エントリが延期される。

## STATE_DB / ERROR_TABLE

失敗フィードバックは syslog のみ。STATE_DB / ERROR_TABLE への書き込みなし。
