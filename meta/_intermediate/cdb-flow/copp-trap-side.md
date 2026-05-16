# COPP_TRAP Phase F — 副次 DB 書き込み (side-effects)

証跡スキャン日: 2026-05-15
対象ファイル: `sonic-swss/cfgmgr/coppmgr.cpp`, `sonic-swss/orchagent/copporch.cpp`

---

## 書き込み先サマリー

| DB | テーブル名 | 定数名 | キー形式 | フィールド | 書き込みタイミング | 書き込み元 |
|---|---|---|---|---|---|---|
| `APPL_DB` | `COPP_TABLE` | `APP_COPP_TABLE_NAME` | `COPP_TABLE\|<group>` | `trap_ids`, `trap_action`, `trap_priority`, `queue`, `cir`, `cbs` 等 | `COPP_TRAP` SET/DEL 処理後 | `coppmgr.cpp` `m_appCoppTable` |
| `STATE_DB` | `COPP_TRAP_TABLE` | `STATE_COPP_TRAP_TABLE_NAME` | `COPP_TRAP_TABLE\|<name>` | `state=ok` | APPL_DB 書き込み成功後 | `coppmgr.cpp` `setCoppTrapStateOk()` |
| `STATE_DB` | `COPP_GROUP_TABLE` | `STATE_COPP_GROUP_TABLE_NAME` | `COPP_GROUP_TABLE\|<group>` | `state=ok` | trap_group の APPL_DB 書き込み成功後 | `coppmgr.cpp` `setCoppGroupStateOk()` |
| `STATE_DB` | `COPP_TRAP_TABLE` | `STATE_COPP_TRAP_TABLE_NAME` | `COPP_TRAP_TABLE\|<name>` | `hw_status=installed` / `hw_status=not-installed` | SAI hostif trap 作成/削除後 | `copporch.cpp` `updateTrapOperStatus()` |
| `STATE_DB` | `COPP_TRAP_CAPABILITY_TABLE` | `STATE_COPP_TRAP_CAPABILITY_TABLE_NAME` | `COPP_TRAP_CAPABILITY_TABLE\|traps` | `trap_ids=<comma-separated-supported-list>` | `CoppOrch` 起動時 1 回のみ | `copporch.cpp` `publishTrapIdsCapability()` |

---

## 詳細

### A. APPL_DB[COPP_TABLE|<group>]

`coppmgr` が CONFIG_DB の `COPP_TRAP|<name>` を処理し、`trap_group` で参照される COPP_GROUP 単位に trap_ids を集約して APPL_DB の `COPP_TABLE|<group>` に書き込む。

- **書き込み**: `m_appCoppTable.set(trap_group, fvs)` (coppmgr.cpp:511, 526, 733, 758)
- **削除**: `m_appCoppTable.del(trap_group)` (coppmgr.cpp:126) — 当該グループに属する全 trap が削除された場合
- **集約ロジック**: `COPP_TRAP` は 1 trap/key だが、APPL_DB は 1 group/key に再集計される（ProducerStateTable 経由）

### B. STATE_DB[COPP_TRAP_TABLE|<name>] — state フィールド (coppmgr 書き込み)

`coppmgr` が APPL_DB 書き込みに成功すると `setCoppTrapStateOk(name)` を呼び `state=ok` を書き込む。

- **書き込み条件 (SET)**: `setCoppTrapStateOk(key)` — coppmgr.cpp:367, 589, 740, 803
- **削除条件 (DEL)**: `delCoppTrapStateOk(key)` — coppmgr.cpp:660, 700, 767

### C. STATE_DB[COPP_GROUP_TABLE|<group>] — state フィールド (coppmgr 書き込み)

`coppmgr` が COPP_GROUP の APPL_DB 書き込みに成功すると `setCoppGroupStateOk(group)` を呼び `state=ok` を書き込む。COPP_TRAP の SET/DEL 処理の中でも、影響する trap_group の state が更新される。

- **書き込み条件 (SET)**: `setCoppGroupStateOk(trap_group)` — coppmgr.cpp:153, 405, 512, 527, 734, 759
- **削除条件 (DEL)**: `delCoppGroupStateOk(trap_group)` — coppmgr.cpp:127, 892

### D. STATE_DB[COPP_TRAP_TABLE|<name>] — hw_status フィールド (CoppOrch 書き込み)

`CoppOrch` が SAI `sai_create_hostif_trap` / `sai_remove_hostif_trap` を呼んだ後 `updateTrapOperStatus()` で `hw_status` を更新する。

- **`hw_status=installed`**: SAI hostif trap 作成成功後 (copporch.cpp:526)
- **`hw_status=not-installed`**: SAI hostif trap 削除後 (copporch.cpp:1413)
- キー形式: `COPP_TRAP_TABLE|<trap_name>` (`trap_name` は SAI trap type から逆引き)

### E. STATE_DB[COPP_TRAP_CAPABILITY_TABLE|traps] (CoppOrch 起動時 1 回)

`CoppOrch` 起動時に `publishTrapIdsCapability()` が SAI `sai_query_attribute_enum_values_capability()` でプラットフォームがサポートする trap_id 一覧を取得し、`COPP_TRAP_CAPABILITY_TABLE|traps` の `trap_ids` フィールドにカンマ区切りで書き込む。

- **書き込み**: `m_trapCapabilityTable->set("traps", ...)` (copporch.cpp:299)
- SAI クエリ失敗時は `default_supported_trap_ids` フォールバック (copporch.cpp:106-151)

---

## 注意事項

- COPP_TRAP の STATE_DB キーは `COPP_TRAP_TABLE|<trap_name>` だが、`state` (coppmgr 書き込み) と `hw_status` (CoppOrch 書き込み) は同一キーに異なるフィールドとして書き込まれる（上書き競合なし）
- APPL_DB への書き込みは 1 trap/key → 1 group/key の集約変換を伴う。直接 APPL_DB を参照する場合は `COPP_TABLE|<group>` で確認する
