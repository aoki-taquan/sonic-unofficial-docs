# FG_NHG テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `FG_NHG` / `FG_NHG_PREFIX` / `FG_NHG_MEMBER` テーブル。FgNhgOrch が直接 CONFIG_DB を購読し、SAI fg_nhg_api を呼び出す経路を記録する。

調査日: 2026-05-16
主要ソース:
- `sonic-swss/orchagent/fgnhgorch.cpp` (全行精読)
- `sonic-swss/orchagent/orchdaemon.cpp` L301-310

## 1. CONFIG_DB Consumer 登録 (orchdaemon.cpp)

`FgNhgOrch` は `Orch(db, tableNames)` 基底クラスを通じて CONFIG_DB の 3 テーブルを優先度 15 で購読する。

```cpp
// orchdaemon.cpp L301-309
const int fgnhgorch_pri = 15;
vector<table_name_with_pri_t> fgnhg_tables = {
    { CFG_FG_NHG,        fgnhgorch_pri },
    { CFG_FG_NHG_PREFIX, fgnhgorch_pri },
    { CFG_FG_NHG_MEMBER, fgnhgorch_pri }
};
gFgNhgOrch = new FgNhgOrch(m_configDb, m_applDb, m_stateDb, fgnhg_tables, gNeighOrch, gIntfsOrch, vrf_orch);
```

`Orch` 基底クラスの `addConsumer()` が `ConsumerStateTable(CONFIG_DB, tableName)` を生成し、Redis keyspace 通知を受信する。APPL_DB 経由ではなく CONFIG_DB から **直接** 購読する点が他テーブルと異なる。

## 2. doTask() ディスパッチ (fgnhgorch.cpp L2126-2160)

`orchdaemon` の `select()` ループが Consumer イベントを検出すると `FgNhgOrch::doTask(Consumer& consumer)` を呼び出す。テーブル名で 3 ハンドラに分岐する:

```cpp
// fgnhgorch.cpp L2126-2160
void FgNhgOrch::doTask(Consumer& consumer) {
    const string & table_name = consumer.getTableName();
    auto it = consumer.m_toSync.begin();
    bool entry_handled = true;

    while (it != consumer.m_toSync.end()) {
        auto t = it->second;
        if (table_name == CFG_FG_NHG)
            entry_handled = doTaskFgNhg(t);          // L2138
        else if (table_name == CFG_FG_NHG_PREFIX)
            entry_handled = doTaskFgNhgPrefix(t);    // L2142
        else if (table_name == CFG_FG_NHG_MEMBER)
            entry_handled = doTaskFgNhgMember(t);    // L2146
        else
            SWSS_LOG_ERROR("Unknown table : %s", table_name.c_str());

        if (entry_handled)
            consumer.m_toSync.erase(it++);   // キューから除去
        else
            it++;                             // return false → キューに残りリトライ
    }
}
```

## 3. SAI fg_nhg_api 呼び出しフロー

### FG_NHG SET → SAI next_hop_group 生成

```
CONFIG_DB[FG_NHG|<name>] SET
  → doTaskFgNhg() L1673
      bucket_size / match_mode / max_next_hops パース
      createFgNhg()  // L238
        sai_next_hop_group_api->create_fine_grained_next_hop_group()
        sai_next_hop_group_api->query_attr(SAI_NEXT_HOP_GROUP_ATTR_REAL_SIZE)
        setNewNhgMembers() → sai_next_hop_group_api->create_next_hop_group_member()
```

### FG_NHG_PREFIX SET → APPL_DB[ROUTE_TABLE] 更新

```
CONFIG_DB[FG_NHG_PREFIX|<prefix>] SET
  → doTaskFgNhgPrefix() L1790
      m_routeTable->del(prefix)    // APPL_DB[APP_ROUTE_TABLE_NAME] 一旦削除
      (RouteOrch DEL 完了待ち → return false で retry)
      m_routeTable->set(prefix, {nexthops})  // FG ルートとして再投入
      sai_route_api->set_route_entry_attribute(SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID)
```

### FG_NHG_MEMBER SET → nexthop 追加

```
CONFIG_DB[FG_NHG_MEMBER|<nh_ip>] SET
  → doTaskFgNhgMember() L1969
      m_neighOrch->hasNextHop(nhk)?  // NeighOrch 解決確認
        No  → return false (retry)
        Yes → validNextHopInNextHopGroup(nhk)
                m_neighOrch->increaseNextHopRefCount()
                sai_next_hop_group_api->create_next_hop_group_member()
                バケット再割り当て
```

## 4. NeighOrch Observer パターン

`FgNhgOrch` は `gPortsOrch->attach(this)` によって PortsOrch の `SUBJECT_TYPE_PORT_OPER_STATE_CHANGE` を購読する (fgnhgorch.cpp L36)。NeighOrch との連携は Observer 経由ではなく **直接メソッド呼び出し** で行う:

