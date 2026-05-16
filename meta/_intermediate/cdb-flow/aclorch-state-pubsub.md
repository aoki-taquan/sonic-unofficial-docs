# STATE_DB ACL (`ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `ACL_STAGE_CAPABILITY_TABLE`) — 通信メカニズム (Phase G) 解析メモ

対象: STATE_DB の `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `ACL_STAGE_CAPABILITY_TABLE`（スキーマ定数: `STATE_ACL_TABLE_TABLE_NAME`, `STATE_ACL_RULE_TABLE_NAME`, `STATE_ACL_STAGE_CAPABILITY_TABLE_NAME` — `sonic-swss-common/common/schema.h`）。

ソース確認: `sonic-swss/orchagent/aclorch.cpp` / `aclorch.h`、`sonic-swss-common/common/table.{h,cpp}`、`sonic-utilities/acl_loader/main.py`。

## 1. STATE_DB 書込 API — 素の `swss::Table` (Pub/Sub 非対応の HSET/DEL)

`AclOrch` は STATE_DB の 3 テーブルを **`swss::Table`** メンバとして保持する（`aclorch.h:706-709`）:

```cpp
// aclorch.h:706-709
Table m_aclStageCapabilityTable;
Table m_aclTableStateTable;
Table m_aclRuleStateTable;
```

`AclOrch` コンストラクタ初期化子で `stateDb` と STATE_DB スキーマ定数文字列を直結する（`aclorch.cpp:4200-4202`）:

```cpp
// aclorch.cpp:4200-4202
m_aclStageCapabilityTable(stateDb, STATE_ACL_STAGE_CAPABILITY_TABLE_NAME),
m_aclTableStateTable(stateDb, STATE_ACL_TABLE_TABLE_NAME),
m_aclRuleStateTable(stateDb, STATE_ACL_RULE_TABLE_NAME),
```

`swss::Table` は素の Redis ラッパで、`set()` / `del()` / `getKeys()` / `get()` だけを提供する。`ProducerStateTable` のような `_KEY_SET` + `PUBLISH <TABLE>_CHANNEL` 系の通知や、`NotificationProducer` の `PUBLISH` も行わない。よって書込は純粋な `HSET` / `HDEL` / `DEL` のみ。

## 2. 書込ポイント

| メソッド | API | 行 | 何を書くか |
|---|---|---|---|
| `setAclTableStatus(table, status)` | `m_aclTableStateTable.set(table, {{"status", ...}})` | `aclorch.cpp:6092` | `ACL_TABLE_TABLE\|<table>` のステータス HSET |
| `setAclTableStatus(table, ...)` 削除側 | `m_aclTableStateTable.del(table)` | `aclorch.cpp:6098` | `ACL_TABLE_TABLE\|<table>` の DEL |
| `setAclRuleStatus(table, rule, status)` | `m_aclRuleStateTable.set(table+"\|"+rule, ...)` | `aclorch.cpp:6106` | `ACL_RULE_TABLE\|<table>\|<rule>` の HSET |
| 同 削除 | `m_aclRuleStateTable.del(table+"\|"+rule)` | `aclorch.cpp:6112` | `ACL_RULE_TABLE\|<table>\|<rule>` の DEL |
| `removeAllAclTableStatus()` | `m_aclTableStateTable.getKeys()` → loop `del(key)` | `aclorch.cpp:6116-6125` | 起動時の `ACL_TABLE_TABLE` 全削除 |
| `removeAllAclRuleStatus()` | `m_aclRuleStateTable.getKeys()` → loop `del(key)` | `aclorch.cpp:6128-6137` | 起動時の `ACL_RULE_TABLE` 全削除 |
| `putAclActionCapabilityInDB(stage)` | `m_aclStageCapabilityTable.set(stage_str, fvVector)` | `aclorch.cpp:4101` | `ACL_STAGE_CAPABILITY_TABLE\|INGRESS\|EGRESS` を init で 1 回 |

これら全て戻り値なし（`swss::Table::set` / `del` は void）。Redis I/O 例外は呼出元で catch されず orchagent プロセスへ伝播する。

## 3. PUBLISH チャンネル / keyspace notification

- **PUBLISH `<TABLE>_CHANNEL` は使わない**: `ProducerStateTable` を持たないため `_KEY_SET` 操作・channel `PUBLISH` は発生しない。
- **`__keyspace@<dbId>__:...` keyspace notification**: Redis サーバ側の `notify-keyspace-events` 設定に依存。STATE_DB ACL 系の正規 consumer はいずれも keyspace 通知を購読しない (下記)。書き手側 (`AclOrch`) は通知の有無を意識しない。
- **`NotificationProducer` (`PUBLISH` to ad-hoc channel)**: 該当しない (`m_notificationProducer` 系のメンバを保有しない)。

## 4. 購読側 (consumer) — 全て polling

STATE_DB ACL 3 テーブルは**書き出し専用のステータスレジスタ**であり、正規 consumer は全て **オンデマンド polling** で `HGETALL` 相当を読むのみ:

| consumer | 参照テーブル | アクセス API | アクセス契機 |
|---|---|---|---|
| `acl-loader` (`sonic-utilities/acl_loader/main.py:533-536`) | `ACL_STAGE_CAPABILITY_TABLE\|INGRESS\|EGRESS` | `statedb.get_all(STATE_DB, "ACL_STAGE_CAPABILITY_TABLE\|<stage>")` | `acl-loader` 実行時 1 回 |
| `show acl table` (`sonic-utilities/show/acl.py` 系) | `ACL_TABLE_TABLE` | sonic-py-swsssdk `get_table()` (HGETALL polling) | CLI 起動時 1 回 |
| `show acl rule` (`sonic-utilities/show/acl.py` 系) | `ACL_RULE_TABLE` | 同上 | CLI 起動時 1 回 |
| `sonic-mgmt-common` (translib) | `ACL_STAGE_CAPABILITY_TABLE` | translib DB read (HGETALL) | REST/gNMI capability クエリ時 |

いずれも `SubscriberStateTable` / `ConsumerStateTable` / `pubsub` を使わない。CONFIG_DB 側の `ACL_TABLE` / `ACL_RULE` を `AclOrch` が `SubscriberStateTable` で購読する経路（cdb-flow/acl-table-pubsub.md 参照）とは非対称。

## 5. select() ループとの関係

`AclOrch` は STATE_DB 3 テーブルを **書き手としてのみ** 接続する。`addConsumer()` / `addExecutor()` で STATE_DB 側に対する consumer は登録しない（`orchdaemon.cpp:408-422` の `acl_table_connectors` には STATE_DB 側 connector は含まれず、CONFIG_DB 3 + APPL_DB 3 のみ）。`SELECT_TIMEOUT=1000ms` の select ループは STATE_DB 書込みには関与しない (CONFIG_DB / APPL_DB からの consumer 通知で wake → `doAclTableTask` / `doAclRuleTask` → 末尾で `setAcl*Status()` が呼ばれる経路)。

## 6. retry / バッチ

- STATE_DB 書込み自体に retry はない。`swss::Table::set` 失敗 (Redis 切断) は例外で orchagent abort → systemd restart → `init()` で再書込み。
- ACL ルールの retry cache (`createRetryCache(CFG_ACL_RULE_TABLE_NAME)` / `APP_ACL_RULE_TABLE_NAME`) は CONFIG_DB / APPL_DB 側の consumer に対するもので、STATE_DB 書込み層には存在しない。retry cache 経由で再キューされたルールが成功すると `setAclRuleStatus(ACTIVE)` で `"Pending creation"` → `"Active"` 上書きされる。

## 7. サマリ

| 観点 | STATE_DB `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `ACL_STAGE_CAPABILITY_TABLE` |
|---|---|
| publish 方式 | **`swss::Table::set()` / `del()` のみ（HSET / HDEL / DEL）** |
| channel `<TABLE>_CHANNEL` PUBLISH | **使わない**（`ProducerStateTable` を持たない） |
| `NotificationProducer` PUBLISH | 使わない |
| keyspace 通知 `__keyspace@<dbId>__:...` | 書き手側は意識しない（Redis サーバ設定依存） |
| 正規 consumer の購読方式 | **全て polling**（`HGETALL` 相当、`acl-loader` / `show acl` / translib） |
| `SubscriberStateTable` 利用 | なし（STATE_DB 側に consumer なし） |
| バッチサイズ | 概念なし（書き手側に batch なし、消費側は CLI 起動毎に 1 回 polling） |
| select タイムアウト | 関与せず |
| 書き手 | `AclOrch` のみ |
| 起動時クリア | `init()` で `removeAllAclTableStatus()` / `removeAllAclRuleStatus()`（`aclorch.cpp:3479-3481, 6116-6137`）。`ACL_STAGE_CAPABILITY_TABLE` は対象外（init の publish で上書きされる） |
| TTL | 未使用 |

