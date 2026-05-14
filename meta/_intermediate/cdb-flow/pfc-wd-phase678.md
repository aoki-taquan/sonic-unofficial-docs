# PFC_WD — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_3)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### db_migrator.py — PFC_WD_TABLE → PFC_WD テーブル名変更マイグレーション

```
# db_migrator.py:158-165  migrate_pfc_wd_table()
def migrate_pfc_wd_table(self):
    data = self.configDB.get_table('PFC_WD_TABLE')
    for key in data:
        self.configDB.set_entry('PFC_WD', key, data[key])
    self.configDB.delete_table('PFC_WD_TABLE')
```

旧テーブル名 `PFC_WD_TABLE` → 新テーブル名 `PFC_WD` への自動移行 (Phase 6 派生代入)。

### minigraph.py / config_samples.py / init_cfg.json.j2 — 該当なし

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録 (重要)

### orchdaemon.cpp — PfcWdSwOrch の ASIC 能力条件分岐

同じ `PFC_WD` テーブルを購読するが、ハンドラクラスが ASIC 種別により切り替わる:

```cpp
// orchdaemon.cpp:666-836 (要約)
// デフォルト:
new PfcWdSwOrch<PfcWdZeroBufferHandler, PfcWdLossyHandler>(...) // L666-672
// DLR サポートあり:
new PfcWdSwOrch<PfcWdDlrHandler, PfcWdDlrHandler>(...)          // L786-792
// ACL ハードウェアサポート (Mellanox 等):
new PfcWdSwOrch<PfcWdAclHandler, PfcWdLossyHandler>(...)        // L724-730
// SAI DLR init サポート:
new PfcWdSwOrch<PfcWdSaiDlrInitHandler, PfcWdActionHandler>(...)// L836
```

Phase 7 の典型的な条件付き Handler 選択。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### pfcwdorch.cpp — doTask 分岐

```cpp
// pfcwdorch.cpp:64-73
if (consumer.getTableName() == CFG_PFC_WD_TABLE_NAME) { ... }
return;  // 他テーブルは即 return (early return)
```

createEntry() 内の early return:

| 条件 | 行 | 戻り値 |
|------|-----|--------|
| ポート不在 | L196 | `task_invalid_entry` |
| detection_time <= 0 | L202 | `task_invalid_entry` |
| action が unknown | L228 | `task_invalid_entry` |

action (`forward`/`drop`/`alert`) で `deserializeAction()` (L141-157) による enum dispatch → Handler テンプレートへ渡す。

<!-- /handler-branching -->