| メソッド | 呼び出し箇所 | 役割 |
|---------|------------|------|
| `m_neighOrch->hasNextHop(nhk)` | L1415, L2071 | nexthop 解決確認 |
| `m_neighOrch->getNextHopId(nhk)` | L1459 | SAI next_hop OID 取得 |
| `m_neighOrch->increaseNextHopRefCount(nhk)` | L1479 | refcount 増加 |
| `m_neighOrch->decreaseNextHopRefCount(nhk)` | L1547 | refcount 減少 |
| `m_neighOrch->getNeighborEntry(ip, nhk, mac)` | L70, L82 | IP → NextHopKey 解決 |

NeighOrch が nexthop を未解決の場合、`doTaskFgNhgMember()` は `return false` でエントリをキューに残す。ARP/NDP 解決後の次回 `select()` ループで自動リトライされる。

## 5. PortsOrch Observer パターン

`FgNhgOrch::update(SubjectType type, void *cntx)` (fgnhgorch.cpp L40) が `SUBJECT_TYPE_PORT_OPER_STATE_CHANGE` を受信する:

```cpp
// fgnhgorch.cpp L46-92
case SUBJECT_TYPE_PORT_OPER_STATE_CHANGE: {
    PortOperStateUpdate *update = ...;
    for (auto &fgNhgEntry : m_FgNhgs) {
        auto entry = fgNhgEntry.second.links.find(update->port.m_alias);
        if (entry != fgNhgEntry.second.links.end()) {
            // link oper-state → nexthop_entry.link_oper_state 更新
            // UP:   validNextHopInNextHopGroup(nhk)   → バケット再追加
            // DOWN: invalidNextHopInNextHopGroup(nhk) → バケット除去
        }
    }
}
```

`FG_NHG_MEMBER.link` に PORT/PORTCHANNEL を指定した場合のみ links マップに登録され、リンクダウン時に自動でバンク再分配が起動する。

## 6. Subscribe パターンまとめ

| 区間 | 方式 | チャンネル |
|------|------|-----------|
| CLI → CONFIG_DB[FG_NHG\|*] | Redis `HSET` (sonic-utilities yang plugin) | — |
| CONFIG_DB[FG_NHG\|*] → FgNhgOrch | `ConsumerStateTable` (keyspace 通知) | `__keyspace@config_db__:FG_NHG\|*` |
| CONFIG_DB[FG_NHG_PREFIX\|*] → FgNhgOrch | `ConsumerStateTable` (keyspace 通知) | `__keyspace@config_db__:FG_NHG_PREFIX\|*` |
| CONFIG_DB[FG_NHG_MEMBER\|*] → FgNhgOrch | `ConsumerStateTable` (keyspace 通知) | `__keyspace@config_db__:FG_NHG_MEMBER\|*` |
| FgNhgOrch → NeighOrch | 直接メソッド呼び出し | — |
| FgNhgOrch → PortsOrch | Observer (attach/update) | `SUBJECT_TYPE_PORT_OPER_STATE_CHANGE` |
| FgNhgOrch → APPL_DB[ROUTE_TABLE] | `ProducerStateTable::set()/del()` | APPL_DB channel |
| FgNhgOrch → SAI | SAI API 直接呼び出し | `sai_next_hop_group_api` / `sai_route_api` |

## 7. APPL_DB / STATE_DB 書き込み

| DB | テーブル | 書き込み主体 | 条件 |
|----|---------|------------|------|
| APPL_DB | `ROUTE_TABLE` | FgNhgOrch (`m_routeTable`) | FG_NHG_PREFIX SET/DEL 時 |
| STATE_DB | `STATE_FG_ROUTE_TABLE` | FgNhgOrch (`m_stateWarmRestartRouteTable`) | warm-restart 復旧時 |
| APPL_DB | `FG_NHG*` | なし | FG_NHG は CONFIG_DB 専用 |

## 8. retry メカニズム

- `return false` → `consumer.m_toSync` にエントリが残り、次回 `select()` ループで再処理
- 主な retry 条件: nexthop 未解決 (`hasNextHop()` false)、親 FG_NHG エントリ未受信、prefix 移行中、RouteOrch DEL 完了待ち
- `return true` → キューから除去（エラーでも `return true` の場合は再試行なし = 破棄）

## 9. 参考行番号

- `orchdaemon.cpp`: L301-310 (FgNhgOrch 生成・テーブル登録)
- `fgnhgorch.cpp`: L24-36 (コンストラクタ、gPortsOrch->attach)
- `fgnhgorch.cpp`: L40-92 (update / PortOperStateChange)
- `fgnhgorch.cpp`: L1415,1459,1479,1547 (NeighOrch 呼び出し群)
- `fgnhgorch.cpp`: L1673-1744 (doTaskFgNhg)
- `fgnhgorch.cpp`: L1790-1895 (doTaskFgNhgPrefix)
- `fgnhgorch.cpp`: L1969-2125 (doTaskFgNhgMember)
- `fgnhgorch.cpp`: L2126-2165 (doTask ディスパッチ)
