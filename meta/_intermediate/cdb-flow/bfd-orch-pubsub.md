# APPL_DB BFD_SESSION_TABLE (bfdorch) — 通信メカニズム (Phase G) 解析メモ

対象: APPL_DB `BFD_SESSION_TABLE` を購読する `bfdorch` (sonic-swss / orchagent)。

`bfdorch` は 2 系統の購読を持つ:

1. APPL_DB `BFD_SESSION_TABLE` の SET / DEL を `swss::ConsumerStateTable` (channel PUBLISH/SUBSCRIBE) で購読
2. ASIC_DB `NOTIFICATIONS` channel を `swss::NotificationConsumer` で購読し、SAI `bfd_session_state_change` 通知を受信して STATE_DB を更新

---

## 1. APPL_DB 側の購読 — ConsumerStateTable

`bfdorch` は `Orch(db, tableName)` を継承し、`m_applDb` + `APP_BFD_SESSION_TABLE_NAME` で初期化される。

```cpp
// sonic-swss/orchagent/orchdaemon.cpp:237-244
TableConnector stateDbBfdSessionTable(m_stateDb, STATE_BFD_SESSION_TABLE_NAME);
...
gBfdOrch = new BfdOrch(m_applDb, APP_BFD_SESSION_TABLE_NAME, stateDbBfdSessionTable);
```

`Orch` 基底クラスの `addConsumer()` が DB ID で分岐し、APPL_DB (= CONFIG_DB / STATE_DB / CHASSIS_APP_DB 以外) には `ConsumerStateTable` を割り当てる (`orch.cpp:1186-1196`)。よって **keyspace 通知 (`__keyspace@<dbId>__:...`) は使わない**。書き込み側 (`bgpcfgd` `StaticRouteBfd` / `BfdMgr` 等の Python ProducerStateTable) が `_BFD_SESSION_TABLE:<key>` への `HSET` + `BFD_SESSION_TABLE_CHANNEL@0` への `PUBLISH "G"` を発行することで通知される。

| 購読者 | 購読 API | 購読 DB / テーブル | 優先度 | バッチ |
|--------|---------|-------------------|--------|--------|
| `orchagent` (`BfdOrch`) | `swss::ConsumerStateTable` | `APPL_DB` / `BFD_SESSION_TABLE` | `default_orch_pri` | `gBatchSize` (default 128) |

`BfdOrch` 自体には独自の priority 定数はなく、`Orch::addConsumer()` 第 3 引数 `pri = default_orch_pri` を使う。

### Producer 側

- `bgpcfgd` `StaticRouteBfd` (`src/sonic-bgpcfgd/staticroutebfd/main.py`) — static route BFD 用に APPL_DB `BFD_SESSION_TABLE` へ直接書き込む
- `bgpcfgd` `BfdMgr` (`src/sonic-bgpcfgd/bgpcfgd/managers_bfd.py`) — software BFD 経路で FRR `bfdd` 連携用に APPL_DB に書き込む
- CONFIG_DB `BFD_SESSION` を直接書く運用も存在 (CONFIG_DB → APPL_DB のミラーは `bgpcfgd` 系が担当)

いずれも `swsscommon.ProducerStateTable` 経由なので、Redis 上は `_BFD_SESSION_TABLE:` プレフィックスの一時 hash + channel PUBLISH の 2 段階になる。

---

## 2. doTask(Consumer&) フロー

