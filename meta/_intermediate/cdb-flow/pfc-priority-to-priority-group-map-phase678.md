# PFC_PRIORITY_TO_PRIORITY_GROUP_MAP — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_3)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 直接派生なし

minigraph.py / config_samples.py / init_cfg.json.j2 に PFC_PRIORITY_TO_PRIORITY_GROUP_MAP の代入なし。

db_migrator.py の `migrate_qos_fieldval_reference_format()` (L555-580) は PORT_QOS_MAP / BUFFER_QUEUE / QUEUE / SCHEDULER を対象としており、PFC_PRIORITY_TO_PRIORITY_GROUP_MAP は明示リストに含まれない。

**結論**: Phase 6 直接派生なし。QoS プロビジョニングで config_db.json に静的設定。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

QosOrch (常時登録) が PFC_PRIORITY_TO_PRIORITY_GROUP_MAP を購読。条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### qosorch.cpp — PFC_PRIORITY_TO_PRIORITY_GROUP_MAP ハンドラ

| 操作 | 処理 |
|------|------|
| SET | `addPfcPrioToPgMap()` → SAI QOS_MAP_TYPE_PFC_PRIORITY_TO_PRIORITY_GROUP 作成 |
| DEL | `removePfcPrioToPgMap()` → SAI map 削除 |

early return: map がポートに適用中 → 削除拒否して `task_failed`。

<!-- /handler-branching -->
