# copp-port — Phase F 副次 DB 書込スキャン (side-effects)

対象フィールド: `CONFIG_DB / COPP_GROUP` の `genetlink_name` / `genetlink_mcgrp_name`
対象ソース:

- `sonic-swss/orchagent/copporch.cpp`
- `sonic-swss/cfgmgr/coppmgr.cpp`

## スキャン手順

`genetlink_name` / `genetlink_mcgrp_name` を SET したときに呼び出されるコードパスを追跡:

1. `coppmgrd` が CONFIG_DB の変化を検知 → `m_appCoppTable.set()` で APPL_DB `COPP_TABLE` に書込 (`coppmgr.cpp:152,511,526`)
2. `CoppOrch::processCoppRule()` が APPL_DB を購読 → `getAttribsFromTrapGroup()` で `genetlink_attribs` を収集 (`copporch.cpp:749-750`)
3. `genetlink_attribs` が非空 → `createGenetlinkHostIf()` + `createGenetlinkHostIfTable()` (`copporch.cpp:833-851`)
4. trap_id が当該グループに属している場合は `applyAttributesToTrapIds()` → `bindTrapCounter()` が呼ばれ COUNTERS_DB / FLEX_COUNTER_DB を更新 (`copporch.cpp:530,1418-1467`)
5. `updateTrapOperStatus()` が STATE_DB `COPP_TRAP_TABLE` に `hw_status="installed"` を書込 (`copporch.cpp:526,222-236`)

## 副次書込まとめ

### APPL_DB 書込

| 操作 | テーブル | キー | フィールド | タイミング | evidence |
|---|---|---|---|---|---|
| `set` | `COPP_TABLE` | `COPP_TABLE\|<group-name>` | `genetlink_name`, `genetlink_mcgrp_name` 他全フィールド | CONFIG_DB 変化を `coppmgrd` が検知後 | `coppmgr.cpp:152,511,526` |
| `del` | `COPP_TABLE` | `COPP_TABLE\|<group-name>` | (全削除) | グループ pending / DEL 時 | `coppmgr.cpp:126,288,891` |

### STATE_DB 書込

| 操作 | テーブル | キー | フィールド | タイミング | evidence |
|---|---|---|---|---|---|
| `set` | `COPP_TRAP_TABLE` | `COPP_TRAP_TABLE\|<trap-name>` | `hw_status="installed"` | SAI `create_hostif_trap()` 成功後 (`applyAttributesToTrapIds`) | `copporch.cpp:526,222-236` |
| `set` | `COPP_TRAP_TABLE` | `COPP_TRAP_TABLE\|<trap-name>` | `hw_status="not-installed"` | SAI trap 削除時 | `copporch.cpp:1413` |

genetlink フィールド自体が STATE_DB への直接書込を追加することはない。`hw_status` 更新は trap_ids の追加 (`trapGroupProcessTrapIdChange`) に伴うもの。

### COUNTERS_DB 書込

| 操作 | テーブル | キー | フィールド | タイミング | evidence |
|---|---|---|---|---|---|
| `set` | `COUNTERS_TRAP_NAME_MAP` | `""` (hash) | `<trap_name>=<counter_oid>` | `bindTrapCounter()` 実行時（trap_ids 追加直後） | `copporch.cpp:1452-1456` |
| `hdel` | `COUNTERS_TRAP_NAME_MAP` | `""` (hash) | `<trap_name>` | `unbindTrapCounter()` 実行時（trap 削除時） | `copporch.cpp:1494-1495` |

### FLEX_COUNTER_DB 書込

| 操作 | グループ | 条件 | evidence |
|---|---|---|---|
| `setCounterIdList(counter_id, HOSTIF_TRAP, stats)` | `HOSTIF_TRAP_FLOW_COUNTER` | `bindTrapCounter()` 成功後 (timer 起動) | `copporch.cpp:950` |
| `clearCounterIdList(counter_id)` | `HOSTIF_TRAP_FLOW_COUNTER` | `unbindTrapCounter()` で pending なければ即削除 | `copporch.cpp:1487` |

FLEX_COUNTER_DB 登録は SelectableTimer (`FLEX_COUNTER_UPD_TIMER`, 1 秒) 経由で非同期に実行される。

### ASIC_DB 副次書込 (syncd 経由)

CoppOrch は ASIC_DB に直接書き込まない。SAI API 呼び出しを受けた `syncd` が ASIC_DB `VIDTORID` テーブルに OID を記録する。

genetlink フィールドが追加されると以下の SAI 呼び出しが追加で発生する:

| SAI API | 条件 | evidence |
|---|---|---|
| `sai_hostif_api->create_hostif()` (TYPE_GENETLINK) | `genetlink_attribs` 非空 | `copporch.cpp:680` |
| `sai_hostif_api->create_hostif_table_entry()` (CHANNEL_TYPE_GENETLINK) | 当該グループ内の各 trap_id に対して | `copporch.cpp:453-466` |
| `sai_hostif_api->remove_hostif()` | DEL または二重作成エラー | `copporch.cpp:702` |
| `sai_hostif_api->remove_hostif_table_entry()` | trap_id 除去時 | `copporch.cpp:481-487` |
