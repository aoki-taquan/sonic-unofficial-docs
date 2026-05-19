# TAM テーブル群 — 通信メカニズム (Phase G) 解析メモ

対象: CONFIG_DB の `TAM_DEVICE_TABLE` / `TAM_COLLECTOR_TABLE` / `TAM_INT_IFA_FEATURE_TABLE` / `TAM_INT_IFA_FLOW_TABLE`。

ソース確認: `sonic-swss/orchagent/orchdaemon.cpp`、`sonic-swss/orchagent/high_frequency_telemetry/hftelorch.cpp`、`sonic-swss/orchagent/orch.cpp`、`sonic-mgmt-common` CVL 層。

## 1. TAM 4 テーブルは orchagent に購読されない

`orchdaemon.cpp` を全文検索しても `TAM_DEVICE_TABLE` / `TAM_COLLECTOR_TABLE` / `TAM_INT_IFA_*` への `TableConnector` / `addConsumer` 登録は存在しない。これらの CONFIG_DB テーブルは **SONiC コミュニティ版 orchagent によって購読されない**。

`HFTelOrch` (High Frequency Telemetry) は `orchdaemon.cpp:860-861` で以下の 2 テーブルだけを購読する:

```cpp
// orchdaemon.cpp:860-861
CFG_HIGH_FREQUENCY_TELEMETRY_PROFILE_TABLE_NAME,   // "HIGH_FREQUENCY_TELEMETRY_PROFILE"
CFG_HIGH_FREQUENCY_TELEMETRY_GROUP_TABLE_NAME       // "HIGH_FREQUENCY_TELEMETRY_GROUP"
```

`portsorch` はポート初期化時に SAI TAM オブジェクトを作成するが、これは `TAM_DEVICE_TABLE` を購読するのではなく Port テーブル変化を起点とした処理の一部である。

## 2. CVL のアクセス方式（Management Framework 経由）

`sonic-mgmt-common` の CVL は GNMI/REST リクエスト受信時に **オンデマンドで** CONFIG_DB を直接参照する。`SubscriberStateTable` や `ConsumerStateTable` のようなイベント駆動購読ではなく、`swss::DBConnector` + `swss::Table::get()` 等による HGETALL 同期読み取りでバリデーションを行う。

## 3. orch.cpp addConsumer の分岐（参考）

仮に今後 orchagent が TAM テーブルを購読することになった場合、`Orch::addConsumer()` (`orch.cpp:1186`) の分岐により CONFIG_DB（dbId=4）は **`SubscriberStateTable`** が選ばれる:

```cpp
// orch.cpp:1186-1195
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
        addExecutor(new Consumer(new SubscriberStateTable(db, tableName,
                                     TableConsumable::DEFAULT_POP_BATCH_SIZE, pri), this, tableName));
    else
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
}
```

CONFIG_DB 購読時のバッチサイズは `DEFAULT_POP_BATCH_SIZE = 128`（`sonic-swss-common/common/table.h:164`）。

## 4. サマリ

| 観点 | TAM_DEVICE_TABLE / TAM_COLLECTOR_TABLE / TAM_INT_IFA_* |
|---|---|
| orchagent による購読 | **なし**（TableConnector 登録なし） |
| 購読クラス | 該当なし |
| keyspace 通知 | 発生しない（書き手なし） |
| アクセス方式 | CVL（Management Framework）がオンデマンド polling で HGETALL 読み出し |
| `ProducerStateTable` / `NotificationProducer` | 使用なし |
| バッチサイズ | 概念なし（polling 読み取りのみ） |

## 5. Evidence

- `sonic-swss/orchagent/orchdaemon.cpp` L857-863 — `HFTelOrch` が購読するのは `HIGH_FREQUENCY_TELEMETRY_PROFILE` / `HIGH_FREQUENCY_TELEMETRY_GROUP` の 2 テーブルのみ
- `sonic-swss/orchagent/orch.cpp` L1186-1195 — `addConsumer()` CONFIG_DB → `SubscriberStateTable` 分岐
- `sonic-swss-common/common/schema.h` L408-409 — `CFG_HIGH_FREQUENCY_TELEMETRY_PROFILE_TABLE_NAME` / `CFG_HIGH_FREQUENCY_TELEMETRY_GROUP_TABLE_NAME` 定義
- `sonic-swss-common/common/table.h` L164 — `DEFAULT_POP_BATCH_SIZE = 128`
