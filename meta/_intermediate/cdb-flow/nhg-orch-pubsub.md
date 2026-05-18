# nhg-orch — 通信メカニズム (Phase G) 中間調査

対象ページ: `docs/reference/config-db/nhg-orch.md`
対象テーブル: APPL_DB
  - `NEXTHOP_GROUP_TABLE`
  - `CLASS_BASED_NEXT_HOP_GROUP_TABLE`
  - `FC_TO_NHG_INDEX_MAP_TABLE`
Consumer: `NhgOrch` / `CbfNhgOrch` / `NhgMapOrch`

---

## 1. 書き込み側 (Producer)

### 1.1 NEXTHOP_GROUP_TABLE — fpmsyncd (RouteSync)

`fpmsyncd/routesync.cpp` L157:

```cpp
m_nexthop_groupTable(pipeline, APP_NEXTHOP_GROUP_TABLE_NAME, true),
```

`RouteSync` は `ProducerStateTable` を使って APPL_DB の `NEXTHOP_GROUP_TABLE` へ書き込む。
FRR/Zebra から kernel netlink 経由で受信した ECMP ルートをパース後、`updateNextHopGroupDb(nhg)` (`routesync.cpp:3400`) が `m_nexthop_groupTable.set(key, fvVector)` を呼ぶ (`routesync.cpp:1882`, `routesync.cpp:3419`)。DEL 時は `m_nexthop_groupTable.del(key)` (`routesync.cpp:3370`)。

`ProducerStateTable::set/del` は内部で:
- `<TABLE>_KEY_SET` / `<TABLE>_KEY_DEL` ハッシュへキーを登録
- `<TABLE>_CHANNEL@<db_id>` (= `NEXTHOP_GROUP_TABLE_CHANNEL@0`) に `PUBLISH` を発行

### 1.2 CLASS_BASED_NEXT_HOP_GROUP_TABLE / FC_TO_NHG_INDEX_MAP_TABLE

現時点の sonic-swss コード上、これら 2 テーブルへの `ProducerStateTable` 書き込みは `fpmsyncd` 以外のデーモンからは確認されない。orchagent 内の Consumer に対応するプロデューサーはテスト (`test_nhg.py` L216-217) が手動で ProducerStateTable を使って書き込む形になっている。本番環境での書き込み元は CBF/FC NHG のサポートを行う上位制御プレーン (BGP 制御ソフトウェア等) であり、`ProducerStateTable` 経由で APPL_DB へ書き込むことが期待される (`orchdaemon.cpp:339`, `orchdaemon.cpp:490` で Consumer として登録済み)。

---

## 2. 消費側 (Consumer) — orchagent

### 2.1 NhgOrch

`orchdaemon.cpp` L338:

```cpp
gNhgOrch = new NhgOrch(m_applDb, APP_NEXTHOP_GROUP_TABLE_NAME);
```

`NhgOrch` は `NhgOrchCommon<NextHopGroup>` を継承し、`NhgOrchCommon` は `Orch(db, tableName)` 基底クラスを呼ぶ (`nhgbase.h:404`)。`Orch` コンストラクタは `ConsumerStateTable` を生成して `addExecutor()` で登録する。`ProducerStateTable` の PUBLISH イベントを受信すると `doTask(Consumer&)` が呼ばれる (`nhgorch.cpp:37`)。

### 2.2 CbfNhgOrch

`orchdaemon.cpp` L339:

```cpp
gCbfNhgOrch = new CbfNhgOrch(m_applDb, APP_CLASS_BASED_NEXT_HOP_GROUP_TABLE_NAME);
```

同様に `ConsumerStateTable` で `CLASS_BASED_NEXT_HOP_GROUP_TABLE` を購読。`doTask(Consumer&)` (`cbfnhgorch.cpp:38`) で処理。

### 2.3 NhgMapOrch

`orchdaemon.cpp` L490:

```cpp
gNhgMapOrch = new NhgMapOrch(m_applDb, APP_FC_TO_NHG_INDEX_MAP_TABLE_NAME);
```

`FC_TO_NHG_INDEX_MAP_TABLE` を `ConsumerStateTable` で購読。`doTask(Consumer&)` (`nhgmaporch.cpp:37`) で処理。

### 2.4 orchagent 主ループのタイムアウト

`orchdaemon.cpp` L23, L959:

```cpp
#define SELECT_TIMEOUT 1000   // ミリ秒
ret = m_select->select(&s, SELECT_TIMEOUT);
```

orchagent は 1000 ms タイムアウトで `Select::select` を回す。タイムアウト時に pipeline flush と `executeTasks()` を呼ぶ (`orchdaemon.cpp:981`)。NhgOrch 固有のリトライ interval はなく、`allPortsReady()` が false の場合は即 return してイベントは `m_toSync` に残される。

### 2.5 orchList 内の処理順

`orchdaemon.cpp` L500:

```cpp
m_orchList = { ..., gNhgMapOrch, gNhgOrch, gCbfNhgOrch, ... };
```

`NhgMapOrch` → `NhgOrch` → `CbfNhgOrch` の順で `executeTasks()` が呼ばれる。同一 select イベント処理サイクル内で FC_TO_NHG_INDEX_MAP → NEXTHOP_GROUP → CLASS_BASED_NEXT_HOP_GROUP の順に消費が試みられるため、同一サイクルで投入された場合でも正しい依存解決が期待できる。

---

## 3. 通信経路サマリ

| 経路 | DB | チャンネル / テーブル | 書き込み元 | 消費者 |
|------|-----|---------------------|-----------|--------|
| FRR/Zebra → fpmsyncd | n/a | kernel netlink | FRR zebra | fpmsyncd RouteSync |
| fpmsyncd → APPL_DB | 0 | `NEXTHOP_GROUP_TABLE_CHANNEL@0` | ProducerStateTable | NhgOrch (ConsumerStateTable) |
| 上位制御プレーン → APPL_DB | 0 | `CLASS_BASED_NEXT_HOP_GROUP_TABLE_CHANNEL@0` | ProducerStateTable | CbfNhgOrch (ConsumerStateTable) |
| 上位制御プレーン → APPL_DB | 0 | `FC_TO_NHG_INDEX_MAP_TABLE_CHANNEL@0` | ProducerStateTable | NhgMapOrch (ConsumerStateTable) |
| NhgOrch → SAI / ASIC_DB | n/a | `sai_next_hop_group_api` | syncd 経由 | ASIC |

NotificationConsumer / ResponsePublisher / FLEX_COUNTER_DB は 3 オーケストレータのいずれにも使用されていない。

---

## 参照

- `sonic-swss/fpmsyncd/routesync.cpp` L157, L1882, L3370, L3400-3419
- `sonic-swss/orchagent/orchdaemon.cpp` L23, L338-339, L490, L500, L959
- `sonic-swss/orchagent/nhgbase.h` L398-404 (NhgOrchCommon)
- `sonic-swss/orchagent/nhgorch.cpp` L37 (doTask)
- `sonic-swss/orchagent/cbf/cbfnhgorch.cpp` L38 (doTask)
- `sonic-swss/orchagent/cbf/nhgmaporch.cpp` L37 (doTask)
