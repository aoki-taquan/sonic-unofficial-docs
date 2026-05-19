# SUBNET_DECAP — pubsub 分析 (Phase G)

## 調査対象ファイル

- `sonic-swss/orchagent/tunneldecaporch.cpp`
- `sonic-swss/orchagent/tunneldecaporch.h`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss-common/common/table.h`
- `sonic-swss-common/common/subscriberstatetable.cpp`

## 購読方式

`TunnelDecapOrch` のコンストラクタ (L39) で直接 `new SubscriberStateTable(configDb, CFG_SUBNET_DECAP_TABLE_NAME, TableConsumable::DEFAULT_POP_BATCH_SIZE, 0)` を生成。`Orch::addConsumer()` 経由ではなく直接生成している点が特徴。

## 先読み初期化

コンストラクタ L41-47: `pops(entries)` で既存エントリを先読みし `doSubnetDecapTask()` を呼んで `subnetDecapConfig` を初期化。`addExecutor()` 登録前に実行するため、orchagent 起動時に CONFIG_DB に設定が存在すれば即座に反映される。

## doTask 分岐

`tunneldecaporch.cpp:69`:
```cpp
else if (table_name == CFG_SUBNET_DECAP_TABLE_NAME)
    doSubnetDecapTask(consumer);
```

## ポーリング間隔

`orchdaemon.cpp:23`: `#define SELECT_TIMEOUT 1000` (ms)

## バッチサイズ

`table.h:164`: `DEFAULT_POP_BATCH_SIZE = 128`（固定、`-b` オプション適用外）

## PortsOrch ガード

`tunneldecaporch.cpp:55-57`:
```cpp
if (!gPortsOrch->allPortsReady())
    return;
```
ポート初期化完了前の通知はキューに残り次ループで処理。
