# DPU / ENI 通知メカニズム調査 (Phase G)

## 調査対象

`DashEniFwdOrch` が `DASH_ENI_FORWARD_TABLE` (APPL_DB) を購読する仕組みと、ACL テーブルへの書き込みに使用される ProducerStateTable の通知方式。

## 書き込み側 — HaMgrd から APPL_DB への ProducerStateTable

`DASH_ENI_FORWARD_TABLE` は APPL_DB (DB ID=0) のテーブルであり、HaMgrd が `ProducerStateTable` (swss-common の Redis List ベース producer) で書き込む。

```
HaMgrd
  → ProducerStateTable(applDb, "DASH_ENI_FORWARD_TABLE")
    → Redis List: APPL_DB:DASH_ENI_FORWARD_TABLE_KEY_SET
    → Redis Hash:  APPL_DB:DASH_ENI_FORWARD_TABLE|<vnet>:<mac>
```

テーブル名: `DASH_ENI_FORWARD_TABLE`  
定数定義: `sonic-swss-common/common/schema.h:196`  
```c
#define APP_DASH_ENI_FORWARD_TABLE "DASH_ENI_FORWARD_TABLE"
```

## 読み取り側 — ConsumerStateTable (Orch2 継承)

`DashEniFwdOrch` は `Orch2(applDb, APP_DASH_ENI_FORWARD_TABLE, request_)` で初期化される  
(`orchdaemon.cpp:615`, `dashenifwdorch.cpp:11-12`)。

`Orch2` は基底 `Orch` のコンストラクタ経由で `addConsumer(db, tableName)` を呼び出す。  
`Orch::addConsumer()` (`orch.cpp:1186-1196`) はDBのIDによって購読方式を切り替える:

```cpp
if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
    // SubscriberStateTable (Redis keyspace notification ベース)
else
    // ConsumerStateTable (Redis List ベース)
```

APPL_DB の `getDbId()` は `0` であり `CONFIG_DB` / `STATE_DB` / `CHASSIS_APP_DB` に該当しないため、  
**ConsumerStateTable** (List ポーリング型) が使用される。

### ConsumerStateTable のメカニズム

| 要素 | 値 |
|------|-----|
| pop 元 Redis キー | `DASH_ENI_FORWARD_TABLE_KEY_SET` (List) |
| pop バッチサイズ | `gBatchSize` (orchagent デフォルト 128) |
| イベントトリガ | `LPUSH` (ProducerStateTable の set/del) |
| 呼び出しメソッド | `Orch2::doTask(Consumer&)` → `addOperation()` / `delOperation()` |

## 出力側 — ProducerStateTable による APPL_DB ACL 書き込み

`EniFwdCtxBase` は 3 本の `ProducerStateTable` を保有する (`dashenifwdorch.cpp:403-405`):

```cpp
rule_table_       = make_unique<ProducerStateTable>(applDb, APP_ACL_RULE_TABLE_NAME);
acl_table_type_   = make_unique<ProducerStateTable>(applDb, APP_ACL_TABLE_TYPE_TABLE_NAME);
acl_table_        = make_unique<ProducerStateTable>(applDb, APP_ACL_TABLE_TABLE_NAME);
```

これらは APPL_DB への SET / DEL を発行し、後段の `AclOrch` が ConsumerStateTable で受け取って SAI へ反映する。

## NeighOrch Observer 通知

`DashEniFwdOrch` は `NeighOrch` の Observer として登録される (`dashenifwdorch.cpp:18-20`):

```cpp
neighorch_->attach(this);
```

Neighbor 解決イベントは `NeighOrch` から Observer パターン (`update()` メソッド) で通知される。  
Redis pub/sub ではなく C++ オブジェクトレベルのコールバックである。

トリガ: ARP/NDP 解決 → `NeighOrch` が `notify(SUBJECT_TYPE_NEIGH_CHANGE, ...)` → `DashEniFwdOrch::update()` → `handleNeighUpdate()` → 影響 ENI の `fireAllRules()` → `rule_table_->set(...)` (ACL_RULE_TABLE への ProducerStateTable SET)

## CONFIG_DB テーブル (DPU / REMOTE_DPU / VDPU) の読み取り方式

`DPU` / `REMOTE_DPU` / `VDPU` は `DpuRegistry::populate()` が **Table の getKeys() / get()** (スナップショット読み取り) で一括取得する (`dashenifwdorch.cpp:212-221`)。  
これらのテーブルに対するサブスクリプションは存在しない。起動時に一度のみ読み込まれ (`lazyInit()` → `populateDpuRegistry()`)、以後の変更は反映されない。

## まとめ

| 通知経路 | 方式 | DB | テーブル |
|----------|------|----|---------|
| HaMgrd → DashEniFwdOrch | ProducerStateTable → ConsumerStateTable (Redis List) | APPL_DB (0) | `DASH_ENI_FORWARD_TABLE` |
| DashEniFwdOrch → AclOrch | ProducerStateTable → ConsumerStateTable (Redis List) | APPL_DB (0) | `ACL_RULE_TABLE`, `ACL_TABLE_TABLE`, `ACL_TABLE_TYPE_TABLE` |
| NeighOrch → DashEniFwdOrch | Observer コールバック (C++ オブジェクト) | なし | — |
| DPU/VDPU 読み取り | Table::getKeys() スナップショット | CONFIG_DB | `DPU`, `REMOTE_DPU`, `VDPU` |
