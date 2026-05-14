# PORT_QOS_MAP — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_4)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### db_migrator.py — 2 種のマイグレーション (重要)

```
# db_migrator.py:700-714  migrate_port_qos_map_global()
def migrate_port_qos_map_global(self):
    qos_maps = self.configDB.get_table('PORT_QOS_MAP')
    dscp_to_tc_map_table_names = [...]
    if dscp_to_tc_map_table_names:
        self.configDB.set_entry('PORT_QOS_MAP', 'global',
            {"dscp_to_tc_map": dscp_to_tc_map_table_names[0]})
```

既存 DSCP_TO_TC_MAP から `global` エントリを **自動生成** — Phase 6 典型派生。

```
# db_migrator.py:555-580  migrate_qos_fieldval_reference_format()
('PORT_QOS_MAP', ['dscp_to_tc_map', 'dot1p_to_tc_map', 'tc_to_pg_map',
                   'pfc_enable', 'pfcwd_sw_enable', 'tc_to_queue_map', 'scheduler'])
```

フィールド参照フォーマット正規化マイグレーション。

### minigraph.py / config_samples.py / init_cfg.json.j2 — 該当なし

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

QosOrch (常時登録) が PORT_QOS_MAP を購読。条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### qosorch.cpp — PORT_QOS_MAP doTask フィールド別 dispatch

| フィールド | SAI 属性 |
|-----------|---------|
| `dscp_to_tc_map` | SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP |
| `dot1p_to_tc_map` | SAI_PORT_ATTR_QOS_DOT1P_TO_TC_MAP |
| `tc_to_pg_map` | SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP |
| `pfc_enable` | SAI_PORT_ATTR_PRIORITY_FLOW_CONTROL |
| `scheduler` | SAI_PORT_ATTR_QOS_SCHEDULER_PROFILE_ID |

early return:
- ポート不在 → `task_need_retry`
- 参照先 MAP 未作成 → `task_need_retry`
- SAI 設定失敗 → `task_failed`

<!-- /handler-branching -->
