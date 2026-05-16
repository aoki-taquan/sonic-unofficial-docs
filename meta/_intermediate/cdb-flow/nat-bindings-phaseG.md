# NAT_BINDINGS — Phase G: 通信メカニズム (Redis Subscribe / SAI / conntrack)

調査日: 2026-05-16
対象テーブル: CONFIG_DB `NAT_BINDINGS`
ソース: `sonic-swss/cfgmgr/natmgrd.cpp`, `sonic-swss/cfgmgr/natmgr.cpp`, `sonic-swss/orchagent/natorch.cpp`

---

## 1. CONFIG_DB 購読 — SubscriberStateTable (natmgrd 層)

`natmgrd.cpp:109-121` で生成された `NatMgr` は `Orch` 基底クラス経由で以下のテーブルを一括購読する:

```
CFG_NAT_BINDINGS_TABLE_NAME   (= "NAT_BINDINGS")
CFG_NAT_POOL_TABLE_NAME
CFG_NAT_GLOBAL_TABLE_NAME
CFG_STATIC_NAT_TABLE_NAME
CFG_STATIC_NAPT_TABLE_NAME
CFG_INTF_TABLE_NAME  (+ LAG / VLAN / Loopback)
CFG_ACL_TABLE_TABLE_NAME
CFG_ACL_RULE_TABLE_NAME
```

`Orch::addConsumer()` (`orch.cpp:1186-1194`) は CONFIG_DB に対して **`SubscriberStateTable`** を生成する:

```cpp
// CONFIG_DB / STATE_DB は SubscriberStateTable (keyspace notification)
addExecutor(new Consumer(new SubscriberStateTable(db, tableName, ...), this, tableName));
```

### Redis keyspace channel

```
PSUBSCRIBE __keyspace@4__:NAT_BINDINGS|*
```

- CONFIG_DB の DB 番号は通常 4
- `NAT_BINDINGS|<binding_name>` のキーへの HSET / HDEL / DEL を捕捉

### イベント受信フロー

```
CONFIG_DB への HSET (nat_pool / access_list / nat_type / twice_nat_id)
  → Redis: __keyspace@4__:NAT_BINDINGS|<name> に pmessage 発火
  → SubscriberStateTable::readData()
    → m_keyspace_event_buffer に push
  → SubscriberStateTable::pops()
    → "del" → DEL_COMMAND
    → それ以外 → HGETALL でフィールド値取得 → SET_COMMAND
    → KeyOpFieldsValuesTuple (key, op, fvs) 返却
  → natmgrd select ループ (SELECT_TIMEOUT=1000ms)
    → Consumer::execute() → NatMgr::doTask(Consumer&)
      → doNatBindingTask(key, op, data)
```

### 起動時スナップショット再生

`SubscriberStateTable` コンストラクタ (`subscriberstatetable.cpp:25-42`) は PSUBSCRIBE 後に `m_table.getKeys()` で既存 key を全件取得し、SET イベントとして積む。natmgrd 再起動後も全バインディングが再処理される（再起動耐性）。

---

## 2. natmgrd メインループ

```cpp
// natmgrd.cpp:143-198
swss::Select s;
s.addSelectables(natmgr->getSelectables());          // SubscriberStateTable 群
s.addSelectable(timeoutNotificationsConsumer);        // SETTIMEOUTNAT チャンネル
s.addSelectable(flushNotificationsConsumer);          // FLUSHNATENTRIES チャンネル

while (!gExit)
{
    ret = s.select(&sel, SELECT_TIMEOUT);  // 1000ms タイムアウト
    if (ret == Select::TIMEOUT) { natmgr->doTask(); continue; }

    if (sel == timeoutNotificationsConsumer) { natmgr->timeoutNotifications(...); continue; }
    if (sel == flushNotificationsConsumer)   { natmgr->flushNotifications(...); continue; }

    auto *c = (Executor *)sel;
    c->execute();  // → NatMgr::doTask(Consumer&) → doNatBindingTask
}
```

---

## 3. doNatBindingTask — ハンドラ内処理

`natmgr.cpp:6868-7100` (`doNatBindingTask`):

1. フィールド (`nat_pool`, `access_list`, `nat_type`, `twice_nat_id`) を解析
2. `m_natBindingInfo[key]` に格納
3. `addDynamicNatRule(key)` を呼び出し

`addDynamicNatRule` (`natmgr.cpp:4621-4679`):

- `isNatEnabled()` → false ならスキップ (`"NAT is not yet enabled"`)
- pool キャッシュ確認 → 未登録ならスキップ (`"Pool is not yet enabled"`)
- `twice_nat_id` が空 → `setDynamicAllForwardOrAclbasedRules(ADD, ...)` (iptables)
- `twice_nat_id` が非空 → `addDynamicTwiceNatRule(key)` (Twice NAT)

---

## 4. natmgr → APPL_DB 書き込み (ProducerStateTable)

`natmgr.cpp:43-49` で以下の `ProducerStateTable` を生成:

```cpp
m_appNatTableProducer      (appDb, APP_NAT_TABLE_NAME)           // 単体 NAT エントリ
m_appNaptTableProducer     (appDb, APP_NAPT_TABLE_NAME)          // NAPT エントリ
m_appTwiceNatTableProducer (appDb, APP_NAT_TWICE_TABLE_NAME)     // Twice NAT
m_appTwiceNaptTableProducer(appDb, APP_NAPT_TWICE_TABLE_NAME)    // Twice NAPT
m_appNatGlobalTableProducer(appDb, APP_NAT_GLOBAL_TABLE_NAME)    // グローバル設定
m_appNatDnatPoolProducer   (appDb, APP_NAT_DNAT_POOL_TABLE_NAME) // DNAT pool
```

