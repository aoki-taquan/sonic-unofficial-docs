# dash-acl — Phase D: 失敗挙動スキャンノート

対象スラグ: `dash-acl`
調査日: 2026-05-17 (chore/q67-f-dash-acl2-next)
スキャン対象:
- `sonic-swss/orchagent/dash/dashaclorch.cpp`
- `sonic-swss/orchagent/dash/dashaclgroupmgr.cpp`

---

## Phase D: 失敗挙動マトリクス

### DashAclOrch::doTask — タスクディスパッチ層の失敗

| 失敗条件 | 結果 | ログ | evidence |
|----------|------|------|----------|
| `table_name` + `op` の組み合わせが `TaskMap` に存在しない | `task_failed`（エントリ破棄） | `SWSS_LOG_ERROR "Unknown task : %s - %s"` | `dashaclorch.cpp:130-134` |

### DASH_ACL_GROUP_TABLE SET (taskUpdateDashAclGroup) の失敗

| 失敗条件 | 結果 | ログ | evidence |
|----------|------|------|----------|
| グループ ID が既に `m_groups_table` に存在する（重複 SET） | `task_failed` | `SWSS_LOG_WARN "Cannot update attributes of ACL group %s"` | `dashaclorch.cpp:231-235` |
| `from_pb()` 失敗 — `ip_version` が UNSPECIFIED または不正値 | `task_failed` | なし（`from_pb` 内で `to_sai()` が `false` を返す） | `dashaclgroupmgr.cpp:84-92` |
| SAI `create_dash_acl_group` 失敗 | `handleSaiCreateStatus()` 経由（通常プロセス終了またはリトライ） | `SWSS_LOG_ERROR "Failed to create ACL group: %d, %s"` | `dashaclgroupmgr.cpp:168-172` |

### DASH_ACL_GROUP_TABLE DEL (taskRemoveDashAclGroup) の失敗

| 失敗条件 | 結果 | ログ | evidence |
|----------|------|------|----------|
| グループが ENI にバインド中（`m_in_tables` または `m_out_tables` が非空） | `task_need_retry`（自動リトライ） | `SWSS_LOG_ERROR "ACL group %s still has %zu references"` | `dashaclgroupmgr.cpp:234-238` |
| グループ ID が存在しない場合の DEL | `task_success`（冪等: 何もしない） | `SWSS_LOG_INFO "ACL group %s doesn't exist"` | `dashaclgroupmgr.cpp:225-229` |
| SAI `remove_dash_acl_group` 失敗 | `handleSaiRemoveStatus()` 経由 | `SWSS_LOG_ERROR "Failed to remove ACL group: %d, %s"` | `dashaclgroupmgr.cpp:208-211` |

### DASH_ACL_RULE_TABLE SET (taskUpdateDashAclRule) の失敗

| 失敗条件 | 結果 | ログ | evidence |
|----------|------|------|----------|
| キーが `group_id:rule_num` 形式でない（`lexical_convert` 例外） | `task_failed` | `SWSS_LOG_ERROR "Failed to parse key %s"` | `dashaclorch.cpp:261-265` |
| `from_pb()` 失敗 — `src_addr`/`dst_addr` の IP プレフィックスパースエラー | `task_failed` | なし（`to_sai()` が `false` を返す） | `dashaclgroupmgr.cpp:43-51` |
| グループが ENI にバインド中の状態でルール追加 | `task_failed` | `SWSS_LOG_INFO "Failed to set dash ACL rule %s:%s, ACL group is bound to the ENI"` | `dashaclorch.cpp:274-278` |
| 参照グループ (`group_id`) が未作成 | `task_need_retry`（自動リトライ） | `SWSS_LOG_INFO "ACL group %s doesn't exist, waiting for group creating before creating rule %s"` | `dashaclgroupmgr.cpp:385-389` |
| `src_tag` / `dst_tag` に指定されたタグが未作成 | `task_need_retry`（自動リトライ） | `SWSS_LOG_INFO "ACL tag %s doesn't exist, waiting for tag creating before creating rule %s"` | `dashaclgroupmgr.cpp:393-408` |
| SAI `create_dash_acl_rule` 失敗 | `handleSaiCreateStatus()` 経由 | `SWSS_LOG_ERROR "Failed to create ACL rule: %d, %s"` | `dashaclgroupmgr.cpp:369-371` |

