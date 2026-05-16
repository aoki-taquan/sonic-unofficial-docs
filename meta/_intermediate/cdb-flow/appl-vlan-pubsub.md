# APPL_DB VLAN_TABLE / VLAN_MEMBER_TABLE — 通信メカニズム (Phase G) 解析メモ

対象: APPL_DB の `VLAN_TABLE` / `VLAN_MEMBER_TABLE`（スキーマ定数: `APP_VLAN_TABLE_NAME` / `APP_VLAN_MEMBER_TABLE_NAME`、`sonic-swss-common/common/schema.h:41-42`）。

ソース確認 (`sonic-swss` sha `4305596156d70e9797e8a881b3d19b46de0bce0d`):
- `cfgmgr/vlanmgr.cpp` / `cfgmgr/vlanmgr.h` — 書き込み側 (`vlanmgrd`)
- `orchagent/portsorch.cpp` — 購読側 (`PortsOrch`)
- `orchagent/orchdaemon.cpp` — TableConnector 登録 (ports_tables)
- `orchagent/orch.cpp` — `Orch::addConsumer()` DB ID 分岐
- `orchagent/main.cpp` — `gBatchSize` / `DEFAULT_BATCH_SIZE` / `SELECT_TIMEOUT`

## 1. 購読 API — `ConsumerStateTable` (channel ベース PUBLISH/SUBSCRIBE)

`orchdaemon.cpp:215-224` で VLAN 系の APPL_DB テーブルが `PortsOrch` に渡される consumer リスト (`ports_tables`) として登録される:

```cpp
// orchdaemon.cpp:215-224
const int portsorch_base_pri = 40;

vector<table_name_with_pri_t> ports_tables = {
    { APP_PORT_TABLE_NAME,                  portsorch_base_pri + 5 },
    { APP_SEND_TO_INGRESS_PORT_TABLE_NAME,  portsorch_base_pri + 5 },
    { APP_VLAN_TABLE_NAME,                  portsorch_base_pri + 2 },
    { APP_VLAN_MEMBER_TABLE_NAME,           portsorch_base_pri     },
    { APP_LAG_TABLE_NAME,                   portsorch_base_pri + 4 },
    { APP_LAG_MEMBER_TABLE_NAME,            portsorch_base_pri     }
};
gPortsOrch = new PortsOrch(m_applDb, m_stateDb, ports_tables, m_chassisAppDb);
```

`PortsOrch` のコンストラクタは基底 `Orch(applDb, ports_tables)` を呼び、その中で各テーブル名について `Orch::addConsumer()` が回る。`addConsumer()` は DB ID で分岐する:

```cpp
// orch.cpp:1186-1196
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
        addExecutor(new Consumer(new SubscriberStateTable(db, tableName, ..., pri), this, tableName));
    else
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
}
```

APPL_DB は CONFIG_DB / STATE_DB / CHASSIS_APP_DB のいずれでもないため **`ConsumerStateTable`** が選択される。これは channel ベースの PUBLISH/SUBSCRIBE プロトコル:

- producer 側 (`ProducerStateTable::set()`) は `_<TABLE>` ハッシュへ HSET + `<TABLE>_CHANNEL@<dbId>` への `PUBLISH "G"` を発行
- consumer 側 (`ConsumerStateTable`) は `SUBSCRIBE <TABLE>_CHANNEL@<dbId>` で待機、PUBLISH を受けると `pops()` で `_<TABLE>:<key>` を batch fetch
- **keyspace 通知 (`__keyspace@<dbId>__:...`) は使わない**

バッチサイズは `gBatchSize`（`orchagent/main.cpp` の `DEFAULT_BATCH_SIZE = 128`、`-b <n>` オプションで上書き可）。TTL は APPL_DB エントリで使われない（`vlanmgrd` 側 `set()` は HSET のみ）。

## 2. 書き込み側 (publisher) — `vlanmgrd`

`cfgmgr/vlanmgr.h:22-23` で `VlanMgr` が `ProducerStateTable` を保持:

