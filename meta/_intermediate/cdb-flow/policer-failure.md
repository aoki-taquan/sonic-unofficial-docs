# POLICER 失敗挙動 (Phase D) — 中間ファイル

根拠: `sonic-swss/orchagent/policerorch.cpp` 全行精読
commit: `4305596156d70e9797e8a881b3d19b46de0bce0d`

## SET (create) 失敗パターン

### 1. METER_TYPE / MODE 欠落 — silent-proceed

```
policerorch.cpp:491-495
if (!meter_type || !mode)
{
    SWSS_LOG_ERROR("Failed to create policer %s, missing mandatory fields", key.c_str());
}
// 注意: ここで return しない → create_policer() が続行
```

- `meter_type` または `mode` が欠落していても `create_policer()` を呼び続ける。
- SAI 側でエラーが返るまで処理は止まらない。
- SAI エラーが返ると `handleSaiCreateStatus()` の判定によりキューから削除（`task_need_retry` でなければ `erase(it)` ） → **リトライなし**で消失。

### 2. SAI create 失敗 → task_need_retry 分岐

```
policerorch.cpp:500-508
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create policer %s, rv:%d", key.c_str(), status);
    if (handleSaiCreateStatus(SAI_API_POLICER, status) == task_need_retry)
    {
        it++;   // キューに残してリトライ
        continue;
    }
}
// SAI_STATUS_SUCCESS 扱いなら m_syncdPolicers に不正な OID が入る可能性あり
```

- `handleSaiCreateStatus` が `task_need_retry` を返した場合のみ `it++`（キュー保留）。
- それ以外 (success / failed) の場合は `erase(it)` により**エントリ消失**（エラーログのみ残る）。
- 消失後は再 SET が必要。

### 3. 不明フィールド — フィールドスキップ後 create 続行

```
policerorch.cpp:478-483
SWSS_LOG_ERROR("Unknown policer attribute %s specified", field.c_str());
continue;  // attrs に push しないでスキップ
```

- エラーログ出力後、当該フィールドを無視して残りを処理。
- `create_policer()` は呼ばれる（欠落フィールドは SAI デフォルト）。

## SET (update) 失敗パターン

### 4. SAI set_policer_attribute 失敗

```
policerorch.cpp:535-546
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to update policer %s attribute, rv:%d", key.c_str(), status);
    if (handleSaiSetStatus(SAI_API_POLICER, status) == task_need_retry)
    {
        it++;
        continue;
    }
}
```

- 属性ごとにループするため、失敗した属性でループを抜けるが、**他属性の処理は継続**しない（`continue` でループ全体から抜けず、外側の while に戻る）。
- `task_need_retry` なら次ループで再試行。それ以外はエラーログのみで `erase(it)`。

### 5. create-only フィールドを UPDATE で送った場合

```
policerorch.cpp:527-533
if (attr.id != SAI_POLICER_ATTR_CBS &&
        attr.id != SAI_POLICER_ATTR_CIR &&
        attr.id != SAI_POLICER_ATTR_PBS &&
        attr.id != SAI_POLICER_ATTR_PIR)
{
    continue;  // SAI に渡さず silently ignore
}
```

- `METER_TYPE` / `MODE` / `COLOR_SOURCE` / `*_PACKET_ACTION` は **エラーなし・サイレント破棄**。
- ログすら出ない。

## DEL 失敗パターン

### 6. DEL で存在しない policer

```
policerorch.cpp:556-560
if (m_syncdPolicers.find(key) == m_syncdPolicers.end())
{
    SWSS_LOG_ERROR("Policer %s does not exists", key.c_str());
    it = consumer.m_toSync.erase(it);  // エラーログ後に消去
    continue;
}
```

- エラーログを出してキューから消去（冪等的に成功扱い）。

### 7. 参照カウント > 0 の間 DEL がブロック

```
policerorch.cpp:563-568
if (m_policerRefCounts[key] > 0)
{
    SWSS_LOG_INFO("Policer %s is still referenced", key.c_str());
    it++;  // キュー保留・ログは INFO
    continue;
}
```

- `SWSS_LOG_INFO` レベル（ERROR ではない）。
- 参照が解放されるまでキューに残り続ける（ハングアップに見える）。

### 8. SAI remove_policer 失敗

```
policerorch.cpp:573-581
SWSS_LOG_ERROR("Failed to remove policer %s, rv:%d", key.c_str(), status);
if (handleSaiRemoveStatus(SAI_API_POLICER, status) == task_need_retry)
{
    it++;
    continue;
}
```

- `task_need_retry` なら保留、そうでなければ `erase(it)` + エラーログのみ。

## storm-control 経由の固有失敗パターン

### 9. Ethernet 以外のインターフェース

```
policerorch.cpp:132-137
SWSS_LOG_ERROR("Unsupported / Invalid interface %s", interface_name.c_str());
return task_process_status::task_success;  // success 扱いで消去
```

- `task_success` を返すため `erase(it)` → 再試行なし。

### 10. ポート未発見 (getPort 失敗)

```
policerorch.cpp:139-144
SWSS_LOG_ERROR("Failed to apply storm-control %s to port %s. Port not found", ...);
return task_process_status::task_success;  // success 扱いで消去
```

- PortsOrch で該当ポートが未登録の場合は `task_success` で消去。

### 11. CIR 欠落 (storm-control)

```
policerorch.cpp:195-200
SWSS_LOG_ERROR("Failed to create storm control policer %s, missing mandatory fields", ...);
return task_process_status::task_failed;
```

- `task_failed` → 呼び出し元 `doTask()` で `erase(it)` → エントリ消失。

### 12. set_port_attribute 失敗 → 作成済み policer を SAI から削除してリトライ

```
policerorch.cpp:291-313
if (status != SAI_STATUS_SUCCESS)
{
    // remove_policer で SAI から SAI policer を削除
    sai_policer_api->remove_policer(m_syncdPolicers[storm_policer_name]);
    m_syncdPolicers.erase(storm_policer_name);
    m_policerRefCounts.erase(storm_policer_name);
    return task_process_status::task_need_retry;
}
```

- SAI policer は作成後に削除され、`m_syncdPolicers` からも消去して `task_need_retry`。
- 次ループで最初から再作成を試みる。
