# DEBUG_COUNTER — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/debug-counter.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `DebugCounterOrch` (orchagent 直接 CFG 購読) |
| 2. CFG→APPL 翻訳 | なし (orchagent が直接 CONFIG_DB を購読) |
| 3. APPL→SAI | `sai_debug_counter_api` — デバッグカウンタ (drop reason 集計) を SAI に作成/削除 |
| 4. タイミング+副作用 | orchagent が CONFIG_DB 変化を検知後即座に SAI debug counter を作成/削除。カウンタは作成後即座に集計開始。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`DebugCounterOrch` (orchagent 直接 CFG 購読) が CONFIG_DB の `DEBUG_COUNTER` テーブルを購読する。

`DEBUG_COUNTER` と `DEBUG_COUNTER_DROP_REASON` は対で使用。drop reason リストで集計対象を指定。

### 段階 2 — CFG→APPL 翻訳

なし (orchagent が直接 CONFIG_DB を購読)

### 段階 3 — APPL→SAI

`sai_debug_counter_api` — デバッグカウンタ (drop reason 集計) を SAI に作成/削除

### 段階 4 — タイミングと副作用

**適用タイミング**: orchagent が CONFIG_DB 変化を検知後即座に SAI debug counter を作成/削除。カウンタは作成後即座に集計開始。

**副作用**: デバッグカウンタはハードウェアリソースを消費。作成後は `COUNTERS_DB` に counter OID がマッピングされ `show dropcounters` で確認可能。
<!-- /runtime-trace -->
```
