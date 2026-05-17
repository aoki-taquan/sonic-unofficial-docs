# DASH_PREFIX_TAG_TABLE — Phase B 書込み順依存スキャンノート

対象テーブル: `DASH_PREFIX_TAG_TABLE`
Consumer: `DashAclOrch::taskUpdateDashPrefixTag()` / `taskRemoveDashPrefixTag()` (`sonic-swss/orchagent/dash/dashaclorch.cpp`)
スキャン範囲: `dashaclorch.cpp` L283–312、`dashtagmgr.cpp` 全行、`orchdaemon.cpp` L1371–1409 精読

---

## 検出した順序依存・タイミング依存

### 1. 外部テーブル依存なし (SET 時)

`taskUpdateDashPrefixTag()` は protobuf をデシリアライズして `DashTagMgr::create()` または `update()` を呼ぶだけ。
他テーブルの先行存在確認・OID 解決・`allPortsReady()` 相当のガードは一切存在しない。
`DASH_PREFIX_TAG_TABLE` の SET は orchagent 起動直後から処理可能。

- evidence: `dashaclorch.cpp` L283–311 (`taskUpdateDashPrefixTag`)、`dashtagmgr.cpp` L30–70 (`create`/`update`)

### 2. ACL rule SET は PREFIX_TAG より後 (ACL rule 側の制約)

`DashAclGroupMgr::createRule()` は `src_tag` / `dst_tag` の各タグ名について `DashTagMgr::exists()` を確認し、タグが未存在なら `task_need_retry` を返す。
つまり ACL rule が `src_tag` / `dst_tag` を参照する場合、**タグ先行作成が必須**。コントローラはタグを ACL rule より前に送信しなければならない。

- 違反時の挙動: rule が `task_need_retry` で待機。タグが後から作成されると次回イベントループで自動再処理。
- evidence: `dashaclgroupmgr.cpp` L393–409

### 3. DEL 時の順序: ACL rule → PREFIX_TAG (参照カウント保護)

タグが ACL group から参照中 (`DashTag::m_groups` 非空) の間は `DashTagMgr::remove()` が `task_need_retry` を返す。
DEL の推奨順序: `DASH_ACL_RULE_TABLE` → `DASH_ACL_GROUP_TABLE` → `DASH_PREFIX_TAG_TABLE`。
上流の rule / group を先に削除して `m_groups` を空にしてからタグを削除すること。逆順に送ると DEL が無限 retry になる。

- evidence: `dashtagmgr.cpp` L84–88 (`m_groups.empty()` ガード)

### 4. 起動時 (orchdaemon) の初期化順: DashAclOrch は DashOrch より後

`orchdaemon.cpp` では `DashOrch`（L1350）の後に `DashAclOrch`（L1378）が生成され、`addOrchList` の順序も `dash_acl_orch` (L1409) → `dash_orch` (L1412) となっている。ただし DASH_PREFIX_TAG_TABLE 処理は `DashOrch` の完了を待たないため、起動時の実用的なブロッキングはない。

- evidence: `orchdaemon.cpp` L1350, L1378, L1409, L1412

## 順序依存サマリ

| # | 依存関係 | 方向 | 違反時の挙動 |
|---|----------|------|------------|
| 1 | なし (SET) — 外部テーブル不要 | — | 制約なし、即処理可 |
| 2 | `src_tag` / `dst_tag` を持つ ACL rule より **PREFIX_TAG を先に** SET | SET (コントローラ送信順) | rule が `task_need_retry` で待機 → タグ作成後に自動再処理 |
| 3 | ACL rule / group を先に DEL してから PREFIX_TAG を DEL | DEL (コントローラ送信順) | `m_groups` 非空 → `task_need_retry`（DEL 無限 retry） |
