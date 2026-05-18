# cbf-nhg Phase G — PUBSUB / Keyspace 通知メカニズム調査

## 調査対象

- テーブル: `APPL_DB CLASS_BASED_NEXT_HOP_GROUP_TABLE`
- 書き手 (producer): カスタムアプリケーション / 修正版 fpmsyncd (標準 fpmsyncd は非対応)
- 読み手 (consumer): `CbfNhgOrch` (`sonic-swss/orchagent/cbf/cbfnhgorch.cpp`)

## 書き込みメカニズム: ProducerStateTable

APPL_DB の `CLASS_BASED_NEXT_HOP_GROUP_TABLE` への書き込みは `swsscommon.ProducerStateTable` を使用する。
テスト (`sonic-swss/tests/test_nhg.py:216`) で確認:

```python
self.cbf_nhg_ps = swsscommon.ProducerStateTable(
    self.app_db.db_connection, swsscommon.APP_CLASS_BASED_NEXT_HOP_GROUP_TABLE_NAME)
```

`ProducerStateTable` は内部で EVALSHA スクリプトを実行し、`CLASS_BASED_NEXT_HOP_GROUP_TABLE_CHANNEL@0` チャンネルに PUBLISH を発行する。

## 読み取りメカニズム: ConsumerStateTable (Orch フレームワーク)

`CbfNhgOrch` は `Orch` 基底クラスを継承し、コンストラクタで `ConsumerStateTable` を自動生成する:

```cpp
// nhgbase.h:404
NhgOrchCommon(DBConnector *db, string tableName) : Orch(db, tableName) {}

// orch.cpp:1194
addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
```

`ConsumerStateTable` は `CLASS_BASED_NEXT_HOP_GROUP_TABLE_CHANNEL@0` を SUBSCRIBE し、
PUBLISH 受信時に `doTask(Consumer&)` を呼び出す。

## 通知フロー

```
ProducerStateTable::set() / del()
  ↓ EVALSHA → HSET APPL_DB + PUBLISH CLASS_BASED_NEXT_HOP_GROUP_TABLE_CHANNEL@0 <key>
Redis channel 通知
  ↓ ConsumerStateTable が受信 → m_toSync に追積
orchdaemon select() ループ
  ↓ CbfNhgOrch::doTask(Consumer&) 呼び出し
```

## 起動時スナップショット

`ConsumerStateTable` は起動時に既存の `_DEL:CLASS_BASED_NEXT_HOP_GROUP_TABLE:*` を含む
pending エントリを `pops()` で一括取得する。warm-reboot 時は orchdaemon が
`warmRestoreAndSyncUp()` で複数回ループを実行し既存エントリを再処理する。

## 他プロセスの購読

`CLASS_BASED_NEXT_HOP_GROUP_TABLE` を購読するプロセスは `CbfNhgOrch` のみ。
`show` コマンド等は APPL_DB を直接 `Table::get()` / `Table::getKeys()` で読む。

## 証跡

- `sonic-swss/orchagent/cbf/cbfnhgorch.cpp` L21-24 (コンストラクタ)
- `sonic-swss/orchagent/nhgbase.h` L404 (`NhgOrchCommon` コンストラクタ)
- `sonic-swss/orchagent/orch.cpp` L1194 (`ConsumerStateTable` 生成)
- `sonic-swss/tests/test_nhg.py` L216 (`ProducerStateTable` 使用例)
- `sonic-swss-common/common/schema.h` L56 (`APP_CLASS_BASED_NEXT_HOP_GROUP_TABLE_NAME`)
