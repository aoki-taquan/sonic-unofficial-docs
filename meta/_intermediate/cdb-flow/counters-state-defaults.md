# counters-state Phase A — implicit defaults (code-derived)

Generated: 2026-05-15  
Target doc: docs/reference/config-db/counters-state.md

## 対象テーブル

STATE_DB に格納されるカウンタ関連能力情報テーブル群:

| STATE_DB テーブル | スキーマ定数 | 書き込み元 |
|-----------------|------------|----------|
| `PORT_COUNTER_CAPABILITIES` | `STATE_PORT_COUNTER_CAPABILITIES_NAME` (schema.h:529) | `portsorch.cpp` |
| `QUEUE_COUNTER_CAPABILITIES` | `STATE_QUEUE_COUNTER_CAPABILITIES_NAME` (schema.h:528) | `portsorch.cpp` |
| `DEBUG_COUNTER_CAPABILITIES` | `STATE_DEBUG_COUNTER_CAPABILITIES_NAME` (schema.h:438) | `debugcounterorch.cpp` |

---

## Field-by-field analysis

### PORT_COUNTER_CAPABILITIES テーブル

#### 起動時デフォルト (false 初期化)

portsorch の `initCounterCapabilities()` (portsorch.cpp:1865-1879) で呼ばれ、まず全フィールドを `isSupported=false` で書き込む。

| STATE_DB key | field | 初期値 | コード |
|-------------|-------|--------|--------|
| `PORT_COUNTER_CAPABILITIES\|WRED_ECN_PORT_WRED_GREEN_DROP_COUNTER` | `isSupported` | `"false"` | portsorch.cpp:1876 |
| `PORT_COUNTER_CAPABILITIES\|WRED_ECN_PORT_WRED_YELLOW_DROP_COUNTER` | `isSupported` | `"false"` | portsorch.cpp:1877 |
| `PORT_COUNTER_CAPABILITIES\|WRED_ECN_PORT_WRED_RED_DROP_COUNTER` | `isSupported` | `"false"` | portsorch.cpp:1878 |
| `PORT_COUNTER_CAPABILITIES\|WRED_ECN_PORT_WRED_TOTAL_DROP_COUNTER` | `isSupported` | `"false"` | portsorch.cpp:1879 |

#### SAI 問い合わせ後の更新 (プラットフォーム依存)

`sai_query_stats_capability(SAI_OBJECT_TYPE_PORT, ...)` が成功した場合に限り、対応する SAI 統計 enum が含まれていれば `isSupported=true` に更新される (portsorch.cpp:1936-1968)。

| STATE_DB key | 更新条件 | SAI enum | コード |
|-------------|---------|---------|--------|
| `WRED_ECN_PORT_WRED_GREEN_DROP_COUNTER` | `SAI_PORT_STAT_GREEN_WRED_DROPPED_PACKETS` が stat capability リストに存在 | `SAI_PORT_STAT_GREEN_WRED_DROPPED_PACKETS` | portsorch.cpp:1941-1944 |
| `WRED_ECN_PORT_WRED_YELLOW_DROP_COUNTER` | `SAI_PORT_STAT_YELLOW_WRED_DROPPED_PACKETS` が存在 | `SAI_PORT_STAT_YELLOW_WRED_DROPPED_PACKETS` | portsorch.cpp:1946-1949 |
| `WRED_ECN_PORT_WRED_RED_DROP_COUNTER` | `SAI_PORT_STAT_RED_WRED_DROPPED_PACKETS` が存在 | `SAI_PORT_STAT_RED_WRED_DROPPED_PACKETS` | portsorch.cpp:1951-1954 |
| `WRED_ECN_PORT_WRED_TOTAL_DROP_COUNTER` | `SAI_PORT_STAT_WRED_DROPPED_PACKETS` が存在 | `SAI_PORT_STAT_WRED_DROPPED_PACKETS` | portsorch.cpp:1956-1959 |

SAI 問い合わせ失敗時 (SAI_STATUS_SUCCESS でない場合) は全フィールドが `"false"` のまま残る。SWSS_LOG_NOTICE で通知されるのみで orchagent はエラー終了しない (portsorch.cpp:1965-1968)。

---

### QUEUE_COUNTER_CAPABILITIES テーブル

#### 起動時デフォルト (false 初期化)

同じ `initCounterCapabilities()` で呼ばれ、まず全フィールドを `isSupported=false` で書き込む (portsorch.cpp:1871-1875)。

| STATE_DB key | field | 初期値 | コード |
|-------------|-------|--------|--------|
| `QUEUE_COUNTER_CAPABILITIES\|WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER` | `isSupported` | `"false"` | portsorch.cpp:1872 |
| `QUEUE_COUNTER_CAPABILITIES\|WRED_ECN_QUEUE_ECN_MARKED_BYTE_COUNTER` | `isSupported` | `"false"` | portsorch.cpp:1873 |
| `QUEUE_COUNTER_CAPABILITIES\|WRED_ECN_QUEUE_WRED_DROPPED_PKT_COUNTER` | `isSupported` | `"false"` | portsorch.cpp:1874 |
| `QUEUE_COUNTER_CAPABILITIES\|WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER` | `isSupported` | `"false"` | portsorch.cpp:1875 |

#### SAI 問い合わせ後の更新 (プラットフォーム依存)

`sai_query_stats_capability(SAI_OBJECT_TYPE_QUEUE, ...)` が成功した場合に限り更新 (portsorch.cpp:1889-1918)。

