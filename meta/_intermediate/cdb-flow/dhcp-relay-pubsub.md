# DHCP_RELAY — Phase G 通信メカニズム (Redis PUBSUB / keyspace notification)

対象ページ: `docs/reference/config-db/dhcp-relay.md`
調査日: 2026-05-14
Evidence: `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp`, `sonic-swss-common/common/subscriberstatetable.cpp`

---

## 概要

`dhcp6relay` は CONFIG_DB の `DHCP_RELAY` テーブルを **`swss::SubscriberStateTable`** 経由で購読する。
内部実装は Redis の **keyspace notification (PUBSUB PSUBSCRIBE)** を使用しており、ConsumerStateTable / NotificationConsumer は使用しない。
TTL/keyevent 系の expire 通知も使用しない。

---

## 通信シーケンス

### 1. 初期化 — `initialize_swss()` (config_interface.cpp:18-29)

```
dhcp6relay プロセス起動
  └─ initialize_swss(vlans)
       └─ DBConnector("CONFIG_DB", 0)       ← Redis DB #4 (CONFIG_DB)
       └─ SubscriberStateTable(db, "DHCP_RELAY")
            └─ [ctor] psubscribe(db, "__keyspace@4__:DHCP_RELAY|*")
                      ─ PSUBSCRIBE __keyspace@4__:DHCP_RELAY|*
            └─ [ctor] Table::getKeys()       ← KEYS "DHCP_RELAY|*" で起動時スナップショット取得
            └─ [ctor] m_buffer に全エントリを SET_COMMAND として積む
       └─ swssSelect.addSelectable(&ipHelpersTable)
       └─ get_dhcp(vlans, &ipHelpersTable, dynamic=false, config_db)
```

### 2. keyspace notification パターン

`SubscriberStateTable` が発行する PSUBSCRIBE パターン:

```
__keyspace@4__:DHCP_RELAY|*
```

- `@4__` は CONFIG_DB の Redis DB 番号 (通常 4)
- `|` は SONiC テーブルセパレータ (GetTableNameSeparator)
- `*` はすべての VLAN キーにマッチ

Redis サーバ側では `notify-keyspace-events = "KEA"` を設定 (sonic-swss-common/dbinterface.cpp:345)。  
`K` = keyspace 通知、`E` = keyevent 通知、`A` = すべての操作 (= g$lszxetd の省略形)。

### 3. Select ループ — `get_dhcp()` (config_interface.cpp:63-80)

```
swssSelect.select(&selectable, timeout_ms=1000)
  ├─ TIMEOUT (1000ms 無通知) → 何もしない
  ├─ ERROR → LOG_WARNING "Select: returned ERROR"
  └─ データあり && selectable == ipHelpersTable
       ├─ dynamic=false (起動時) → handleRelayNotification()
       └─ dynamic=true  (実行時) → LOG_WARNING "relay config changed, need restart container"
                                   (設定変更は無視 = dead consumer)
```

### 4. pops → processRelayNotification

```
handleRelayNotification(ipHelpersTable, vlans, config_db)
  └─ ipHelpersTable.pops(entries)          ← std::deque<KeyOpFieldsValuesTuple>
       ├─ m_buffer に cached data があれば flush (起動時スナップショット)
       └─ m_keyspace_event_buffer を処理:
            event.type="pmessage"
            event.channel = "__keyspace@4__:DHCP_RELAY|<vlan>"
            event.data    = "set" | "del" | "hset" など
            → op = "del" → kfvOp = DEL_COMMAND
            → それ以外 → Table::get(key) で最新値を再取得 → kfvOp = SET_COMMAND
  └─ processRelayNotification(entries, vlans, config_db)
       └─ for entry in entries:
            vlan      = kfvKey(entry)
            operation = kfvOp(entry)   ← "SET" or "DEL"
            fields    = kfvFieldsValues(entry)
            ...
```

---

## 重要な特性

| 特性 | 内容 |
|------|------|
| 通知種別 | Redis keyspace notification (PUBSUB PSUBSCRIBE) |
| パターン | `__keyspace@4__:DHCP_RELAY\|*` |
| notify-keyspace-events | `KEA` (keyspace + keyevent + all commands) |
| SWSS abstraction | `swss::SubscriberStateTable` → `swss::Select` (1000ms timeout poll) |
| ConsumerStateTable | **不使用** |
| NotificationConsumer | **不使用** |
| TTL / keyspace expire 通知 | **不使用** |
| 起動時スナップショット | `Table::getKeys()` + `Table::get()` で全エントリ即時読み込み (m_buffer) |
| 実行時変更検知 | keyspace event 受信するが `dynamic=true` フラグにより **無視**。ログのみ |
| 設定反映 | **コンテナ再起動必須** (config_interface.cpp:76-78) |

---

## TTL / expire の非使用

