# QUEUE — Phase B 書込み順依存分析

中間ファイル。最終成果は `docs/reference/config-db/queue.md` の `<!-- ordering -->` ブロックに反映済み。

## 分析対象ソース

- `sonic-swss/orchagent/qosorch.cpp` (`handleQueueTable` L1750-1949)

## 書込み順依存の要点

### 1. PORT が先行必須

`handleQueueTable` (L1911-1914) は `gPortsOrch->getPort(port_name, port)` でポートの存在を確認する。
ポートが見つからない場合は `task_invalid_entry` を即座に返す（リトライなし）。

```cpp
if (!gPortsOrch->getPort(port_name, port))
{
    SWSS_LOG_ERROR("Port with alias:%s not found", port_name.c_str());
    return task_process_status::task_invalid_entry;
}
```

**QUEUE エントリは PORT が CONFIG_DB に存在し orchagent が初期化済みでなければ設定できない。**  
`task_invalid_entry` のためリトライキューにも残らず、恒久的にスキップされる。

### 2. SCHEDULER 参照の順序依存 (task_need_retry)

`handleQueueTable` L1822-1835:

```cpp
resolve_result = resolveFieldRefValue(m_qos_maps, scheduler_field_name, ..., sai_scheduler_profile, ...);
if (ref_resolve_status::not_resolved == resolve_result)
{
    SWSS_LOG_INFO("Missing or invalid scheduler reference");
    return task_process_status::task_need_retry;
}
```

`scheduler` フィールドで参照する SCHEDULER エントリが存在しない場合は `task_need_retry` を返す。
SCHEDULER 処理は同一 QosOrch 内で行われるため、**SCHEDULER エントリが CONFIG_DB に先行して存在していれば**
QosOrch がリトライ時に解決できる。

- `field_not_found`（フィールド自体が省略）の場合はリトライしない（省略可）。
- 解決不可な参照（恒久エラー）は `task_failed`。

### 3. WRED_PROFILE 参照の順序依存 (task_need_retry)

`handleQueueTable` L1857-1870:

```cpp
resolve_result = resolveFieldRefValue(m_qos_maps, wred_profile_field_name, ..., sai_wred_profile, ...);
if (ref_resolve_status::not_resolved == resolve_result)
{
    SWSS_LOG_INFO("Missing or invalid wred profile reference");
    return task_process_status::task_need_retry;
}
```

SCHEDULER と同じパターン。`wred_profile` が参照する WRED_PROFILE エントリが未作成なら `task_need_retry`。
WRED_PROFILE が先行して CONFIG_DB に存在していれば、QosOrch がリトライ時に OID を解決する。

### 4. SCHEDULER / WRED_PROFILE 解決順序

`handleQueueTable` 内では SCHEDULER を先に解決し (`resolveFieldRefValue` 1回目)、
その後 WRED_PROFILE を解決する (`resolveFieldRefValue` 2回目)。

SCHEDULER の解決が `task_need_retry` を返した時点で関数がリターンするため、
**SCHEDULER が未解決の場合は WRED_PROFILE の確認が行われない**。
この2段階チェックは以下の結果を持つ:

- SCHEDULER が未解決 → QUEUE エントリ全体がリトライ待ち（WRED 適用も保留）
- SCHEDULER が解決済み + WRED が未解決 → WRED のみリトライ待ち

### 5. DEL 時の依存

DEL 操作 (L1889-1893):

```cpp
else if (op == DEL_COMMAND)
{
    removeObject(QosOrch::getTypeMap(), CFG_QUEUE_TABLE_NAME, key);
    sai_scheduler_profile = SAI_NULL_OBJECT_ID;
    sai_wred_profile = SAI_NULL_OBJECT_ID;
}
```

DEL は参照先の存在チェックを行わず、無条件に SAI attribute を NULL OID に設定して解除する。
**QUEUE を削除する前に SCHEDULER / WRED_PROFILE を削除しても問題はない**（逆参照エラーなし）。

### 6. 起動時シーケンス

```
portsyncd が PortConfigDone → PortInitDone を発行
  ↓
allPortsReady() = true → QosOrch がアンブロック
  ↓
CONFIG_DB | SCHEDULER エントリが存在する (config qos reload 等で投入済み)
  ↓
CONFIG_DB | WRED_PROFILE エントリが存在する
  ↓
CONFIG_DB | QUEUE エントリを投入 → QosOrch::handleQueueTable が解決 → SAI 適用
```

実運用では `config qos reload` がすべてのエントリ（SCHEDULER / WRED_PROFILE / QUEUE）を
テンプレートから一括生成するため、順序制御は sonic-cfggen / qos_config.j2 が暗黙に担保する。

## まとめ（書込み順依存テーブル）

| 操作 | 必須先行テーブル | 理由 | 違反時の結果 |
|------|--------------|------|------------|
| SET | `PORT` (PortInitDone 済み) | `getPort()` でポート存在確認 | `task_invalid_entry` — 恒久スキップ |
| SET (`scheduler` フィールドあり) | `SCHEDULER` | `resolveFieldRefValue` で OID 参照 | `task_need_retry` — 自動リトライ |
| SET (`wred_profile` フィールドあり) | `WRED_PROFILE` | `resolveFieldRefValue` で OID 参照 | `task_need_retry` — 自動リトライ |
| DEL | なし（順序制約なし） | DEL は参照先チェックなし | — |

## evidence

- `qosorch.cpp` L1822-1835 SCHEDULER 参照解決 + `task_need_retry`
- `qosorch.cpp` L1857-1870 WRED_PROFILE 参照解決 + `task_need_retry`
- `qosorch.cpp` L1911-1914 `getPort()` 失敗時 `task_invalid_entry`
- `qosorch.cpp` L1889-1893 DEL ハンドラ（参照先チェックなし）