### DASH_ACL_IN/OUT_TABLE SET (taskUpdateDashAclIn/Out) の失敗

| 失敗条件 | 結果 | ログ | evidence |
|----------|------|------|----------|
| キーが `eni:stage` 形式でない（`lexical_convert` 例外） | `task_failed` | `SWSS_LOG_ERROR "Invalid key : %s"` | `dashaclorch.cpp:322-325` |
| ステージ番号が `1`〜`5` 範囲外 | `task_failed` | `SWSS_LOG_ERROR "Invalid stage : %s"` → `invalid_argument` スロー | `dashaclorch.cpp:69-72` |
| 参照グループ (`acl_group_id`) が `m_groups_table` に未存在 | `task_failed`（自動回復なし） | `SWSS_LOG_INFO "Failed to bind ACL group %s to ENI %s. ACL group does not exist"` | `dashaclgroupmgr.cpp:442-447` |
| グループのルール件数が 0 件 | `task_failed`（自動回復なし） | `SWSS_LOG_INFO "Failed to bind ACL group %s to ENI %s. ACL group has no rules attached."` | `dashaclgroupmgr.cpp:451-454` |
| ENI (`eni_id`) が `DashOrch` に未登録 | `task_need_retry`（自動リトライ） | `SWSS_LOG_INFO "eni %s cannot be found"` | `dashaclgroupmgr.cpp:457-461` |
| SAI `set_eni_attribute` 失敗（バインド） | `handleSaiSetStatus(SAI_API_DASH_ENI, …)` 経由 | `SWSS_LOG_ERROR "Failed to bind ACL group to ENI: %d"` | `dashaclgroupmgr.cpp:431-434` |

### DASH_ACL_IN/OUT_TABLE DEL (taskRemoveDashAclIn/Out) の失敗

| 失敗条件 | 結果 | ログ | evidence |
|----------|------|------|----------|
| キーが `eni:stage` 形式でない | `task_failed` | `SWSS_LOG_ERROR "Invalid key : %s"` | `dashaclorch.cpp:348-351` |
| ACL エントリが `m_dash_acl_in/out_table` に存在しない | `task_success`（冪等） | `SWSS_LOG_WARN "ACL %s doesn't exist"` | `dashaclorch.cpp:356-359` |
| SAI `set_eni_attribute` 失敗（アンバインド） | `handleSaiSetStatus(SAI_API_DASH_ENI, …)` 経由 | `SWSS_LOG_ERROR "Failed to unbind ACL group from ENI: %d"` | `dashaclgroupmgr.cpp:487-490` |

### DASH_PREFIX_TAG_TABLE SET/DEL の失敗

| 失敗条件 | 結果 | ログ | evidence |
|----------|------|------|----------|
| `from_pb()` 失敗（タグの IP プレフィックスパースエラー） | `task_failed` | なし（`to_sai()` が `false` を返す） | `dashaclorch.cpp:290-294` |
| タグが使用中（グループが `m_tag_groups` でアタッチ中）の DEL | `task_need_retry`（自動リトライ） | `DashTagMgr::remove()` 内でチェック | `dashtagmgr.cpp`（別スキャン） |

### 非対称なリトライ特性（重要）

`DASH_ACL_IN/OUT_TABLE` バインド時の失敗は **`task_failed` と `task_need_retry` が混在** する：

- グループ未作成 → **`task_failed`**（エントリ破棄、SDN コントローラ側で再投入が必要）
- ENI 未作成 → **`task_need_retry`**（キューに残し自動リトライ）

これはグループが「事前作成必須の静的依存」、ENI が「後から来ることを許容する動的依存」として設計されているため。
