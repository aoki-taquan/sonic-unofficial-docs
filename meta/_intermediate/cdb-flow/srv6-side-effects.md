# Srv6Orch (APP_DB SRV6) — Phase F 副次 DB 書込 中間ファイル

生成日: 2026-05-16
ソース: `sonic-swss/orchagent/srv6orch.cpp` (rev 4305596156d70e9797e8a881b3d19b46de0bce0d)
主要関数: `addMySidCounter`, `removeMySidCounter`, `setCountersState`, `doTask(SelectableTimer&)`, `createMysidEntry`, `deleteMysidEntry`

---

## 概要

`Srv6Orch` が APP_DB (`SRV6_SID_LIST_TABLE` / `SRV6_MY_SID_TABLE` / `PIC_CONTEXT_TABLE`) の変化を処理すると、以下の副次 DB へ書き込みが波及する。

| 副次 DB | テーブル / マップ | 操作 | トリガ |
|---------|----------------|------|--------|
| ASIC_DB | `VIDTORID` | hget (読み取りのみ) | gTraditionalFlexCounter 有効時: counter OID の VID→RID 解決待ち |
| COUNTERS_DB | `COUNTERS_SRV6_NAME_MAP` | set / hdel | MY_SID エントリ追加/削除 + counters 有効時 |
| FLEX_COUNTER_DB | `SRV6_STAT_COUNTER:<oid>` | set / del | counter OID が ASIC_DB に反映済み（VID→RID 解決後）に登録 |
| CRM (in-memory) | `CRM_SRV6_MY_SID_ENTRY` カウンタ | inc / dec | MY_SID エントリ SAI 作成/削除成功後 |

---

## 1. COUNTERS_DB / `COUNTERS_SRV6_NAME_MAP`

`addMySidCounter()` (`srv6orch.cpp:184-210`) が書き込む。

```cpp
// srv6orch.cpp:196-199
vector<FieldValueTuple> fvs = {
    {key, sai_serialize_object_id(counter_oid)}
};
m_mysid_counters_table->set("", fvs);
```

- **テーブル**: `COUNTERS_SRV6_NAME_MAP`（`schema.h:257` で定義）
- **hash フィールド**: `getMySidCounterKey(sai_entry)` が返す文字列（My SID プレフィックス形式。例: `fc00:0:1:1::/64`）
- **値**: SAI SAI counter OID のシリアライズ文字列

### DEL

`removeMySidCounter()` (`srv6orch.cpp:211-234`) が `m_mysid_counters_table->hdel("", key)` で削除する。

### 条件

- `getMySidCountersSupported()` かつ `getMySidCountersEnabled()` が両方 true の場合のみ。
- 起動時に `sai_query_attribute_capability()` (`srv6orch.cpp:147`) が SAI の counter 能力を確認し、非対応プラットフォームでは全 counter 機能が無効化される。

---

## 2. FLEX_COUNTER_DB / `SRV6_STAT_COUNTER:<oid>`

`m_counter_manager.setCounterIdList()` (`srv6orch.cpp:300`) 経由で書き込まれる。

- **グループ**: `SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP = "SRV6_STAT_COUNTER"` (`srv6orch.h:30`)
- **stat リスト**: `FlowCounterHandler::getGenericCounterStatIdList()` が返す `SAI_COUNTER_STAT_PACKETS` / `SAI_COUNTER_STAT_BYTES` の 2 stat（固定）
- **ポーリング間隔**: `SRV6_STAT_COUNTER_POLLING_INTERVAL_MS = 10000` ms（10秒）

### 遅延登録メカニズム

MY_SID 追加直後は counter OID を `m_pending_counters` に積み、`SRV6_FLEX_COUNTER_UPDATE_TIMER = 1` 秒タイマー (`srv6orch.cpp:138`) が満了するたびに `doTask(SelectableTimer&)` を実行する。`gTraditionalFlexCounter` 有効時は ASIC_DB `VIDTORID` で VID→RID 変換が確認できた OID のみ登録し、未解決分は次のタイマー周期に持ち越す。`m_pending_counters` が空になるとタイマーは自動停止する。

### DEL

`m_counter_manager.clearCounterIdList()` (`srv6orch.cpp:229`) で FLEX_COUNTER_DB エントリを削除。

---

## 3. ASIC_DB / `VIDTORID`

`gTraditionalFlexCounter` が有効な場合のみ、`m_vid_to_rid_table->hget("", oid, value)` (`srv6orch.cpp:294`) で **読み取り専用** アクセスする。SAI から取得した counter OID が syncd によって ASIC_DB に反映済みかを確認するための poll。書き込みは行わない。

実際の ASIC_DB への書き込みは SAI API (`sai_srv6_api->create_my_sid_entry()` / `create_srv6_sidlist()`) 呼び出しを受けた syncd プロセスが担う。

---

## 4. CRM カウンタ更新

`gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_SRV6_MY_SID_ENTRY)` (`srv6orch.cpp:1612`) が MY_SID 作成成功後に、`decCrmResUsedCounter` (`srv6orch.cpp:1675`) が削除成功後に呼ばれる。CRM カウンタは in-process メモリ内で管理され、`CrmOrch` が定期的に COUNTERS_DB の `CRM_STATS` / `CRM_ACL_STATS` テーブルに書き出す（`crmorch.cpp` 側の責務）。

---

## フロー概要

```
APP_DB SRV6_MY_SID_TABLE (set)
  └─► Srv6Orch::createMysidEntry()
        ├─ sai_srv6_api->create_my_sid_entry()
        │    └─► syncd → ASIC_DB (VIDTORID 等, 非同期)
        ├─ gCrmOrch->incCrmResUsedCounter(CRM_SRV6_MY_SID_ENTRY)
        └─ addMySidCounter()  [counters enabled 時のみ]
             ├─ COUNTERS_DB COUNTERS_SRV6_NAME_MAP hset(sid_prefix, counter_oid)
             └─ m_pending_counters に追加 → 1秒タイマー起動
                  └─ doTask(timer): VID→RID 確認後
                       └─ FLEX_COUNTER_DB SRV6_STAT_COUNTER:<oid> set

APP_DB SRV6_MY_SID_TABLE (del)
  └─► Srv6Orch::deleteMysidEntry()
        ├─ sai_srv6_api->remove_my_sid_entry()
        │    └─► syncd → ASIC_DB (非同期)
        ├─ gCrmOrch->decCrmResUsedCounter(CRM_SRV6_MY_SID_ENTRY)
        └─ removeMySidCounter()
             ├─ COUNTERS_DB COUNTERS_SRV6_NAME_MAP hdel(sid_prefix)
             └─ FLEX_COUNTER_DB SRV6_STAT_COUNTER:<oid> del
```

---

## 注記

- `SRV6_SID_LIST_TABLE` / `PIC_CONTEXT_TABLE` の処理では counter 管理・CRM 更新は行われない（MY_SID 専用）。
- `SRV6_MY_SID_TABLE` の counter 機能は `SRV6_MY_SID_COUNTER|state` (CONFIG_DB or flexcounterorch 経由) の `enable=true` 設定が必要（`setCountersState()` `srv6orch.cpp:255-304` を参照）。
