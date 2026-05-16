# STATE_DB QUEUE_COUNTER_CAPABILITIES フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象: STATE_DB QUEUE_COUNTER_CAPABILITIES テーブル

## 調査対象ファイル

- `sonic-swss/orchagent/portsorch.cpp` — `initCounterCapabilities()` (L1850-1918) で STATE_DB への書き込みロジックを実装
- `sonic-swss/orchagent/portsorch.h` — `m_queueCounterCapabilitiesTable` 宣言 (L650)
- `sonic-swss-common/common/schema.h` — `STATE_QUEUE_COUNTER_CAPABILITIES_NAME "QUEUE_COUNTER_CAPABILITIES"` 定義 (L528)
- `sonic-utilities/tests/mock_tables/state_db.json` — テスト用モックデータ (L1087-1097)
- `sonic-utilities/utilities_common/portstat.py` — `isSupported` フィールド参照 (L297-312)
- `sonic-utilities/scripts/wredstat` — STATE_DB 接続とカウンタ参照

---

## 1. テーブル概要

`QUEUE_COUNTER_CAPABILITIES` は STATE_DB に書き込まれる読み取り専用テーブル。
`portsorch` が `PortsOrch::initCounterCapabilities(switchId)` を orchagent 起動時に 1 回だけ呼び出し、SAI WRED/ECN キューカウンタのサポート可否を調査して書き込む。

対応するスキーマ定数:
```cpp
// sonic-swss-common/common/schema.h:528
#define STATE_QUEUE_COUNTER_CAPABILITIES_NAME   "QUEUE_COUNTER_CAPABILITIES"
```

---

## 2. キー一覧（コードハードコード）

`portsorch.cpp:1872-1875` でハードコードされた 4 キー:

| Redis キー | 対応する SAI 統計 enum |
|-----------|---------------------|
| `QUEUE_COUNTER_CAPABILITIES\|WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER` | `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` |
| `QUEUE_COUNTER_CAPABILITIES\|WRED_ECN_QUEUE_ECN_MARKED_BYTE_COUNTER` | `SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES` |
| `QUEUE_COUNTER_CAPABILITIES\|WRED_ECN_QUEUE_WRED_DROPPED_PKT_COUNTER` | `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS` |
| `QUEUE_COUNTER_CAPABILITIES\|WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER` | `SAI_QUEUE_STAT_WRED_DROPPED_BYTES` |

---

## 3. フィールド一覧

各キーに対して `isSupported` フィールドのみ:

| フィールド | 型 | デフォルト値 | 更新タイミング |
|-----------|-----|------------|-------------|
| `isSupported` | boolean string ("true"/"false") | `"false"` | `initCounterCapabilities()` 実行時（1 回のみ） |

---

## 4. コード由来デフォルト詳細

### 4-1. 初期化（全フラグ false）

```cpp
// portsorch.cpp:1865-1875
vector<FieldValueTuple> fieldValuesFalse;
fieldValuesFalse.push_back(FieldValueTuple("isSupported", "false"));

/* 1. Initialize the WRED stats capabilities with false for all counters */
m_queueCounterCapabilitiesTable->set("WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER",  fieldValuesFalse);
m_queueCounterCapabilitiesTable->set("WRED_ECN_QUEUE_ECN_MARKED_BYTE_COUNTER", fieldValuesFalse);
m_queueCounterCapabilitiesTable->set("WRED_ECN_QUEUE_WRED_DROPPED_PKT_COUNTER",  fieldValuesFalse);
m_queueCounterCapabilitiesTable->set("WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER", fieldValuesFalse);
```

**デフォルトは必ず `"false"`。** SAI クエリより前に全キーが `"false"` で初期化される。

### 4-2. SAI クエリ（成功時のみ true に上書き）

```cpp
// portsorch.cpp:1882-1913
sai_status_t status = sai_query_stats_capability(switchId, SAI_OBJECT_TYPE_QUEUE, &queue_stats_capability);
// ... (SAI_STATUS_BUFFER_OVERFLOW の場合はリサイズして再クエリ) ...
if (status == SAI_STATUS_SUCCESS)
{
    for(it=0; it<queue_stats_capability.count; it++)
    {
        if (SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS == queue_stats_capability.list[it].stat_enum)
            m_queueCounterCapabilitiesTable->set("WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER", fieldValuesTrue);
        else if (SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES == queue_stats_capability.list[it].stat_enum)
            m_queueCounterCapabilitiesTable->set("WRED_ECN_QUEUE_ECN_MARKED_BYTE_COUNTER", fieldValuesTrue);
        else if (SAI_QUEUE_STAT_WRED_DROPPED_PACKETS == queue_stats_capability.list[it].stat_enum)
            m_queueCounterCapabilitiesTable->set("WRED_ECN_QUEUE_WRED_DROPPED_PKT_COUNTER", fieldValuesTrue);
        else if (SAI_QUEUE_STAT_WRED_DROPPED_BYTES == queue_stats_capability.list[it].stat_enum)
            m_queueCounterCapabilitiesTable->set("WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER", fieldValuesTrue);
    }
}
else
{
    SWSS_LOG_NOTICE("Queue stat capability get failed: WRED queue stats can not be enabled, rv:%d", status);
}
```

