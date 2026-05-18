# nat-counters Phase D — 失敗挙動スキャンノート

Generated: 2026-05-18
Target doc: docs/reference/config-db/nat-counters.md

対象テーブル: `COUNTERS_DB:COUNTERS_NAT / COUNTERS_NAPT / COUNTERS_TWICE_NAT / COUNTERS_TWICE_NAPT / COUNTERS_GLOBAL_NAT`
Consumer: `orchagent/NatOrch`
スキャン範囲: `natorch.cpp` 全行、`orchdaemon.cpp` NatOrch 初期化部分、`main.cpp` gIsNatSupported 設定箇所

---

## 検出した失敗挙動

### 1. SAI `create_nat_entry` 失敗 → カウンタエントリ不在

`addHwDnatEntry()` / `addHwSnatEntry()` / `addHwTwiceNatEntry()` 等が `sai_nat_api->create_nat_entry()` で失敗した場合、`parseHandleSaiStatusFailure()` が `false` を返して即 return。`updateNatCounters()` は呼ばれないため COUNTERS_DB に該当エントリが存在しない。

evidence: `natorch.cpp:774-783` (addHwDnatEntry), `natorch.cpp:1307-1316` (addHwSnatEntry), `natorch.cpp:856-865` (addHwDnaptEntry)

### 2. SAI `get_nat_entry_attribute` 失敗 → カウンタが 0 にリセット

`getNatCounters()` / `getTwiceNatCounters()` / `getNaptCounters()` が 5 秒周期ポーリング中に SAI から `get_nat_entry_attribute` を取得失敗した場合、`nat_translations_pkts = 0, nat_translations_bytes = 0` のまま `updateNatCounters()` を呼ぶ。結果として COUNTERS_DB の `NAT_TRANSLATIONS_PKTS` / `NAT_TRANSLATIONS_BYTES` が `"0"` に上書きされる。前回の正常値は失われる。

evidence: `natorch.cpp:3546-3574` (getNatCounters), `natorch.cpp:3609-3623` (getTwiceNatCounters)

### 3. `gIsNatSupported=false` → タイマー未起動 → 周期ポーリング停止

`gIsNatSupported` が `false` の場合 `enableNatFeature()` が即 return し `m_natQueryTimer->start()` に到達しない。タイマーが起動しないため `queryCounters()` は永遠に呼ばれず、COUNTERS_NAT エントリはエントリ追加時の 0 初期化から更新されない。

evidence: `natorch.cpp:2541-2544`, `natorch.cpp:2564-2565`

### 4. `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` クエリ失敗 → `MAX_NAT_ENTRIES="0"` → NAT 全体無効

NatOrch コンストラクタでの SAI switch attribute クエリが失敗した場合 `maxAllowedSNatEntries=0` のまま `COUNTERS_GLOBAL_NAT|Values.MAX_NAT_ENTRIES="0"` が書き込まれる。`main.cpp:945-948` で `attr.value.u32 != 0` の条件を満たさず `gIsNatSupported=false` となり NAT 機能全体が無効化される。

evidence: `natorch.cpp:115-135`, `main.cpp:940-948`

### 5. DNAT ネクストホップ未解決 → `addedToHw=false` → カウンタ取得スキップ

`gNhTrackingSupported=true` のプラットフォームで DNAT エントリの nexthop が未解決の場合、`addHwDnatEntry()` が呼ばれず `entry.addedToHw == false` のまま。`getNatCounters()` 冒頭の `if (entry.addedToHw == false) return 0;` により SAI クエリをスキップ。COUNTERS_NAT エントリはゼロ初期化値 (または不在) のまま。

evidence: `natorch.cpp:3517-3521`, `natorch.cpp:1921-1940` (NH cache path)

### 6. `clearCounters()` (FLUSHNATSTATISTICS) 中の SAI `reset` 失敗

`clearCounters()` が SAI で `NAT_ENTRY_ATTR_PACKET_COUNT` / `BYTE_COUNT` をリセット中に失敗した場合、`SWSS_LOG_ERROR` を出力するが処理は継続する。COUNTERS_DB のカウンタは更新されず前回値が残る。

evidence: `natorch.cpp:3271-3303` (clearCounters)

### 7. `clock_gettime` 失敗 → `queryCounters` 早期 return

`queryCounters()` 冒頭の `clock_gettime(CLOCK_MONOTONIC, &time_now) < 0` が失敗した場合 即 return し、その周期はカウンタ更新が完全にスキップされる。次の 5 秒周期で再試行される。

evidence: `natorch.cpp:3125-3128`