`DHCP_RELAY` エントリには TTL が設定されず、keyevent の `expired` / `evicted` 通知も監視しない。
`notify-keyspace-events = "KEA"` には `x` (expired) も含まれるが (`A` = all の一部)、
dhcp6relay は op 種別を見て `del` のみ DEL_COMMAND として扱い、それ以外は SET_COMMAND として処理する。
実質的に expire による削除は `del` 通知として届くが、通常運用では TTL 設定がないため発生しない。

---

## 参照コード (dhcp6relay / C++)

| ファイル | 行 | 内容 |
|---|---|---|
| `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp` | 18-29 | `initialize_swss()` — SubscriberStateTable 生成と Select 登録 |
| `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp` | 63-80 | `get_dhcp()` — Select ループ本体 |
| `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp` | 93-100 | `handleRelayNotification()` — pops 呼び出し |
| `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp` | 113-184 | `processRelayNotification()` — entries 処理 |
| `sonic-swss-common/common/subscriberstatetable.cpp` | 17-43 | SubscriberStateTable ctor — psubscribe + 起動時スナップショット |
| `sonic-swss-common/common/subscriberstatetable.cpp` | 95-165 | `pops()` — keyspace event バッファ処理 |
| `sonic-swss-common/common/dbinterface.h` | 83 | `KEYSPACE_PATTERN = "__key*__:*"` |
| `sonic-swss-common/common/dbinterface.h` | 102 | `KEYSPACE_EVENTS = "KEA"` |

---

## dhcprelayd (Python) — DHCPv4 リレー制御の通信メカニズム

調査日: 2026-05-16
Evidence: `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py`、`dhcp_utilities/common/dhcp_db_monitor.py`

### 概要

`dhcprelayd` は DHCPv4 向け Python デーモンで、`dhcp6relay` (C++) とは独立した別実装。CONFIG_DB の複数テーブルを動的に購読し、設定変更に応じて `isc-dhcp-relay` (`dhcrelay`) プロセスを subprocess / supervisord 経由で制御する。ホットリロード対応（`dhcp6relay` と異なり動的変更に即時反応）。

### 購読テーブルと Checker クラス

| Checker クラス | 購読テーブル | 購読条件 | 用途 |
|---|---|---|---|
| `DhcpServerFeatureStateChecker` | `FEATURE` | 常時有効 | `dhcp_server` フィーチャー enabled/disabled 変更 |
| `DhcpServerTableIntfEnablementEventChecker` | `DHCP_SERVER_IPV4` | dhcp_server 有効時のみ | DHCP_SERVER_IPV4 の state フィールド変更 |
| `VlanTableEventChecker` | `VLAN` | VLAN DHCP インタフェース存在時 | VLAN メンバ追加/削除 |
| `VlanIntfTableEventChecker` | `VLAN_INTERFACE` | VLAN DHCP インタフェース存在時 | VLAN への IPv4 アドレス追加/削除 (port-watch) |
| `MidPlaneTableEventChecker` | `MID_PLANE_BRIDGE` | SmartSwitch かつ mid-plane DHCP IF 存在時 | bridge フィールド変更 |

### 通信シーケンス

```
dhcprelayd 起動 (main() in dhcprelayd.py)
  └─ swsscommon.Select() ← 単一 Select で全テーブルを管理
  └─ 各 Checker.__init__(sel, config_db)
  │    └─ subscriber_state_table = None  (disabled 状態)
  └─ DhcpRelaydDbMonitor(db_connector, sel, checkers, timeout=5000ms)
  └─ dhcprelayd.start()
       ├─ _is_dhcp_server_enabled() ← FEATURE テーブルを一括取得
       ├─ DhcpServerFeatureStateChecker.enable()
       │    └─ SubscriberStateTable(config_db, "FEATURE")
       │         └─ PSUBSCRIBE __keyspace@4__:FEATURE|*
       │    └─ sel.addSelectable(subscriber_state_table)
       └─ dhcp_server 有効時: DhcpServerTableIntfEnablementEventChecker.enable()
            └─ SubscriberStateTable(config_db, "DHCP_SERVER_IPV4")
                 └─ PSUBSCRIBE __keyspace@4__:DHCP_SERVER_IPV4|*

dhcprelayd.wait() ループ
  └─ DhcpRelaydDbMonitor.check_db_update(db_snapshot)
       └─ sel.select(timeout_ms=5000)
            ├─ TIMEOUT → {} 返却 (処理なし)
            └─ OBJECT → 各 enabled Checker.check_update_event(db_snapshot)
                  └─ subscriber_state_table.pop() ← keyspace event 取り出し
                        → 条件判定 → True/False
  └─ _proceed_with_check_res(check_res) → dhcrelay プロセス制御
```

### isc-dhcp-relay 制御 — port-watch 経路

