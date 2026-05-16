# SCHEDULER — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/scheduler.md`
解析日: 2026-05-16
根拠ソース: `sonic-swss/orchagent/qosorch.cpp`

---

## 目的

`SCHEDULER` エントリが CONFIG_DB に書かれたとき、`QosOrch` が **暗黙的に** 参照・依存する
他テーブルのキー / フィールドを網羅する。また SCHEDULER プロファイルを**参照している**テーブル
（被参照元）も列挙し、削除順序の制約根拠を提示する。

---

## 1. QUEUE テーブル (被参照: QUEUE → SCHEDULER)

### 参照箇所

`handleQueueTable()` — `qosorch.cpp:1822-1853`

```cpp
resolve_result = resolveFieldRefValue(m_qos_maps, scheduler_field_name,
                                      qos_to_ref_table_map.at(scheduler_field_name), tuple,
                                      sai_scheduler_profile, scheduler_profile_name);
if (ref_resolve_status::success != resolve_result)
{
    if(ref_resolve_status::not_resolved == resolve_result)
    {
        SWSS_LOG_INFO("Missing or invalid scheduler reference");
        return task_process_status::task_need_retry;
    }
    ...
}
else
{
    setObjectReference(m_qos_maps, CFG_QUEUE_TABLE_NAME, key, scheduler_field_name, scheduler_profile_name);
}
```

### 依存内容

| `QUEUE` フィールド | 参照先テーブル | 参照先キー形式 | 参照タイミング |
|---|---|---|---|
| `scheduler` | `SCHEDULER` | `SCHEDULER\|<name>` | SET 処理時 `handleQueueTable()` |

### 特記事項

- `QUEUE.scheduler` が指定されているが対応する `SCHEDULER|<name>` エントリが存在しない場合、
  `resolveFieldRefValue` が `ref_resolve_status::not_resolved` を返し `task_need_retry` となる。
  `SCHEDULER` エントリが登録されるまで QUEUE の SAI バインドは完了しない。
- `SCHEDULER` エントリが `QUEUE` から参照されている間は、`handleSchedulerTable` の DEL ハンドラが
  `isObjectBeingReferenced` で参照を検出し `m_pendingRemove = true` にして削除を保留する。
  QUEUE 参照を先に解除してから SCHEDULER を削除する必要がある。

---

## 2. PORT_QOS_MAP テーブル (被参照: PORT_QOS_MAP → SCHEDULER)

### 参照箇所

`qos_to_attr_map` 定義 — `qosorch.cpp:70`

```cpp
{scheduler_field_name, SAI_PORT_ATTR_QOS_SCHEDULER_PROFILE_ID},
```

`qos_to_ref_table_map` 定義 — `qosorch.cpp:109`

```cpp
{scheduler_field_name, CFG_SCHEDULER_TABLE_NAME},
```

`handlePortQosMapTable()` — `qosorch.cpp:2124-2133`

```cpp
ref_resolve_status status = resolveFieldRefValue(m_qos_maps, map_type_name,
    qos_to_ref_table_map.at(map_type_name), tuple, id, object_name);
if (status != ref_resolve_status::success)
{
    SWSS_LOG_INFO("Port QoS map %s is not yet created", map_name.c_str());
    return task_process_status::task_need_retry;
}
setObjectReference(m_qos_maps, CFG_PORT_QOS_MAP_TABLE_NAME, key, map_type_name, object_name);
```

### 依存内容

| `PORT_QOS_MAP` フィールド | 参照先テーブル | 参照先キー形式 | SAI 属性 | 参照タイミング |
|---|---|---|---|---|
| `scheduler` | `SCHEDULER` | `SCHEDULER\|<name>` | `SAI_PORT_ATTR_QOS_SCHEDULER_PROFILE_ID` | SET 処理時 `handlePortQosMapTable()` |

### 特記事項

- PORT_QOS_MAP の `scheduler` フィールドはポートレベルのスケジューラプロファイルを指定する。
  SCHEDULER エントリが未存在の場合は `task_need_retry` で保留され、ポートへの SAI 属性設定も保留される。
- `PORT_QOS_MAP` が参照している間は SCHEDULER の削除が保留（QUEUE と同様の参照カウント機構）。

