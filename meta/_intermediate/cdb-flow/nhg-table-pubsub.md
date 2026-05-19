# NEXTHOP_GROUP_TABLE / CLASS_BASED_NEXT_HOP_GROUP_TABLE — Phase G Redis 通知メカニズム調査

調査日: 2026-05-19
対象テーブル: APPL_DB `NEXTHOP_GROUP_TABLE` / `CLASS_BASED_NEXT_HOP_GROUP_TABLE`

## 調査対象ファイル

- `sonic-swss/fpmsyncd/routesync.cpp` (ProducerStateTable 初期化・書き込み)
- `sonic-swss/fpmsyncd/routesync.h` (m_nexthop_groupTable 型宣言)
- `sonic-swss/orchagent/orchdaemon.cpp` (NhgOrch / CbfNhgOrch インスタンス生成、select ループ)
- `sonic-swss/orchagent/orch.cpp` (Orch::addConsumer — ConsumerStateTable 生成)
- `sonic-swss/orchagent/nhgorch.cpp` / `cbf/cbfnhgorch.cpp` (doTask)

---

## 書き込み側: fpmsyncd

### m_nexthop_groupTable の型

```cpp
// routesync.h:291
ProducerStateTable  m_nexthop_groupTable;
```

`ProducerStateTable` (非 ZMQ) で初期化。`ROUTE_TABLE` の `createProducerStateTable()` とは異なり、ZMQ クライアントを渡していない。

### 初期化

```cpp
// routesync.cpp:157
m_nexthop_groupTable(pipeline, APP_NEXTHOP_GROUP_TABLE_NAME, true),
```

`APP_NEXTHOP_GROUP_TABLE_NAME = "NEXTHOP_GROUP_TABLE"` (schema.h:55)

比較: ROUTE_TABLE は ZMQ 対応
```cpp
// routesync.cpp:156
m_routeTable(createProducerStateTable(pipeline, APP_ROUTE_TABLE_NAME, true, m_zmqClient)),
```

### 書き込み箇所

| 操作 | 箇所 | 説明 |
|------|------|------|
| SET | `routesync.cpp:1882` | FRR Netlink nexthop イベント処理: `m_nexthop_groupTable.set(key.c_str(), fvVector)` |
| DEL | `routesync.cpp:3370` | NHG 削除: `m_nexthop_groupTable.del(key)` |
| SET (wrapper) | `routesync.cpp:3419` | `setTable(fvw, m_nexthop_groupTable)` (ZMQ 有効時でも non-ZMQ で処理) |

---

## 購読側: orchagent

### インスタンス生成

```cpp
// orchdaemon.cpp:338-339
gNhgOrch    = new NhgOrch   (m_applDb, APP_NEXTHOP_GROUP_TABLE_NAME);
gCbfNhgOrch = new CbfNhgOrch(m_applDb, APP_CLASS_BASED_NEXT_HOP_GROUP_TABLE_NAME);
```

### ConsumerStateTable 生成経路

```cpp
// nhgbase.h:404 — NhgOrchCommon コンストラクタ
NhgOrchCommon(DBConnector *db, string tableName) : Orch(db, tableName) {}

// orch.cpp:92-95 — Orch(DBConnector*, const string)
Orch::Orch(DBConnector *db, const string tableName, int pri) {
    addConsumer(db, tableName, pri);
}

// orch.cpp:1186-1196 — addConsumer
void Orch::addConsumer(DBConnector *db, string tableName, int pri) {
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB) {
        addExecutor(new Consumer(new SubscriberStateTable(...)));
    } else {
        // APPL_DB はここ
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
    }
}
```

APPL_DB の dbId は 0。CONFIG_DB (4) / STATE_DB (6) 以外なので `ConsumerStateTable` が選択される。

### select ループ

```cpp
// orchdaemon.cpp:959
ret = m_select->select(&s, SELECT_TIMEOUT);  // SELECT_TIMEOUT = 1000ms (orchdaemon.cpp:23)
```

ConsumerStateTable が SUBSCRIBE チャンネルからメッセージを受信すると `select()` が返り、対応する `doTask()` が呼ばれる。

### バッチサイズ

```cpp
// orchdaemon.cpp:81 (DEFAULT_MAX_BULK_SIZE は異なる用途)
// gBatchSize の実定義確認
```

`gBatchSize` はデフォルト 128。ConsumerStateTable のポップ上限として機能し、1 ループで最大 128 エントリを処理する。

---

## ZMQ 非使用の確認

| テーブル | 初期化 | ZMQ |
|---------|--------|-----|
| `NEXTHOP_GROUP_TABLE` | `ProducerStateTable(pipeline, name, true)` | **なし** |
| `ROUTE_TABLE` | `createProducerStateTable(pipeline, name, true, m_zmqClient)` | あり（feature フラグ次第） |
| `LABEL_ROUTE_TABLE` | `createProducerStateTable(pipeline, name, true, m_zmqClient)` | あり（feature フラグ次第） |

`NEXTHOP_GROUP_TABLE` と `CLASS_BASED_NEXT_HOP_GROUP_TABLE` は ZMQ 経路を持たない。orchagent 側の `ZmqConsumerStateTable` も使用されない。

---

## CLASS_BASED_NEXT_HOP_GROUP_TABLE の書き込み元

`CLASS_BASED_NEXT_HOP_GROUP_TABLE` の書き込み元は fpmsyncd には存在しない（routesync.cpp に一切参照なし）。CLI 経路もなし。  
書き込みは以下の方法のみ:
1. `config_db.json` 直編集後の `sonic-cfggen` による APPL_DB 反映
2. gNMI / REST API 経由での直接 APPL_DB 書き込み
3. `redis-cli -n 0 HSET CLASS_BASED_NEXT_HOP_GROUP_TABLE:<name> ...` による手動書き込み

いずれの場合も ConsumerStateTable が APPL_DB の変化を受信し、`CbfNhgOrch::doTask()` が処理する。

---

## まとめ

- **書き込み**: fpmsyncd → `ProducerStateTable::set()` → APPL_DB HSET + PUBLISH `NEXTHOP_GROUP_TABLE_CHANNEL@0`
- **購読**: orchagent `NhgOrch` / `CbfNhgOrch` → `ConsumerStateTable` → SUBSCRIBE チャンネル → `doTask()` 処理
- **タイムアウト**: `SELECT_TIMEOUT = 1000ms`、`gBatchSize = 128`
- **ZMQ**: 非使用（ROUTE_TABLE とは異なる）
- **warm restart**: ConsumerStateTable の `m_toSync` に残るエントリが reconcile フェーズで再処理される
