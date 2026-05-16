# QUEUE — Phase B 書込み順依存分析

中間ファイル。最終成果は `docs/reference/config-db/queue.md` の `<!-- ordering -->` ブロックに反映済み。

## 分析対象ソース

- `sonic-swss/orchagent/qosorch.cpp` (`handleQueueTable` L1750-1949)
- `sonic-swss/orchagent/bufferorch.cpp` (`processQueue` L896-1110)

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

### 5. SAI queue bind 順序

フィールド解決後、各 queue index (`range_low` から `range_high`) に対してループ処理が行われる（`qosorch.cpp:1920-1944`）:

1. `applySchedulerToQueueSchedulerGroup(port, queue_ind, sai_scheduler_profile)` — scheduler group の `SAI_SCHEDULER_GROUP_ATTR_SCHEDULER_PROFILE_ID` を設定
2. `applyWredProfileToQueue(port, queue_ind, sai_wred_profile)` — queue の `SAI_QUEUE_ATTR_WRED_PROFILE_ID` を設定

この2呼び出しは独立しており、scheduler の SAI 書き込み成功後に WRED が失敗した場合 rollback されない（部分適用）。

### 6. VOQ 4-token key の処理順序

`gMySwitchType == "voq"` の場合、`handleQueueTable` は以下の順で key をパースする（`qosorch.cpp:1772-1799`）:

1. tokens を `|` で分割し 4 トークンを確認（違反時: `task_invalid_entry`）
2. `tokens[3]` を `parseIndexRange` で qindex パース（違反時: `task_invalid_entry`）
3. `tokens[0]` が `gMyHostName`、`tokens[1]` が `gMyAsicName`（大文字小文字無視）か確認
   - 一致: `local_port = true`、`local_port_name = tokens[2]` → ローカルポートとして処理
   - 不一致: リモートポート → `applySchedulerToQueueSchedulerGroup` の VOQ 分岐で `return true` (no-op)

`bufferorch::processQueue` も同一ロジックで VOQ 4-token key を処理する（`bufferorch.cpp:920-944`）。

### 7. bufferorch との関係

`bufferorch` は `BUFFER_QUEUE` テーブル (APPL_DB) を購読し、同一 queue OID に `SAI_QUEUE_ATTR_BUFFER_PROFILE_ID` を設定する。qosorch とは独立した経路で同一 queue OID を操作する:

- `bufferorch.processQueue` は `BUFFER_PROFILE` OID 未解決時に `task_need_retry`
- VOQ 環境では `getPortVoQIds()` で VoQ ID リストを取得し、`m_queue_ids` の代わりに使用

### 8. DEL 時の依存

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

### 9. 起動時シーケンス

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
- `qosorch.cpp` L1920-1944 scheduler → WRED の SAI bind 順序（queue index ループ内）
- `qosorch.cpp` L1772-1799 VOQ 4-token key パース + local_port 判定
- `qosorch.cpp` L1637-1705 `applySchedulerToQueueSchedulerGroup` VOQ 分岐 + remote skip
- `qosorch.cpp` L1708-1747 `applyWredProfileToQueue` VOQ 分岐 (`getPortVoQIds`)
- `bufferorch.cpp` L920-944 `processQueue` VOQ 4-token key パース（同一ロジック）
- `bufferorch.cpp` L964-972 BUFFER_PROFILE 未解決時 `task_need_retry`
