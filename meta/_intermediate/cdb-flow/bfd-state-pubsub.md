# STATE_DB BFD_SESSION_TABLE — 通信メカニズム (Phase G) 解析メモ

対象: `STATE_DB` の `BFD_SESSION_TABLE`（および付帯 `BFD_SOFTWARE_SESSION_TABLE`）。
ソース: `sonic-swss/orchagent/bfdorch.cpp` (HEAD)。

## 1. パブリッシュ側 — `swss::Table` 直書き（書込のみ、Redis keyspace のみ）

`BfdOrch` は **`swss::Table m_stateBfdSessionTable`** (`STATE_DB`, `STATE_BFD_SESSION_TABLE_NAME`) を 1 つだけ保持し、書き手はこのテーブル直書きのみ。`ProducerStateTable` / `NotificationProducer` / channel `PUBLISH` は **使用しない**。

```text
sai_bfd_session_state_change (NOTIFICATIONS ch on ASIC_DB)
   │
   ▼
NotificationConsumer m_bfdStateNotificationConsumer (BFD_STATE_NOTIFICATIONS)
   │  bfdorch.cpp:63-65, 86 — Orch::addExecutor(Notifier(...))
   ▼
BfdOrch::doTask(NotificationConsumer&)  bfdorch.cpp:220-268
   │  op == "bfd_session_state_change" を deserialize
   │  state != lookup[id].state のときのみ:
   ▼
m_stateBfdSessionTable.hset(key, "state", session_state_lookup.at(state))
                                          bfdorch.cpp:252
   │
   ├─ in-process notify(SUBJECT_TYPE_BFD_SESSION_STATE_CHANGE, &update)
   │       bfdorch.cpp:257-260 — Observer pattern (Orch::notify)
   │
   └─ Redis HSET → keyspace 通知 (`__keyspace@6__:BFD_SESSION_TABLE|...`)
```

書き込み箇所まとめ:

| 行 | 操作 | 契機 |
|---|---|---|
| `bfdorch.cpp:78` | `m_stateBfdSessionTable.del(alias)` (全件) | コンストラクタ起動時クリーンアップ |
| `bfdorch.cpp:252` | `m_stateBfdSessionTable.hset(key, "state", ...)` | SAI BFD_SESSION_STATE_CHANGE 通知受信時 |
| `bfdorch.cpp:565` | `m_stateBfdSessionTable.set(state_db_key, fvVector)` | `create_bfd_session()` 成功直後 (`state=Down` 固定で初期書込み) |
| `bfdorch.cpp:629` | `m_stateBfdSessionTable.del(peer)` | `remove_bfd_session()` 内 |

`swss::Table::set/hset/del` は内部で Redis `HSET` / `HDEL` を発行するのみで、**LUA + channel PUBLISH（`ProducerStateTable` 系）には乗らない**。よって `BFD_SESSION_TABLE_CHANNEL` のような専用 channel は存在せず、subscriber 側は Redis の keyspace 通知 (`notify-keyspace-events Kh`) または polling/HGETALL に依存する。

## 2. SAI 通知購読パス — NotificationConsumer

`BfdOrch` ctor (`bfdorch.cpp:63-65`) で:

```cpp
DBConnector *notificationsDb = new DBConnector("ASIC_DB", 0);
m_bfdStateNotificationConsumer = new swss::NotificationConsumer(notificationsDb, "NOTIFICATIONS");
auto bfdStateNotificatier = new Notifier(m_bfdStateNotificationConsumer, this, "BFD_STATE_NOTIFICATIONS");
...
Orch::addExecutor(bfdStateNotificatier);   // bfdorch.cpp:86
```

`ASIC_DB` の `NOTIFICATIONS` channel を `swss::NotificationConsumer` (LPOP + PUBSUB) で待機し、`doTask(NotificationConsumer&)` で `op` をディスパッチ。`op == "bfd_session_state_change"` のみが BFD_SESSION_TABLE への書込みを起こす。

SAI 側通知ハンドラ登録は `register_bfd_state_change_notification()` (`bfdorch.cpp:270-303`):
- `sai_query_attribute_capability(SAI_SWITCH_ATTR_BFD_SESSION_STATE_CHANGE_NOTIFY)` で SAI 側対応を確認
- 未対応なら STATE_DB への state 更新自体が走らない（初期 `Down` のみで固定）
- 対応している場合は `set_switch_attribute` で `on_bfd_session_state_change` コールバックを SAI に登録（`notifications.h` 経由）

## 3. 購読側 — keyspace 通知 / HGETALL polling

`BFD_SESSION_TABLE` の読者は CONFIG_DB のような `ConfigDBConnector.subscribe()` 経路を **使わない**。代わりに以下:

