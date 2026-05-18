# counters-portchannel Phase G — Redis 通知メカニズム スキャンノート

Generated: 2026-05-18
Target doc: docs/reference/config-db/counters-portchannel.md

対象テーブル: `COUNTERS_DB COUNTERS_LAG_NAME_MAP` / `COUNTERS_RIF_NAME_MAP` / `COUNTERS_RIF_TYPE_MAP`
書き込み元: `portsorch` (`m_counterLagTable` = swsscommon::Table) + `intfsorch` (`m_rifNameTable`, `m_rifTypeTable` = swsscommon::Table)
スキャン範囲: `portsorch.cpp:762`, `intfsorch.cpp:70-71`, `sonic-utilities/scripts/intfstat:77-130`, `sonic-utilities/scripts/vnet_route_check.py:114`

---

## 書き込み方式の確認

### swsscommon::Table vs ProducerStateTable

```cpp
// portsorch.cpp:762
m_counterLagTable = unique_ptr<Table>(new Table(m_counter_db.get(), COUNTERS_LAG_NAME_MAP));

// intfsorch.cpp:70-71
m_rifNameTable = unique_ptr<Table>(new Table(m_counter_db.get(), COUNTERS_RIF_NAME_MAP));
m_rifTypeTable = unique_ptr<Table>(new Table(m_counter_db.get(), COUNTERS_RIF_TYPE_MAP));
```

いずれも `swsscommon::Table` (直接 Redis HSET/HDEL) であり、`ProducerStateTable` ではない。
ProducerStateTable は書き込み時に `HMSET` + `PUBLISH <TABLE>_CHANNEL@<db_index>` を行うが、
`Table::set()` は HMSET のみ → **PUBLISH なし**。

---

## 消費側のアクセス方式

### intfstat (sonic-utilities/scripts/intfstat)

```python
# intfstat:123
counter_rif_name_map = self.db.get_all(self.db.COUNTERS_DB, COUNTERS_RIF_NAME_MAP)
```

`SonicV2Connector.get_all()` = HGETALL の 1 回呼び出し。起動時または `-p` (periodic) モードで定期実行。

### vnet_route_check.py

```python
# vnet_route_check.py:114
rif_table = swsscommon.Table(db, 'COUNTERS_RIF_NAME_MAP')
```

swsscommon::Table 経由の 1 回読み取り（スクリプト実行時のみ）。

### FlexCounter (syncd)

FlexCounter は `COUNTERS_RIF_NAME_MAP` を直接購読しない。`intfsorch::addRifToFlexCounter()` が
`FLEX_COUNTER_DB` の `RIF_STAT_COUNTER:<rif_oid>` に `RIF_COUNTER_ID_LIST` を書き込む（ProducerStateTable ではなく直接 Table）と、
FlexCounter が `FLEX_COUNTER_DB` の変化を検知してポーリングを開始する。
FlexCounter は COUNTERS_DB `COUNTERS:<rif_oid>` に収集結果を書き込む。

---

## keyspace notification 不使用の影響

- `COUNTERS_LAG_NAME_MAP` / `COUNTERS_RIF_NAME_MAP` への書き込みは Redis PUBLISH を発生させない
- 消費ツール（intfstat 等）はポーリング（起動時または定期実行）でアクセスする
- RIF 登録タイミングのズレ（addRifToFlexCounter 非同期呼び出し）の間に intfstat を実行すると "Interface missing" エラーになる

---

## 結論

Phase G として記載すべき内容:
- 書き込みは swsscommon::Table (直接 HSET)、ProducerStateTable 不使用 → PUBLISH なし
- 消費側はポーリング（HGETALL）アクセス
- FlexCounter は FLEX_COUNTER_DB 経由（間接的な副次登録）で COUNTERS:<rif_oid> を更新
