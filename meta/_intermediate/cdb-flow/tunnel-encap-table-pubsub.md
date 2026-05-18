# tunnel-encap-table — Phase G pubsub 調査ノート

## 調査対象
- `orchagent/p4orch/p4orch.cpp`
- `orchagent/p4orch/gre_tunnel_manager.cpp`
- `orchagent/zmqorch.h`
- `orchagent/response_publisher.cpp`
- `orchagent/orchdaemon.cpp`
- `orchagent/orchdaemon.h`

## 購読方式

P4Orch は標準の `Orch` サブクラスではなく `ZmqOrch` サブクラスとして実装される。

```cpp
// p4orch.cpp:36-42
P4Orch::P4Orch(swss::DBConnector* db, std::vector<std::string> tableNames,
               ZmqServer* zmqServer, VRFOrch* vrfOrch, CoppOrch* coppOrch)
    : ZmqOrch(db, tableNames, zmqServer, /*orderedQueue=*/true,
              /*dbPersistence=*/false),
      m_zmqServer(zmqServer),
      m_publisher("APPL_DB", /*bool buffered=*/true,
                  /*db_write_thread=*/true, zmqServer)
```

`ZmqOrch` は `ZmqConsumerStateTable` を使い、P4RT gRPC サーバからの書き込みを
ZMQ IPC (`ipc:///zmq_swss/p4orch_zmq_swss_ep`) 経由で受信する。
Redis keyspace 通知 (`__keyspace@<dbId>__:...`) や ProducerStateTable channel
(`<TABLE>_CHANNEL@0`) は使わない。

```cpp
// orchdaemon.cpp:847-849
vector<string> p4rt_tables = {APP_P4RT_TABLE_NAME};
m_p4OrchZmqServer = new swss::ZmqServer(m_p4OrchZmqServerEp, "", false, true);
gP4Orch = new P4Orch(m_applDb, p4rt_tables, m_p4OrchZmqServer, vrf_orch, gCoppOrch);

// orchdaemon.h:121
const std::string m_p4OrchZmqServerEp = "ipc:///zmq_swss/p4orch_zmq_swss_ep";
```

## 応答 publish 先

`m_publisher->publish(APP_P4RT_TABLE_NAME, key, fvs, status)` は以下を実行する:

1. **ZMQ 応答** (`m_zmqServer != nullptr`): `ZmqServer::sendMsg("APPL_DB", response)` で P4RT gRPC サーバに応答を ZMQ 経由で返す (`response_publisher.cpp:107-115, 224-226`)
2. **Redis Notification Channel**: `NotificationProducer` で `APPL_DB_P4RT_TABLE_RESPONSE_CHANNEL` に `PUBLISH` を発行 (`response_publisher.cpp:117-121`)
3. **APPL_STATE_DB 書き込み**: `status.ok()` の場合のみ `APPL_STATE_DB:P4RT_TABLE:FIXED_TUNNEL_TABLE:<key>` に state フィールドを書き込む (`response_publisher.cpp:129-133`)

```cpp
// response_publisher.cpp:104
std::string response_channel = "APPL_DB_" + table + "_RESPONSE_CHANNEL";
// → "APPL_DB_P4RT_TABLE_RESPONSE_CHANNEL"
```

## publish が呼ばれるタイミング

`gre_tunnel_manager.cpp` 内:
- deserialize 失敗時 (:230): 即時 publish (失敗ステータス)
- validation 失敗時 (:248): 即時 publish (失敗ステータス)
- バッチ内先行失敗によるキャンセル (:270): `SWSS_RC_NOT_EXECUTED` で publish
- UPDATE 試行 (:284): `SWSS_RC_UNIMPLEMENTED` で publish
- Bulk SAI 処理完了後 (:551): 成功/失敗とも publish

## APPL_STATE_DB の書き込み条件

`ResponsePublisher::publish()` の2引数版:
```cpp
// response_publisher.cpp:144-149
if (status.ok()) {
    state_attrs = intent_attrs;
}
publish(table, key, intent_attrs, status, state_attrs, replace);
```
→ SET 成功時のみ `state_attrs = intent_attrs` となり APPL_STATE_DB に書き込まれる。
DEL 成功時は `intent_attrs.empty()` で APPL_STATE_DB のエントリが削除される。

## COUNTERS_DB / STATE_DB / FLEX_COUNTER_DB

`gre_tunnel_manager.cpp` は `crmorch.h` をインクルードするが
`gCrmOrch->incCrmResUsedCounter()` を呼び出さない。
COUNTERS_DB / STATE_DB / FLEX_COUNTER_DB への書き込みは発生しない。

## APPL_STATE_DB キー形式

SET 成功時:
```
APPL_STATE_DB: P4RT_TABLE:FIXED_TUNNEL_TABLE:{"match/tunnel_id":"<tunnel_id>"}
  action        = "mark_for_p2p_tunnel_encap"
  param/router_interface_id = "<rif_id>"
  param/encap_src_ip = "<src_ip>"
  param/encap_dst_ip = "<dst_ip>"
  err_str       = ""
```
(フィールドは intent_attrs = P4RT controller が書いたフィールドと同値)

## サービス再起動トリガー

なし。GreTunnelManager は orchagent プロセス内のハンドラ。
エントリ追加/削除は SAI GRE トンネルオブジェクトのライブ操作のみで反映。