| STATE_DB key | 更新条件 | SAI enum | コード |
|-------------|---------|---------|--------|
| `WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER` | `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` が存在 | `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` | portsorch.cpp:1894-1897 |
| `WRED_ECN_QUEUE_ECN_MARKED_BYTE_COUNTER` | `SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES` が存在 | `SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES` | portsorch.cpp:1899-1902 |
| `WRED_ECN_QUEUE_WRED_DROPPED_PKT_COUNTER` | `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS` が存在 | `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS` | portsorch.cpp:1904-1907 |
| `WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER` | `SAI_QUEUE_STAT_WRED_DROPPED_BYTES` が存在 | `SAI_QUEUE_STAT_WRED_DROPPED_BYTES` | portsorch.cpp:1909-1912 |

---

### DEBUG_COUNTER_CAPABILITIES テーブル

#### 書き込み契機

`DebugCounterOrch::publishDropCounterCapabilities()` (debugcounterorch.cpp:315-363) がコンストラクタで呼ばれる。

#### テーブル構造

```
STATE_DB / DEBUG_COUNTER_CAPABILITIES | <counter_type>   (Hash)
  field: count    (string, 例: "4")   — その counter_type で使用可能な SAI debug counter 数
  field: reasons  (string, 例: '["SMAC_EQUALS_DMAC","INGRESS_VLAN_FILTER"]') — サポートされる drop reason 一覧
```

#### counter_type キーの列挙

debugcounterorch.cpp:17-22 の `flex_counter_type_lookup` より:

| counter_type | 種類 | SAI type |
|-------------|------|----------|
| `PORT_INGRESS_DROPS` | ポート別 ingress drop カウンタ | `SAI_DEBUG_COUNTER_TYPE_PORT_IN_DROP_REASONS` |
| `PORT_EGRESS_DROPS` | ポート別 egress drop カウンタ | `SAI_DEBUG_COUNTER_TYPE_PORT_OUT_DROP_REASONS` |
| `SWITCH_INGRESS_DROPS` | スイッチ全体 ingress drop カウンタ | `SAI_DEBUG_COUNTER_TYPE_SWITCH_IN_DROP_REASONS` |
| `SWITCH_EGRESS_DROPS` | スイッチ全体 egress drop カウンタ | `SAI_DEBUG_COUNTER_TYPE_SWITCH_OUT_DROP_REASONS` |

#### デフォルトの決定ロジック

1. **`count` フィールド**: `sai_query_attribute_capability()` で SAI オブジェクト数を取得 (`getSupportedDebugCounterAmounts()`)。プラットフォームが SAI query をサポートしない場合 `0` を返す。`count = "0"` の counter_type はテーブルに書き込まれない (debugcounterorch.cpp:348-354)
2. **`reasons` フィールド**: `sai_query_attribute_enum_values_capability()` で ingress / egress 別サポート drop reason を取得 (`getSupportedDropReasons()`)。プラットフォームが query をサポートしない場合は空 `{}` を返し、drop_reasons が空なら書き込まれない (debugcounterorch.cpp:343-346)
3. **エントリ不存在**: count=0 または reasons が空の counter_type は STATE_DB に登録されない。`show debug-counter capabilities` が何も表示しない場合はプラットフォームが SAI drop counter query をサポートしないことを意味する

---

## 読み取り経路 (consumers)

### portstat.py (sonic-utilities)

```python
# portstat.py:297-329
wred_green_pkt_stat_capable = state_db.get(
    STATE_DB, "PORT_COUNTER_CAPABILITIES|WRED_ECN_PORT_WRED_GREEN_DROP_COUNTER", "isSupported")
```

取得した `isSupported` が `"true"` でない場合、対応する SAI カウンタ (`SAI_PORT_STAT_GREEN_WRED_DROPPED_PACKETS` 等) を `counter_bucket_dict` から削除する。COUNTERS_DB ポーリング対象から外されるためカウンタ値は常に 0 / N/A となる。

### show debug-counter capabilities

`sonic-utilities/show/debug_counter.py` が `DEBUG_COUNTER_CAPABILITIES` テーブルを読み、`count` と `reasons` を整形して表示する。

---

## 検出された discrepancy / 暗黙挙動まとめ

1. **false 初期化の一時ウィンドウ**: orchagent 起動直後、`sai_query_stats_capability()` 完了前は全フィールドが `"false"` のまま。この間に portstat.py が参照すると WRED カウンタが N/A になる。通常は数ミリ秒以内に書き直されるが起動直後の競合タイミングがあり得る。
2. **SAI 失敗時の silent false 残存**: `sai_query_stats_capability()` が失敗すると SWSS_LOG_NOTICE を出すのみで全フィールドが `"false"` のまま。portstat.py はこれを「WRED 未サポートプラットフォーム」として無言で処理する。ユーザーには WRED カウンタが N/A と見えるだけ。
3. **DEBUG_COUNTER_CAPABILITIES の選択的書き込み**: count=0 または reasons 空の counter_type はキー自体が存在しない。`show debug-counter capabilities` が空欄になる場合の原因を特定するにはログを参照する必要がある。
4. **YANG / CONFIG_DB に対応テーブルなし**: これら 3 テーブルはすべて STATE_DB への書き込み専用。CONFIG_DB 側に対応する設定テーブルは存在しない（DEBUG_COUNTER は CONFIG_DB `DEBUG_COUNTER` テーブルが存在するが、DEBUG_COUNTER_CAPABILITIES は STATE_DB 側の read-only 能力情報）。
