# counters-state — Phase H プラットフォーム / SAI Capability 差異 調査証跡

## 対象ページ
`docs/reference/config-db/counters-state.md`

## 調査ソース
- `sonic-swss/orchagent/portsorch.cpp` (initCounterCapabilities, lines 1850-1968)
- `sonic-swss/orchagent/debugcounterorch.cpp` (publishDropCounterCapabilities, lines 314-363)
- `sonic-swss/orchagent/debug_counter/drop_counter.cpp` (getSupportedDropReasons, getSupportedCounterTypes, lines 298-400)

## 発見した差異

### 1. WRED カウンタ能力 — ASIC 依存
`PORT_COUNTER_CAPABILITIES` と `QUEUE_COUNTER_CAPABILITIES` の `isSupported` フラグは SAI `sai_query_stats_capability()` 呼び出しの結果に完全依存する。

- WRED を実装している ASIC (Broadcom Tomahawk 系、Mellanox Spectrum 系など) では `isSupported="true"` が書き込まれる。
- WRED ハードウェアサポートのない ASIC (VS / sonic-vs や一部の廉価 ASIC) では `sai_query_stats_capability()` が `SAI_STATUS_SUCCESS` を返すが対象 enum が含まれないか、呼び出し自体が `SAI_STATUS_NOT_SUPPORTED` / `SAI_STATUS_BUFFER_OVERFLOW` で終わる。その場合、全フィールドが `"false"` のまま残る (portsorch.cpp:1963-1968)。
- VS (virtual switch) では SAI query が成功しても実際の WRED カウンタは 0 のまま。

### 2. DEBUG_COUNTER_CAPABILITIES — SAI debug counter 未サポート ASIC
`sai_query_attribute_enum_values_capability(SAI_OBJECT_TYPE_DEBUG_COUNTER, ...)` が失敗する ASIC では `getSupportedDropReasons()` が空集合を返し、`DEBUG_COUNTER_CAPABILITIES` テーブルにエントリが一切書き込まれない (drop_counter.cpp:305-315, 376-391)。

"This device does not support querying drop reasons" / "This device does not support querying drop counters" の SWSS_LOG_NOTICE が出力される。

### 3. SAI_STATUS_BUFFER_OVERFLOW の 2 段階クエリ
`sai_query_stats_capability()` が最初に count=0 / list=nullptr で呼ばれ `SAI_STATUS_BUFFER_OVERFLOW` が返ると、返却された `count` 値に基づいてバッファを確保して再クエリする。この動作は QUEUE・PORT 両方で実施。クエリ自体が `SAI_STATUS_BUFFER_OVERFLOW` でも `SAI_STATUS_SUCCESS` でもない場合 (例: `SAI_STATUS_NOT_IMPLEMENTED`) は全フィールドが `"false"` のまま (portsorch.cpp:1883-1895, 1930-1942)。

### 4. WRED カウンタ能力と portstat.py の連動
`portstat.py` は起動時に `PORT_COUNTER_CAPABILITIES` を参照し、`isSupported != "true"` のカウンタを `counter_bucket_dict` から除外する。プラットフォームによって表示される列数が異なる。

## 結論
これらのテーブルは純粋にプラットフォーム / SAI 実装の能力反映であり、CONFIG_DB 設定で制御できない。ASIC が WRED / debug counter をサポートするかどうかで STATE_DB の内容が根本的に異なる。
