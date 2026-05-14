# NVGRE_TUNNEL — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_3)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 該当なし

minigraph.py / config_samples.py / db_migrator.py / init_cfg.json.j2 に NVGRE_TUNNEL への代入なし。CLI で明示設定。

**結論**: Phase 6 派生なし。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

TunnelDecapOrch が NVGRE_TUNNEL を処理。orchdaemon で **常時** 生成。条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### tunneldecaporch — doTask 分岐

| 操作 | 処理 |
|------|------|
| SET | `createNvgreTunnel()` → SAI tunnel object 作成 |
| DEL | `removeNvgreTunnel()` → SAI tunnel 削除 |

early return: `src_ip` 不正 / SAI ハードウェア非サポート → `task_invalid_entry` return。

<!-- /handler-branching -->
