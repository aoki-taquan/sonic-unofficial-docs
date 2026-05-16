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
