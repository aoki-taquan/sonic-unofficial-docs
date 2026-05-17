# srv6-state — Phase B 書込み順依存調査メモ

## 対象ページ

`docs/reference/config-db/srv6-state.md`  
(COUNTERS_DB SRv6 MySID: `COUNTERS_SRV6_NAME_MAP` / `COUNTERS:<oid>`)

## 調査ソース

| ファイル | ref |
|---------|-----|
| `sonic-swss/orchagent/srv6orch.cpp` | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `sonic-swss/orchagent/srv6orch.h` | 4305596156d70e9797e8a881b3d19b46de0bce0d |

---

## 検出した順序依存・タイミング依存

### 1. SAI 能力チェックは起動時一回限り (initializeCounters)

`Srv6Orch::initializeCounters()` (srv6orch.cpp:120-132) が orchagent 起動時に一度だけ
`queryMySidCountersCapability()` を呼び、`m_mysid_counters_supported` を確定する。

```cpp
void Srv6Orch::initializeCounters() {
    m_mysid_counters_supported = queryMySidCountersCapability();
    if (!m_mysid_counters_supported) { return; }
    m_mysid_counters_table = make_unique<Table>(m_counter_db.get(), COUNTERS_SRV6_NAME_MAP);
    ...
}
```

**順序依存**: `m_mysid_counters_supported = false` の状態で orchagent が起動した場合、
後から `FLEX_COUNTER_TABLE|SRV6` に `enable` を書いても
`setCountersState()` 冒頭の `getMySidCountersSupported()` チェックで即 return し、
`COUNTERS_SRV6_NAME_MAP` は生成されない。
**再起動なしで能力状態を変更することは不可能**。

evidence: `srv6orch.cpp:120-132`, `srv6orch.cpp:251-260`

---

### 2. FLEX_COUNTER_STATUS=enable が MySID 登録より先でも後でも可

`setCountersState(true)` (srv6orch.cpp:251-284) は `srv6_my_sid_table_` を走査し、
**その時点で存在するすべての MySID エントリ**に対してカウンタを作成する。

```cpp
void Srv6Orch::setCountersState(bool enable) {
    ...
    for (auto& mysid : srv6_my_sid_table_) {
        if (enable) {
            addMySidCounter(sai_entry, counter_oid);
            setMySidEntryCounter(sai_entry, counter_oid);
        }
        ...
    }
}
```

逆に、MySID エントリが `enable` より先に登録された場合も、
`createUpdateMysidEntry` (srv6orch.cpp:1591-1601) の中で
`getMySidCountersEnabled()` が true であれば `addMySidCounter()` を呼ぶ。

```cpp
if (getMySidCountersSupported() && getMySidCountersEnabled()) {
    auto ok = addMySidCounter(my_sid_entry, counter_oid);
}
```

**順序依存なし**: `FLEX_COUNTER_TABLE|SRV6 enable` と `SRV6_MY_SID_TABLE` エントリの
書き込み順序はどちらが先でも最終的に `COUNTERS_SRV6_NAME_MAP` に反映される。

evidence: `srv6orch.cpp:1591-1601`, `srv6orch.cpp:268-282`

---

### 3. COUNTERS_SRV6_NAME_MAP への書き込みは addMySidCounter 内で即時

`addMySidCounter()` (srv6orch.cpp:184-210):
1. SAI カウンタオブジェクト作成 (`FlowCounterHandler::createGenericCounter`)
2. `m_mysid_counters_table->set("", fvs)` で `COUNTERS_SRV6_NAME_MAP` に即時書き込み
3. `m_pending_counters[counter_oid] = key` でペンディングキューに追加
4. タイマーが停止中なら `m_counter_update_timer->start()` で開始

`COUNTERS_SRV6_NAME_MAP` への書き込みは SAI カウンタ作成と同時（即時）だが、
`FLEX_COUNTER_DB` への `SRV6_COUNTER_ID_LIST` 登録（= syncd がポーリング開始する条件）は
`SRV6_FLEX_COUNTER_UPDATE_TIMER = 1` 秒後のタイマーコールバックで行われる。

**タイミング依存**:
- `COUNTERS_SRV6_NAME_MAP` への OID 書き込み: 即時（MySID 追加直後）
- `COUNTERS:<oid>` への最初のカウンタ値反映: `FLEX_COUNTER_DB` 登録（≦1秒）後、
  さらに `SRV6_STAT_COUNTER_POLLING_INTERVAL_MS = 10000` ms の初回ポーリング待ちが必要。
- MySID 追加から最初の `COUNTERS:<oid>` 書き込みまで最大 **1 + 10 = 11 秒**の遅延がある。

evidence: `srv6orch.cpp:184-210`, `srv6orch.cpp:286-313`, `srv6orch.cpp:26-27`

---

### 4. MySID 削除時の COUNTERS_DB クリーンアップ順序

`deleteMysidEntry()` (srv6orch.cpp:1660-1680):
1. SAI `my_sid_entry` 削除
2. `removeMySidCounter()` 呼び出し
   - `FLEX_COUNTER_DB` から `SRV6_COUNTER_ID_LIST` エントリ削除
   - SAI カウンタオブジェクト削除
   - `m_mysid_counters_table->hdel("", key)` で `COUNTERS_SRV6_NAME_MAP` から削除

**順序依存**: `COUNTERS_SRV6_NAME_MAP` からのエントリ削除は MySID の DEL 操作後に自動で行われる。
ユーザーが手動で `COUNTERS_SRV6_NAME_MAP` を操作する必要はない。
`COUNTERS:<oid>` ハッシュ自体は削除されず（syncd がポーリングを停止するだけ）、
古い値が残る場合がある。`sonic-clear srv6stats` でキャッシュをクリアすること。

evidence: `srv6orch.cpp:212-230`, `srv6orch.cpp:1668-1680`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | SAI 能力チェックは orchagent 起動時一回限り | **強制先行**（後変更不可） | SAI 非対応なら orchagent 再起動しか解消手段なし |
| 2 | `FLEX_COUNTER_TABLE\|SRV6 enable` と `SRV6_MY_SID_TABLE` の順序 | どちらが先でも可 | 後から書いた側が自動的に既存エントリへカウンタを付与 |
| 3 | `COUNTERS_SRV6_NAME_MAP` 書き込みは即時だが `COUNTERS:<oid>` 初回値は 最大11秒遅延 | タイミング依存 | 設定直後に `show srv6 stats` が空でも正常 |
| 4 | MySID DEL → `COUNTERS_SRV6_NAME_MAP` 自動クリーンアップ | 自動（ユーザー操作不要） | `COUNTERS:<oid>` 残留値は `sonic-clear srv6stats` でリセット |