---

## 3. WRED_PROFILE との連携 (QUEUE 経由)

### 参照箇所

`handleQueueTable()` — `qosorch.cpp:1857-1886` (wred_profile_field_name の resolveFieldRefValue)

`qos_to_ref_table_map` 定義 — `qosorch.cpp:110`

```cpp
{wred_profile_field_name, CFG_WRED_PROFILE_TABLE_NAME},
```

### 依存内容

SCHEDULER と WRED_PROFILE は QUEUE テーブルを介して**並列に**参照される関係にある。
QUEUE エントリの SET 処理で `scheduler` フィールドと `wred_profile` フィールドが同時に解決される。
SCHEDULER と WRED_PROFILE の間には直接の依存はないが、両者が同一 QUEUE に適用される点で
間接的に関連する。

| QUEUE フィールド | 参照先テーブル | 参照先キー形式 | 参照タイミング |
|---|---|---|---|
| `scheduler` | `SCHEDULER` | `SCHEDULER\|<name>` | SET 処理時 (WRED と並列解決) |
| `wred_profile` | `WRED_PROFILE` | `WRED_PROFILE\|<name>` | SET 処理時 (SCHEDULER と並列解決) |

### 特記事項

- SCHEDULER と WRED_PROFILE は互いに独立したプロファイルであり、QUEUE の `scheduler` フィールドと
  `wred_profile` フィールドがそれぞれ独立して解決される。
- 一方が `not_resolved` で `task_need_retry` を返す場合、他方の解決も再試行に巻き込まれる。
- SCHEDULER は帯域制御（シェーピング・スケジューリング）を担い、WRED_PROFILE はドロップ確率制御を担う。
  両者を組み合わせることで同一キューに対して帯域制御 + 輻輳回避を同時適用できる。

---

## 4. cross-refs ブロック (最終形)

以下を `docs/reference/config-db/scheduler.md` の `<!-- glossary-links-injected -->` 直前に挿入する。

```markdown
<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`SCHEDULER` プロファイルは CONFIG_DB 上では独立したエントリだが、`QosOrch` の
`resolveFieldRefValue` 機構を通じて以下のテーブルから**暗黙的に leafref 参照**される。
YANG leafref として明示されていない参照もコードレベルで強制される。

### SCHEDULER を参照するテーブル (被参照)

| 参照元テーブル | 参照元フィールド | 参照先キー形式 | SAI 効果 | 参照箇所 |
|---|---|---|---|---|
| `QUEUE` | `scheduler` | `SCHEDULER\|<name>` | `SAI_QUEUE_ATTR_SCHEDULER_PROFILE_ID` バインド | `qosorch.cpp:1822-1853` |
| `PORT_QOS_MAP` | `scheduler` | `SCHEDULER\|<name>` | `SAI_PORT_ATTR_QOS_SCHEDULER_PROFILE_ID` バインド | `qosorch.cpp:2124-2133` |

### 解決タイミングと retry 挙動

- `QUEUE.scheduler` または `PORT_QOS_MAP.scheduler` が SET された時点で `SCHEDULER|<name>` が
  未存在の場合、`task_need_retry` が返され参照が解決されるまで SAI バインドは保留される。
- 参照が解決された後、`setObjectReference()` で参照カウントが増加し、被参照中の SCHEDULER は
  DEL ハンドラで削除保留 (`m_pendingRemove = true`) となる。

### WRED_PROFILE との連携

- `QUEUE` は `scheduler` と `wred_profile` フィールドを並列に解決する (`qosorch.cpp:1857-1886`)。
  SCHEDULER (帯域制御) と WRED_PROFILE (ドロップ確率制御) は互いに独立だが、同一 QUEUE に
  同時適用することで帯域制御と輻輳回避を組み合わせることができる。
- SCHEDULER と WRED_PROFILE の間に直接の参照関係はない。

### 削除順序制約

```
QUEUE の scheduler / PORT_QOS_MAP の scheduler 参照を解除
  ↓
SCHEDULER|<name> を DEL
```

参照が残っている間は SAI レベルで EBUSY となり `Failed to remove scheduler profile` エラーが発生する。
<!-- /cross-refs -->
```
