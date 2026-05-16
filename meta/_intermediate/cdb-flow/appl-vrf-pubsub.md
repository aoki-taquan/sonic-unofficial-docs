# appl-vrf — Phase G (通信メカニズム / pub-sub) 中間メモ

調査日: 2026-05-15。ソース: `sonic-swss/orchagent/vrforch.{cpp,h}`、`sonic-swss/orchagent/orch.{cpp,h}`、`sonic-swss/cfgmgr/vrfmgr.cpp`。

## 結論サマリ

`VRFOrch` は `Orch2` を継承し、コンストラクタで APPL_DB (`appDb`) と `APP_VRF_TABLE_NAME = "VRF_TABLE"` を渡す。APPL_DB の `DBConnector` を引数に取る `Orch` コンストラクタは `orch.cpp:1194` で `ConsumerStateTable(db, tableName, gBatchSize, pri)` を生成して `Consumer` にラップする。したがって **VRF_TABLE の購読は `ConsumerStateTable` (Redis Lua-script ベースのバッチ pop) で行われる**。SubscriberStateTable (keyspace notification) ではない。

これは本ページ本体 (appl-vrf.md) の「購読者」節にある "SubscriberStateTable で購読" という記述と矛盾する。ページ内に warning admonition を入れて訂正した。

## 検出した根拠

### 1. VRFOrch のコンストラクタ (`vrforch.h:52-56`)

```cpp
VRFOrch(swss::DBConnector *appDb, const std::string& appTableName,
        swss::DBConnector *stateDb, const std::string& stateTableName) :
    Orch2(appDb, appTableName, request_),
    m_stateVrfObjectTable(stateDb, stateTableName)
{
}
```

第1引数 = APPL_DB の DBConnector、第2引数 = `"VRF_TABLE"`、pri 引数省略 → `default_orch_pri`。

### 2. Orch コンストラクタの consumer 選択分岐 (`orch.cpp:1188-1195`)

```cpp
if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
{
    addExecutor(new Consumer(new SubscriberStateTable(db, tableName, TableConsumable::DEFAULT_POP_BATCH_SIZE, pri), this, tableName));
}
else
{
    addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
}
```

APPL_DB は `else` 分岐 → `ConsumerStateTable` + `gBatchSize`。

### 3. バッチ pop の駆動 (`orch.cpp:556`)

```cpp
getConsumerTable()->pops(*entries);
```

`Consumer::execute()` で `pops()` がコール → Redis 側の Lua スクリプトが `<TABLE>_KEY_SET` を atomically drain → `m_toSync` map にマージ → `Orch2::doTask(Consumer&)` (`orch.cpp:1226`) で 1 件ずつ `Request::parse()` → `addOperation()` / `delOperation()` をディスパッチ。

### 4. doTask の流れ (`orch.cpp:1226 Orch2::doTask`)

`m_toSync` をループし `kfvOp(t)` が `SET_COMMAND` なら `addOperation(request_)`、`DEL_COMMAND` なら `delOperation(request_)` を呼ぶ。`VRFOrch::addOperation` / `delOperation` (`vrforch.cpp:27, 157`) が実装本体。

### 5. 生産側 (writer): `vrfmgrd` (`cfgmgr/vrfmgr.cpp:303`)

```cpp
m_appVrfTableProducer.set(vrfName, kfvFieldsValues(t));
```

`ProducerStateTable` (APPL_DB 用) で `VRF_TABLE` に書き込み。`set()` は Lua スクリプトで `<TABLE>_KEY_SET` に key を追加 + hash 本体を更新するため、消費側の `ConsumerStateTable::pops()` と整合する。

## VxlanTunnelOrch との連携 (非 pub/sub の直接参照)

`VRFOrch::updateVrfVNIMap` (`vrforch.cpp:200-247`) は `gDirectory` レジストリ経由で他 Orch を **同期的にメソッド呼び出し** する。pub/sub 経路ではない点に注意。

```cpp
EvpnNvoOrch* evpn_orch = gDirectory.get<EvpnNvoOrch*>();      // vrforch.cpp:205
VxlanTunnelOrch* tunnel_orch = gDirectory.get<VxlanTunnelOrch*>(); // vrforch.cpp:206
...
vlan_id = tunnel_orch->getVlanMappedToVni(vni);               // vrforch.cpp:233
gPortsOrch->updateL3VniStatus(vlan_id, true);                 // vrforch.cpp:239
```

つまり VNI マッピング処理は「APPL_DB `VRF_TABLE` の `vni` フィールド変化 → ConsumerStateTable で pop → addOperation 内で EvpnNvoOrch / VxlanTunnelOrch / PortsOrch を直接呼ぶ」という流れになる。VxlanTunnelOrch 側の APPL_DB `VXLAN_TUNNEL_MAP_TABLE` 購読とは独立した経路。

## VNET (関連テーブル) との関係

`VRFOrch` は **`VNET_TABLE` を購読しない**。`VnetOrch` (orchagent/vnetorch.cpp) が別 Executor として APPL_DB `VNET_TABLE` を購読し、VNET 単位の VRF 作成を独自に行う。本ページ (appl-vrf.md) のスコープは `VRF_TABLE` 単体に閉じる。

## バッチサイズ / 優先度

- バッチサイズ: `gBatchSize` (orchagent グローバル、デフォルト 128。`--batch-size` で上書き可)。
- 優先度: `pri` 引数省略 → `default_orch_pri` (orch.h)。`Orch::doTask()` 内のラウンドロビンに従う。

## ページ本体に書く要約

- VRF_TABLE の購読は **ConsumerStateTable** (APPL_DB 用バッチ pop)、SubscriberStateTable ではない。
- Producer は `vrfmgrd` の `ProducerStateTable` (`<TABLE>_KEY_SET` 経由)。
- 1 バッチで複数 VRF が並ぶ可能性があり、`Orch2::doTask()` がループで `addOperation` / `delOperation` を 1 件ずつ呼ぶ。
- VNI マッピングは APPL_DB pub/sub ではなく `gDirectory` 経由の Orch 直接呼び出し (EvpnNvoOrch / VxlanTunnelOrch / PortsOrch) で連鎖する。