Dynamic Binding では主に **kernel iptables ルール** を設定し、conntrack 経由で動的エントリが生成される。静的エントリは `m_appNatTableProducer.set()` で APPL_DB に直接書き込む。

APPL_DB への書き込み時、`ProducerStateTable::set()` は対応するチャンネルに PUBLISH する:

```
PUBLISH APP_NAT_TABLE_CHANNEL@0   (NatOrch が SUBSCRIBE)
```

---

## 5. conntrack 経路

Dynamic SNAT の conntrack フロー:

```
送信元パケット → kernel netfilter (iptables MASQUERADE / SNAT ルール)
  → kernel conntrack モジュールが接続追跡エントリを生成
  → (定期) NatOrch::m_natQueryTimer 発火 → ctNetio 経由で conntrack テーブルを読み込み
  → 動的 NAT エントリを APPL_DB (APP_NAT_TABLE / APP_NAPT_TABLE) へ set
  → ConsumerStateTable 経由で NatOrch がエントリを受信
  → addHwSnatEntry() / addHwSnaptEntry() → sai_nat_api->create_nat_entry()
```

Static NAT (Binding 非対象) では `addStaticNatEntry()` が直接 APPL_DB に書き込み、同様に NatOrch → SAI へ進む。

---

## 6. APPL_DB 購読 — ConsumerStateTable (NatOrch 層)

`orchdaemon.cpp:457-465` で `NatOrch` 生成時に以下テーブルを購読:

```
APP_NAT_DNAT_POOL_TABLE_NAME  (優先度 +5)
APP_NAT_TABLE_NAME            (優先度 +4)
APP_NAPT_TABLE_NAME           (優先度 +3)
APP_NAT_TWICE_TABLE_NAME      (優先度 +2)
APP_NAPT_TWICE_TABLE_NAME     (優先度 +1)
APP_NAT_GLOBAL_TABLE_NAME     (優先度 +0)
```

`NatOrch::doTask(Consumer&)` (`natorch.cpp:3033-3094`) でテーブル名をディスパッチ。

---

## 7. NatOrch → SAI nat_api

`natorch.cpp:738-` の `addHwSnatEntry()` (SNAT、動的バインディング経由が最終到達点):

```cpp
sai_nat_entry_t snat_entry = {};
snat_entry.nat_type = SAI_NAT_TYPE_SOURCE_NAT;
// SAI_NAT_ENTRY_ATTR_SRC_IP / SRC_IP_MASK / ENABLE_PACKET_COUNT / ENABLE_BYTE_COUNT
status = sai_nat_api->create_nat_entry(&snat_entry, attr_count, nat_entry_attr);
```

Twice NAT の場合は `addHwTwiceNatEntry()` が `SAI_NAT_TYPE_DOUBLE_NAT` で `create_nat_entry` を呼ぶ (`natorch.cpp:1379-1385`)。

---

## 8. 非同期通知チャンネル (NAT_BINDINGS に関連)

| チャンネル名 | DB | 方向 | 送信者 | 受信者 | 用途 |
|---|---|---|---|---|---|
| `SETTIMEOUTNAT` | APPL_DB | NatOrch → natmgrd | `setTimeoutNotifier` (natorch.cpp:137) | `timeoutNotificationsConsumer` (natmgrd.cpp:149) | conntrack timeout 変更通知 |
| `FLUSHNATENTRIES` | APPL_DB | 外部 CLI → natmgrd | `show nat translate flush` | `flushNotificationsConsumer` (natmgrd.cpp:152) | conntrack エントリ全フラッシュ |
| `NAT_DB_CLEANUP_NOTIFICATION` | APPL_DB | natmgrd → NatOrch | `cleanupNotifier` (natmgrd.cpp:127) | `m_cleanupNotificationConsumer` (natorch.cpp:89) | natmgrd 終了時の ASIC/Redis クリーンアップ |

---

## 9. 全体フロー まとめ

```
CLI (config nat add binding)
  → CONFIG_DB HSET NAT_BINDINGS|<name>
    → SubscriberStateTable (PSUBSCRIBE __keyspace@4__:NAT_BINDINGS|*)
      → natmgrd select ループ (1000ms)
        → doNatBindingTask() → addDynamicNatRule()
          ├─ iptables MASQUERADE/SNAT ルール設定
          │     → kernel conntrack → NatOrch タイマーポーリング
          │       → APP_DB ProducerStateTable::set()
          │         → ConsumerStateTable → NatOrch::doTask()
          │           → addHwSnatEntry()
          │             → sai_nat_api->create_nat_entry() [SAI_NAT_TYPE_SOURCE_NAT]
          └─ (Twice NAT) addDynamicTwiceNatRule()
                → sai_nat_api->create_nat_entry() [SAI_NAT_TYPE_DOUBLE_NAT]
```

---

## 証拠リンク

- `sonic-swss/cfgmgr/natmgrd.cpp:100-198` — メインループ + 購読テーブル一覧
- `sonic-swss/cfgmgr/natmgr.cpp:35-49` — ProducerStateTable 生成
- `sonic-swss/cfgmgr/natmgr.cpp:4621-4679` — `addDynamicNatRule`
- `sonic-swss/cfgmgr/natmgr.cpp:6868-7100` — `doNatBindingTask`
- `sonic-swss/orchagent/natorch.cpp:82-140` — NatOrch 生成 / 非同期通知登録
- `sonic-swss/orchagent/natorch.cpp:1271-1309` — `addHwSnatEntry` / SAI 呼び出し
- `sonic-swss/orchagent/natorch.cpp:3033-3094` — `NatOrch::doTask`
