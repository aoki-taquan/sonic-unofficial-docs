# scheduler-orch Phase B (ordering) — 調査メモ

## ソース
- `sonic-swss/orchagent/qosorch.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
  - `handleSchedulerTable()` DEL ハンドラ: `isObjectBeingReferenced()` チェック → `m_pendingRemove = true` / `task_need_retry`
  - `handleQueueTable()`: `resolveFieldRefValue()` で SCHEDULER 参照を解決 → 未登録なら `task_need_retry`

## 依存関係
- ADD 順: SCHEDULER → QUEUE（leafref 参照）
- DEL 順: QUEUE 参照解除 → SCHEDULER 削除
- `config qos reload` (`qos_config.j2`) は SCHEDULER ブロックを QUEUE より先に展開するため CLI 経由では問題なし

## 結論
Phase B (ordering) ブロックを scheduler-orch.md に追加。
