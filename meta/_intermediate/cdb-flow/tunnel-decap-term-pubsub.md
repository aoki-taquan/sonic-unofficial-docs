# TUNNEL_DECAP_TERM_TABLE — Phase G: 通信メカニズム調査

調査日: 2026-05-17
対象ファイル:
- `sonic-swss/orchagent/tunneldecaporch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/tunnelmgr.cpp` (同 SHA)
- `sonic-swss/orchagent/routeorch.cpp` (同 SHA)
- `sonic-swss/orchagent/vnetorch.cpp` (同 SHA)

---

## 1. tunnelmgrd → APPL_DB (ProducerStateTable)

`TunnelMgr` コンストラクタ (tunnelmgr.cpp L108-113) で以下を初期化:

```cpp
ProducerStateTable m_appIpInIpTunnelDecapTermTable(appDb, APP_TUNNEL_DECAP_TERM_TABLE_NAME);
```

書き込みは `doTunnelTask()` (L276-289) 内:
- SET: `m_appIpInIpTunnelDecapTermTable.set(key, fvs)` — Lua スクリプトで `SADD KEY_SET` + `HSET _<table>:<key>` + `PUBLISH CHANNEL G` をアトミック実行
- DEL: `m_appIpInIpTunnelDecapTermTable.del(key)` — Lua で `SADD DEL_SET` + `HDEL` + `PUBLISH CHANNEL G`

## 2. routeorch / vnetorch → APPL_DB (ProducerStateTable)

`RouteOrch` コンストラクタ (routeorch.cpp L53):
```cpp
ProducerStateTable m_appTunnelDecapTermProducer(db, APP_TUNNEL_DECAP_TERM_TABLE_NAME);
```

VIP subnet decap ルート追加/削除時 (routeorch.cpp L3220-3251) に同テーブルへ書き込む。
`VNetRouteOrch` も同様 (vnetorch.cpp:1563-1594)。

## 3. APPL_DB → tunneldecaporch (ConsumerStateTable / SubscriberStateTable)

`TunnelDecapOrch` は `Orch(appDb, tableNames)` 継承で初期化 (tunneldecaporch.cpp L30-35)。
`tableNames` には `APP_TUNNEL_DECAP_TERM_TABLE_NAME` が含まれる。

`Orch` ベースクラスが `ConsumerStateTable` を生成し、`APP_TUNNEL_DECAP_TERM_TABLE_CHANNEL@0` を購読。
通知受信 → `Select::select()` wake-up → `consumer_state_table_pops.lua` で `SPOP KEY_SET` + `HGETALL _<table>:<key>` → `TunnelDecapOrch::doTask()` → `doDecapTunnelTermTask()` 呼び出し。

## 4. CONFIG_DB → tunneldecaporch (SubscriberStateTable)

コンストラクタ (tunneldecaporch.cpp L39-48) で `SUBNET_DECAP` を `SubscriberStateTable` で購読:

```cpp
auto cfgSubnetDecapSubTable = new SubscriberStateTable(
    configDb, CFG_SUBNET_DECAP_TABLE_NAME,
    TableConsumable::DEFAULT_POP_BATCH_SIZE, 0);
```

Redis keyspace notification: `PSUBSCRIBE __keyspace@{db_id}__:SUBNET_DECAP|*`
イベント受信 → `pops()` → `doSubnetDecapTask()` 呼び出し。
また、コンストラクタ内で初期 pops() を実行して起動時のキャッチアップも行う (L40-46)。

## 5. tunneldecaporch → STATE_DB (Table 直接書き込み)

`setDecapTunnelTermStatus()` / `removeDecapTunnelTermStatus()` (tunneldecaporch.cpp L1539-1567):
```cpp
Table stateTunnelDecapTermTable(stateDb, STATE_TUNNEL_DECAP_TERM_TABLE_NAME);
stateTunnelDecapTermTable->set(key, fv);   // SAI create 成功後
stateTunnelDecapTermTable->del(key);        // SAI remove 成功後
```
`Table` クラスは `HSET` / `HDEL` を直接 Redis に発行する。keyspace notification は発生するが、
STATE_DB の読み取り側（モニタリング用）は別途 `SubscriberStateTable` または `Table::get()` で参照する。

## 6. まとめ: 通信メカニズム一覧

| 経路 | Publish 側 | Subscribe 側 | メカニズム |
|------|-----------|-------------|-----------|
| CONFIG_DB → tunnelmgrd (TUNNEL) | CLI/config push | tunnelmgrd | `SubscriberStateTable` (keyspace notification) |
| tunnelmgrd → APPL_DB (TUNNEL_DECAP_TERM_TABLE) | tunnelmgrd `m_appIpInIpTunnelDecapTermTable.set/del` | tunneldecaporch | `ProducerStateTable` / `ConsumerStateTable` |
| routeorch → APPL_DB (TUNNEL_DECAP_TERM_TABLE) | routeorch `m_appTunnelDecapTermProducer.set/del` | tunneldecaporch | `ProducerStateTable` / `ConsumerStateTable` |
| CONFIG_DB → tunneldecaporch (SUBNET_DECAP) | CONFIG_DB 直接変更 | tunneldecaporch | `SubscriberStateTable` (keyspace notification) |
| tunneldecaporch → STATE_DB | tunneldecaporch `stateTunnelDecapTermTable->set/del` | モニタリング系 | `Table` 直接 (HSET/HDEL) |

---

*生成日: 2026-05-17*
