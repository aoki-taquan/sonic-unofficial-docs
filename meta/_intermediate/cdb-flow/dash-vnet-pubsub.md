# DASH_VNET — 通信メカニズム (Phase G) 解析メモ

対象: `APPL_DB` (DPU_APPL_DB) の `DASH_VNET_TABLE` / `DASH_VNET_MAPPING_TABLE`
Consumer: `DashVnetOrch` (`sonic-swss/orchagent/dash/dashvnetorch.cpp`)
スキャン範囲: `dashvnetorch.cpp` 全行・`zmqorch.cpp` 全行・`orchdaemon.cpp:1325-1345` 精読

---

## 1. ZMQ チャネル経由の購読

DASH テーブルは通常の `ConsumerStateTable`（Redis Pub/Sub + keyspace notification）ではなく、
`ZmqConsumerStateTable` という ZeroMQ ベースのチャネルを使用する。

`DashVnetOrch` は `ZmqOrch` を継承し、コンストラクタで購読テーブルを登録する:

```cpp
// orchdaemon.cpp:1333-1340
vector<string> dash_vnet_tables = {
    APP_DASH_VNET_TABLE_NAME,           // "DASH_VNET_TABLE"
    APP_DASH_VNET_MAPPING_TABLE_NAME    // "DASH_VNET_MAPPING_TABLE"
};
DashVnetOrch *dash_vnet_orch = new DashVnetOrch(m_dpu_appDb, dash_vnet_tables, m_dpu_appstateDb, dash_zmq_server);
```

ZMQ サーバが有効な場合（`ORCH_NORTHBOND_DASH_ZMQ_ENABLED` フィーチャフラグが true）、
`ZmqOrch::addConsumer()` が `ZmqConsumerStateTable` を生成してエグゼキュータとして登録する。
ZMQ が無効の場合は通常の `ConsumerStateTable` にフォールバックする。

## 2. ZmqOrch / ZmqConsumer のメカニズム

```
gNMI (north-bound) / sonic-cfggen
    └─ APPL_DB (DPU_APPL_DB)
           DASH_VNET_TABLE
           DASH_VNET_MAPPING_TABLE
               ↓ (ZMQ channel または Redis ConsumerStateTable)
    ZmqConsumerStateTable::pops()
    ZmqConsumer::execute()
    ZmqConsumer::drain()
    DashVnetOrch::doTask(ConsumerBase& consumer)
        ├─ APP_DASH_VNET_TABLE_NAME → doTaskVnetTable()
        └─ APP_DASH_VNET_MAPPING_TABLE_NAME → doTaskVnetMapTable()
```

- `ZmqConsumer::execute()` が `pops()` でエントリをバッチ取得し `m_toSync` に積む。
- `drain()` が `DashVnetOrch::doTask()` を呼び出し、テーブル名でディスパッチする。
- `doTask()` は `ZmqOrch::doTask(Consumer&)` → `doTask(ConsumerBase&)` の委譲経路で仮想ディスパッチを行う。

## 3. 書き込み元 (publisher)

| 書き込み元 | テーブル | 経路 |
|-----------|---------|------|
| gNMI / gnmi-server (sonic-gnmi) | `DASH_VNET_TABLE` / `DASH_VNET_MAPPING_TABLE` | ZMQ → `ZmqConsumerStateTable` |
| テスト・sonic-cfggen | 同上 | `ConsumerStateTable` (ZMQ 無効時) |

CONFIG_DB `DASH_VNET` → APPL_DB `DASH_VNET_TABLE` の変換は `fpmsyncd` ではなく
gnmi-server (sonic-net/sonic-gnmi) が担当する。cli `config` コマンドは CONFIG_DB への書き込みのみ行い、
gnmi-server がその変化を検知して APPL_DB へ転送する。

## 4. SAI API 呼び出し

| 操作 | SAI API | ソース |
|------|---------|--------|
| VNET 作成 | `sai_dash_vnet_api->create_vnets()` (bulker) | `dashvnetorch.cpp:98-101` |
| VNET 削除 | `sai_dash_vnet_api->remove_vnets()` (bulker) | `dashvnetorch.cpp:124-127` |
| outbound CA to PA 作成 | `sai_dash_outbound_ca_to_pa_api->create_outbound_ca_to_pa_entries()` | `dashvnetorch.cpp:~L445` |
| PA validation 作成 | `sai_dash_pa_validation_api->create_pa_validation_entries()` | `dashvnetorch.cpp:~L475` |

バルクアクション (`ObjectBulker` / `EntityBulker`) を使用し、イベントループ内で `vnet_bulker_.flush()` /
`outbound_ca_to_pa_bulker_.flush()` / `pa_validation_bulker_.flush()` が一括送信する。

## 5. APPL_STATE_DB への結果書き戻し

処理結果は `APPL_STATE_DB` (`DPU_APPL_STATE_DB`) の対応テーブルに書き戻される:

| 操作 | 結果テーブル | キー形式 | 値 |
|------|------------|---------|-----|
| VNET SET 成功 | `DASH_VNET_TABLE` (APPL_STATE_DB) | `<vnet_name>` | `DASH_RESULT_SUCCESS (0)` |
| VNET SET 失敗 | 同上 | `<vnet_name>` | `DASH_RESULT_FAILURE (1)` |
| VNET DEL 成功 | 同上 | `<vnet_name>` | エントリ削除 |
| VNET_MAPPING SET 成功/失敗 | `DASH_VNET_MAPPING_TABLE` (APPL_STATE_DB) | `<vnet_name>:<dip>` | `DASH_RESULT_SUCCESS/FAILURE` |

## 6. CONFIG_DB との関係

CONFIG_DB `DASH_VNET` テーブルは `DashVnetOrch` が**直接購読しない**。
フロー: CONFIG_DB (`DASH_VNET`) → gnmi-server → APPL_DB (`DASH_VNET_TABLE`) → ZmqOrch → DashVnetOrch。
keyspace 通知や直接の ConsumerStateTable による CONFIG_DB 購読は存在しない。

## 7. フィーチャフラグ

`ORCH_NORTHBOND_DASH_ZMQ_ENABLED` フラグ（デフォルト `true`）が ZMQ モードを制御する:

```cpp
// orchdaemon.cpp:1327-1332
if (get_feature_status(ORCH_NORTHBOND_DASH_ZMQ_ENABLED, true))
{
    dash_zmq_server = m_zmqServer;
}
```

- ZMQ 有効: `ZmqConsumerStateTable` で ZeroMQ チャネル経由
- ZMQ 無効 (`nullptr`): `ConsumerStateTable` で Redis Pub/Sub 経由（テスト・フォールバック用途）

## 8. 参考行番号

- `sonic-swss/orchagent/orchdaemon.cpp`: 1325-1345 (DashVnetOrch 登録)
- `sonic-swss/orchagent/zmqorch.cpp`: 全行 (ZmqConsumer, ZmqOrch 実装)
- `sonic-swss/orchagent/dash/dashvnetorch.cpp`: 42-51 (コンストラクタ), 869-884 (doTask)
