# PASS_THROUGH_ROUTE_TABLE (ChassisOrch) — 通信メカニズム (Phase G) 解析メモ

調査日: 2026-05-17
対象テーブル: CONFIG_DB `PASS_THROUGH_ROUTE_TABLE`
ソース: `sonic-swss/orchagent/chassisorch.cpp`, `orchagent/vnetorch.cpp`, `orchagent/observer.h`

---

## 1. CONFIG_DB Subscribe メカニズム

`ChassisOrch` は `Orch` 基底クラスを継承し、コンストラクタで `cfgDb` (CONFIG_DB) と `tableNames` を渡す。

```cpp
// chassisorch.cpp:4-13
ChassisOrch::ChassisOrch(
    DBConnector* cfgDb,
    DBConnector* applDb,
    const std::vector<std::string>& tableNames,
    VNetRouteOrch* vNetRouteOrch) :
    Orch(cfgDb, tableNames),           // ← CONFIG_DB tableNames を Consumer として登録
    m_passThroughRouteTable(applDb, APP_PASS_THROUGH_ROUTE_TABLE_NAME),
    m_vNetRouteOrch(vNetRouteOrch)
```

- `Orch(cfgDb, tableNames)` が内部で `swsscommon::Consumer` を生成し、`SubscriberStateTable` 相当の仕組みで CONFIG_DB の `PASS_THROUGH_ROUTE_TABLE` 変化を待ち受ける
- テーブル名定数: `CFG_PASS_THROUGH_ROUTE_TABLE_NAME = "PASS_THROUGH_ROUTE_TABLE"` (`schema.h:371`)
- イベントは `Orch::execute()` → `doTask(Consumer&)` の順で同期的に処理される

### orchdaemon による登録 (`orchdaemon.cpp:290-293`)

```cpp
const vector<string> chassis_frontend_tables = {
    CFG_PASS_THROUGH_ROUTE_TABLE_NAME,
};
ChassisOrch* chassis_frontend_orch = new ChassisOrch(m_configDb, m_applDb, chassis_frontend_tables, vnet_rt_orch);
```

`OrchDaemon` の select ループが `epoll` ベースで変化通知を受け、ChassisOrch の `doTask()` を呼び出す。

---

## 2. VNetRouteOrch Observer パターン

### Observer インタフェース (`observer.h`)

```cpp
// observer.h:9-33
enum SubjectType {
    SUBJECT_TYPE_NEXTHOP_CHANGE,   // ← ChassisOrch が受け取る型
    SUBJECT_TYPE_NEIGH_CHANGE,
    ...
};

class Observer {
public:
    virtual void update(SubjectType, void *) = 0;
};

class Subject {
public:
    virtual void attach(Observer *observer) { ... }
    virtual void detach(Observer *observer) { ... }
    virtual void notify(SubjectType type, void *cntx) { ... }
};
```

### ChassisOrch の Observer 登録

`doTask()` が CONFIG_DB `SET` を受けると `VNetRouteOrch::attach(this, ip)` を呼ぶ:

```cpp
// chassisorch.cpp:50-67
void ChassisOrch::doTask(Consumer &consumer)
{
    auto it = consumer.m_toSync.begin();
    while (it != consumer.m_toSync.end())
    {
        const std::string & op = kfvOp(t);
        const std::string & ip = kfvKey(t);

        if (op == SET_COMMAND)
            m_vNetRouteOrch->attach(this, ip);   // 登録
        else
            m_vNetRouteOrch->detach(this, ip);   // 解除
        it = consumer.m_toSync.erase(it);
    }
}
```

`VNetRouteOrch` は `Subject` を継承し、`next_hop_observers_` (`VNetNextHopObserverTable`) で IP アドレスごとにオブザーバリストを管理する:

```cpp
// vnetorch.h:596
VNetNextHopObserverTable next_hop_observers_;
// typedef std::map<IpAddress, VNetNextHopObserverEntry> VNetNextHopObserverTable
// VNetNextHopObserverEntry::observers = list<Observer*>
```

### VNetNextHopUpdate 通知データ構造 (`vnetorch.h:400-411`)

```cpp
struct VNetNextHopUpdate {
    std::string op;          // SET_COMMAND / DEL_COMMAND
    std::string vnet;        // VNet 名
    IpAddress   destination; // 監視対象 IP アドレス
    IpPrefix    prefix;      // カバーするプレフィックス
    nextHop     nexthop;     // { ips, ifname, ... }
};
```

---

## 3. ChassisOrch::update() — 通知受信ハンドラ

`VNetRouteOrch` が `observer->update(SUBJECT_TYPE_NEXTHOP_CHANGE, ...)` を呼ぶと ChassisOrch の以下が実行される:

```cpp
// chassisorch.cpp:15-26
void ChassisOrch::update(SubjectType type, void* ctx)
{
    VNetNextHopUpdate* updateInfo = reinterpret_cast<VNetNextHopUpdate*>(ctx);
    if (updateInfo->op == SET_COMMAND)
        addRouteToPassThroughRouteTable(*updateInfo);
    else
        deleteRoutePassThroughRouteTable(*updateInfo);
}
```

