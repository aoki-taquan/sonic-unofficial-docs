# route-orch-event — Phase B 書込み順依存スキャンノート

## 対象ソース

- `orchagent/routeorch.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/routeorch.h` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/orchdaemon.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/mirrororch.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/natorch.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `fpmsyncd/fpmsyncd.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## 調査対象: RouteOrch 通知機構の初期化順序依存

RouteOrch の通知機構（ResponsePublisher / NextHopObserver）は 2 つの軸で「順序」が問題になる。

1. **ResponsePublisher 有効化と fpmsyncd の suppress-fib-pending 設定**
2. **NextHopObserver の `attach()` タイミング**

---

## 1. ResponsePublisher の有効化順序

### orchdaemon.cpp での RouteOrch 初期化 (L337)

```cpp
gRouteOrch = new RouteOrch(m_applDb, route_tables, gSwitchOrch, gNeighOrch,
                            gIntfsOrch, vrf_orch, gFgNhgOrch, gSrv6Orch, route_zmq_sever);
```

RouteOrch は `gNeighOrch`・`gIntfsOrch`・`vrf_orch`・`gFgNhgOrch`・`gSrv6Orch` が
すべて生成完了した後でインスタンス化される。

コンストラクタ内で `m_publisher.setBuffered(true)` を設定し、
バッファリングモードで起動する (routeorch.cpp L57-58):

```cpp
m_publisher.setBuffered(true);
m_publisher.m_directDbWrite = true;
```

→ **`ResponsePublisher` はインスタンス化と同時に有効** になる。
  通知バッファは `doTask()` 末尾の `flush()` まで溜まる。

### fpmsyncd 側 — suppress-fib-pending 設定が必要 (fpmsyncd.cpp L78–120)

```cpp
const auto routeResponseChannelName =
    std::string("APPL_DB_") + APP_ROUTE_TABLE_NAME + "_RESPONSE_CHANNEL";
...
std::string suppressionEnabledStr;
deviceMetadataTable.hget("localhost", "suppress-fib-pending", suppressionEnabledStr);
if (suppressionEnabledStr == "enabled")
{
    routeResponseChannel = std::make_unique<NotificationConsumer>(&applStateDb, routeResponseChannelName);
    sync.setSuppressionEnabled(true);
}
```

`fpmsyncd` が `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` を購読するのは、
`CONFIG_DB DEVICE_METADATA|localhost` の `suppress-fib-pending = "enabled"` が設定されているときのみ。

**順序**: `CONFIG_DB` に `suppress-fib-pending = enabled` を書き込む → fpmsyncd 起動
（または再起動）→ fpmsyncd が RESPONSE_CHANNEL を購読開始 →
RouteOrch の `publishRouteState()` 通知が有効に利用される。

`suppress-fib-pending` が未設定のままだと `fpmsyncd` は RESPONSE_CHANNEL を購読せず、
orchagent 側の通知は無視される（Redis Pub/Sub なのでバッファされない）。

---

## 2. NextHopObserver `attach()` の順序依存

### `attach()` の仕様 (routeorch.cpp L308-350)

```cpp
void RouteOrch::attach(Observer *observer, const IpAddress& dstAddr, sai_object_id_t vrf_id)
{
    ...
    // Observer が attach() した時点で最長プレフィックスマッチが存在すれば即時通知
    auto route = observerEntry->second.routeTable.rbegin();
    if (route != observerEntry->second.routeTable.rend())
    {
        NextHopUpdate update = { vrf_id, dstAddr, route->first, route->second.nhg_key };
        observer->update(SUBJECT_TYPE_NEXTHOP_CHANGE, static_cast<void *>(&update));
    }
}
```

Observer が `attach()` したタイミングで、追跡対象 IP を含む最長プレフィックスマッチが
RouteOrch 内部テーブルにあれば **即時に `NextHopUpdate` を送出** する。

これは `attach()` タイミングによって Observer が受け取る初回通知が変わることを意味する:

| `attach()` のタイミング | 初回 `NextHopUpdate` |
|-------------------------|----------------------|
| RouteOrch がデフォルトルートを SAI に書き込む **前** | 通知なし（テーブルが空） |
| RouteOrch がデフォルトルートを SAI に書き込んだ **後** | 即時通知（デフォルトルート 0.0.0.0/0） |

### MirrorOrch の `attach()` タイミング (orchdaemon.cpp L406, mirrororch.cpp L517)

orchdaemon の初期化順:

```
gRouteOrch = new RouteOrch(...)  // L337
...
gMirrorOrch = new MirrorOrch(..., gRouteOrch, ...)  // L406
```

MirrorOrch がミラーセッションエントリを処理する際に `m_routeOrch->attach(this, entry.dstIp)` を呼ぶ (mirrororch.cpp L517)。
初期化順では RouteOrch が先に生成されるため、`attach()` 呼び出し時には RouteOrch が稼働済み。

### NatOrch の `attach()` タイミング (orchdaemon.cpp L465, natorch.cpp L414,458,504,591)

```
gNatOrch = new NatOrch(m_applDb, m_stateDb, nat_tables, gRouteOrch, gNeighOrch);  // L465
```

NatOrch も設定エントリ処理時に `m_routeOrch->attach(this, translatedIp)` を呼ぶ。
同様に RouteOrch が先に生成されるため順序問題は発生しない。

---

## 3. `m_orchList` 処理順序（`doTask()` 呼び出し順）

orchdaemon.cpp L500:

```cpp
m_orchList = { gSwitchOrch, gCrmOrch, gPortsOrch, gBufferOrch, gFlowCounterRouteOrch,
               gIntfsOrch, gNeighOrch, gNhgMapOrch, gNhgOrch, gCbfNhgOrch, gFgNhgOrch,
               gRouteOrch, gCoppOrch, ... };
```

`gNeighOrch` → `gNhgOrch` → `gCbfNhgOrch` → `gFgNhgOrch` → **`gRouteOrch`** の順で `doTask()` が呼ばれる。

これにより:
- 同一バッチサイクルで NeighOrch・NhgOrch が処理を完了してから RouteOrch が起動
- RouteOrch が `addRoute()` 内で `hasNhg()` / `hasNextHop()` を確認した時点で
  同じサイクル内のエントリが既に登録済みになっている

**ただし `publishRouteState()` / `flush()` は RouteOrch の `doTask()` 末尾まで呼ばれないため、
`notifyNextHopChangeObservers()` と同様に同一バッチ内では「RouteOrch の doTask() 完了後」に発火する。**

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 影響 |
|---|----------|------|------|
| 1 | `CONFIG_DB suppress-fib-pending = enabled` → fpmsyncd 起動 | 設定先行必須 | 未設定だと fpmsyncd は RESPONSE_CHANNEL を購読しない |
| 2 | RouteOrch `doTask()` 完了 → RESPONSE_CHANNEL 通知発火 | バッチ末尾の `flush()` 依存 | `doTask()` が完了するまで通知はバッファされる |
| 3 | RouteOrch インスタンス化 → Observer `attach()` | Observer は RouteOrch 生成後に `attach()` する | MirrorOrch / NatOrch はセッション設定処理時に `attach()` — RouteOrch より後に初期化される |
| 4 | デフォルトルート SAI 書き込み後 → Observer `attach()` | 即時通知の有無が変わる | `attach()` 前にルートが存在しない場合、初回通知は次のルート変化まで遅延 |
| 5 | NeighOrch / NhgOrch `doTask()` → RouteOrch `doTask()` | `m_orchList` 順序で担保 | 同バッチ内で nexthop 登録 → 経路 SAI プログラミングが完結 |
