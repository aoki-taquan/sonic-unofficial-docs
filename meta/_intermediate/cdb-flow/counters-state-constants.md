# counters-state — Phase E ハードコード定数スキャンノート

対象テーブル: `STATE_DB / PORT_COUNTER_CAPABILITIES`, `STATE_DB / QUEUE_COUNTER_CAPABILITIES`, `STATE_DB / DEBUG_COUNTER_CAPABILITIES`
スキャン範囲: orchagent/portsorch.cpp, orchagent/debugcounterorch.cpp, orchagent/debug_counter/drop_counter.cpp, orchagent/debug_counter/debug_counter.h, sonic-swss-common/common/schema.h

---

## 検出した定数一覧

### 1. STATE_DB テーブル名定数 (schema.h)

| 定数名 | 値 | 用途 | evidence |
|--------|-----|------|---------|
| `STATE_PORT_COUNTER_CAPABILITIES_NAME` | `"PORT_COUNTER_CAPABILITIES"` | STATE_DB テーブル名。portsorch が Table() コンストラクタへ渡す | `schema.h:529` |
| `STATE_QUEUE_COUNTER_CAPABILITIES_NAME` | `"QUEUE_COUNTER_CAPABILITIES"` | STATE_DB テーブル名。portsorch が Table() コンストラクタへ渡す | `schema.h:528` |
| `STATE_DEBUG_COUNTER_CAPABILITIES_NAME` | `"DEBUG_COUNTER_CAPABILITIES"` | STATE_DB テーブル名。debugcounterorch が Table() コンストラクタへ渡す | `schema.h:438` |

### 2. isSupported フィールド名とリテラル値 (portsorch.cpp)

| 定数相当 | 値 | 用途 | evidence |
|----------|-----|------|---------|
| フィールド名リテラル `"isSupported"` | `"isSupported"` | PORT_COUNTER_CAPABILITIES / QUEUE_COUNTER_CAPABILITIES の唯一フィールド名。YANG 非定義のためコード内ハードコード | `portsorch.cpp:1866-1869` |
| `"true"` リテラル | `"true"` | SAI が対応カウンタをサポートする場合に書き込まれる値 | `portsorch.cpp:1866` |
| `"false"` リテラル | `"false"` | 初期化時・SAI 非対応時に書き込まれる値 | `portsorch.cpp:1869` |

### 3. WRED 能力テーブルの固定 key 名 (portsorch.cpp:1872-1879)

| key 名 | テーブル | 対応 SAI enum | evidence |
|--------|---------|--------------|---------|
| `"WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER"` | `QUEUE_COUNTER_CAPABILITIES` | `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` | `portsorch.cpp:1872` |
| `"WRED_ECN_QUEUE_ECN_MARKED_BYTE_COUNTER"` | `QUEUE_COUNTER_CAPABILITIES` | `SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES` | `portsorch.cpp:1873` |
| `"WRED_ECN_QUEUE_WRED_DROPPED_PKT_COUNTER"` | `QUEUE_COUNTER_CAPABILITIES` | `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS` | `portsorch.cpp:1874` |
| `"WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER"` | `QUEUE_COUNTER_CAPABILITIES` | `SAI_QUEUE_STAT_WRED_DROPPED_BYTES` | `portsorch.cpp:1875` |
| `"WRED_ECN_PORT_WRED_GREEN_DROP_COUNTER"` | `PORT_COUNTER_CAPABILITIES` | `SAI_PORT_STAT_GREEN_WRED_DROPPED_PACKETS` | `portsorch.cpp:1876` |
| `"WRED_ECN_PORT_WRED_YELLOW_DROP_COUNTER"` | `PORT_COUNTER_CAPABILITIES` | `SAI_PORT_STAT_YELLOW_WRED_DROPPED_PACKETS` | `portsorch.cpp:1877` |
| `"WRED_ECN_PORT_WRED_RED_DROP_COUNTER"` | `PORT_COUNTER_CAPABILITIES` | `SAI_PORT_STAT_RED_WRED_DROPPED_PACKETS` | `portsorch.cpp:1878` |
| `"WRED_ECN_PORT_WRED_TOTAL_DROP_COUNTER"` | `PORT_COUNTER_CAPABILITIES` | `SAI_PORT_STAT_WRED_DROPPED_PACKETS` | `portsorch.cpp:1879` |

