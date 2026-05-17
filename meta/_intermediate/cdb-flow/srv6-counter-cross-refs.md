# FLEX_COUNTER_TABLE SRV6 — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/srv6-counter.md` Phase C 追加分。
YANG `sonic-flex_counter.yang` の `SRV6` container には leafref 定義が一切ない。
よって以下は全て実装レベルの暗黙参照となる。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/srv6orch.cpp` | `initializeCounters()` / `setCountersState()` / `doTask(SelectableTimer)` — カウンタ OID 管理・DB 参照 |
| `sonic-swss/orchagent/flexcounterorch.cpp` | `doTask(Consumer)` — `FLEX_COUNTER_TABLE|SRV6` の値変化を検知し `gSrv6Orch->setCountersState()` を呼び出す |
| `sonic-swss/orchagent/flex_counter/flow_counter_handler.cpp` | `getGenericCounterStatIdList()` — 収集 stat リストを返す |
| `sonic-swss-common/common/schema.h` | `COUNTERS_SRV6_NAME_MAP` / `SRV6_COUNTER_ID_LIST` 定数 |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-flex_counter.yang` | SRV6 container 定義 (leafref なし) |

## YANG leafref

`FLEX_COUNTER_TABLE.SRV6` は leafref なし。以下の参照は全て実装レベルの暗黙参照。

## 暗黙参照 (実装レベル)

### 1. SRV6_MY_SIDS テーブル（APP_SRV6_MY_SID_TABLE / CFG_SRV6_MY_SID_TABLE）

- **参照先テーブル**: APPL_DB `APP_SRV6_MY_SID_TABLE_NAME` / CONFIG_DB `CFG_SRV6_MY_SID_TABLE_NAME`
- **参照方向**: 走査・OID 管理（カウンタ作成/削除のトリガー）
- **条件**: `FLEX_COUNTER_STATUS = enable` / `disable` 切り替え時
- **参照元**: `srv6orch.cpp:268` — `setCountersState()` が `srv6_my_sid_table_` を全走査し `addMySidCounter()` / `removeMySidCounter()` を呼ぶ
- **意味**: FLEX_COUNTER_TABLE|SRV6 の enable/disable は SRV6_MY_SIDS に登録済みの全 MySID エントリに対して SAI カウンタ OID の生成・削除を行う。MySID が存在しない状態で enable を書いても副作用は発生しない（空走査）。

### 2. COUNTERS_DB（COUNTERS_SRV6_NAME_MAP）

- **参照先 DB / テーブル**: `COUNTERS_DB` の `COUNTERS_SRV6_NAME_MAP` テーブル（`schema.h:257`）
- **参照方向**: 書き込み（SID 文字列 → counter OID マッピング追加/削除）
- **条件**: `addMySidCounter()` 呼び出し時 / `removeMySidCounter()` 呼び出し時
- **参照元**: `srv6orch.cpp:131` (`m_mysid_counters_table = make_unique<Table>(m_counter_db.get(), COUNTERS_SRV6_NAME_MAP)`) / `srv6orch.cpp:199` (`m_mysid_counters_table->set(...)`) / `srv6orch.cpp:223` (`m_mysid_counters_table->hdel(...)`)
- **意味**: `COUNTERS_SRV6_NAME_MAP` に SID → counter OID の対応を書き込む。CLI (`show srv6` / `sonic-clear srv6`) はこのマッピングを参照してカウンタ値を表示・クリアする。

### 3. FLEX_COUNTER_DB（SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP）

