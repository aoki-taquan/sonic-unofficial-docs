# PORT_STORM_CONTROL — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_4)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 該当なし

minigraph.py / config_samples.py / db_migrator.py / init_cfg.json.j2 に PORT_STORM_CONTROL への代入なし。CLI (`config storm-control`) で明示設定。

**結論**: Phase 6 派生なし。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

PortsOrch (常時登録) が PORT_STORM_CONTROL を処理。条件付き登録なし。ハードウェア非サポート時は SAI 設定失敗として記録。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### portsorch.cpp — PORT_STORM_CONTROL ハンドラ分岐

| 操作 | 処理 |
|------|------|
| SET | `setStormControl()` → SAI policer 作成 + INGRESS_STORM_CONTROL 属性設定 |
| DEL | `unsetStormControl()` → SAI policer 削除、ポート属性クリア |

storm type (`broadcast`/`multicast`/`unknown-unicast`) で別々の SAI policer を作成。

early return:
- ポート不在 → `task_need_retry`
- `kbps_value` <= 0 → `task_invalid_entry`
- SAI 作成失敗 → `task_failed`

<!-- /handler-branching -->