```
bgpcfgd / static route BFD producer
  ↓ ProducerStateTable::set("<vrf>:<intf>:<peer>", fvs)
APPL_DB: HSET "_BFD_SESSION_TABLE:<vrf>:<intf>:<peer>" local_addr=... type=...
  ↓ Redis PUBLISH "BFD_SESSION_TABLE_CHANNEL@0" "G"
OrchDaemon main loop: m_select->select(&s, SELECT_TIMEOUT=1000ms)
  ↓ Consumer::execute() → ConsumerStateTable::pops()
BfdOrch::doTask(Consumer&)  (bfdorch.cpp:111-217)
  ↓ BgpGlobalStateOrch から tsa_enabled / use_software_bfd を取得
  ↓ SET の場合:
  ↓   use_software_bfd == true  → STATE_DB SOFTWARE_BFD_SESSION_TABLE 転記のみ
  ↓   shutdown_bfd_during_tsa  → tsa_enabled に応じて create or notify_session_state_down
  ↓   通常 → create_bfd_session()
  ↓ DEL の場合: remove_bfd_session()
  ↓
SAI: sai_bfd_api->create_bfd_session / remove_bfd_session
ASIC (sairedis → ASIC_DB)
```

- `doTask(Consumer&)` 冒頭に `allPortsReady()` チェックは **無い** (FdbOrch とは異なり、BFD はポート準備完了を待たない)。
- `m_toSync` 残留: `create_bfd_session()` が `false` を返した場合 (`it++; continue;`) のみエントリは残留する。`true` で `erase` される。

---

## 3. ASIC_DB NOTIFICATIONS 側の購読 — NotificationConsumer

セッション状態変化 (`SAI_BFD_SESSION_STATE_*`) は、SAI コールバック `on_bfd_session_state_change` が ASIC_DB `NOTIFICATIONS` チャネルに `bfd_session_state_change` op で publish し、`BfdOrch::m_bfdStateNotificationConsumer` が受信する。

```cpp
// sonic-swss/orchagent/bfdorch.cpp:57-87 (BfdOrch ctor)
DBConnector *notificationsDb = new DBConnector("ASIC_DB", 0);
m_bfdStateNotificationConsumer = new swss::NotificationConsumer(notificationsDb, "NOTIFICATIONS");
auto bfdStateNotificatier = new Notifier(m_bfdStateNotificationConsumer, this, "BFD_STATE_NOTIFICATIONS");
...
Orch::addExecutor(bfdStateNotificatier);
```

`Notifier` executor として `Orch` の select() ループに混ぜ込まれ、event 受信時に `BfdOrch::doTask(NotificationConsumer&)` (`bfdorch.cpp:220-268`) が呼ばれる。

### ハンドラ動作 (bfdorch.cpp:220-268)

```cpp
consumer.pop(op, data, values);
if (&consumer != m_bfdStateNotificationConsumer) return;
if (op == "bfd_session_state_change") {
    sai_deserialize_bfd_session_state_ntf(data, count, &bfdSessionState);
    for each session_id:
        state = bfdSessionState[i].session_state;
        if (state != bfd_session_lookup[id].state) {
            m_stateBfdSessionTable.hset(key, "state", session_state_lookup.at(state));
            notify(SUBJECT_TYPE_BFD_SESSION_STATE_CHANGE, &update);
            bfd_session_lookup[id].state = state;
        }
    sai_deserialize_free_bfd_session_state_ntf(count, bfdSessionState);
}
```

- 状態差分があるときのみ STATE_DB `BFD_SESSION_TABLE|<vrf>|<intf>|<peer>` の `state` フィールドを HSET する (毎回上書きはしない)。
- 同時に C++ レベルの `Subject::notify(SUBJECT_TYPE_BFD_SESSION_STATE_CHANGE, ...)` でプロセス内 observer (例: `MuxOrch` / `VxlanTunnelOrch` の dynamic next-hop tracking) に伝搬する。
- 識別子は `op == "bfd_session_state_change"` 固定。他 op (例: `fdb_event`) は同じ NOTIFICATIONS チャネルに流れてくるが、`&consumer != m_bfdStateNotificationConsumer` ガードで弾く構造。

### コールバック登録

