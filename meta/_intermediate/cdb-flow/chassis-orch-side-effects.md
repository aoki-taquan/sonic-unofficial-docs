# ChassisOrch Side-Effects 調査メモ (Phase F)

対象: `PASS_THROUGH_ROUTE_TABLE`（ChassisOrch）

## 調査対象ファイル

- `sonic-swss/orchagent/chassisorch.cpp`
- `sonic-swss/orchagent/vnetorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss-common/common/schema.h`

## ChassisOrch が引き起こす副作用

### 1. `VNetRouteOrch::attach()` による即時通知

`doTask()` が CONFIG_DB の `SET` を処理すると、`m_vNetRouteOrch->attach(this, ip)` を呼び出す。
`VNetRouteOrch::attach()` の内部では:

1. `next_hop_observers_` マップに dstAddr エントリを追加（初回のみ）
2. 既存の `syncd_routes_` から dstAddr を包含するプレフィックスを全検索
3. 最良ルート（`routeTable.rbegin()`）が存在する場合、**即座に** `observer->update(SUBJECT_TYPE_NEXTHOP_CHANGE, ...)` を `SET_COMMAND` で呼び出す

→ ChassisOrch の `update()` が同期的に呼ばれ、APP_DB `PASS_THROUGH_ROUTE_TABLE` に直ちにエントリが書き込まれる。

```cpp
// vnetorch.cpp:1895-1905
auto bestRoute = observerEntry->second.routeTable.rbegin();
if (bestRoute != observerEntry->second.routeTable.rend())
{
    for (auto vnetEntry : bestRoute->second)
    {
        VNetNextHopUpdate update = { SET_COMMAND, ... };
        observer->update(SUBJECT_TYPE_NEXTHOP_CHANGE, reinterpret_cast<void*>(&update));
    }
}
```

### 2. `VNetRouteOrch::detach()` による即時削除通知

CONFIG_DB `DEL` → `m_vNetRouteOrch->detach(this, ip)` → 最良ルートが存在すれば `DEL_COMMAND` で `update()` を呼び出す
→ ChassisOrch の `deleteRoutePassThroughRouteTable()` が呼ばれ、APP_DB エントリが削除される。

```cpp
// vnetorch.cpp:1934-1946
auto bestRoute = observerEntry->second.routeTable.rbegin();
if (bestRoute != observerEntry->second.routeTable.rend())
{
    VNetNextHopUpdate update = { DEL_COMMAND, ... };
    observer->update(SUBJECT_TYPE_NEXTHOP_CHANGE, ...);
}
next_hop_observers_.erase(observerEntry);
```

### 3. VNetRoute 変化による自動更新

VNetRouteOrch が `addRoute()` / `delRoute()` でルートを更新した際、登録済みオブザーバ（ChassisOrch）に通知が届く:

- `addRoute()` → 新規ルートが best route になった場合: `SET_COMMAND` で `update()` → APP_DB 上書き更新
- `delRoute()` → ルート削除後に best route が変わった場合: `DEL_COMMAND` で `update()` → APP_DB エントリ削除

つまり、VNet 側ルートが変化するたびに APP_DB `PASS_THROUGH_ROUTE_TABLE` も自動的に更新される。

### 4. APP_DB への書き込み（直接副作用）

ChassisOrch が呼び出す `m_passThroughRouteTable.set(everflow_route, fvVector)` は:
- `Table::set()` を経由して APP_DB の `PASS_THROUGH_ROUTE_TABLE|<IP_prefix>` に直接書き込む
- 書き込みは同期的（Redis `HSET` コマンド）
- APP_DB を購読する下流エージェント（bgpcfgd や fpmsyncd 等）が通知を受け取る

APP_DB `PASS_THROUGH_ROUTE_TABLE` の消費者は orchagent 内には存在せず（grep 確認済み）、
データプレーン連携エージェントが外部で購読する設計と推定される。

### 5. CONFIG_DB フィールド値の無視

`doTask()` は `kfvKey(t)` のみを参照し、`kfvFieldsValues(t)` は一切読まない。
CONFIG_DB テーブルへのフィールド書き込みは副作用なし（無視される）。

## まとめ（副作用一覧）

| トリガー | 副作用 |
|---------|--------|
| CONFIG_DB `SET` 時 | `VNetRouteOrch::attach()` → 即時 APP_DB set（既存 best route があれば） |
| CONFIG_DB `DEL` 時 | `VNetRouteOrch::detach()` → 即時 APP_DB del → observer エントリ削除 |
| VNetRoute `addRoute()` | best route 変化時に APP_DB 上書き |
| VNetRoute `delRoute()` | ルート消失時に APP_DB エントリ削除 |
| CONFIG_DB フィールド書込 | 無視（副作用なし） |