- `SubjectType` のチェックなし — `update()` 呼び出し元は常に `SUBJECT_TYPE_NEXTHOP_CHANGE` のみ
- `ctx` を `VNetNextHopUpdate*` に直接 `reinterpret_cast` — 型安全性は呼び出し元に依存

---

## 4. 通知トリガー（VNetRouteOrch 側）

ChassisOrch に通知が届く全パスを示す:

| 発生源 | 関数 | op | 行番号 |
|--------|------|----|--------|
| `attach()` 時（best route あり） | `VNetRouteOrch::attach()` | SET | vnetorch.cpp:1905 |
| `detach()` 時（best route あり） | `VNetRouteOrch::detach()` | DEL | vnetorch.cpp:1946 |
| VNet ルート追加（new best route） | `VNetRouteOrch::addRoute()` | SET | vnetorch.cpp:1985 |
| VNet ルート削除（後継 best あり） | `VNetRouteOrch::delRoute()` | SET | vnetorch.cpp:2032 |
| VNet ルート削除（後継 best なし） | `VNetRouteOrch::delRoute()` | DEL | vnetorch.cpp:2032 |

すべての通知は同プロセス内の同期呼び出し（関数コール）であり、メッセージキューや Redis 経由ではない。

---

## 5. APP_DB 書き込み (`ProducerStateTable`)

`ChassisOrch` コンストラクタで `m_passThroughRouteTable` を `Table` として初期化:

```cpp
// chassisorch.cpp:10
m_passThroughRouteTable(applDb, APP_PASS_THROUGH_ROUTE_TABLE_NAME),
```

- `swsscommon::Table` を使用 (`ProducerStateTable` ではなく直接 `Table`)
- `m_passThroughRouteTable.set(key, fvVector)` / `.del(key)` で APP_DB に書き込む
- APP_DB テーブル名定数: `APP_PASS_THROUGH_ROUTE_TABLE_NAME = "PASS_THROUGH_ROUTE_TABLE"` (`schema.h:93`)

---

## 6. 通信フロー全体図

```
orchdaemon の select ループ (epoll)
  │
  ▼
CONFIG_DB PASS_THROUGH_ROUTE_TABLE 変化
  │  (Orch 基底 Consumer / SubscriberStateTable 相当)
  ▼
ChassisOrch::doTask(Consumer&)
  │  SET → attach(this, ip)
  │  DEL → detach(this, ip)
  ▼
VNetRouteOrch::attach()/detach()/addRoute()/delRoute()
  │  (インプロセス同期呼び出し)
  │  observer->update(SUBJECT_TYPE_NEXTHOP_CHANGE, &VNetNextHopUpdate)
  ▼
ChassisOrch::update(SubjectType, void*)
  │  SET_COMMAND → addRouteToPassThroughRouteTable()
  │  DEL_COMMAND → deleteRoutePassThroughRouteTable()
  ▼
APP_DB PASS_THROUGH_ROUTE_TABLE
  (swsscommon::Table::set() / ::del())
```

---

## 7. タイミング特性

| 段階 | 遅延 | メカニズム |
|------|------|-----------|
| CONFIG_DB → doTask() 呼び出し | epoll 即時 (ms オーダー) | Orch Consumer |
| doTask() → VNetRouteOrch::attach() | 同期 (0 ms) | 直接関数呼び出し |
| attach() → ChassisOrch::update() | 同期 (0 ms) | Observer::update() 直接呼び出し |
| update() → APP_DB 書き込み | 同期 (0 ms) | swsscommon::Table::set() |

全体として CONFIG_DB 変化から APP_DB 書き込み完了まで**完全同期**で処理される。orchdaemon の次のイベントループイテレーション前に APP_DB が更新される。

---

## 8. 証拠リンク

- `chassisorch.cpp:4-13` — コンストラクタ: `Orch(cfgDb, tableNames)` CONFIG_DB 購読
- `chassisorch.cpp:15-26` — `update()`: Observer 通知受信ハンドラ
- `chassisorch.cpp:50-67` — `doTask()`: attach/detach 制御
- `observer.h:9-55` — `SubjectType` enum, `Observer`, `Subject` インタフェース定義
- `vnetorch.h:596` — `next_hop_observers_` マップ
- `vnetorch.h:400-411` — `VNetNextHopUpdate` 構造体
- `vnetorch.cpp:1861-1910` — `attach()`: observer 登録 + 即時 update 送出
- `vnetorch.cpp:1910-1949` — `detach()`: observer 解除 + 即時 DEL 通知
- `vnetorch.cpp:1955-1990` — `addRoute()`: best route 更新時通知
- `vnetorch.cpp:2004-2040` — `delRoute()`: ルート削除時通知
- `orchdaemon.cpp:290-293` — ChassisOrch インスタンス化
- `schema.h:93` — `APP_PASS_THROUGH_ROUTE_TABLE_NAME`
- `schema.h:371` — `CFG_PASS_THROUGH_ROUTE_TABLE_NAME`
