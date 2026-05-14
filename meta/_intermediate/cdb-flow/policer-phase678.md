# POLICER — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_4)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 該当なし

minigraph.py / config_samples.py / db_migrator.py / init_cfg.json.j2 に POLICER への代入なし。CLI (`config policer`) で明示設定。

**結論**: Phase 6 派生なし。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### orchdaemon.cpp — PolicerOrch 登録

```cpp
// orchdaemon.cpp:402
gPolicerOrch = new PolicerOrch(policer_tables, gPortsOrch);
```

PolicerOrch は **常時** 生成 (MirrorOrch の依存として先に生成)。条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### policerorch.cpp — doTask 分岐

| 操作 | 処理 |
|------|------|
| SET | `addPolicer()` → SAI policer 作成 (`meter_type`, `mode`, `color_source` → SAI 属性変換) |
| DEL | `delPolicer()` → 参照カウント 0 のみ SAI policer 削除 |

early return:

| 条件 | 処理 |
|------|------|
| `meter_type` 不正 | `task_invalid_entry` |
| policer が他から参照中 (refcount > 0) | DEL 拒否 `task_failed` |
| SAI 作成失敗 | `task_failed` |

参照カウント管理: `increaseRefCount()` / `decreaseRefCount()` で MirrorOrch 等の依存を追跡。

<!-- /handler-branching -->
