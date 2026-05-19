# QUEUE_COUNTER_CAPABILITIES (STATE_DB) — Phase H プラットフォーム差分調査ノート

調査日: 2026-05-19
対象ページ: `docs/reference/config-db/queue-state.md`
対象テーブル: `STATE_DB QUEUE_COUNTER_CAPABILITIES`
Producer: `PortsOrch::initCounterCapabilities()` (`sonic-swss/orchagent/portsorch.cpp:1850-1969`)

---

## 調査方針

`initCounterCapabilities()` の全コードパスを精読し、`gMySwitchType` や `isChassisDbInUse()` 等の
プラットフォーム条件分岐が存在するかを確認する。

---

## 1. initCounterCapabilities() — プラットフォーム条件分岐の有無

`PortsOrch::initCounterCapabilities()` (`portsorch.cpp:1850-1969`) には
`gMySwitchType` / `isChassisDbInUse()` / `m_cmisModuleAsicSyncSupported` 等の
プラットフォーム条件分岐は一切存在しない。

呼び出し元 (`portsorch.cpp:1107`) も無条件呼び出しであり、DPU / VOQ / 標準 BOX スイッチの
いずれの構成でも実行される。

```cpp
// portsorch.cpp:1107 (構造的に無条件 — DPU / VOQ / 標準どれも到達)
initCounterCapabilities(gSwitchId);
```

---

## 2. 書き込まれるキー — 全プラットフォーム共通

4 キーはハードコードされたリテラル文字列:

```cpp
// portsorch.cpp:1872-1875
m_queueCounterCapabilitiesTable->set("WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER",  fieldValuesFalse);
m_queueCounterCapabilitiesTable->set("WRED_ECN_QUEUE_ECN_MARKED_BYTE_COUNTER", fieldValuesFalse);
m_queueCounterCapabilitiesTable->set("WRED_ECN_QUEUE_WRED_DROPPED_PKT_COUNTER",  fieldValuesFalse);
m_queueCounterCapabilitiesTable->set("WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER", fieldValuesFalse);
```

これらのキーは `gMySwitchType` に依存しない。DPU/VOQ 環境でも同じ 4 キーが書き込まれる。

---

## 3. `isSupported` の値 — SAI 実装依存

`sai_query_stats_capability(gSwitchId, SAI_OBJECT_TYPE_QUEUE, ...)` の結果が唯一の
プラットフォーム差分源。

| ケース | 典型的プラットフォーム | 結果 |
|--------|---------------------|------|
| SAI が WRED/ECN キューカウンタをサポート | Broadcom ASIC (WRED 対応 SKU) | 対応キーが `"true"` |
| SAI が `SAI_STATUS_SUCCESS` を返すが WRED 統計がリストに含まれない | WRED 未対応 SKU / ソフトウェア SAI | 全 4 キーが `"false"` |
| SAI が `SAI_STATUS_NOT_SUPPORTED` / その他エラーを返す | Mellanox legacy / p4 SAI / vstest | 全 4 キーが `"false"` のまま確定 |
| SAI が `SAI_STATUS_BUFFER_OVERFLOW` を返す | SAI ケイパビリティリストが大きいプラットフォーム | 1 回リトライ後、成功すれば通常フロー |

---

## 4. VOQ シャーシの影響

VOQ (`gMySwitchType == "voq"`) でも `initCounterCapabilities()` は実行される。
ただし WRED/ECN カウンタの FlexCounter 登録
(`addWredQueueFlexCountersPerPortPerQueueIndex`) は、VOQ ポートに対して
`m_port_voq_ids` を使用する (`portsorch.cpp:9583-9586`)。

これは COUNTERS_DB への登録対象 OID の差異であり、`QUEUE_COUNTER_CAPABILITIES` テーブルの
`isSupported` フィールド値には影響しない。

VoQ はハードウェアで WRED/ECN をサポートしないことが多く、VOQ 環境では全 4 キーが
`"false"` のままになるケースが実運用上多い。

---

## 5. DPU の影響

DPU (`gMySwitchType == "dpu"`) でも `initCounterCapabilities()` は実行される。
DPU の SAI 実装は WRED 統計をサポートしない場合が多く、全 4 キーが `"false"` となる可能性が高い。

コードレベルでの DPU 条件分岐はない（DPU 用 skip なし）。

---

## 6. wred_queue_stat_ids — 全プラットフォーム共通

```cpp
// portsorch.cpp:429-435
static const vector<sai_queue_stat_t> wred_queue_stat_ids =
{
    SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS,
    SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES,
    SAI_QUEUE_STAT_WRED_DROPPED_PACKETS,
    SAI_QUEUE_STAT_WRED_DROPPED_BYTES
};
```

4 つの SAI 統計 enum はプラットフォーム非依存の静的定数。

---

## 7. まとめ

`QUEUE_COUNTER_CAPABILITIES` テーブルの構造（キー名・フィールド名）は
全プラットフォームで共通。唯一のプラットフォーム差分は `isSupported` の値であり、
それは `sai_query_stats_capability()` に対する SAI SDK の応答に依存する。

WRED/ECN カウンタをサポートする SAI 実装 (主に Broadcom ASIC 系) では
対応キーが `"true"` となるが、VOQ シャーシ / DPU / p4 SAI / vstest 環境では
通常全て `"false"` となる。

---

## 証拠リンク

- `sonic-swss/orchagent/portsorch.cpp:1850-1969` — `initCounterCapabilities()` 全実装
- `sonic-swss/orchagent/portsorch.cpp:1107` — 無条件呼び出し
- `sonic-swss/orchagent/portsorch.cpp:429-435` — `wred_queue_stat_ids` 定数
- `sonic-swss/orchagent/portsorch.cpp:9574-9593` — `addWredQueueFlexCountersPerPortPerQueueIndex` (VOQ 対応)
