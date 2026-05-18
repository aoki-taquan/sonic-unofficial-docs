# tunnel-encap-action — Phase G pubsub 調査ノート

## 調査対象
- `orchagent/p4orch/next_hop_manager.cpp`
- `orchagent/p4orch/next_hop_manager.h`
- `orchagent/response_publisher.cpp`
- `orchagent/orchdaemon.cpp`
- `orchagent/orchdaemon.h`

## 購読方式

`NextHopManager` は `P4Orch` (`ZmqOrch` サブクラス) に属するマネージャ。
`FIXED_NEXTHOP_TABLE` を含む `P4RT_TABLE` の書き込みは P4RT gRPC サーバが
**ZMQ IPC** 経由で orchagent に送信する。
Redis keyspace 通知や ProducerStateTable channel は使わない。

```cpp
// orchdaemon.cpp:847-849
vector<string> p4rt_tables = {APP_P4RT_TABLE_NAME};
m_p4OrchZmqServer = new swss::ZmqServer(m_p4OrchZmqServerEp, "", false, true);
gP4Orch = new P4Orch(m_applDb, p4rt_tables, m_p4OrchZmqServer, vrf_orch, gCoppOrch);

// orchdaemon.h:121
const std::string m_p4OrchZmqServerEp = "ipc:///zmq_swss/p4orch_zmq_swss_ep";
```

## 応答 publish 先

`m_publisher->publish(APP_P4RT_TABLE_NAME, key, fvs, status, /*replace=*/true)` が
以下を順に実行する (`response_publisher.cpp:96-133`):

1. **ZMQ 応答** (`m_zmqServer != nullptr`): `ZmqServer::sendMsg()` で P4RT gRPC サーバへ WriteResponse を返す
2. **Redis Notification Channel**: `NotificationProducer` で `APPL_DB_P4RT_TABLE_RESPONSE_CHANNEL` に PUBLISH
   ```cpp
   // response_publisher.cpp:104
   std::string response_channel = "APPL_DB_" + table + "_RESPONSE_CHANNEL";
   // → "APPL_DB_P4RT_TABLE_RESPONSE_CHANNEL"
   ```
3. **APPL_STATE_DB 書き込み**: `status.ok()` かつ `intent_attrs` 非空の場合のみ
   `APPL_STATE_DB:P4RT_TABLE:FIXED_NEXTHOP_TABLE:<key>` に state フィールドを書き込む

## publish が呼ばれるタイミング (`next_hop_manager.cpp`)

| タイミング | 行番号 | ステータス |
|-----------|--------|-----------|
| deserialize 失敗 | :324-326 | エラーコード |
| validateAppDbEntry 失敗 | :342-344 | エラーコード |
| バッチ内先行失敗によるキャンセル | :364-367 | `SWSS_RC_NOT_EXECUTED` |
| UPDATE 試行 (既存エントリへの SET) | :378-380 | `SWSS_RC_UNIMPLEMENTED` |
| Bulk SAI 処理完了後 (SET / DEL) | :678-680 | 成功/失敗とも |

## APPL_STATE_DB の書き込み条件

`ResponsePublisher::publish()` の2引数版 (`response_publisher.cpp:136-149`):
- SET 成功時: `state_attrs = intent_attrs` → APPL_STATE_DB に nexthop フィールドを書き込む
- DEL 成功時: `intent_attrs.empty()` → APPL_STATE_DB のエントリを削除
- 失敗時: APPL_STATE_DB への書き込みなし

## APPL_STATE_DB キー形式

SET 成功時:
```
APPL_STATE_DB: P4RT_TABLE:FIXED_NEXTHOP_TABLE:{"match/nexthop_id":"<nexthop_id>"}
  action          = "set_p2p_tunnel_encap_nexthop"
  param/tunnel_id = "<tunnel_id>"
  err_str         = ""
```
(フィールドは intent_attrs = P4RT controller が書いたフィールドと同値)

## COUNTERS_DB / STATE_DB / FLEX_COUNTER_DB

`next_hop_manager.cpp` は `gCrmOrch->incCrmResUsedCounter(CRM_IPV4_NEXTHOP)` /
`decCrmResUsedCounter(CRM_IPV6_NEXTHOP)` を呼び出す (:559-561, :637-639)。
これは CRM リソース使用量カウンタ (内部カウンタ) のみであり、
COUNTERS_DB / FLEX_COUNTER_DB への書き込みは発生しない。

## サービス再起動トリガー

なし。`NextHopManager` は orchagent プロセス内のハンドラ。
エントリ追加/削除は SAI nexthop オブジェクトのライブ操作のみで反映。
