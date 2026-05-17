# DASH_PREFIX_TAG_TABLE — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-17 (q67-f-dash-prefix-tag3-next)

ソース: `sonic-net/sonic-swss/orchagent/dash/dashtagmgr.cpp` + `dashaclorch.cpp` + `dashaclgroupmgr.cpp`
ref: 4305596156d70e9797e8a881b3d19b46de0bce0d

---

## Phase D: 失敗挙動マトリクス

### SET 処理における失敗経路

**`taskUpdateDashPrefixTag` → `from_pb()` → `DashTagMgr::create/update` チェーン**

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `ip_version` が proto3 デフォルト `0` (= `IP_VERSION_UNSPECIFIED`) | `from_pb()` → `to_sai(data.ip_version(), ...)` | `from_pb` が `false` → `taskUpdateDashPrefixTag` が `task_failed` 返却。エントリは `m_toSync.erase()` で恒久スキップ | なし (WARN ログなし、silent reject) | `dashtagmgr.cpp:11-14` |
| `ip_version` が 1/2 以外の未知値 | `to_sai(IpVersion, ...)` — `pbutils.cpp:9-24` | 同上: `false` → `task_failed` → 恒久スキップ | なし | `pbutils.cpp:9-24` |
| `prefix_list` の `IpPrefix` 変換失敗（アドレス不正） | `to_sai(data.prefix_list(), ...)` — `pbutils.cpp:74-93` | `from_pb` が `false` → `task_failed` → 恒久スキップ | なし | `dashtagmgr.cpp:16-19` |
| 同一 `tag_id` で重複 SET (既に存在するが `update` 呼出時、`ip_version` が変更されている) | `DashTagMgr::update()` L61-65 | `SWSS_LOG_WARN` + `task_failed`。`m_prefixes` 更新なし | WARN: `"'ip_version' changing is not supported for tag %s"` | `dashtagmgr.cpp:61-65` |
| `update()` 時に `tag_id` が `m_tag_table` に存在しない (登録前の update) | `DashTagMgr::update()` L52-57 | `SWSS_LOG_ERROR` + `task_failed` | ERROR: `"Prefix tag %s does not exist"` | `dashtagmgr.cpp:52-57` |
| `create()` 時に `tag_id` が既に存在する (重複 create) | `DashTagMgr::create()` L34-37 | `task_failed` (WARN/ERROR ログなし) | なし | `dashtagmgr.cpp:34-37` |

> **注**: `task_failed` を受け取ると `doTask()` は `m_toSync.erase(itr)` でエントリを削除し、WARN ログ `"Task %s - %s fail"` を出力する (`dashaclorch.cpp:149-151`)。自動リトライは行われない。

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| タグが ACL rule から参照中 (`m_groups` 非空) | `DashTagMgr::remove()` L84-88 | `task_need_retry`。タグは削除されず `m_toSync` に残留し次イベントループで再試行 | WARN: `"Prefix tag %s is still in use by ACL rule(s)"` | `dashtagmgr.cpp:84-88` |
| 未存在タグの DEL | `DashTagMgr::remove()` L78-82 | `task_success` (idempotent)。エラー扱いなし | WARN: `"Prefix tag %s does not exist"` | `dashtagmgr.cpp:78-82` |

> **注**: `task_need_retry` を受け取ると `doTask()` は `itr++` でエントリをキューに残したまま次へ進む (`dashaclorch.cpp:136-143`)。ACL rule が DEL されて `m_groups` が空になると次ループで DEL が成功する。

### 失敗後の状態サマリ

| 操作 | 戻り値 | エントリの運命 | STATE_DB / ASIC_DB 影響 |
|---|---|---|---|
| SET: `ip_version` 不正 | `task_failed` | 恒久スキップ（キューから削除） | なし（タグ未登録のまま） |
| SET: protobuf 変換失敗 | `task_failed` | 恒久スキップ | なし |
| SET: `ip_version` 変更 | `task_failed` | 恒久スキップ | タグの既存 `m_ip_version` 保持 |
| SET: 未存在タグへの update | `task_failed` | 恒久スキップ | なし |
| SET: 重複 create | `task_failed` | 恒久スキップ | 既存タグ変化なし |
| DEL: 参照中タグ | `task_need_retry` | 待機・自動再試行 | なし（タグ保持） |
| DEL: 未存在タグ | `task_success` | 正常削除（idempotent） | なし |

### 補足

- **SAI 非経由のため SAI エラーなし**: `DASH_PREFIX_TAG_TABLE` 処理は orchagent 内メモリ (`m_tag_table`) のみ操作し、SAI API を呼び出さない。したがって `SAI_STATUS_*` 系エラーや `handleSaiCreateStatus` / `handleSaiRemoveStatus` の呼び出しパスは存在しない。
- **STATE_DB への書き込みなし**: ACL ルールと異なり、タグの処理結果は STATE_DB / APPL_STATE_DB に書き込まれない。デバッグは syslog (`/var/log/swss/orchagent.log`) のみで確認できる。
- **`task_failed` の silent reject**: `ip_version` 不正や protobuf 変換失敗は WARN/ERROR ログが出ない場合があり、SDN コントローラ側から見ると「送ったのに反映されない」状態になる。orchagent ログの `"Task %s - %s fail"` 行を確認するか、`DashTagMgr::exists()` を通じて確認するしかない。
