# counter-buffer Phase A — implicit defaults (code-derived)

Generated: 2026-05-15  
Target doc: docs/reference/config-db/counter-buffer.md

## Field-by-field analysis

### ポーリング間隔のハードコードデフォルト

各バッファカウンタグループのポーリング間隔は `portsorch.cpp` / `portsorch.h` / `bufferorch.h` にハードコードされており、`FLEX_COUNTER_TABLE` の `POLL_INTERVAL` が未設定の場合この値が syncd に投入される。

| 検出種類 | 詳細 |
|---------|------|
| ハードコード固定値 | `QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS = 10000` (portsorch.cpp:90) → Queue Stats グループ |
| ハードコード固定値 | `QUEUE_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS = 60000` (portsorch.cpp:91) → Queue WM グループ |
| ハードコード固定値 | `PG_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS = 60000` (portsorch.cpp:92) → PG WM グループ |
| ハードコード固定値 | `PG_DROP_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS = 10000` (portsorch.cpp:93) → PG Drop グループ |
| ハードコード固定値 | `PORT_BUFFER_DROP_STAT_POLLING_INTERVAL_MS = 60000` (portsorch.cpp:88) → Port Buffer Drop グループ |
| ハードコード固定値 | `BUFFER_POOL_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS = "60000"` (bufferorch.h:16) → Buffer Pool WM グループ |
| WRED グループ | WRED_ECN_QUEUE_STAT_COUNTER は QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS と同値 (10000ms) を使用 (portsorch.cpp:739) |
| CLI との一致 | すべてのグループで counterpoll デフォルト値とハードコード値が一致。乖離なし |

### StatsMode::READ_AND_CLEAR の暗黙動作

| 検出種類 | 詳細 |
|---------|------|
| コード由来デフォルト | QUEUE_WATERMARK_STAT_COUNTER と PG_WATERMARK_STAT_COUNTER は `StatsMode::READ_AND_CLEAR` で初期化 (portsorch.cpp:735-736)。SAI 読取後に HW カウンタがリセットされる。YANG / CLI ドキュメントに記載なし |
| 条件付き動作 | BUFFER_POOL_WATERMARK: 各プールで `clear_buffer_pool_stats` SAI API を試行。未対応は READ に降格 (bufferorch.cpp:318-324) |
| 累積カウンタ | QUEUE_STAT / PG_DROP / PORT_BUFFER_DROP は READ のみ。ゼロリセットなし |

### DEFAULT_TELEMETRY_INTERVAL の暗黙値

| 検出種類 | 詳細 |
|---------|------|
| ハードコードデフォルト | `DEFAULT_TELEMETRY_INTERVAL = 120` 秒 (watermarkorch.cpp:9)。PERIODIC_WATERMARKS テーブルのリセット間隔 |
| 上書き可能 | `CONFIG_DB WATERMARK_TABLE|TELEMETRY_INTERVAL: {interval: <秒>}` で変更可能 |
| YANG default 外 | YANG に `default` 宣言なし。counterpoll show に "120" と表示されるのもコード由来 |

### Lua plugin の nil fallback (初期ウォーターマーク値)

| 検出種類 | 詳細 |
|---------|------|
| コード由来デフォルト | watermark_pg.lua:36 / watermark_queue.lua / watermark_bufferpool.lua で `periodic_shared_wm and math.max(...) or pg_shared_wm` パターン。テーブルエントリが nil の場合 max() をスキップし SAI 実測値をそのまま書き込む |
| 意味 | 初回測定値が自動的に初期ウォーターマーク最大値になる。クリア後は "0" が書かれ次の測定から積算 |

### WRED Queue カウンタの SAI 能力ガード

| 検出種類 | 詳細 |
|---------|------|
| コード由来条件 | `sai_query_stats_capability()` で WRED 対応を確認 (portsorch.cpp:1882-1909)。未対応 SAI フィールドは wred_queue_stat_ids から除外。SAI API 自体が未対応 (`NOT_SUPPORTED`) なら全 WRED フィールドをスキップ |
| 乖離なし | 除外時に LOG_NOTICE を出力するため silent ではないが、YANG は能力ガードの存在を記述していない |

### PORT_BUFFER_DROP_STAT_POLLING_INTERVAL_MS の二重定数問題

| 検出種類 | 詳細 |
|---------|------|
| 実装乖離 | `portsorch.cpp:88` の `PORT_BUFFER_DROP_STAT_POLLING_INTERVAL_MS = 60000` と counterpoll CLI が FLEX_COUNTER_TABLE に書く 30000ms は別定数。未設定時は orchagent ハードコード 60000ms が有効。counterpoll が上書きすれば 30000ms になる |

## 検出された discrepancy / 暗黙挙動まとめ

1. **READ_AND_CLEAR の非明示**: YANG / HLD にウォーターマーク系が READ_AND_CLEAR であることが記述されていない。SAI HW カウンタが自動リセットされることを知らないと「なぜウォーターマーク値が定期的に 0 になるのか」が不明。
2. **Buffer Pool clear 能力差異**: プラットフォームによって `clear_buffer_pool_stats` が対応していない場合、ウォーターマークが単調増加し続ける。エラーは LOG_NOTICE のみで運用的な通知はない。
3. **PORT_BUFFER_DROP の二重間隔**: orchagent ハードコード 60000ms と counterpoll デフォルト 30000ms が別定数として共存。どちらが有効かは FLEX_COUNTER_TABLE への書き込み有無次第。
4. **Lua nil fallback**: 初回起動直後はすべてのウォーターマークテーブルが空（nil）のため、最初の SAI ポーリング値がそのまま PERIODIC/PERSISTENT/USER に書き込まれる。これは正常動作だが YANG に記述なし。

## 書き込み経路サマリ

| 経路 | 対象テーブル | 詳細 |
|------|------------|------|
| portsorch init | COUNTERS_QUEUE_NAME_MAP, COUNTERS_PG_NAME_MAP | 名前→OID マッピング |
| syncd FlexCounter (QUEUE_STAT) | COUNTERS:<oid> | 10000ms ポーリング、READ |
| syncd FlexCounter (PG_DROP) | COUNTERS:<oid> | 10000ms ポーリング、READ |
| syncd FlexCounter (PORT_BUFFER_DROP) | COUNTERS:<oid> | 60000ms ポーリング、READ |
| syncd Lua (QUEUE_WATERMARK) | *_WATERMARKS:<oid> | 60000ms READ_AND_CLEAR + max 集計 |
| syncd Lua (PG_WATERMARK) | *_WATERMARKS:<oid> | 60000ms READ_AND_CLEAR + max 集計 |
| bufferorch + Lua (BUFFER_POOL_WATERMARK) | *_WATERMARKS:<oid> | 60000ms + max 集計 |
| watermarkorch timer | PERIODIC_WATERMARKS | 120s 周期ゼロリセット |
| WATERMARK_CLEAR_REQUEST notification | PERSISTENT/USER_WATERMARKS | ユーザー/persistent クリア (フィールドを "0" に) |
