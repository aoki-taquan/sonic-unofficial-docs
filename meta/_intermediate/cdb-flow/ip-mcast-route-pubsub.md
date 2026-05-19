# ip-mcast-route — Phase G 通信メカニズム 調査メモ

調査日: 2026-05-19
対象ソース: sonic-swss/orchagent/p4orch/p4orch.cpp, orchdaemon.cpp, ip_multicast_manager.cpp, l3_multicast_manager.cpp

## 結論

`FIXED_IPV4_MULTICAST_TABLE` / `FIXED_IPV6_MULTICAST_TABLE` / `REPLICATION_IP_MULTICAST_TABLE` /
`FIXED_MULTICAST_ROUTER_INTERFACE_TABLE` はすべて **通常の redis ConsumerStateTable / keyspace 通知パスを使わず、専用 ZMQ チャネル経由で配送される**。

## ZMQ エンドポイント

- `orchdaemon.h:121`: `m_p4OrchZmqServerEp = "ipc:///zmq_swss/p4orch_zmq_swss_ep"`
- `orchdaemon.cpp:848-849`: `m_p4OrchZmqServer = new swss::ZmqServer(m_p4OrchZmqServerEp, ...)` → `gP4Orch = new P4Orch(m_applDb, p4rt_tables, m_p4OrchZmqServer, ...)`

## P4Orch 初期化

- `p4orch.cpp:36-43`: `P4Orch : public ZmqOrch`, ZMQ ソケット受信 + `ResponsePublisher("APPL_DB", buffered=true, db_write_thread=true, zmqServer)` で応答
- `p4orch.cpp:51-54`: `L3MulticastManager` / `IpMulticastManager` を同一 `m_publisher` で初期化
- `p4orch.cpp:72-79`: `m_p4TableToManagerMap` に 4 テーブルをすべて登録

## テーブル → マネージャ マッピング

| テーブル名 | マネージャ | ソース行 |
|-----------|-----------|---------|
| FIXED_IPV4_MULTICAST_TABLE | `IpMulticastManager` | `p4orch.cpp:72-73` |
| FIXED_IPV6_MULTICAST_TABLE | `IpMulticastManager` | `p4orch.cpp:74-75` |
| FIXED_MULTICAST_ROUTER_INTERFACE_TABLE | `L3MulticastManager` | `p4orch.cpp:76-77` |
| REPLICATION_IP_MULTICAST_TABLE | `L3MulticastManager` | `p4orch.cpp:78-79` |

## 応答パス

- 各マネージャは `m_publisher->publish(APP_P4RT_TABLE_NAME, ...)` で処理結果を APP_DB に書き戻す
- `IpMulticastManager::drain()`: `ip_multicast_manager.cpp:132, 147, 159, 185, 230`
- `L3MulticastManager::drain()`: `l3_multicast_manager.cpp:375, 433, 448, 476, 530, 547, 562, 594`
- バッチ中断時は `SWSS_RC_NOT_EXECUTED` を付与 (`ip_multicast_manager.cpp:185-191`, `l3_multicast_manager.cpp:375`)

## redis keyspace との差異

- `p4rt_tables = {APP_P4RT_TABLE_NAME}` (単一エントリのみ) `orchdaemon.cpp:847` — keyspace 購読は行わない
- redis `__keyspace@...` 通知では観測不可。トリガは ZMQ フレーム受信のみ