```
refresh_dhcrelay(force_kill)
  ├─ DHCP_SERVER_IPV4 テーブルを一括取得
  ├─ VLAN テーブルを一括取得
  │    → enabled_dhcp_interfaces (state=="enabled" かつ VLAN 存在) を構築
  ├─ VlanTableEventChecker / VlanIntfTableEventChecker の動的 enable/disable
  ├─ DEVICE_METADATA.has_sonic_dhcpv4_relay == "False" の場合のみ:
  │    _start_dhcrelay_process(dhcp_interfaces, dhcp_server_ip, force_kill)
  │         ├─ psutil.process_iter() で既存 dhcrelay プロセス走査
  │         │    → force_kill or インタフェースセット変更時: terminate_proc()
  │         └─ subprocess.Popen(["/usr/sbin/dhcrelay", "-d", "-m", "discard",
  │                  "-a", "%h:%p", "%P", "--name-alias-map-file", ...,
  │                  "-id", <vlan>, ..., "-iu", "docker0", <dhcp_server_ip>])
  └─ supervisord 経由 (dhcp_server 有効/無効切り替え時):
       supervisorctl stop/start <isc-dhcpv4-relay-VlanXXXX>
```

**port-watch 経路**: `VlanIntfTableEventChecker` が `VLAN_INTERFACE` の IPv4 アドレス変更を検知 → `refresh_dhcrelay(force_kill=True)` → dhcrelay 強制再起動。`VlanTableEventChecker` が VLAN 変更を検知 → `refresh_dhcrelay(force_kill=False)` → インタフェースセット変更時のみ再起動。

### Select タイムアウトと Checker 動的制御

| パラメータ | 値 | 根拠 |
|---|---|---|
| `DEFAULT_SELECT_TIMEOUT` | `5000` ms | dhcprelayd.py:22 |
| 起動時に有効 | `DhcpServerFeatureStateChecker` のみ | start() |
| dhcp_server 有効時に追加 | `DhcpServerTableIntfEnablementEventChecker` | _proceed_with_check_res() |
| VLAN あり時に追加 | `VlanTableEventChecker`, `VlanIntfTableEventChecker` | refresh_dhcrelay() |
| SmartSwitch 時に追加 | `MidPlaneTableEventChecker` | refresh_dhcrelay() |
| FEATURE / DHCP_SERVER チェッカー | 無効化対象外 (常時維持) | dhcprelayd.py:107-108 |

### dhcprelayd と dhcp6relay の購読方式比較

| 項目 | dhcp6relay (C++) | dhcprelayd (Python) |
|---|---|---|
| 購読テーブル | `DHCP_RELAY` | `FEATURE`, `DHCP_SERVER_IPV4`, `VLAN`, `VLAN_INTERFACE`, `MID_PLANE_BRIDGE` |
| Select timeout | 1000 ms | 5000 ms |
| 動的変更への反応 | **無視** (dead consumer, コンテナ再起動必須) | **即時反応** → dhcrelay 再起動 |
| 起動時スナップショット | `Table::getKeys()` で即時読み込み (m_buffer) | `get_config_db_table()` で都度取得 |
| プロセス制御 | なし (自身がリレーを実装) | subprocess / supervisorctl で dhcrelay を制御 |
| ConsumerStateTable | 不使用 | 不使用 |
| NotificationConsumer | 不使用 | 不使用 |

### 参照コード (dhcprelayd / Python)

| ファイル | 行 | 内容 |
|---|---|---|
| `dhcp_utilities/dhcprelayd/dhcprelayd.py` | 22 | `DEFAULT_SELECT_TIMEOUT = 5000` |
| `dhcp_utilities/dhcprelayd/dhcprelayd.py` | 58-72 | `start()` — 起動時 feature 確認と checker 有効化 |
| `dhcp_utilities/dhcprelayd/dhcprelayd.py` | 74-116 | `refresh_dhcrelay()` — dhcrelay 再起動制御 |
| `dhcp_utilities/dhcprelayd/dhcprelayd.py` | 118-178 | `wait()` / `_proceed_with_check_res()` — Select ループと分岐 |
| `dhcp_utilities/dhcprelayd/dhcprelayd.py` | 290-313 | `_start_dhcrelay_process()` — subprocess.Popen で dhcrelay 起動 |
| `dhcp_utilities/common/dhcp_db_monitor.py` | 20-136 | `ConfigDbEventChecker` 基底クラス — enable/disable/check_update_event |
| `dhcp_utilities/common/dhcp_db_monitor.py` | 281-324 | `VlanTableEventChecker`, `VlanIntfTableEventChecker` |
| `dhcp_utilities/common/dhcp_db_monitor.py` | 388-411 | `DhcpServerFeatureStateChecker` |
| `dhcp_utilities/common/dhcp_db_monitor.py` | 442-485 | `DhcpRelaydDbMonitor.check_db_update()` — Select ループ本体 |
