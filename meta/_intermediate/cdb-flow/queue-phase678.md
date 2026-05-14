# QUEUE — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_4)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### db_migrator.py — QUEUE フィールド参照フォーマット移行

```
# db_migrator.py:575
('QUEUE', ['scheduler', 'wred_profile']),
```

`migrate_qos_fieldval_reference_format()` の対象に QUEUE が含まれる。`scheduler` / `wred_profile` フィールド値を旧フォーマットから新フォーマットに正規化。

### minigraph.py / config_samples.py / init_cfg.json.j2 — 該当なし

(config_samples.py:38-50 は QoS サンプルとして QUEUE を含むが自動生成ではない)

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

QosOrch (常時登録) が QUEUE テーブルを購読し SAI キューにスケジューラ / WRED プロファイルを適用。条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### qosorch.cpp — QUEUE doTask フィールド別 dispatch

| フィールド | SAI 属性 |
|-----------|---------|
| `scheduler` | SAI_QUEUE_ATTR_SCHEDULER_PROFILE_ID |
| `wred_profile` | SAI_QUEUE_ATTR_WRED_PROFILE_ID |

early return:
- キュー不在 (ポート初期化前) → `task_need_retry`
- `scheduler` が SCHEDULER テーブル未登録 → `task_need_retry`
- `wred_profile` が WRED_PROFILE テーブル未登録 → `task_need_retry`
- SAI 属性設定失敗 → `task_failed`

DEL: スケジューラ/WRED を NULL にリセット。

<!-- /handler-branching -->