`BfdOrch::register_bfd_state_change_notification()` (`bfdorch.cpp:270-303`) が `sai_query_attribute_capability(SAI_SWITCH_ATTR_BFD_SESSION_STATE_CHANGE_NOTIFY)` で `set_implemented == true` を確認した上で、`sai_switch_api->set_switch_attribute(BFD_SESSION_STATE_CHANGE_NOTIFY, on_bfd_session_state_change)` を呼ぶ。

呼び出しタイミングは **初回 `create_bfd_session()` 内** (`bfdorch.cpp:307-314`)。`register_state_change_notif` フラグで一度きりに制御される。capability が false の場合は session 作成自体を reject する (= `BFD register change notification not supported`)。

---

## 4. STATE_DB 側

`bfdorch` は 2 つの STATE_DB Table を保持する (どちらも書き込みのみで購読しない):

| Table | 用途 |
|-------|------|
| `m_stateBfdSessionTable` (`STATE_BFD_SESSION_TABLE_NAME` = `BFD_SESSION_TABLE`) | hardware BFD 経路のランタイム状態 (`state=Up/Down/Init/Admin_Down`) |
| `m_stateSoftBfdSessionTable` (`STATE_BFD_SOFTWARE_SESSION_TABLE_NAME` = `SOFTWARE_BFD_SESSION_TABLE`) | software BFD 経路で APPL_DB エントリを転記するスナップショット |

両 Table とも ctor で `getKeys()` + `del()` で起動時に空にされる (`bfdorch.cpp:74-85`)。STATE_DB を読み戻すロジックは無い。

---

## 5. 通信パターン要約

| 区間 | 方向 | 方式 | チャンネル / API |
|------|------|------|-----------------|
| bgpcfgd / static route BFD producer → APPL_DB | publish | `ProducerStateTable::set()` | `BFD_SESSION_TABLE_CHANNEL@0` (PUBLISH "G") |
| APPL_DB → BfdOrch | subscribe | `swss::ConsumerStateTable` (Orch base) | 同上 channel |
| BfdOrch → SAI | call | SAI BFD API | `sai_bfd_api->create_bfd_session` / `remove_bfd_session` |
| ASIC (SAI) → BfdOrch | notify | SAI switch attr callback → ASIC_DB NOTIFICATIONS | `op="bfd_session_state_change"` |
| ASIC_DB NOTIFICATIONS → BfdOrch | subscribe | `swss::NotificationConsumer` (`BFD_STATE_NOTIFICATIONS` Notifier) | channel `NOTIFICATIONS` |
| BfdOrch → STATE_DB | write | `swss::Table::hset()` | `BFD_SESSION_TABLE\|<vrf>\|<intf>\|<peer>` (`state` field) |
| BfdOrch → in-process observers | notify | `Subject::notify()` | `SUBJECT_TYPE_BFD_SESSION_STATE_CHANGE` |

keyspace 通知 (`__keyspace@<dbId>__:...`) は不使用。CONFIG_DB は直接購読せず、`bgpcfgd` 系 manager が CONFIG_DB → APPL_DB のミラーを担う。

---

## スキャン証跡

- `bfdorch.h` L1-73 — クラス構造 / メンバ確認 (NotificationConsumer + STATE_DB Table)
- `bfdorch.cpp` L57-88 — ctor (ASIC_DB NOTIFICATIONS / STATE_DB / Notifier 登録)
- `bfdorch.cpp` L111-217 — `doTask(Consumer&)` (APPL_DB SET/DEL ハンドラ)
- `bfdorch.cpp` L220-268 — `doTask(NotificationConsumer&)` (SAI 状態変化ハンドラ)
- `bfdorch.cpp` L270-303 — `register_bfd_state_change_notification()` (SAI capability 照会 + コールバック登録)
- `bfdorch.cpp` L307-314 — 初回 `create_bfd_session()` での register 1 回起動
- `orchdaemon.cpp` L237-244 — `BfdOrch` 生成 (APPL_DB バインド)
- `orch.cpp` L1186-1196 — DB ID 分岐 (APPL_DB → ConsumerStateTable)
