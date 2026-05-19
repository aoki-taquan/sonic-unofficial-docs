# vnet-route — Redis 通知メカニズム (Phase G) 中間調査

対象ページ: `docs/reference/config-db/vnet-route.md`

`VNET_ROUTE` / `VNET_ROUTE_TUNNEL` の CONFIG_DB → APPL_DB → SAI 経路では 2 つの Orch が連携する。
書き込み側は `VNetCfgRouteOrch`（CONFIG_DB 購読 + APPL_DB ProducerStateTable 書き込み）、消費側は `VNetRouteOrch`（APPL_DB ConsumerStateTable + SAI 反映）。

## 1. CONFIG_DB 購読 — VNetCfgRouteOrch

### 1.1 購読方式: SubscriberStateTable → Consumer

`VNetCfgRouteOrch` は `Orch(db, tableNames)` で初期化されるため、内部で `Consumer`（`ConsumerStateTable` ラッパー）が生成される（vnetorch.cpp:3571）。

orchagent 起動時に `orchdaemon.cpp:270-279` で登録:

```cpp
vector<string> cfg_vnet_tables = {
    CFG_VNET_RT_TABLE_NAME,         // "VNET_ROUTE"
    CFG_VNET_RT_TUNNEL_TABLE_NAME   // "VNET_ROUTE_TUNNEL"
};
VNetCfgRouteOrch *cfg_vnet_rt_orch = new VNetCfgRouteOrch(m_configDb, m_applDb, cfg_vnet_tables);
```

CONFIG_DB `VNET_ROUTE` / `VNET_ROUTE_TUNNEL` テーブルに keyspace notification が発行されると orchagent の Select ループが起動し `doTask()` へ制御が渡る。

### 1.2 APPL_DB への書き込み — ProducerStateTable

`VNetCfgRouteOrch` は APPL_DB 書き込みに `ProducerStateTable` を使用する（vnetorch.cpp:3573-3574）:

```cpp
m_appVnetRouteTable       = ProducerStateTable(appDb, APP_VNET_RT_TABLE_NAME);
m_appVnetRouteTunnelTable = ProducerStateTable(appDb, APP_VNET_RT_TUNNEL_TABLE_NAME);
```

`ProducerStateTable::set/del` は以下を実行する:
1. `VNET_ROUTE_TABLE_KEY_SET` / `VNET_ROUTE_TABLE_KEY_DEL` ハッシュに書き込む
2. `VNET_ROUTE_TABLE_CHANNEL@0` チャネルに `G` / `D` コマンドを PUBLISH する

これにより `VNetRouteOrch` 側の `ConsumerStateTable` が即座に通知を受け取る。

## 2. APPL_DB 消費 — VNetRouteOrch

### 2.1 ConsumerStateTable で APPL_DB を購読

`VNetRouteOrch` は `Orch2(db, tableNames, request_)` で初期化される（vnetorch.cpp:732）。orchdaemon での登録:

```cpp
vector<string> vnet_tables = {
    APP_VNET_RT_TABLE_NAME,         // "VNET_ROUTE_TABLE"
    APP_VNET_RT_TUNNEL_TABLE_NAME   // "VNET_ROUTE_TUNNEL_TABLE"
};
VNetRouteOrch *vnet_rt_orch = new VNetRouteOrch(m_applDb, vnet_tables, vnet_orch);
```

APPL_DB チャネルへの PUBLISH を受信すると orchagent が `doTask()` → `handler_map_` ディスパッチ → `handleRoutes()` or `handleTunnel()` へ処理する（vnetorch.cpp:740-741）。

### 2.2 select タイムアウト

orchagent 主ループは `SELECT_TIMEOUT = 1000` ms でポーリングする（orchdaemon.cpp:23）:

```cpp
#define SELECT_TIMEOUT 1000   // ms
ret = m_select->select(&s, SELECT_TIMEOUT);
```

VNET_ROUTE 専用の追加タイムアウト設定はなく、orchagent の共通サイクルに従う。

## 3. BFD セッション通知 — BfdOrch との pub/sub

`VNET_ROUTE_TUNNEL` で `endpoint_monitor` を設定する場合、`VNetRouteOrch` は BFD セッション状態の変化通知を受け取る必要がある。

```cpp
// vnetorch.cpp:754
gBfdOrch->attach(this);
```

`BfdOrch` は STATE_DB `BFD_SESSION_TABLE` を `SubscriberStateTable` で購読し、BFD 状態変化を `notifyObservers()` 経由で `VNetRouteOrch` に伝達する（Observer パターン）。`VNetRouteOrch` の `update()` コールバックが呼ばれ、`updateVnetRouteEntry()` が STATE_DB `VNET_ROUTE_TUNNEL_TABLE` に active/inactive を書き込む。

BFD セッションの書き込みは `bfd_session_producer_` (ProducerStateTable) 経由で APPL_DB `BFD_SESSION_TABLE` に行われる（vnetorch.cpp:733）。

## 4. 購読チャネルまとめ

| 経路 | DB | チャネル / パターン | 書き込み元 | 消費者 |
|------|-----|---------------------|-----------|--------|
| CONFIG_DB → VNetCfgRouteOrch | CONFIG_DB (4) | `__keyspace@4__:VNET_ROUTE\|*` | configd / config CLI | `VNetCfgRouteOrch` (Consumer) |
| CONFIG_DB → VNetCfgRouteOrch | CONFIG_DB (4) | `__keyspace@4__:VNET_ROUTE_TUNNEL\|*` | configd / config CLI | `VNetCfgRouteOrch` (Consumer) |
| VNetCfgRouteOrch → APPL_DB | APPL_DB (0) | `VNET_ROUTE_TABLE_CHANNEL@0` | `ProducerStateTable` | `VNetRouteOrch` (ConsumerStateTable) |
| VNetCfgRouteOrch → APPL_DB | APPL_DB (0) | `VNET_ROUTE_TUNNEL_TABLE_CHANNEL@0` | `ProducerStateTable` | `VNetRouteOrch` (ConsumerStateTable) |
| VNetRouteOrch → APPL_DB BFD | APPL_DB (0) | `BFD_SESSION_TABLE_CHANNEL@0` | `bfd_session_producer_` | `BfdOrch` |
| BfdOrch → VNetRouteOrch | STATE_DB (6) | `__keyspace@6__:BFD_SESSION_TABLE\|*` | BFD デーモン | `BfdOrch` → Observer → `VNetRouteOrch` |

## 5. リトライ / バックオフ

- `VNetCfgRouteOrch::doTask()` はエントリを `m_toSync` に保留して orchagent の次サイクル（最大 1000 ms 後）に再試行。VNET_ROUTE 専用の backoff/sleep はない。
- `VNetRouteOrch` も同様に `return false` で `m_toSync` に残留し、1 サイクルごとに再試行する。
- BFD 状態変化は非同期（BFD デーモン主導）であり、明示的な retry interval は存在しない。

## 6. 参照

- `sonic-swss/orchagent/vnetorch.cpp` L732-754, L3570-3577
- `sonic-swss/orchagent/orchdaemon.cpp` L23, L265-282
- `sonic-swss-common/common/producerstatetable.h` (CHANNEL, KEY_SET, KEY_DEL)
- `sonic-swss-common/common/subscriberstatetable.cpp` (PSUBSCRIBE パターン)