```cpp
// vlanmgr.h:22-23
ProducerStateTable m_appVlanTableProducer, m_appVlanMemberTableProducer;
ProducerStateTable m_appFdbTableProducer, m_appPortTableProducer;
```

`vlanmgr.cpp:33-34` で APPL_DB に向けてバインド:

```cpp
// vlanmgr.cpp:33-34
m_appVlanTableProducer(appDb, APP_VLAN_TABLE_NAME),
m_appVlanMemberTableProducer(appDb, APP_VLAN_MEMBER_TABLE_NAME),
```

実際の SET / DEL は `doVlanTask()` / `doVlanMemberTask()` / `processUntaggedVlanMembers()` / `doVlanPacVlanMemberTask()` 内で `m_appVlanTableProducer.set(...)` / `.del(...)` を呼ぶ。書き込み元プロセスは `vlanmgrd` 1 つに集約され、ACL 系（複数プロセスから書き込まれる）と対照的に publisher 集中型。

## 3. 購読側 ディスパッチ

`PortsOrch::doTask()` (`portsorch.cpp:6464-6489`) は consumer drain を **固定順** で呼ぶ:

```cpp
// portsorch.cpp:6464-6489
void PortsOrch::doTask()
{
    auto tableOrder = {
        APP_PORT_TABLE_NAME,
        APP_LAG_TABLE_NAME,
        APP_LAG_MEMBER_TABLE_NAME,
        APP_VLAN_TABLE_NAME,
        APP_VLAN_MEMBER_TABLE_NAME
    };

    for (auto tableName: tableOrder)
    {
        auto consumer = getExecutor(tableName);
        consumer->drain();
    }
    // drain remaining tables...
}
```

これにより、同一 select サイクル内でも PORT → LAG → LAG_MEMBER → VLAN → VLAN_MEMBER の順序が **テーブル単位で保証される**。各 drain は内部で `Consumer::execute()` → `ConsumerStateTable::pops()` → `Orch::doTask(Consumer&)` を呼ぶ。

`PortsOrch::doTask(Consumer&)` (`portsorch.cpp:6492-6526`):

```cpp
// portsorch.cpp:6492-6526 (抜粋)
void PortsOrch::doTask(Consumer &consumer)
{
    string table_name = consumer.getTableName();
    // ...
    else
    {
        if (!allPortsReady()) return;  // L6513-6517 全 PORT 初期化待ち

        if (table_name == APP_VLAN_TABLE_NAME)
            doVlanTask(consumer);
        else if (table_name == APP_VLAN_MEMBER_TABLE_NAME)
            doVlanMemberTask(consumer);
        // ...
    }
}
```

`allPortsReady()` ガードにより、PORT 初期化未完了の間は VLAN 経路は呼ばれず、エントリは `m_toSync` で保留される。

## 4. select タイムアウト

`OrchDaemon` メインループは `m_select->select(&s, SELECT_TIMEOUT)` で待機。`SELECT_TIMEOUT` は `orchdaemon.cpp` で 1000 ms 定義（ACL ページ参照済み）。`<VLAN_TABLE>_CHANNEL` / `<VLAN_MEMBER_TABLE>_CHANNEL` への PUBLISH があれば即座に wake up し、`execute()` → `pop()` → `doTask()` が走る。PUBLISH 不在時も 1 秒ごとに wake up して各種 retry / flush を回す。

## 5. リトライキャッシュ

VLAN 経路には `createRetryCache(APP_VLAN_TABLE_NAME)` のような明示的 retry キャッシュは **存在しない**（ACL の `createRetryCache(APP_ACL_RULE_TABLE_NAME)` と異なる）。代わりに以下の汎用 retry が使われる:

- **`Consumer::m_toSync`** に保留: ハンドラが `it++; continue;` でエントリを残すと次 select サイクルで再評価
- **`erase(it)`**: 永続失敗（key 形式不正・不正 `tagging_mode`）は破棄

