# SCHEDULER — Phase B 書込み順依存 調査メモ

対象ページ: `docs/reference/config-db/scheduler.md`
調査日: 2026-05-15

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/qosorch.cpp` | `QosOrch::handleSchedulerTable` / `handleQueueTable` — SCHEDULER / QUEUE の SET/DEL ハンドラ本体 |
| `sonic-buildimage/files/build_templates/qos_config.j2` | `config qos reload` 時の SCHEDULER / QUEUE 投入テンプレート |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-scheduler.yang` | YANG: QUEUE.scheduler の leafref 制約定義 |

## 検出した書込み順依存

### 1. SCHEDULER → QUEUE の順（ADD 時の必須順序）

`handleQueueTable`（qosorch.cpp:1822-1832）は、QUEUE エントリの `scheduler` フィールドを処理する際に `resolveFieldRefValue` を呼び出す。

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
```

`resolveFieldRefValue` は SCHEDULER エントリが `m_qos_maps[CFG_SCHEDULER_TABLE_NAME]` に登録済みでなければ `not_resolved` を返し、`handleQueueTable` は `task_need_retry` を返す。QosOrch の Consumer ループはこのエントリをキューに戻して再試行する。SCHEDULER が存在しない限り QUEUE のバインドは完了しない。

- **順序制約**: `SCHEDULER|<name>` を書き込んでから `QUEUE|<port>|<index>` (scheduler フィールドあり) を書き込む。
- evidence: `qosorch.cpp:1822-1832`

### 2. QUEUE 削除 → SCHEDULER 削除の順（DEL 時の必須順序）

`handleSchedulerTable` DEL ハンドラ（qosorch.cpp:1483-1488）は、SCHEDULER が他オブジェクトから参照されているかどうかを `isObjectBeingReferenced` で確認する。

```cpp
if (gQosOrch->isObjectBeingReferenced(QosOrch::getTypeMap(), qos_map_type_name, qos_object_name))
{
    auto hint = gQosOrch->objectReferenceInfo(...);
    SWSS_LOG_NOTICE("Can't remove object %s due to being referenced (%s)", ...);
    (*(m_qos_maps[qos_map_type_name]))[qos_object_name].m_pendingRemove = true;
    return task_process_status::task_need_retry;
}
```

QUEUE が参照している間は SCHEDULER を削除できない。`m_pendingRemove = true` にセットして `task_need_retry` を返す。QUEUE が削除 or `scheduler` フィールドをクリアするまで SCHEDULER の SAI 削除は実行されない。

- **順序制約**: `QUEUE|<port>|<index>` の scheduler 参照を解除（DEL or scheduler フィールド削除）→ `SCHEDULER|<name>` DEL の順。
- evidence: `qosorch.cpp:1483-1488`

### 3. SCHEDULER SET 中のフィールドが途中で pending_remove フラグをブロック

`handleSchedulerTable` SET ハンドラ（qosorch.cpp:1366-1370）は、既存エントリが `m_pendingRemove = true` の間に SET を受けると `task_need_retry` を返す。

```cpp
if ((*(m_qos_maps[qos_map_type_name]))[qos_object_name].m_pendingRemove && op == SET_COMMAND)
{
    SWSS_LOG_NOTICE("Entry %s %s is pending remove, need retry", ...);
    return task_process_status::task_need_retry;
}
```

DEL 要求が pending_remove 状態（QUEUE 参照が残っている）のまま SET を発行すると、QUEUE 参照が解消されるまで SET も処理されない。再設定フローでは QUEUE 参照を外してから DEL、DEL が完了してから SET するのが安全。

- **順序制約**: 同一 SCHEDULER 名の DEL → SET をまたぐ場合、QUEUE の参照解除 → DEL 完了後に SET。
- evidence: `qosorch.cpp:1366-1370`

### 4. qos_config.j2 テンプレートが SCHEDULER を QUEUE より先に配置

`config qos reload` が生成する設定ファイルでは、SCHEDULER ブロックが QUEUE ブロックより先に定義される（qos_config.j2:343-383 vs 508-574）。これは上記の ADD 依存順序を反映したテンプレート設計である。

- evidence: `qos_config.j2:343-383`, `qos_config.j2:508-574`

### 5. PORT / PortsOrch 先行必須（QUEUE バインド時）

`handleQueueTable`（qosorch.cpp:1911-1914）は各ポート名を `gPortsOrch->getPort()` で解決する。

```cpp
if (!gPortsOrch->getPort(port_name, port))
{
    SWSS_LOG_ERROR("Port with alias:%s not found", port_name.c_str());
    return task_process_status::task_invalid_entry;
}
```

ポートが PortsOrch に登録されていなければ `task_invalid_entry`（破棄）。ただしこれは QUEUE の依存であり SCHEDULER 自体の書込み順には影響しない。SCHEDULER 単体は PORT に依存せず SAI scheduler profile を作成できる。

- **補足**: SCHEDULER は PORT に依存しない。QUEUE → PORT の依存は SCHEDULER 書込み後でも成立する。
- evidence: `qosorch.cpp:1911-1914`

## 順序依存サマリ

| # | 依存関係 | 方向 | 対象パス | 違反時の挙動 |
|---|----------|------|---------|------------|
| 1 | `SCHEDULER\|<name>` → `QUEUE\|<port>\|<idx>` (scheduler フィールドあり) | ADD 時の強制先行 | QosOrch (handleQueueTable) | `task_need_retry`（無限再試行、QUEUE バインド未完了） |
| 2 | `QUEUE\|<port>\|<idx>` 参照解除 → `SCHEDULER\|<name>` DEL | DEL 時の強制後行 | QosOrch (handleSchedulerTable) | `m_pendingRemove=true` + `task_need_retry`（削除待機） |
| 3 | pending_remove 状態中の同名 SET | ADD 時のブロック | QosOrch (handleSchedulerTable) | `task_need_retry`（QUEUE 参照解消まで SET 保留） |
| 4 | qos_config.j2 がテンプレートで先行保証 | ビルド/CLI 設計 | `config qos reload` | テンプレートが順序を自動担保（実運用では問題なし） |
| 5 | SCHEDULER 自体は PORT に非依存 | 独立 | SAI scheduler profile 作成 | SCHEDULER は PORT 存在前でも作成可能 |