- **参照先 DB / テーブル**: `FLEX_COUNTER_DB` の `FLEX_COUNTER_TABLE|SRV6_STAT_COUNTER|<oid>` エントリ
- **参照方向**: 書き込み（counter OID リスト登録）
- **条件**: `doTask(SelectableTimer)` でペンディング OID が ASIC_DB に登録済みと確認できた時点
- **参照元**: `srv6orch.cpp:300` (`m_counter_manager.setCounterIdList(it->first, CounterType::SRV6, counter_stats)`) / `srv6orch.cpp:229` (`m_counter_manager.clearCounterIdList(counter_oid)`)
- **意味**: `FlexCounterManager` 経由で syncd の `FlexCounter` が参照する `SRV6_COUNTER_ID_LIST` (`schema.h:313`) を書き込む。syncd はこのリストに基づき SAI `sai_counter_api` を周期呼び出しし収集結果を `COUNTERS_DB` に蓄積する。

### 4. ASIC_DB（VIDTORID — gTraditionalFlexCounter 時のみ）

- **参照先 DB / テーブル**: `ASIC_DB` の `VIDTORID` テーブル
- **参照方向**: 読み取り（VID → RID 変換確認）
- **条件**: `gTraditionalFlexCounter == true` かつ `doTask(SelectableTimer)` での OID 登録処理時
- **参照元**: `srv6orch.cpp:134–136` (`m_vid_to_rid_table = make_unique<Table>(m_asic_db.get(), "VIDTORID")`) / `srv6orch.cpp:294` (`m_vid_to_rid_table->hget("", oid, value)`)
- **意味**: Traditional FlexCounter モード（非 gRPC モード）では、counter OID が ASIC_DB に存在することを確認してから FLEX_COUNTER_DB に登録する。`VIDTORID` に OID が存在しない場合はペンディングキューに残し次回タイマーで再試行する。

### 5. SAI（sai_counter_api — SAI_OBJECT_TYPE_COUNTER）

- **参照先**: SAI の `sai_counter_api`（`SAI_OBJECT_TYPE_COUNTER` 操作）
- **参照方向**: SAI API 呼び出し（create / remove / attribute set）
- **条件**: `addMySidCounter()` / `removeMySidCounter()` / `setMySidEntryCounter()` 呼び出し時
- **参照元**: `srv6orch.cpp` 内の SAI counter create/remove/attr set 呼び出し群
- **意味**: `SAI_OBJECT_TYPE_COUNTER` を作成し `SAI_MY_SID_ENTRY_ATTR_COUNTER_ID` で MySID エントリにアタッチする。プラットフォームが `capability.set_implemented && capability.create_implemented` でない場合は `queryMySidCountersCapability()` が false を返し SAI 呼び出し自体が行われない。

## 参照関係サマリ

```
FLEX_COUNTER_TABLE|SRV6
  ├─ [暗黙] SRV6_MY_SIDS (APPL_DB / CONFIG_DB)   (enable/disable 時に全走査・カウンタ OID 管理)
  ├─ [暗黙] COUNTERS_DB.COUNTERS_SRV6_NAME_MAP    (SID → counter OID マッピング書き込み)
  ├─ [暗黙] FLEX_COUNTER_DB.SRV6_STAT_COUNTER_*   (syncd 向け counter OID リスト書き込み)
  ├─ [暗黙] ASIC_DB.VIDTORID                      (gTraditionalFlexCounter 時のみ OID 存在確認)
  └─ [SAI]  sai_counter_api (SAI_OBJECT_TYPE_COUNTER) (MySID カウンタ作成・削除・アタッチ)
```

## evidence

- `srv6orch.cpp`: L120–142 (`initializeCounters()`), L144–155 (`queryMySidCountersCapability()`), L199 (`m_mysid_counters_table->set()`), L223 (`m_mysid_counters_table->hdel()`), L229 (`clearCounterIdList()`), L251–283 (`setCountersState()`), L286–313 (`doTask(SelectableTimer)`), L294 (`VIDTORID hget`), L300 (`setCounterIdList()`)
- `flexcounterorch.cpp`: L337–340 (`gSrv6Orch->setCountersState()`)
- `schema.h`: L257 (`COUNTERS_SRV6_NAME_MAP`), L313 (`SRV6_COUNTER_ID_LIST`)
- `sonic-flex_counter.yang`: L465–484 (SRV6 container — leafref なし)
