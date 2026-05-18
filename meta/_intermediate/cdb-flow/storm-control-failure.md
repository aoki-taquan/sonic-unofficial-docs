# PORT_STORM_CONTROL テーブル — Phase D 失敗挙動スキャンノート

対象テーブル: `CONFIG_DB PORT_STORM_CONTROL`
Consumer: `PolicerOrch::handlePortStormControlTable()` / `doTask()` (`sonic-swss/orchagent/policerorch.cpp`)
スキャン範囲: `policerorch.cpp` 全行（589 行）

---

## 検出した失敗パス

### 1. `kbps` フィールド欠如 → `task_failed` でエントリ erase

`policerorch.cpp:194-200`:

```cpp
if (!cir)
{
    SWSS_LOG_ERROR("Failed to create storm control policer %s, missing mandatory fields",
            storm_policer_name.c_str());
    return task_process_status::task_failed;
}
```

- `task_failed` を返す → `doTask()` L398-400 で `consumer.m_toSync.erase(it)` が呼ばれエントリは破棄される
- リトライなし。syslog ERROR のみ

### 2. 不明な `storm_type` → `task_failed`

SET パス (`policerorch.cpp:217-220`):

```cpp
SWSS_LOG_ERROR("Unknown storm_type %s", storm_type.c_str());
return task_process_status::task_failed;
```

DEL パス (`policerorch.cpp:337-340`) でも同様に `task_failed`。

有効な storm_type は `"broadcast"` / `"unknown-unicast"` / `"unknown-multicast"` のみ（YANG enum で拒否されるはずだが、直接 DB 書き込み時はこのパスに到達する）。

### 3. `sai_policer_api->create_policer()` 失敗

`policerorch.cpp:226-235`:

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create policer %s, rv:%d", ...);
    if (handleSaiCreateStatus(SAI_API_POLICER, status) == task_need_retry)
    {
        return task_process_status::task_need_retry;
    }
}
```

- SAI status が `SAI_STATUS_ITEM_ALREADY_EXISTS` 等の場合は `handleSaiCreateStatus` が `task_success` を返す可能性あり（swss 共通実装）
- `task_need_retry` → `m_toSync` に残り次回 `doTask()` でリトライ
- 注意: `create_policer` が失敗しても `m_syncdPolicers` へのエントリ登録は `L239` で create 成功後に行われるため、失敗時はキャッシュ汚染なし

### 4. `sai_port_api->set_port_attribute()` 失敗（policer アタッチ）

`policerorch.cpp:291-313`:

```cpp
sai_status_t status = sai_port_api->set_port_attribute(port.m_port_id, &port_attr);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to apply storm-control %s to port %s, rv:%d", ...);
    // remove_policer を試みる（失敗してもログのみ）
    if (SAI_STATUS_SUCCESS != sai_policer_api->remove_policer(m_syncdPolicers[storm_policer_name]))
    {
        SWSS_LOG_ERROR("Failed to remove policer %s, rv:%d", ...);
        /* TODO: Just doing a syslog. */
    }
    m_syncdPolicers.erase(storm_policer_name);
    m_policerRefCounts.erase(storm_policer_name);
    return task_process_status::task_need_retry;
}
```

- SAI ポートアタッチ失敗時、orchagent は作成済み policer の `remove_policer` を試みる
- `remove_policer` が失敗した場合: syslog ERROR のみ、SAI 側にリソースリークの可能性（TODO コメント残存）
- `m_syncdPolicers` / `m_policerRefCounts` は erase されるため orchagent キャッシュは整合性を失う（SAI 側に孤立 policer が残る可能性）
- `task_need_retry` → 次回 `doTask()` でリトライ

### 5. DEL 時: policer 未登録 → `task_success` erase

`policerorch.cpp:317-320`:

```cpp
if (m_syncdPolicers.find(storm_policer_name) == m_syncdPolicers.end())
{
    SWSS_LOG_ERROR("Policer %s not configured", storm_policer_name.c_str());
    return task_process_status::task_success;
}
```

- `task_success` → `m_toSync` から erase（リトライなし）
- 存在しない policer への DEL は冪等に処理される

### 6. DEL 時: `set_port_attribute` (NULL デタッチ) 失敗

`policerorch.cpp:344-352`:

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to remove storm-control %s from port %s, rv:%d", ...);
    if (handleSaiRemoveStatus(SAI_API_POLICER, status) == task_need_retry)
    {
        return task_process_status::task_need_retry;
    }
}
```

- `task_need_retry` の場合は次回 `doTask()` でリトライ
- `task_success` の場合は後続の `remove_policer` が実行される（SAI アタッチ解除に失敗しても policer 削除を試みる設計）

### 7. DEL 時: `remove_policer` 失敗

`policerorch.cpp:355-364`:

```cpp
status = sai_policer_api->remove_policer(m_syncdPolicers[storm_policer_name]);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to remove policer %s, rv:%d", ...);
    if (handleSaiRemoveStatus(SAI_API_POLICER, status) == task_need_retry)
    {
        return task_process_status::task_need_retry;
    }
}
```

- `handleSaiRemoveStatus` が `task_need_retry` → `m_toSync` に残りリトライ
- `task_success` → `L367-369` で `m_syncdPolicers.erase()` / `m_policerRefCounts.erase()` が呼ばれ orchagent キャッシュはクリアされるが SAI 側に孤立 policer が残る

---

## 失敗パス サマリ

| # | 失敗トリガー | `task_` 戻り値 | 再試行 | SAI 影響 |
|---|------------|--------------|--------|---------|
| 1 | `kbps` 欠如 | `task_failed` | なし | SAI 変更なし |
| 2 | 不明 storm_type | `task_failed` | なし | SAI 変更なし |
| 3 | `create_policer` SAI エラー | `task_need_retry` | あり | SAI 変更なし |
| 4 | `set_port_attribute` SAI エラー (アタッチ) | `task_need_retry` | あり | 孤立 policer リーク可能性 |
| 5 | DEL: policer 未登録 | `task_success` | なし | SAI 変更なし |
| 6 | DEL: `set_port_attribute` NULL エラー | `task_need_retry` | あり | SAI デタッチ失敗 |
| 7 | DEL: `remove_policer` SAI エラー | `task_need_retry` | あり | SAI 孤立 policer 残存 |
