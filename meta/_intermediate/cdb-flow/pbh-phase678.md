# PBH (Policy-Based Hashing) — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_3)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 該当なし

minigraph.py / config_samples.py / db_migrator.py / init_cfg.json.j2 に PBH テーブルへの代入なし。CLI (`config pbh`) で明示設定。

**結論**: Phase 6 派生なし。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### orchdaemon.cpp — PbhOrch 登録

```cpp
// orchdaemon.cpp:565, 570
gPbhOrch = new PbhOrch(pbhTableConnectorList, gAclOrch, gPortsOrch);
m_orchList.push_back(gPbhOrch);
```

PbhOrch は **常時** 生成・登録。条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### pbhorch.cpp — doTask 分岐 (4テーブル)

| テーブル | SET | DEL |
|----------|-----|-----|
| PBH_TABLE | `addPbhTable()` → SAI ACL table | `removePbhTable()` |
| PBH_RULE | `addPbhRule()` → SAI ACL entry | `removePbhRule()` |
| PBH_HASH | `addPbhHash()` → SAI hash object | `removePbhHash()` |
| PBH_HASH_FIELD | `addPbhHashField()` → SAI hash field | `removePbhHashField()` |

early return: 依存オブジェクト (hash/table) 未作成 → `task_need_retry` で再キューイング。

<!-- /handler-branching -->
