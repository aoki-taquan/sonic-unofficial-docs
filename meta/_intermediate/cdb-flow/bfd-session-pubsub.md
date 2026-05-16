# BFD_SESSION — 通信メカニズム (Phase G) 解析メモ

対象: CONFIG_DB の `BFD_SESSION` テーブルと、その APPL_DB 反映先である `BFD_SESSION_TABLE` (key 区切り `:`)。主購読者は `orchagent` 内 `BfdOrch` (`sonic-swss/orchagent/bfdorch.cpp`)。

注意: `BfdOrch` は **CONFIG_DB の `BFD_SESSION` を直接購読しない**。CONFIG_DB → APPL_DB の橋渡しは `bgpcfgd` / 上位プロセス (static route BFD、DASH HA 等) が `BFD_SESSION_TABLE` (APPL_DB) に Producer で投入し、`BfdOrch` はその APPL_DB テーブルを購読する。

## 1. 購読 API — `ConsumerStateTable` (APPL_DB 経由)

`BfdOrch` のコンストラクタは `Orch(db, tableName)` (`bfdorch.cpp:58-59`) を継承する単一テーブル形。`orchdaemon.cpp:243` で `m_applDb` + `APP_BFD_SESSION_TABLE_NAME = "BFD_SESSION_TABLE"` を渡して生成される:

```cpp
// orchagent/orchdaemon.cpp:237-243
TableConnector stateDbBfdSessionTable(m_stateDb, STATE_BFD_SESSION_TABLE_NAME);
...
gBfdOrch = new BfdOrch(m_applDb, APP_BFD_SESSION_TABLE_NAME, stateDbBfdSessionTable);
```

`Orch::addConsumer()` の DB 種別分岐で APPL_DB は `else` 分岐に入り、**`ConsumerStateTable`** + `gBatchSize` が選ばれる:

```cpp
// orchagent/orch.cpp:1186-1196
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
    {
        addExecutor(new Consumer(new SubscriberStateTable(db, tableName,
            TableConsumable::DEFAULT_POP_BATCH_SIZE, pri), this, tableName));
    }
    else
    {
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
    }
}
```

- APPL_DB 起源の `BFD_SESSION_TABLE` は **`ConsumerStateTable`** が選ばれる (CONFIG_DB / STATE_DB のような keyspace 通知ではなく、Producer 側が `_KEYS` / `_CHANNEL` を介して push する channel ベース)。
- Producer 側 (例: `bgpcfgd/managers_bfd.py`, `staticroutebfd/main.py`, DashHaOrch) は `ProducerStateTable` で `set/del` し、Redis LIST + PUBLISH によりイベントを配送する。
- CONFIG_DB の `BFD_SESSION` writer は `sonic-cfggen` / `config` CLI / SONiC 上位プロセス。APPL_DB への橋渡しを担うコンポーネントが間に挟まる。

## 2. POP_BATCH_SIZE

`ConsumerStateTable` の第3引数は orchagent グローバル `gBatchSize` (`orchdaemon.cpp` で初期化、CLI `--batchsize` で上書き可、既定 128)。

- CONFIG_DB 経路 (`SubscriberStateTable`) の `DEFAULT_POP_BATCH_SIZE = 128` (`sonic-swss-common/common/table.h:164`) とは別系統。
- 1 回の `pops()` で最大 `gBatchSize` 件のイベントを取り出す。

## 3. Key パターン

- APPL_DB Key: `BFD_SESSION_TABLE:<vrf>:<interface>:<peer_ip>` (区切りは APPL_DB 既定 `:`)。
- channel: `BFD_SESSION_TABLE_CHANNEL` (ProducerStateTable / ConsumerStateTable が暗黙生成、`<table>_CHANNEL@<db>` 形)。
- CONFIG_DB Key: `BFD_SESSION|<vrf>|<interface>|<peer_ip>` (区切り `|`)。

## 4. ディスパッチ — `doTask(Consumer &)`

`BfdOrch::doTask(Consumer&)` (`bfdorch.cpp:111-217`) は `consumer.m_toSync` を線形に処理し、`use_software_bfd` フラグで hardware / software 経路を選択:

```cpp
// orchagent/bfdorch.cpp:111-138
void BfdOrch::doTask(Consumer &consumer)
{
    BgpGlobalStateOrch* bgp_global_state_orch = gDirectory.get<BgpGlobalStateOrch*>();
    bool tsa_enabled = false;
    bool use_software_bfd = true;
    if (bgp_global_state_orch)
    {
        tsa_enabled = bgp_global_state_orch->getTsaState();
        use_software_bfd = bgp_global_state_orch->getSoftwareBfd();
    }
    ...
    if (op == SET_COMMAND)
    {
        if (use_software_bfd)
        {
            m_stateSoftBfdSessionTable->set(createStateDBKey(key), data);  // STATE_DB へ転記のみ
            it = consumer.m_toSync.erase(it);
            continue;
        }
        ...
        create_bfd_session(key, data);  // hardware 経路: SAI BFD 作成
    }
}
```

