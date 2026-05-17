# DASH_PREFIX_TAG_TABLE — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-17 (q67-f-dash-prefix-tag2-next)

ソース:
- `sonic-net/sonic-swss/orchagent/dash/dashtagmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-net/sonic-swss/orchagent/dash/dashaclorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-net/sonic-swss/orchagent/dash/dashaclgroupmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

### retry パターン概要

`DASH_PREFIX_TAG_TABLE` のタスク処理は `DashAclOrch::taskUpdateDashPrefixTag` / `taskRemoveDashPrefixTag` で行われ、`task_process_status` を返す。

| パターン | 代表的なトリガー | 挙動 |
|---|---|---|
| **`task_need_retry`** | 参照中タグ（ACL rule 紐付き中）の DEL | `m_toSync` に残し次 `doTask()` で自動再試行。上限なし |
| **`task_failed`** | `from_pb()` 失敗・重複 SET・存在しないタグへの UPDATE・`ip_version` 変更試行 | エントリ破棄。自動回復なし |
| **`task_success`** | 正常 create/update・存在しないタグへの DEL（冪等） | エントリ削除 |

### SET 処理における失敗詳細

#### protobuf デシリアライズ失敗（`from_pb()` false）

`from_pb(data, tag)` が `false` を返すと `taskUpdateDashPrefixTag` は即 `task_failed`。

失敗するケース:
1. `ip_version` が `0` (= `IP_VERSION_UNSPECIFIED` / proto3 デフォルト): `to_sai(data.ip_version(), tag.m_ip_version)` が `false` を返す (`dashtagmgr.cpp:11-13`, `pbutils.cpp:9-24`)
2. `ip_version` が `1` / `2` 以外の不正な enum 値: 同様に `to_sai()` が `false`
3. `prefix_list` 内のプレフィックスパース失敗（形式不正な `IpPrefix`）: `to_sai(data.prefix_list(), tag.m_prefixes)` が `false` (`dashtagmgr.cpp:16-18`, `pbutils.cpp:74-93`)

いずれも SAI 呼び出し前、メモリ書き込み前に失敗する。

#### 重複 SET（create 時の既存チェック）

タグ ID が `m_tag_table` に既に存在する状態で SET が届き、かつ内部で `create()` ルートに入った場合: `SWSS_LOG_INFO` は記録されず `task_failed` を返す。(`dashtagmgr.cpp:34-37`)

ただし `taskUpdateDashPrefixTag` は `exists(tag_id)` で分岐して `update()` / `create()` を切り替えるため、**通常の重複 SET は `update()` ルートに進む**。`create()` の重複エラーは直接呼び出しからのみ発生する。

#### `ip_version` の変更試行（update 時の不変制約）

既存タグへの SET で `ip_version` が変更されていた場合: `SWSS_LOG_WARN "'ip_version' changing is not supported for tag %s"` → `task_failed`。`prefix_list` は更新されない。(`dashtagmgr.cpp:61-65`)

#### 存在しないタグへの UPDATE

`m_tag_table` に存在しないタグ ID への update 経路（実装上は `exists()` チェックで create 側に誘導されるため直接は発生しないが）:  `SWSS_LOG_ERROR "Prefix tag %s does not exist"` → `task_failed`。(`dashtagmgr.cpp:52-57`)

### DEL 処理における失敗詳細

#### ACL rule 参照中タグの削除（`m_groups` 非空）

`m_tag_table[tag_id].m_groups` が空でない（= 何らかの ACL group が当該タグを参照している）場合:
`SWSS_LOG_WARN "Prefix tag %s is still in use by ACL rule(s)"` → `task_need_retry`。

全参照 ACL rule が削除されて `detachTags()` → `detach()` が呼ばれ `m_groups` が空になると、次の `doTask()` ループで DEL が成功する。(`dashtagmgr.cpp:84-88`)

#### 存在しないタグへの DEL（冪等）

`m_tag_table` に存在しないタグへの DEL: `SWSS_LOG_WARN "Prefix tag %s does not exist"` → `task_success`。(`dashtagmgr.cpp:78-81`)

### ACL rule 作成側への波及（タグ未作成時の retry）

`DashAclGroupMgr::createRule()` は、`src_tag` / `dst_tag` に指定されたタグが `m_tag_table` に存在しない場合に `task_need_retry` を返す。これはタグ側の失敗ではなく、タグ不在による ACL rule 側の待機だが、タグが正しく作成されれば自動解消する。(`dashaclgroupmgr.cpp:393-409`)

### 失敗後の状態整合性

- `task_failed` でエントリが破棄されると、`DashAclOrch::doTask()` の `doTask()` ループは WARN ログを出力し `erase(it)` でキューから除去する (`dashaclorch.cpp:146-153`)
- タグはオーケストレーターメモリ (`m_tag_table`) にのみ存在し、SAI への書き込みはないため、`task_failed` による部分的な ASIC 汚染は発生しない
- `task_need_retry` のエントリはキューに残留し、上限なく自動再試行される（SAI スロットリングなし）

### グレップカバレッジ

| 項目 | ソース位置 |
|---|---|
| `from_pb(data, tag)` 失敗 → `task_failed` | `dashaclorch.cpp:291-294` |
| `create()` 重複 → `task_failed` | `dashtagmgr.cpp:34-37` |
| `update()` 不存在 → `task_failed` | `dashtagmgr.cpp:52-57` |
| `update()` `ip_version` 変更 → `task_failed` | `dashtagmgr.cpp:61-65` |
| `remove()` `m_groups` 非空 → `task_need_retry` | `dashtagmgr.cpp:84-88` |
| `remove()` 不存在 → `task_success` | `dashtagmgr.cpp:78-81` |
| ACL rule 側 tag 未作成 → `task_need_retry` | `dashaclgroupmgr.cpp:393-409` |

<!-- /failure -->
