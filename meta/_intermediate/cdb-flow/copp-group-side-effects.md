# copp-group — Phase F 副次 DB 書込スキャン (side-effects)

対象テーブル: `CONFIG_DB / COPP_GROUP`
対象ソース:

- `sonic-swss/cfgmgr/coppmgr.cpp`
- `sonic-swss/orchagent/copporch.cpp`

## スキャン結果

### APPL_DB 書込 (`COPP_TABLE`)

`coppmgr` が CONFIG_DB `COPP_GROUP` / `COPP_TRAP` 変化を受けて `m_appCoppTable.set()` を呼び出す。

| 操作 | タイミング | evidence |
|---|---|---|
| `m_appCoppTable.set(trap_group, fvs)` — グループ有効化 | trap_group が pending → enabled になった時 | `coppmgr.cpp:152` |
| `m_appCoppTable.set(trap_group, fvs)` — グループ更新 | COPP_GROUP フィールド変化時 | `coppmgr.cpp:511,526,733,758,874,914` |
| `m_appCoppTable.del(trap_group)` — グループ削除 | trap_group が pending 状態に遷移 / DEL コマンド | `coppmgr.cpp:126,288,891` |

書込キーパターン: `COPP_TABLE|<group-name>`（例: `COPP_TABLE|queue4_group1`）

書込フィールド（APPL_DB）:

| フィールド | 内容 |
|---|---|
| `queue` | CPU 受信キュー番号 |
| `trap_priority` | トラップ優先度 |
| `trap_action` | trap / forward / copy / drop |
| `meter_type` | packets / bytes |
| `mode` | sr_tcm / tr_tcm / storm |
| `cir`, `cbs`, `pir`, `pbs` | policer レート / バースト値 |
| `green_action`, `yellow_action`, `red_action` | カラー別アクション |
| `trap_ids` | 当該グループに属するトラップ ID リスト |

### STATE_DB 書込 (`COPP_GROUP_TABLE` / `COPP_TRAP_TABLE` / `COPP_TRAP_CAPABILITY_TABLE`)

#### COPP_GROUP_TABLE (coppmgr)

`setCoppGroupStateOk()` / `delCoppGroupStateOk()` が `m_stateCoppGroupTable.set/del()` を呼び出す。

| 操作 | タイミング | evidence |
|---|---|---|
| `set(alias, [("state","ok")])` | APPL_DB への書込成功後 | `coppmgr.cpp:424-430` |
| `del(alias)` | グループ削除時 / pending 遷移時 | `coppmgr.cpp:433-436` |

キーパターン: `COPP_GROUP_TABLE|<group-name>`

#### COPP_TRAP_TABLE (coppmgr)

`setCoppTrapStateOk()` / `delCoppTrapStateOk()` が `m_stateCoppTrapTable.set/del()` を呼び出す。

| 操作 | タイミング | evidence |
|---|---|---|
| `set(alias, [("state","ok")])` | COPP_TRAP 処理成功後 | `coppmgr.cpp:439-445` |
| `del(alias)` | COPP_TRAP 削除時 | `coppmgr.cpp:448-451` |

キーパターン: `COPP_TRAP_TABLE|<trap-name>`

#### COPP_TRAP_TABLE (copporch — hw_status)

`updateTrapOperStatus()` が `m_trapTable->set()` を呼び出し。

| 操作 | タイミング | evidence |
|---|---|---|
| `set(trap_name, [("hw_status","ok")])` | SAI でトラップ作成成功後 | `copporch.cpp:222-236` |

キーパターン: `COPP_TRAP_TABLE|<trap-name>`

#### COPP_TRAP_CAPABILITY_TABLE (copporch)

`publishTrapIdsCapability()` が起動時に SAI ケーパビリティを問い合わせて書込。

| 操作 | タイミング | evidence |
|---|---|---|
| `set("traps", [("trap_ids","<comma-list>")])` | `CoppOrch` コンストラクタ実行時（orchagent 起動時） | `copporch.cpp:296-299` |

### ASIC_DB 副次書込

`syncd` が APPL_DB `COPP_TABLE` の変化を受けて `CoppOrch` 経由で SAI API を呼び出し、
`syncd` 内部で ASIC_DB に OID を記録する（`VIDTORID` テーブル）。CoppOrch 自体は ASIC_DB に直接書き込まない。

SAI 呼び出し:
- `sai_hostif_api->create_hostif_trap_group()` — トラップグループ新規作成 (`copporch.cpp:780`)
- `sai_hostif_api->set_hostif_trap_group_attribute()` — グループ属性更新 (`copporch.cpp:552,621,762`)
- `sai_create_policer()` (内部) — policer 作成 (`copporch.cpp:trapGroupUpdatePolicer`)

### COUNTERS_DB 書込

`CoppOrch::bindTrapCounter()` / `unbindTrapCounter()` が `COUNTERS_TRAP_NAME_MAP` を更新。

| 操作 | タイミング | evidence |
|---|---|---|
| `set("", [(trap_name, counter_oid)])` | SAI ホスト IF トラップにカウンタバインド後 | `copporch.cpp:1452-1456` |
| `hdel("", trap_name)` | トラップアンバインド時 | `copporch.cpp:1494-1495` |

キーパターン: `COUNTERS_TRAP_NAME_MAP|""` (ハッシュフィールド = trap 名)

## 副次書込まとめ

| 副次 DB | テーブル | 操作 | キーパターン | フィールド | ソース |
|---|---|---|---|---|---|
| APPL_DB | `COPP_TABLE` | set | `COPP_TABLE\|<group-name>` | queue, trap_action, meter_type, mode, cir/cbs/pir/pbs, trap_ids 等 | `coppmgr.cpp:152` |
| APPL_DB | `COPP_TABLE` | del | `COPP_TABLE\|<group-name>` | (全削除) | `coppmgr.cpp:126,288,891` |
| STATE_DB | `COPP_GROUP_TABLE` | set/del | `COPP_GROUP_TABLE\|<group-name>` | `state=ok` | `coppmgr.cpp:424-436` |
| STATE_DB | `COPP_TRAP_TABLE` | set/del | `COPP_TRAP_TABLE\|<trap-name>` | `state=ok` (coppmgr), `hw_status=ok` (copporch) | `coppmgr.cpp:439-451`, `copporch.cpp:236` |
| STATE_DB | `COPP_TRAP_CAPABILITY_TABLE` | set | `COPP_TRAP_CAPABILITY_TABLE\|traps` | `trap_ids=<comma-list>` | `copporch.cpp:296-299` |
| ASIC_DB | `VIDTORID` | set (syncd 経由) | SAI OID | hostif_trap_group / policer OID | `copporch.cpp:780` |
| COUNTERS_DB | `COUNTERS_TRAP_NAME_MAP` | set/hdel | `""` (hash field = trap_name) | counter_oid | `copporch.cpp:1452-1495` |
