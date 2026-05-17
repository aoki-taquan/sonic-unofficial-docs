---
title: PASS_THROUGH_ROUTE_TABLE テーブル（ChassisOrch）
description: "PASS_THROUGH_ROUTE_TABLE テーブル — VoQ チャシスのフロントエンドルータにおける VNet パススルールートを CONFIG_DB に保持し、ChassisOrch が APP_DB へ転送するテーブル。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/chassisorch.cpp
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/chassisorch.h
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/orchdaemon.cpp
    ref: master
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: master
related:
  config_db:
    - PASS_THROUGH_ROUTE_TABLE
    - VNET_ROUTE_TABLE
  app_db:
    - PASS_THROUGH_ROUTE_TABLE
---

# PASS_THROUGH_ROUTE_TABLE テーブル（ChassisOrch）

## 概要

`PASS_THROUGH_ROUTE_TABLE` は [CONFIG_DB](../../reference/glossary.md#term-config_db) に保持され、VoQ (Virtual Output Queue) チャシスの**フロントエンドルータ**が VNet パススルールートを管理するテーブルである[^1]。`orchagent` 内の `ChassisOrch` がこのテーブルを購読し、VNet nextHop 変化通知を受けて APP_DB の同名テーブルへルートエントリを転送する。

<!-- cdb-mermaid -->
### データフロー

```mermaid
flowchart LR
  CDB[("CONFIG_DB\nPASS_THROUGH_ROUTE_TABLE")]
  ChOrch["ChassisOrch\n(orchagent)"]
  VNetOrch["VNetRouteOrch\n(observer)"]
  ADB[("APP_DB\nPASS_THROUGH_ROUTE_TABLE")]
  RouteOrch["routeorch"]

  CDB -->|doTask: attach/detach| ChOrch
  ChOrch -->|attach(observer)| VNetOrch
  VNetOrch -->|VNetNextHopUpdate| ChOrch
  ChOrch -->|set/del| ADB
  ADB --> RouteOrch
```

!!! note "凡例"
    CONFIG_DB エントリが「パススルールートを有効にする」シグナルとして機能する。実際のルート情報は VNetRouteOrch から通知された `VNetNextHopUpdate` をもとに APP_DB に書き込まれる。
<!-- /cdb-mermaid -->

## key 構造

```text
PASS_THROUGH_ROUTE_TABLE|<IP_prefix>
```

- `<IP_prefix>`: VNet ルートの宛先 IP プレフィックス（例: `10.1.0.0/16`）
- `IpPrefix` クラスで正規化される

## フィールド（CONFIG_DB 側）

このテーブルは**フィールドを持たない key-only テーブル**である。

CONFIG_DB に書き込まれる情報は key（IP プレフィックス）のみで、フィールド値は使用しない。ChassisOrch の `doTask()` は key を読み取り、`SET` 操作時は `VNetRouteOrch::attach()`、`DEL` 操作時は `VNetRouteOrch::detach()` を呼び出すだけである[^2]。

!!! info "YANG スキーマ"
    本テーブルの YANG モデルは存在しない。YANG バリデーションの対象外。

## APP_DB への書き込みフィールド

`ChassisOrch` が VNet nextHop 更新を受けて APP_DB `PASS_THROUGH_ROUTE_TABLE` に書き込むフィールドを以下に示す。

| フィールド | 型 | 固定値 / 由来 | 説明 |
|-----------|----|-------------|------|
| `redistribute` | string | `"true"` (固定) | ルートの再配布フラグ。常に `"true"` |
| `next_vrf_name` | string | `VNetNextHopUpdate.vnet` | nextHop が属する VNet 名 |
| `next_hop_ip` | string | `VNetNextHopUpdate.nexthop.ips.to_string()` | nextHop IP アドレス |
| `ifname` | string | `VNetNextHopUpdate.nexthop.ifname` | 出力インタフェース名 |
| `source` | string | `"CHASSIS_ORCH"` (固定) | 書き込み主体の識別子 |

<!-- defaults -->
## 暗黙デフォルト・コード由来挙動

### `redistribute = "true"` の固定値

APP_DB に書き込まれる `redistribute` は常に `"true"` のハードコード固定値である。ユーザー設定不可・YANG 未定義。

```cpp
// orchagent/chassisorch.cpp:34
fvVector.emplace_back("redistribute", "true");
```

routeorch はこのフィールドを参照してルート再配布の制御を行う（routeorch 側の実装による）。

### `source = "CHASSIS_ORCH"` の識別子

全エントリに `source = "CHASSIS_ORCH"` が付与される。書き込み主体を識別するための固定文字列で、変更不可。

```cpp
// orchagent/chassisorch.cpp:38
fvVector.emplace_back("source", "CHASSIS_ORCH");
```

### エントリ削除の連鎖

CONFIG_DB から `PASS_THROUGH_ROUTE_TABLE|<prefix>` が削除（`DEL`）された場合:
1. `ChassisOrch::doTask()` が `VNetRouteOrch::detach(this, ip)` を呼び出す
2. その後 VNetNextHopUpdate 通知経由で `deleteRoutePassThroughRouteTable()` が呼び出される
3. APP_DB から対応エントリが削除される

```cpp
// orchagent/chassisorch.cpp:43-47
void ChassisOrch::deleteRoutePassThroughRouteTable(const VNetNextHopUpdate& update)
{
    const std::string everflow_route = IpPrefix(update.destination.to_string()).to_string();
    m_passThroughRouteTable.del(everflow_route);
}
```

### ChassisOrch の初期化依存

ChassisOrch は orchdaemon の VNET 系orch 初期化後に登録される:

```cpp
// orchagent/orchdaemon.cpp:290-293
const vector<string> chassis_frontend_tables = {
    CFG_PASS_THROUGH_ROUTE_TABLE_NAME,  // = "PASS_THROUGH_ROUTE_TABLE"
};
ChassisOrch* chassis_frontend_orch = new ChassisOrch(m_configDb, m_applDb, chassis_frontend_tables, vnet_rt_orch);
```

`VNetRouteOrch` (`vnet_rt_orch`) が存在しない場合、ChassisOrch は機能しない（constructor で受け取る依存関係）。

### ハードコード定数一覧

| 定数 | 値 | 場所 |
|------|-----|------|
| CONFIG_DB テーブル名 | `"PASS_THROUGH_ROUTE_TABLE"` | `schema.h:371` `CFG_PASS_THROUGH_ROUTE_TABLE_NAME` |
| APP_DB テーブル名 | `"PASS_THROUGH_ROUTE_TABLE"` | `schema.h:93` `APP_PASS_THROUGH_ROUTE_TABLE_NAME` |
| `redistribute` | `"true"` | `chassisorch.cpp:34` |
| `source` | `"CHASSIS_ORCH"` | `chassisorch.cpp:38` |

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存・タイミング依存 (Phase B)

`ChassisOrch` (`chassis_frontend_orch`) は `orchdaemon.cpp` の初期化シーケンスと `m_orchList` に特定の順序制約を持つ。

### 1. VNetRouteOrch より後に生成（必須）

```cpp
// orchagent/orchdaemon.cpp:281-293
VNetRouteOrch *vnet_rt_orch = new VNetRouteOrch(m_applDb, vnet_tables, vnet_orch);
gDirectory.set(vnet_rt_orch);
// ...
ChassisOrch* chassis_frontend_orch = new ChassisOrch(m_configDb, m_applDb, chassis_frontend_tables, vnet_rt_orch);
```

`ChassisOrch` の constructor は `VNetRouteOrch*` を直接受け取り、メンバー `m_vNetRouteOrch` として保持する。`VNetRouteOrch` が先に生成されていないとコンパイル時に依存が解決できない（ポインタが null になりクラッシュする）。

→ **生成順依存**: `VNetRouteOrch` ≺ `ChassisOrch`（必須）

### 2. m_orchList 登録位置と doTask 処理順

```
// orchagent/orchdaemon.cpp 抜粋
m_orchList = { gSwitchOrch, ..., gPortsOrch, ..., gRouteOrch, ... };  // 初期一覧
// ...push_back 群:
gFdbOrch → gMirrorOrch → gAclOrch → gPbhOrch → chassis_frontend_orch → vrf_orch → ...
// → cfg_vnet_rt_orch → vnet_orch → vnet_rt_orch (VNetRouteOrch)
```

`m_orchList` における処理順では `chassis_frontend_orch` は `vnet_rt_orch` より**前**に配置される。  
ただし `ChassisOrch::doTask()` は CONFIG_DB テーブルの key を読み `VNetRouteOrch::attach()/detach()` を呼ぶだけで、SAI API を直接呼び出さない。そのため m_orchList 上の前後関係が機能的な問題を起こすことはない。

### 3. allPortsReady ガードなし

`ChassisOrch::doTask()` に `gPortsOrch->allPortsReady()` による early-return ガードは存在しない。

```cpp
// orchagent/chassisorch.cpp:50-72
void ChassisOrch::doTask(Consumer &consumer)
{
    auto it = consumer.m_toSync.begin();
    while (it != consumer.m_toSync.end())
    {
        // ガードなし — ポート初期化完了を待たずに実行
        const std::string & op = kfvOp(t);
        const std::string & ip = kfvKey(t);
        if (op == SET_COMMAND)
            m_vNetRouteOrch->attach(this, ip);
        else
            m_vNetRouteOrch->detach(this, ip);
        it = consumer.m_toSync.erase(it);
    }
}
```

CONFIG_DB にエントリが存在すれば、ポート初期化完了前でも即座に `attach()/detach()` が実行される。

### 4. warm-reboot 挙動

warm-reboot シーケンスでは `OrchDaemon::warmRestoreAndSyncUp()` が `m_orchList` 全体を対象に `bake()` → `doTask()` を **3 イテレーション**実行する（`orchdaemon.cpp:1100-1136`）。

`ChassisOrch` は warm-reboot 専用の reconciliation ロジック（`bake()` オーバーライド・`onWarmBootEnd()` オーバーライド）を持たない。CONFIG_DB に残存するエントリが再通知されることで `attach()` が再度呼ばれ、`VNetRouteOrch` に observer として自然に再登録される。APP_DB への実際の書き込みは `VNetRouteOrch` からの `VNetNextHopUpdate` 通知を待ってから行われる。

→ **warm-reboot 依存順**: `VNetRouteOrch` の state restore が完了してから `VNetNextHopUpdate` が流れる必要があるが、これは `VNetRouteOrch` 側の責務であり `ChassisOrch` 側での特別なハンドリングは不要。
<!-- /ordering -->

<!-- failure -->
## 失敗挙動 (Phase D)

ソース: `sonic-net/sonic-swss/orchagent/chassisorch.cpp`、`orchagent/vnetorch.cpp`

### doTask() — 入力バリデーションなし

`ChassisOrch::doTask()` は CONFIG_DB エントリの key に対するバリデーションを行わない。不正な IP 文字列が key として書き込まれた場合、`IpAddress` コンストラクタが例外を投げ、`m_toSync` に未処理エントリを残したまま例外が上位に伝播する。

| 失敗条件 | 挙動 |
|---------|------|
| key が無効な IP プレフィックス文字列 | `IpAddress()` コンストラクタが例外; `m_toSync.erase()` に到達しない → エントリが残留しリトライが繰り返される |
| `SET` 操作で `VNetRouteOrch::attach()` が呼ばれた後に即 `DEL` 操作 | `detach()` が正常に実行される（attach 済み observer は `next_hop_observers_` に存在するため） |

### VNetRouteOrch::detach() の assert(false)

CONFIG_DB から `DEL` 操作が到達すると `m_vNetRouteOrch->detach(this, ip)` が呼ばれる。対応 observer エントリが存在しない場合は `SWSS_LOG_ERROR` + `assert(false)` が実行される:

```cpp
// vnetorch.cpp:1910-1950
void VNetRouteOrch::detach(Observer* observer, const IpAddress& dstAddr)
{
    auto observerEntry = next_hop_observers_.find(dstAddr);
    if (observerEntry == next_hop_observers_.end())
    {
        SWSS_LOG_ERROR("Failed to detach observer for %s. Entry not found.",
                       dstAddr.to_string().c_str());
        assert(false);  // デバッグビルドではクラッシュ
        return;
    }
    // observer が見つからない場合も同様
    SWSS_LOG_ERROR("Failed to detach observer for %s. Observer not found.", ...);
    assert(false);
}
```

| 失敗条件 | 発生経路 | 挙動 |
|---------|---------|------|
| `DEL` 到着時に observer エントリが `next_hop_observers_` に不在 | CONFIG_DB 直接書込 / warm-reboot 再同期ズレ | `SWSS_LOG_ERROR` + `assert(false)` (デバッグビルド: クラッシュ) |
| observer リストに自身が含まれない | observer 二重 detach | `SWSS_LOG_ERROR` + `assert(false)` |

### VoQ 非環境での silent drop

`ChassisOrch` は `orchdaemon.cpp` で VoQ が有効な場合のみ生成される。VoQ 無効環境では `PASS_THROUGH_ROUTE_TABLE` への書き込みがあっても購読者が存在せず、APP_DB への転送は一切行われない (silent drop)。

> **Evidence**: `sonic-swss/orchagent/chassisorch.cpp:50-72`; `sonic-swss/orchagent/vnetorch.cpp:1910-1952`; `sonic-swss/orchagent/orchdaemon.cpp:281-293`; 詳細分析 `meta/_intermediate/cdb-flow/chassis-orch-failure.md`
<!-- /failure -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`ChassisOrch` が消費する `PASS_THROUGH_ROUTE_TABLE` はフィールドを持たない key-only テーブルであるため、フィールドベースの leafref は存在しない。ただし key（IP プレフィックス文字列）がコードレベルで複数のオブジェクトと暗黙的な依存を形成する。

| 参照元 | 参照先 | 参照種別 | 解決タイミング |
|--------|--------|---------|--------------|
| `PASS_THROUGH_ROUTE_TABLE\|<ip>` の key | `VNetRouteOrch::next_hop_observers_`（メモリ上の `std::map<IpAddress, VNetNextHopObserverEntry>`） | Observer 登録（コード内依存） | `doTask()` SET 実行時 |
| CONFIG_DB key（IP） | `VNetRouteOrch::syncd_routes_` 内プレフィックス（APP_DB VNet ルートから同期） | サブネット包含チェック（`isAddressInSubnet()`） | `attach()` 呼び出し時（即時または遅延） |
| CONFIG_DB key（IP）→ 正規化後 | APP_DB `PASS_THROUGH_ROUTE_TABLE\|<prefix>` | 書き込み先（1:1 正規化対応、ホストビット切り捨て） | `VNetNextHopUpdate` 受信時 |

### 解決タイミングの詳細

**即時通知（`syncd_routes_` にマッチあり）**: `VNetRouteOrch::attach()` 呼び出し時点で `syncd_routes_` に dstAddr を包含するプレフィックスが存在する場合、`attach()` の内部で即座に `observer->update(SUBJECT_TYPE_NEXTHOP_CHANGE, ...)` が呼ばれる。ChassisOrch は `attach()` の呼び出し完了前に `VNetNextHopUpdate` を受け取り APP_DB への書込みが行われる[^3]。

```cpp
// vnetorch.cpp:1869-1905
for (auto route : syncd_routes_)
{
    if (route.first.isAddressInSubnet(dstAddr))
        observerEntry->second.routeTable.emplace(route.first, route.second);
}
// bestRoute が存在すれば即座に observer->update() を呼ぶ
```

**遅延通知（`syncd_routes_` にマッチなし）**: CONFIG_DB に `PASS_THROUGH_ROUTE_TABLE` エントリを書いた時点では `VNetRouteOrch` が対応 VNet ルートを未処理の場合、`routeTable` は空となり即時通知は行われない。後から VNet ルートが追加・解決されると `VNetRouteOrch` が `notifyObservers()` を呼び、登録済み Observer である ChassisOrch に `VNetNextHopUpdate` が届く。

> **Evidence**: `vnetorch.cpp:1861-1905`（`attach()` 実装）; `chassisorch.cpp:14-27`（`update()` 実装）; 詳細分析 `meta/_intermediate/cdb-flow/chassis-orch-cross-refs.md`
<!-- /cross-refs -->

<!-- constants -->
## ハードコード定数 (Phase E)

> 調査証跡: `meta/_intermediate/cdb-flow/chassis-orch-constants.md`

### テーブル名定数 (`schema.h`)

`PASS_THROUGH_ROUTE_TABLE` は CONFIG_DB 側と APP_DB 側で同一の文字列を使用する。

| 定数名 | 値 | 行 |
|--------|-----|-----|
| `CFG_PASS_THROUGH_ROUTE_TABLE_NAME` | `"PASS_THROUGH_ROUTE_TABLE"` | `schema.h:371` |
| `APP_PASS_THROUGH_ROUTE_TABLE_NAME` | `"PASS_THROUGH_ROUTE_TABLE"` | `schema.h:93` |

両者が同一文字列のため、CONFIG_DB と APP_DB で同名テーブルが存在する点に注意。

### APP_DB フィールド値固定定数 (`chassisorch.cpp`)

`addRouteToPassThroughRouteTable()` がリテラル文字列として直接 `emplace_back()` に渡す固定値:

```cpp
// orchagent/chassisorch.cpp:34,38
fvVector.emplace_back("redistribute", "true");
fvVector.emplace_back("source", "CHASSIS_ORCH");
```

| フィールド | 固定値 | 行 | 備考 |
|-----------|-------|----|------|
| `redistribute` | `"true"` | `chassisorch.cpp:34` | ユーザー設定不可・YANG 未定義 |
| `source` | `"CHASSIS_ORCH"` | `chassisorch.cpp:38` | 書き込み主体の識別子 |

`chassisorch.h` にフィールド名文字列定数は定義されておらず、すべてリテラルとしてソースに直書きされている。

### key 正規化定数

key（IP プレフィックス）は `IpPrefix::to_string()` で正規化される:

```cpp
// chassisorch.cpp:39,46
const std::string everflow_route = IpPrefix(update.destination.to_string()).to_string();
```

ホストビットが切り捨てられる（例: `10.1.0.1/16` → `10.1.0.0/16`）。この正規化は `IpPrefix` クラス（`sonic-swss-common`）が担い、ChassisOrch 側に数値定数は存在しない。

!!! note "YANG 未定義"
    本テーブルは YANG スキーマが存在しないため、YANG 側に定数定義は一切ない。
<!-- /constants -->

<!-- side-effects -->
## 副作用・連鎖更新 (Phase F)

> 調査証跡: `meta/_intermediate/cdb-flow/chassis-orch-side-effects.md`

`ChassisOrch` が CONFIG_DB `PASS_THROUGH_ROUTE_TABLE` を処理する際に発生する主要な副作用を示す。

### 1. `VNetRouteOrch::attach()` 呼び出し時の即時 APP_DB 書き込み

CONFIG_DB `SET` を `doTask()` が処理すると `m_vNetRouteOrch->attach(this, ip)` が呼ばれる。  
`attach()` の内部では `VNetRouteOrch::syncd_routes_` から dstAddr を包含するプレフィックスを検索し、**best route が存在する場合はその場で `observer->update()` が同期呼び出しされる**。

```cpp
// vnetorch.cpp:1895-1905
auto bestRoute = observerEntry->second.routeTable.rbegin();
if (bestRoute != observerEntry->second.routeTable.rend())
{
    for (auto vnetEntry : bestRoute->second)
    {
        VNetNextHopUpdate update = { SET_COMMAND, vnetEntry.first, dstAddr, bestRoute->first, vnetEntry.second };
        observer->update(SUBJECT_TYPE_NEXTHOP_CHANGE, reinterpret_cast<void*>(&update));
    }
}
```

→ `attach()` の呼び出しが完了する前に ChassisOrch の `update()` → `addRouteToPassThroughRouteTable()` → APP_DB `PASS_THROUGH_ROUTE_TABLE` への `Table::set()` が**同期的に**実行される。

### 2. `VNetRouteOrch::detach()` 呼び出し時の即時 APP_DB 削除

CONFIG_DB `DEL` → `m_vNetRouteOrch->detach(this, ip)`:
- best route が存在すれば `DEL_COMMAND` で `observer->update()` を同期呼び出し
- → `deleteRoutePassThroughRouteTable()` → `m_passThroughRouteTable.del(everflow_route)`
- `next_hop_observers_` から対応エントリも同時に削除される

```cpp
// vnetorch.cpp:1934-1951
auto bestRoute = observerEntry->second.routeTable.rbegin();
if (bestRoute != observerEntry->second.routeTable.rend())
{
    VNetNextHopUpdate update = { DEL_COMMAND, ... };
    observer->update(SUBJECT_TYPE_NEXTHOP_CHANGE, reinterpret_cast<void*>(&update));
}
next_hop_observers_.erase(observerEntry);
```

### 3. VNetRoute 変化による自動追従更新

CONFIG_DB に登録した後、`VNetRouteOrch` 側でルートが追加（`addRoute()`）または削除（`delRoute()`）されると、登録済みオブザーバとして ChassisOrch に通知が届く:

| VNetRouteOrch 操作 | 条件 | ChassisOrch への副作用 |
|-------------------|------|----------------------|
| `addRoute()` | 追加ルートが new best route になった場合 | `SET_COMMAND` → APP_DB 上書き更新 |
| `delRoute()` | 削除ルートが best route で後継あり | `SET_COMMAND` → APP_DB に新 best route で書き換え |
| `delRoute()` | 削除ルートが best route で後継なし | `DEL_COMMAND` → APP_DB エントリ削除 |

これにより、VNet ルート変化は CONFIG_DB `PASS_THROUGH_ROUTE_TABLE` を経由せず**自動的に** APP_DB `PASS_THROUGH_ROUTE_TABLE` に反映される。

### 4. CONFIG_DB フィールド値は副作用を生じない

`doTask()` は `kfvKey(t)` のみ参照し、`kfvFieldsValues(t)` を読まない。  
CONFIG_DB エントリのフィールドへの書き込みは ChassisOrch に対して**一切の副作用をもたらさない**。

### 副作用まとめ

| トリガー | 発生主体 | APP_DB 変化 |
|---------|---------|------------|
| CONFIG_DB `SET`（best route あり） | `attach()` 内同期 | `PASS_THROUGH_ROUTE_TABLE` エントリ追加/更新 |
| CONFIG_DB `SET`（best route なし） | なし（遅延） | VNetRoute 解決後に更新 |
| CONFIG_DB `DEL` | `detach()` 内同期 | `PASS_THROUGH_ROUTE_TABLE` エントリ削除 |
| VNetRoute `addRoute()` | `VNetRouteOrch` 通知 | APP_DB 上書き更新 |
| VNetRoute `delRoute()` | `VNetRouteOrch` 通知 | APP_DB エントリ削除（後継なし時） |
| CONFIG_DB フィールド書き込み | — | 変化なし（無視） |

> **Evidence**: `sonic-swss/orchagent/chassisorch.cpp:14-47`; `sonic-swss/orchagent/vnetorch.cpp:1861-2040`; 詳細分析 `meta/_intermediate/cdb-flow/chassis-orch-side-effects.md`
<!-- /side-effects -->

## 制約

- `<IP_prefix>` は `IpPrefix` クラスで正規化される（ホストビットが切り捨てられる）
- CONFIG_DB エントリはフィールドを持たないため、値の書き込みは不要
- YANG モデルが存在しないため、`config load` / `config reload` 時の YANG バリデーション対象外

## 書き込み入り口

対象テーブル: CONFIG_DB `PASS_THROUGH_ROUTE_TABLE`

- 通常は**BGP / sonic-cfggen / 手動設定**経由で CONFIG_DB に書き込まれる想定
- CLI コマンドは現時点で存在しない（`config` / `show` サブコマンドなし）
- `sonic-db-cli CONFIG_DB hset 'PASS_THROUGH_ROUTE_TABLE|10.1.0.0/16' dummy 1` で直接設定可能

## 購読者

- `ChassisOrch` (`orchagent`) — CONFIG_DB テーブルチェンジを購読し VNetRouteOrch に attach/detach する

## 関連 CONFIG_DB / APP_DB

- 関連 CONFIG_DB: `VNET_ROUTE_TABLE`（VNet ルート設定）
- 関連 APP_DB: `PASS_THROUGH_ROUTE_TABLE`（ChassisOrch の書き込み先）、`SYSTEM_NEIGH`、`SYSTEM_LAG_TABLE`（chassis app DB クリーンアップ対象）

<!-- ref-triangle:start -->

## 関連リファレンス

- ソース: [`sonic-swss/orchagent/chassisorch.cpp`](https://github.com/sonic-net/sonic-swss/blob/master/orchagent/chassisorch.cpp)
- ソース: [`sonic-swss/orchagent/chassisorch.h`](https://github.com/sonic-net/sonic-swss/blob/master/orchagent/chassisorch.h)
- ソース: [`sonic-swss/orchagent/orchdaemon.cpp`](https://github.com/sonic-net/sonic-swss/blob/master/orchagent/orchdaemon.cpp)
- スキーマ定数: [`sonic-swss-common/common/schema.h`](https://github.com/sonic-net/sonic-swss-common/blob/master/common/schema.h)

<!-- ref-triangle:end -->

## 引用元

[^1]: ChassisOrch 実装: `chassisorch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/chassisorch.cpp>
[^2]: ChassisOrch の `doTask()`: `chassisorch.cpp:50-67`. observer attach/detach のみを行い、CONFIG_DB フィールドは参照しない。
[^3]: `VNetRouteOrch::attach()` の即時通知: `vnetorch.cpp:1891-1905`. `syncd_routes_` に一致プレフィックスがある場合は `attach()` 内部で `observer->update()` を呼ぶ。