SAI クエリが失敗した場合、または対応する統計が SAI 能力リストに含まれない場合、フラグは `"false"` のまま。

### 4-3. テストモックデータ（比較参照）

`sonic-utilities/tests/mock_tables/state_db.json:1087-1097` より（テスト環境では全て `"true"`）:

```json
"QUEUE_COUNTER_CAPABILITIES|WRED_ECN_QUEUE_WRED_DROPPED_PKT_COUNTER": { "isSupported": "true" },
"QUEUE_COUNTER_CAPABILITIES|WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER": { "isSupported": "true" },
"QUEUE_COUNTER_CAPABILITIES|WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER": { "isSupported": "true" },
"QUEUE_COUNTER_CAPABILITIES|WRED_ECN_QUEUE_ECN_MARKED_BYTE_COUNTER": { "isSupported": "true" }
```

---

## 5. 消費者（Consumer）の参照パターン

### 5-1. portstat.py（ポートカウンタ側・パターン参照）

```python
# utilities_common/portstat.py:297-312
wred_green_pkt_stat_capable = self.db.get(
    self.db.STATE_DB,
    "PORT_COUNTER_CAPABILITIES|WRED_ECN_PORT_WRED_GREEN_DROP_COUNTER",
    "isSupported")
# (QUEUE 側は同パターンで QUEUE_COUNTER_CAPABILITIES を参照)
```

QUEUE 側も同じ構造で STATE_DB から直接 GET し、`"true"` でなければ COUNTERS_DB から対応フィールドを除外する。

### 5-2. wredstat（キューカウンタ表示）

`scripts/wredstat:196-197` で STATE_DB に接続し、COUNTERS_DB から取得した WRED カウンタに対して N/A 判定を行う。`isSupported != "true"` の場合、SAI フィールドが存在しないため `counter_data is None` → `fields[pos] = STATUS_NA`。

---

## 6. 暗黙デフォルトまとめ

| キー | デフォルト | 変更条件 | 証拠 |
|------|----------|---------|------|
| `WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER.isSupported` | `"false"` | SAI が `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` を返せば `"true"` | portsorch.cpp:1872, 1896 |
| `WRED_ECN_QUEUE_ECN_MARKED_BYTE_COUNTER.isSupported` | `"false"` | SAI が `SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES` を返せば `"true"` | portsorch.cpp:1873, 1901 |
| `WRED_ECN_QUEUE_WRED_DROPPED_PKT_COUNTER.isSupported` | `"false"` | SAI が `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS` を返せば `"true"` | portsorch.cpp:1874, 1906 |
| `WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER.isSupported` | `"false"` | SAI が `SAI_QUEUE_STAT_WRED_DROPPED_BYTES` を返せば `"true"` | portsorch.cpp:1875, 1911 |

**重要事項**:
- `initCounterCapabilities()` は orchagent 起動時に 1 回だけ実行される（再起動しない限り再実行されない）
- FLEX_COUNTER_TABLE の WRED_ECN_QUEUE FLEX_COUNTER_STATUS 設定とは独立して動作する
- YANG schema は存在しない（コードレベルのみ制約）
- `PORT_COUNTER_CAPABILITIES` テーブルも同じ `initCounterCapabilities()` 内で同様のパターンで書き込まれる（port 側は SAI_OBJECT_TYPE_PORT でクエリ）

---

## 7. 証拠リンク

- `sonic-swss/orchagent/portsorch.cpp:1850-1918` — `initCounterCapabilities()` 完全実装
- `sonic-swss/orchagent/portsorch.h:650` — `m_queueCounterCapabilitiesTable` 宣言
- `sonic-swss-common/common/schema.h:528` — `STATE_QUEUE_COUNTER_CAPABILITIES_NAME` 定義
- `sonic-utilities/tests/mock_tables/state_db.json:1087-1097` — テスト用モックデータ（全 true）
- `sonic-utilities/utilities_common/portstat.py:297-312` — isSupported 参照パターン（PORT 側、QUEUE 側は同等）