| 読者 | 取得方法 | 根拠 |
|------|---------|------|
| `BfdOrch` 内 in-process subscriber (例: `VNetRouteOrch`) | `Orch::notify(SUBJECT_TYPE_BFD_SESSION_STATE_CHANGE, ...)` Observer | `bfdorch.cpp:257-260` |
| `BfdMonitorOrch` / VNet 監視 | STATE_DB `SubscriberStateTable(state_db, STATE_BFD_SESSION_TABLE_NAME)` または in-process notify | swss-common keyspace 通知ベース |
| `show bfd peers` (sonic-utilities) | `sonic-db-cli STATE_DB hgetall 'BFD_SESSION_TABLE\|*'` snapshot | sonic-utilities `show/bfd.py` |
| gNMI / sonic-mgmt-common | translib による STATE_DB HGETALL マッピング | translib bfd モジュール |

`NotificationProducer` を `BFD_SESSION_TABLE` 用に張る発信者は SONiC ソース内に存在しない（grep 範囲: `bfdorch.cpp` のみで `NotificationProducer` 名は無し）。

## 4. ソフトウェア BFD パス (`BFD_SOFTWARE_SESSION_TABLE`)

`use_software_bfd == true` (`BGP_DEVICE_GLOBAL.STATE.use_software_bfd`) の場合 (`bfdorch.cpp:133-139, 706-710`):

```cpp
m_stateSoftBfdSessionTable->set(createStateDBKey(key), data);
```

こちらも `swss::Table::set` のみで、`state` フィールドは含まれない（FRR 側で状態管理）。`m_stateSoftBfdSessionTable` は `std::unique_ptr<swss::Table>`、STATE_DB index 6。

## 5. 通信パスまとめ

| 役割 | クラス | 経路 | 根拠 |
|---|---|---|---|
| 書込 (state 初期) | `swss::Table` | `HSET STATE_DB BFD_SESSION_TABLE\|<k>` 全フィールド | `bfdorch.cpp:565` |
| 書込 (state 変化) | `swss::Table::hset` | `HSET ... state <enum>` | `bfdorch.cpp:252` |
| 削除 | `swss::Table::del` | `DEL STATE_DB BFD_SESSION_TABLE\|<k>` | `bfdorch.cpp:78, 629` |
| 内部通知 | `Orch::notify` (Observer) | プロセス内コールバック | `bfdorch.cpp:257-260` |
| SAI → orchagent | `NotificationConsumer` (ASIC_DB `NOTIFICATIONS`) | LPOP + PUBSUB | `bfdorch.cpp:63-65, 220-268` |
| 外部購読 | `SubscriberStateTable` / HGETALL | Redis keyspace 通知または polling | swss-common keyspace 通知ベース |

## 6. ResponsePublisher / APPL_STATE_DB 非使用の確認

- `BfdOrch` は `ZmqOrch` を継承していない（`Orch` 直系）。`ZmqProducerStateTable` / `ZmqConsumerStateTable` 経路は **無し**。
- `ResponsePublisher` も `BfdOrch` ctor で生成されない。APPL_STATE_DB への状態反映 channel は **無い**。
- `NotificationProducer` を介した channel publish も **無し**。

結論: STATE_DB `BFD_SESSION_TABLE` の通信メカニズムは「**SAI 通知 → bfdorch → swss::Table 直書き**」の単純経路。書込側は `ProducerStateTable` 系ではなく `swss::Table` を使用するため、subscriber は Redis keyspace 通知または polling/HGETALL に依存する。

## 7. 参考行番号・パス

- `sonic-swss/orchagent/bfdorch.cpp`
  - L9 `#include "notifications.h"` — SAI 通知コールバック宣言
  - L49-55 `session_state_lookup` — SAI enum → 文字列マップ
  - L57-88 ctor — `m_stateBfdSessionTable` 初期化 + `NotificationConsumer("NOTIFICATIONS")` 登録 + 全件 cleanup
  - L220-268 `doTask(NotificationConsumer&)` — `op == "bfd_session_state_change"` 受信 → `hset(state)` + `Orch::notify`
  - L270-303 `register_bfd_state_change_notification()` — SAI 側ハンドラ登録 (`SAI_SWITCH_ATTR_BFD_SESSION_STATE_CHANGE_NOTIFY`)
  - L305-575 `create_bfd_session()` — STATE_DB 初期書込み `set(state_db_key, fvVector)` (L565)
  - L629 `m_stateBfdSessionTable.del(peer)` — `remove_bfd_session()` 内
  - L658-704 `notify_session_state_down()` / `handleTsaStateChange()` — TSA 連動削除
  - L706-710 `createSoftwareBfdSession()` — `m_stateSoftBfdSessionTable->set()` 経路
