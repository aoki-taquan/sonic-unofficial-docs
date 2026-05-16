# DASH_PREFIX_TAG_TABLE — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/dash-prefix-tag.md` Phase C 追加分。
DASH_PREFIX_TAG_TABLE は orchagent 内メモリ (`m_tag_table`) に保持され、SAI に直接書かない。
外部テーブルとの依存は「参照される側」であり、タグ自体が他テーブルを参照する依存は存在しない。
ただし、タグが ACL rule から参照される際の双方向依存を実装レベルで網羅した。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/dash/dashtagmgr.cpp` | タグの CRUD・attach/detach 実装。`m_groups` でどの ACL group がタグを使用中かを追跡 |
| `sonic-swss/orchagent/dash/dashaclorch.cpp` | `PbWorker<PrefixTag>` として `taskUpdateDashPrefixTag` / `taskRemoveDashPrefixTag` をハンドル |
| `sonic-swss/orchagent/dash/dashaclgroupmgr.cpp` | `DashAclRule` の `src_tag` / `dst_tag` を処理し、タグ存在確認 + `getPrefixes()` で SAI ACL エントリに展開 |

## YANG leafref

DASH_PREFIX_TAG_TABLE は YANG 未定義テーブルのため leafref は存在しない。全参照が実装レベルの暗黙参照。

## 暗黙参照 (実装レベル)

### 1. DASH_ACL_RULE_TABLE (src_tag / dst_tag フィールド) ← タグを「参照する側」

- **参照先テーブル**: `DASH_PREFIX_TAG_TABLE`（本テーブル）
- **参照方向**: 存在確認 + prefix 展開（参照される側）
- **条件**: `DASH_ACL_RULE_TABLE` エントリの `src_tag` または `dst_tag` にタグ名が指定されたとき
- **参照元**: `dashaclgroupmgr.cpp` L393–409 (`taskCreateDashAclRule` 内の tag 存在確認), L316–327 (`createRule` 内の `getPrefixes()` 呼び出し)
- **意味**:
  - タグが `m_tag_table` に存在しない場合 → `task_need_retry`（タグ作成後に自動再処理）
  - タグが存在する場合 → `DashTagMgr::getPrefixes(tag_id)` で prefix 集合を取得し SAI ACL エントリに展開
  - タグが参照中 (`m_groups` 非空) の間は `DASH_PREFIX_TAG_TABLE` への DEL が `task_need_retry` になる（逆依存）

### 2. DASH_ACL_GROUP (attach/detach によるライフサイクル連動)

- **参照先テーブル**: `DASH_ACL_GROUP_TABLE`（間接）
- **参照方向**: group_id を通じた refcount 管理（タグが参照されるグループ追跡）
- **条件**: ACL rule が group にバインドされるとき
- **参照元**: `dashaclgroupmgr.cpp` L558–575 (`attachTags` / `detachTags`), `dashtagmgr.cpp` L112–137 (`DashTagMgr::attach` / `detach`)
- **意味**: rule 作成時に `attachTags()` → `DashTagMgr::attach(tag_id, group_id)` で `m_groups.insert(group_id)`。rule 削除時に `detachTags()` → `detach()` で `m_groups.erase(group_id)`。`m_groups` が空になるまでタグ削除は拒否される。

## 参照方向サマリ

```
DASH_PREFIX_TAG_TABLE (本テーブル)
  ← [暗黙・参照される] DASH_ACL_RULE_TABLE.src_tag / dst_tag
        (ACL rule 作成時: 存在確認 → task_need_retry if absent; 存在時: getPrefixes() で SAI 展開)
  ← [暗黙・参照される] DASH_ACL_GROUP_TABLE (group_id を m_groups で追跡)
        (attach/detach で m_groups を更新; 非空の間は DEL が task_need_retry)

タグ自体が他テーブルを参照する YANG leafref / 実装レベル参照は存在しない。
```

## evidence

- `dashaclgroupmgr.cpp`: L53–60 (`src_tag` / `dst_tag` のパース), L393–409 (tag 存在確認と `task_need_retry`), L316–327 (`getPrefixes()` 呼び出し), L558–575 (`attachTags` / `detachTags`)
- `dashtagmgr.cpp`: L84–88 (`m_groups.empty()` ガード → `task_need_retry`), L112–137 (`attach` / `detach`)
- `dashaclorch.cpp`: L111–112 (PbWorker<PrefixTag> 登録), L283–311 (`taskUpdateDashPrefixTag` / `taskRemoveDashPrefixTag`)