- SET (hardware): `create_bfd_session()` → SAI `create_bfd_session` 呼び出し。
- SET (software): `m_stateSoftBfdSessionTable->set(...)` で STATE_DB `BFD_SOFTWARE_SESSION_TABLE` に転記し、bgpcfgd の `BfdMgr` が後段で拾う。
- 失敗時 (`return false`): `it++` のみ実施しイベント保持。次イベントループ周回で**自動再試行**。

## 5. もう 1 経路 — SAI BFD state change 通知 (NotificationConsumer)

`BfdOrch` は購読側として **2 つ目の Executor** を持つ。SAI からの state change 通知を受ける `NotificationConsumer` (channel ベース):

```cpp
// orchagent/bfdorch.cpp:63-65, 87
DBConnector *notificationsDb = new DBConnector("ASIC_DB", 0);
m_bfdStateNotificationConsumer = new swss::NotificationConsumer(notificationsDb, "NOTIFICATIONS");
auto bfdStateNotificatier = new Notifier(m_bfdStateNotificationConsumer, this, "BFD_STATE_NOTIFICATIONS");
...
Orch::addExecutor(bfdStateNotificatier);
```

- channel 名: `NOTIFICATIONS` (ASIC_DB 上の SAI redis sairedis 共通 channel)。
- op 値: `"bfd_session_state_change"` を `doTask(NotificationConsumer&)` (`bfdorch.cpp:217-265`) で受理。
- ペイロードは `sai_deserialize_bfd_session_state_ntf()` で `sai_bfd_session_state_notification_t[]` に復元、`BFD_SESSION_TABLE.state` (STATE_DB) を `Up`/`Down`/`Init`/`Admin_Down` で更新。
- SAI 側が `SAI_SWITCH_ATTR_BFD_SESSION_STATE_CHANGE_NOTIFY` を `set_implemented=false` で返すと通知ハンドラ未登録となり、STATE_DB の状態が永続に更新されない (`bfdorch.cpp:286-290`)。

## 6. CONFIG_DB → APPL_DB の橋渡し (BfdOrch スコープ外)

`BfdOrch` 自身は CONFIG_DB を購読しないため、`BFD_SESSION` (CONFIG_DB) を直接書いても hardware 経路には到達しない。実運用での橋渡しは:

- `bgpcfgd` (`sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bfd.py`): software BFD のとき STATE_DB `BFD_SOFTWARE_SESSION_TABLE` を購読 → FRR bfdd に vtysh 注入。CONFIG_DB の `BFD_SESSION` 自体は通常 `sonic-cfggen` 系が APPL_DB `BFD_SESSION_TABLE` に転送する設計。
- `staticroutebfd` (`sonic-swss/cfgmgr/staticroutebfd/main.py:101`): static route の BFD 監視を APPL_DB `BFD_SESSION_TABLE` に Producer で直接書き込む。
- `DashHaOrch` (`orchdaemon.cpp:1356-1359`): DPU 側 APPL_DB の `BFD_SESSION_TABLE` を別途扱う。

## 7. 起動時スナップショット

`ConsumerStateTable` は購読開始時に Producer 側が積み残した LIST 上の未処理エントリを `pops()` で吸い上げる。`SubscriberStateTable` のように Redis 既存キーを `HGETALL` 再配信する設計ではないため、orchagent の crash → restart で APPL_DB に残っている `BFD_SESSION_TABLE|*` の再構築は `warm-reboot` レイヤ (`m_stateBfdSessionTable.getKeys` での cold-start cleanup, `bfdorch.cpp:75-83`) が担う。

## 8. TTL / 永続性

- APPL_DB `BFD_SESSION_TABLE` エントリには TTL 設定なし。
- STATE_DB の `BFD_SESSION_TABLE` (`SAI_OBJECT_TYPE_BFD_SESSION` の状態) も TTL なし。コールド起動時に BfdOrch ctor で `del()` クリーンアップ (`bfdorch.cpp:75-83`)。
- `BFD_SOFTWARE_SESSION_TABLE` (STATE_DB) も同様に ctor で del される。

## 9. 関連リファレンス

- `sonic-swss/orchagent/bfdorch.cpp:58-91` (`BfdOrch::BfdOrch` — `Orch(db,tableName)` 継承 + NotificationConsumer 登録)
- `sonic-swss/orchagent/bfdorch.cpp:111-217` (`BfdOrch::doTask(Consumer&)`)
- `sonic-swss/orchagent/bfdorch.cpp:217-302` (`BfdOrch::doTask(NotificationConsumer&)` + `register_bfd_state_change_notification`)
- `sonic-swss/orchagent/orchdaemon.cpp:237-244` (`BfdOrch` 生成、APPL_DB + `APP_BFD_SESSION_TABLE_NAME`)
- `sonic-swss/orchagent/orch.cpp:1186-1196` (`Orch::addConsumer` の DB 種別分岐)
- `sonic-swss-common/common/schema.h:120` (`APP_BFD_SESSION_TABLE_NAME = "BFD_SESSION_TABLE"`)
- `sonic-swss-common/common/schema.h:491-492` (`STATE_BFD_SESSION_TABLE_NAME`, `STATE_BFD_SOFTWARE_SESSION_TABLE_NAME`)
- `sonic-swss-common/common/table.h:164` (`DEFAULT_POP_BATCH_SIZE = 128`)
