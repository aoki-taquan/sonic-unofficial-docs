# DHCP_SERVER_IPV6 — Phase G 通信メカニズム (Redis PUBSUB / keyspace notification)

対象ページ: `docs/reference/config-db/dhcp-server-ipv6.md`
調査日: 2026-05-16
Evidence: `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp`, `sonic-dhcp-relay/dhcp6relay/src/relay.cpp`

---

## 概要

`DHCP_SERVER_IPV6` テーブルは **2026-05-16 時点で未実装**であり、このテーブルを購読・監視するデーモンは存在しない。
CONFIG_DB Subscribe、dhcrelay 制御、netlink 監視はすべて **`DHCP_RELAY` テーブルを対象とした `dhcp6relay` プロセス**が担っている。

---

## CONFIG_DB Subscribe

`dhcp6relay` (`sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp`) は `swss::SubscriberStateTable` 経由で
CONFIG_DB の `DHCP_RELAY` テーブルを購読する。内部実装は Redis **keyspace notification (PSUBSCRIBE)**。

### 初期化シーケンス

```
dhcp6relay 起動
  └─ initialize_swss(vlans)                        (config_interface.cpp:18-29)
       ├─ DBConnector("CONFIG_DB", 0)               ← Redis DB #4 (CONFIG_DB)
       ├─ SubscriberStateTable(db, "DHCP_RELAY")
       │    └─ PSUBSCRIBE __keyspace@4__:DHCP_RELAY|*
       │    └─ Table::getKeys() で起動時スナップショット取得 (m_buffer)
       └─ swssSelect.addSelectable(&ipHelpersTable)
            └─ get_dhcp(vlans, &ipHelpersTable, dynamic=false, config_db)
                 └─ swssSelect.select(timeout_ms=1000)
                      ├─ TIMEOUT → 何もしない
                      ├─ ERROR   → LOG_WARNING "Select: returned ERROR"
                      └─ データあり && selectable == ipHelpersTable
                           ├─ dynamic=false → handleRelayNotification()
                           └─ dynamic=true  → LOG_WARNING "relay config changed, need restart container"
```

### 通信特性

| 項目 | 値 |
|------|-----|
| 購読テーブル | `DHCP_RELAY`（`DHCP_SERVER_IPV6` は **なし**） |
| SWSS abstraction | `swss::SubscriberStateTable` + `swss::Select` |
| PSUBSCRIBE パターン | `__keyspace@4__:DHCP_RELAY|*` |
| notify-keyspace-events | `KEA` (keyspace + keyevent + all commands) |
| Select timeout | 1000 ms |
| 起動時スナップショット | `Table::getKeys()` + `Table::get()` で全エントリ即時読み込み (m_buffer) |
| 実行時変更検知 | keyspace event 受信するが `dynamic=true` フラグにより **無視** |
| ConsumerStateTable | **不使用** |
| NotificationConsumer | **不使用** |
| TTL / keyspace expire | **不使用** |
| 設定反映 | **コンテナ再起動必須** |

---

## dhcrelay 制御

`dhcp6relay` はシグナルで制御される。`relay.cpp` で `libevent` (`event_base`) を使い、
SIGINT / SIGTERM をキャッチして `event_base_loopbreak()` でイベントループを終了する。

```
signal_init()                                      (relay.cpp:1154-1172)
  ├─ evsignal_new(base, SIGINT,  signal_callback, base)
  └─ evsignal_new(base, SIGTERM, signal_callback, base)

signal_callback(fd, event, base)                   (relay.cpp:1214-1221)
  └─ if fd == SIGTERM || SIGINT:
       event_base_loopbreak(base)
```

設定変更は `dynamic=true` フラグにより無視される (`config_interface.cpp:73-78`)。
コンテナ再起動（supervisord 経由）が唯一の設定反映手段。

---

## netlink（間接利用のみ）

`dhcp6relay` は netlink ソケットを直接使用しない。

- **LLA 確認**: `popen("ip -6 addr show <vlan> scope link", "r")` で外部コマンドを呼び出す  
  (`config_interface.cpp:196-209`)
- **インタフェースインデックス**: `if_nametoindex(interface.c_str())` のみ使用  
  (`relay.cpp:829`)
- **netlink ソケット直接使用**: なし

---

## 参照コード

| ファイル | 行 | 内容 |
|---|---|---|
| `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp` | 18-29 | `initialize_swss()` — SubscriberStateTable 生成と Select 登録 |
| `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp` | 63-80 | `get_dhcp()` — Select ループ本体、dynamic=true 時の dead consumer |
| `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp` | 93-100 | `handleRelayNotification()` — pops 呼び出し |
| `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp` | 113-184 | `processRelayNotification()` — entries 処理 |
| `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp` | 196-209 | `check_is_lla_ready()` — popen による LLA 確認（netlink 非使用） |
| `sonic-dhcp-relay/dhcp6relay/src/relay.cpp` | 829 | `if_nametoindex()` によるインタフェースインデックス取得 |
| `sonic-dhcp-relay/dhcp6relay/src/relay.cpp` | 1154-1221 | `signal_init()` / `signal_callback()` — SIGTERM/SIGINT 処理 |