VLAN 系の retry 判定は本体ページの「書込失敗・retry 分岐」セクションを参照（vlanmgr.cpp:316-322,642-647 / portsorch.cpp:5900-5912,7392-7402 など）。

## 6. サマリ

| 観点 | APPL_DB `VLAN_TABLE` / `VLAN_MEMBER_TABLE` |
|---|---|
| 購読方式 | `ConsumerStateTable`（channel ベース PUBLISH/SUBSCRIBE） |
| バッチサイズ | `gBatchSize` (default 128, `orchagent -b` で上書き可) |
| 優先度 | `VLAN_TABLE`: 42 (`portsorch_base_pri + 2`), `VLAN_MEMBER_TABLE`: 40 (`portsorch_base_pri`) |
| select タイムアウト | 1000 ms (`SELECT_TIMEOUT`) |
| 書き込み側プロセス | `vlanmgrd` 単一 publisher（`ProducerStateTable::set()`） |
| 購読プロセス | `orchagent` (`PortsOrch`) 単一 subscriber |
| ハンドラ | `doVlanTask` / `doVlanMemberTask` (table_name で分岐) |
| doTask drain 順 | PORT → LAG → LAG_MEMBER → **VLAN → VLAN_MEMBER** (固定順) |
| `allPortsReady()` ガード | あり (PORT 初期化未完了の間 VLAN 経路スキップ) |
| 明示 retry キャッシュ | なし (`m_toSync` 汎用 retry のみ) |
| keyspace 通知 (`__keyspace@<dbId>__:...`) | **使わない**（channel ベースのため） |
| TTL | 未使用 |
| warm-restart 再注入 | `addExistingData(APP_VLAN_TABLE_NAME)` / `addExistingData(APP_VLAN_MEMBER_TABLE_NAME)` (`portsorch.cpp:4389-4390`) |

## 7. ACL APPL_DB 系との対比

| 観点 | APPL_DB ACL 3 テーブル | APPL_DB VLAN 2 テーブル |
|---|---|---|
| 購読方式 | `ConsumerStateTable` | 同 |
| publisher | 複数 (`vnetorch` / `mclagsyncd` / `dashenifwdorch`) | 単一 (`vlanmgrd`) |
| CONFIG_DB 同等テーブル併存 | あり (CONFIG_DB ACL 3 テーブル) | なし (CONFIG_DB は `VLAN` / `VLAN_MEMBER` だが vlanmgrd 経由で APPL_DB に集約) |
| 明示 retry キャッシュ | `ACL_RULE_TABLE` のみ | なし |
| doTask drain 順制約 | なし (個別 doTask) | 固定順 (`PortsOrch::doTask()`) |
| ハンドラ共有 | CONFIG_DB 版と同一 (`doAclTableTask` 等) | N/A (CONFIG_DB 側は vlanmgrd が処理) |

## 8. Evidence サマリ

- `sonic-swss-common/common/schema.h:41-42` — `APP_VLAN_TABLE_NAME` / `APP_VLAN_MEMBER_TABLE_NAME` 定数
- `sonic-swss/orchagent/orchdaemon.cpp:215-224,232` — `ports_tables` 登録、`PortsOrch` 構築
- `sonic-swss/orchagent/orch.cpp:1186-1196` — `Orch::addConsumer()` DB ID 分岐
- `sonic-swss/orchagent/portsorch.cpp:4389-4390` — warm-restart `addExistingData`
- `sonic-swss/orchagent/portsorch.cpp:6464-6489` — `PortsOrch::doTask()` 固定順 drain
- `sonic-swss/orchagent/portsorch.cpp:6492-6526` — `PortsOrch::doTask(Consumer&)` table_name 分岐 + `allPortsReady()` ガード
- `sonic-swss/cfgmgr/vlanmgr.h:22-23` — `ProducerStateTable` メンバー
- `sonic-swss/cfgmgr/vlanmgr.cpp:33-34` — `APP_VLAN_TABLE_NAME` / `APP_VLAN_MEMBER_TABLE_NAME` バインド
