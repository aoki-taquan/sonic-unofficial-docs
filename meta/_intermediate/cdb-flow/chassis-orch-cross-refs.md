# PASS_THROUGH_ROUTE_TABLE / ChassisOrch — Phase C 暗黙参照テーブルスキャンノート

調査日: 2026-05-17
対象テーブル: CONFIG_DB `PASS_THROUGH_ROUTE_TABLE`
Consumer: `ChassisOrch` (`sonic-swss/orchagent/chassisorch.cpp`)
スキャン範囲: `chassisorch.cpp`・`chassisorch.h`・`vnetorch.h`・`vnetorch.cpp:1861-1950`・`orchdaemon.cpp:275-294`

---

## 概要

`ChassisOrch` はフィールドを持たない key-only テーブルを消費するため、フィールドベースの
leafref は存在しない。ただし key（IP プレフィックス文字列）が複数のオブジェクトと暗黙参照を
形成しており、コードレベルでの依存関係は以下の通り。

---

## 暗黙参照テーブル一覧

### 1. CONFIG_DB `PASS_THROUGH_ROUTE_TABLE` → VNetRouteOrch 内部状態

- `ChassisOrch::doTask()` は SET 時に `m_vNetRouteOrch->attach(this, IpAddress(ip))` を呼ぶ。
- `VNetRouteOrch::attach()` は `next_hop_observers_` テーブル（メモリ上の `VNetNextHopObserverTable`、
  `std::map<IpAddress, VNetNextHopObserverEntry>`）に dstAddr をキーとして observer を登録する。
- **暗黙参照**: CONFIG_DB の key が `VNetRouteOrch::syncd_routes_`（APP_DB VNet ルートから同期された
  プレフィックステーブル）と照合される。dstAddr を包含するプレフィックスが `syncd_routes_` に
  存在すれば即座に `VNetNextHopUpdate` が通知される。
- **証拠**: `vnetorch.cpp:1869-1905`
  ```cpp
  for (auto route : syncd_routes_)
  {
      if (route.first.isAddressInSubnet(dstAddr))
          observerEntry->second.routeTable.emplace(route.first, route.second);
  }
  ```

### 2. APP_DB `PASS_THROUGH_ROUTE_TABLE` (書き込み先)

- `ChassisOrch` は `VNetNextHopUpdate` 受信時に `m_passThroughRouteTable.set(prefix, fvVector)` /
  `m_passThroughRouteTable.del(prefix)` で APP_DB を更新する。
- `m_passThroughRouteTable` は `Table(applDb, APP_PASS_THROUGH_ROUTE_TABLE_NAME)` として初期化。
- 書き込む key は CONFIG_DB key（IP プレフィックス）を `IpPrefix` で正規化したもの。
- **参照方向**: CONFIG_DB key → 正規化 → APP_DB key（1:1 対応、ホストビット切り捨て正規化あり）

### 3. `VNetRouteOrch` の `syncd_routes_` への間接依存

- CONFIG_DB エントリが書かれた時点で `VNetRouteOrch` が対応する VNet ルートを処理済みでなければ、
  `routeTable` は空となり `VNetNextHopUpdate` は即時通知されない。
- 後から VNet ルートが追加されると `VNetRouteOrch` が `notifyObservers()` を呼び、登録済みの
  ChassisOrch observer へ UPDATE が届く（遅延参照解決）。
- **暗黙参照先**: APP_DB `VNET_ROUTE_TABLE` → `VNetRouteOrch::syncd_routes_`

---

## 参照テーブル一覧（サマリ）

| 参照元 | 参照先 | 参照種別 | 解決タイミング |
|--------|--------|---------|--------------|
| CONFIG_DB `PASS_THROUGH_ROUTE_TABLE\|<ip>` の key | `VNetRouteOrch::next_hop_observers_` (メモリ) | Observer 登録（コード依存） | `doTask()` SET 実行時 |
| CONFIG_DB key（IP） | `VNetRouteOrch::syncd_routes_` 内プレフィックス | サブネット包含チェック | `attach()` 呼び出し時（即時 or 遅延）|
| CONFIG_DB key（IP） → APP_DB key | APP_DB `PASS_THROUGH_ROUTE_TABLE` | 書き込み先（1:1 正規化対応） | `VNetNextHopUpdate` 受信時 |