## 8. Evidence

- `sonic-swss/orchagent/aclorch.h` L706-709 — `Table m_aclStageCapabilityTable / m_aclTableStateTable / m_aclRuleStateTable` メンバ宣言（`ProducerStateTable` / `NotificationProducer` 系の宣言なし）
- `sonic-swss/orchagent/aclorch.cpp` L4200-4202 — `Table(stateDb, STATE_ACL_*_TABLE_NAME)` 初期化
- `sonic-swss/orchagent/aclorch.cpp` L4087-4101 — `putAclActionCapabilityInDB()` → `m_aclStageCapabilityTable.set(stage_str, fvVector)`
- `sonic-swss/orchagent/aclorch.cpp` L6088-6098 — `setAclTableStatus()` の `set` / `del`
- `sonic-swss/orchagent/aclorch.cpp` L6102-6112 — `setAclRuleStatus()` の `set` / `del`
- `sonic-swss/orchagent/aclorch.cpp` L6116-6137 — `removeAllAclTableStatus()` / `removeAllAclRuleStatus()`（`getKeys` + 個別 `del`）
- `sonic-swss/orchagent/orchdaemon.cpp` L408-422 — `acl_table_connectors` に STATE_DB connector は含まれず（書き手専用）
- `sonic-utilities/acl_loader/main.py` L88, L533-536 — `statedb.get_all(STATE_DB, "ACL_STAGE_CAPABILITY_TABLE|<stage>")` polling 読み出し
- `sonic-swss-common/common/schema.h` — `STATE_ACL_TABLE_TABLE_NAME`, `STATE_ACL_RULE_TABLE_NAME`, `STATE_ACL_STAGE_CAPABILITY_TABLE_NAME` 定義
