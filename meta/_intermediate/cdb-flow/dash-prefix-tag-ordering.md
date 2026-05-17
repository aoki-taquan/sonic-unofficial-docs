# DASH_PREFIX_TAG_TABLE — ordering (Phase B) 調査メモ

調査日: 2026-05-17
ソース: sonic-swss orchagent/dash/dashtagmgr.cpp, dashaclorch.cpp, dashaclgroupmgr.cpp

---

## 1. DASH_PREFIX_TAG_TABLE の依存関係上の位置

DASH PREFIX TAG テーブルは DASH ACL 依存チェーンの **最上流** に位置する。

```
[1] DASH_PREFIX_TAG_TABLE          ← このテーブル（タグ登録）
         ↓ (ACL rule が src_tag / dst_tag でタグ名参照)
[2] DASH_ACL_GROUP_TABLE           ← ACL グループ作成
         ↓
[3] DASH_ACL_RULE_TABLE            ← ルール作成（タグ + グループ両方が必要）
         ↓
[4] DASH_ACL_IN_TABLE / DASH_ACL_OUT_TABLE  ← ENI へのバインド
```

コード根拠: `dashaclgroupmgr.cpp:395-407` — `createRule()` 内で `src_tag` / `dst_tag` ごとに
`m_dash_acl_orch->getDashAclTagMgr().exists(tag_id)` を呼び出し、存在しない場合
`task_need_retry` を返す。

---

## 2. エントリ作成 / 削除の制約

### 作成時（SET）

- `DashTagMgr::create()` (dashtagmgr.cpp:30) は同一タグ ID が既に存在する場合 `task_failed` を返す
  （重複作成不可）。
- `ip_version` の proto3 デフォルト値 (`0 = IP_VERSION_UNSPECIFIED`) は `to_sai()` が `false` を
  返すため `task_failed`（これは ordering ではなく constants の問題だが order 違反とは別に発生する）。

### 削除時（DEL）

- `DashTagMgr::remove()` (dashtagmgr.cpp:73) は `m_groups` が非空（ACL グループに参照中）の場合
  `task_need_retry` を返す。
- **タグ削除は必ず ACL グループの detach 後**（= DASH_ACL_RULE_TABLE の DEL → DASH_ACL_GROUP_TABLE の DEL 後）に行う必要がある。
- detach は `DashAclGroupMgr::detachTags()` (dashaclgroupmgr.cpp:568) が `DashTagMgr::detach()` を呼び出すことで自動的に実行される。

### 更新時（SET 上書き）

- `DashAclOrch::taskUpdateDashPrefixTag()` (dashaclorch.cpp:296) が `exists()` を呼び、
  既存なら `update()`、未存在なら `create()` を分岐する（upsert 相当）。
- `update()` は `ip_version` の変更を拒否するが `prefix_list` の更新は許容する。
- **更新後も既バインド済み ACL ルールには SAI 再 SET が行われない**
  (`DashTagMgr::update()` がメモリ更新のみでグループ再構築をトリガーしない)。

---

## 3. task_need_retry vs task_failed の分類

| 状況 | 戻り値 | 自動回復 |
|------|-------|--------|
| ACL ルール作成時にタグが未登録 | `task_need_retry` | タグ登録後に自動解消 |
| タグ削除時にグループ参照中 | `task_need_retry` | グループ detach 後に自動解消 |
| 同一タグ ID で重複 create | `task_failed` | 自動回復なし |
| 更新時にタグ未存在 | `task_failed` | 自動回復なし（先に create が必要）|

---

## 4. warm-reboot 挙動

`DashAclOrch` は `ZmqOrch` を継承し `m_orchList` には登録されない（`gDirectory.set()` のみ）。

タグエントリを含む DASH ACL 系のリストアは warm-reboot 時に orchagent が自動リプレイしない
（ステートレス warm-reboot）。SDN コントローラが gNMI 経由で全エントリを再投入する設計。
再投入順序は上記 1. と同じ順序（タグ → グループ → ルール → バインド）を守る必要がある。