これら 8 個の key 名は YANG で定義されておらず、ソースコード内リテラルのみで管理される。追加・変更にはコード修正が必要。

### 4. DEBUG_COUNTER_CAPABILITIES のフィールド名定数 (debugcounterorch.cpp)

| フィールド名リテラル | 値 | 用途 | evidence |
|---------------------|-----|------|---------|
| `"count"` | `"count"` | 利用可能な debug counter 数（文字列化整数） | `debugcounterorch.cpp:357` |
| `"reasons"` | `"reasons"` | サポート drop reason の JSON 配列文字列 | `debugcounterorch.cpp:358` |

### 5. DEBUG_COUNTER_CAPABILITIES の key 名定数 (debug_counter.h)

| #define 定数 | 値 | 用途 | evidence |
|-------------|-----|------|---------|
| `PORT_INGRESS_DROPS` | `"PORT_INGRESS_DROPS"` | DEBUG_COUNTER_CAPABILITIES の counter_type key | `debug_counter.h:27` |
| `PORT_EGRESS_DROPS` | `"PORT_EGRESS_DROPS"` | DEBUG_COUNTER_CAPABILITIES の counter_type key | `debug_counter.h:28` |
| `SWITCH_INGRESS_DROPS` | `"SWITCH_INGRESS_DROPS"` | DEBUG_COUNTER_CAPABILITIES の counter_type key | `debug_counter.h:29` |
| `SWITCH_EGRESS_DROPS` | `"SWITCH_EGRESS_DROPS"` | DEBUG_COUNTER_CAPABILITIES の counter_type key | `debug_counter.h:30` |

### 6. drop_counter.cpp の能力問い合わせ定数

| 定数名 | 値 | 用途 | evidence |
|--------|-----|------|---------|
| `maxDropReasons` | `100` | `sai_query_attribute_enum_values_capability()` 呼び出し時に確保するバッファサイズ（理由の最大数）。コメント: "gives us plenty of space for both ingress and egress drop reasons" | `drop_counter.cpp:86` |
| `INGRESS_DROP_REASON_PREFIX_LENGTH` | `19` | `"SAI_IN_DROP_REASON_"` の文字数。drop reason 文字列からプレフィクスを除去する際に使用 | `drop_counter.cpp:17` |
| `EGRESS_DROP_REASON_PREFIX_LENGTH` | `20` | `"SAI_OUT_DROP_REASON_"` の文字数。同様に除去用 | `drop_counter.cpp:18` |

### 7. wred_port_stat_ids / wred_queue_stat_ids 配列 (portsorch.cpp)

| 配列 | 要素数 | 参照箇所 |
|------|--------|---------|
| `wred_port_stat_ids` | 4 (`SAI_PORT_STAT_GREEN_WRED_DROPPED_PACKETS` 等) | `portsorch.cpp:421-427`。PORT_COUNTER_CAPABILITIES 書き込みに対応する SAI enum のハードコードリスト |
| `wred_queue_stat_ids` | 4 (`SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` 等) | `portsorch.cpp:429-435`。QUEUE_COUNTER_CAPABILITIES に対応する SAI enum のハードコードリスト |

---

## 定数スキャンサマリ

- STATE_DB テーブル名: `schema.h` で `#define` として一元管理（3 件）
- WRED 能力 key 名: `portsorch.cpp` 内ソースリテラル（8 件、YANG 未定義）
- フィールド名 (`isSupported`, `count`, `reasons`): ソースリテラル（YANG 未定義）
- counter_type key 名: `debug_counter.h` の `#define`（4 件）
- SAI バッファサイズ: `maxDropReasons=100`（drop_counter.cpp:86）
- prefix 長: `INGRESS=19`, `EGRESS=20`（drop_counter.cpp:17-18）
