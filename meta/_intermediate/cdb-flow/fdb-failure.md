# CONFIG_DB FDB — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-fdb)

ソース: `sonic-net/sonic-swss` `orchagent/fdborch.cpp` (master)

## 1. SET 失敗パス / retry マトリクス

`FdbOrch::doTask(Consumer&)` / `addFdbEntry()` を精読し、書込失敗・retry・silent-ignore 経路を抽出した。

| # | トリガー | 検出箇所 | 結果 | retry |
|---|---------|---------|------|-------|
| 1 | VLAN 未作成 (`getPort(keys[0], vlan)` 失敗) | `fdborch.cpp:738-761` | SET は `it++` で次周回再試行。DEL は `deleteFdbEntryFromSavedFDB()` のみ実行 | SET: あり (orchagent select-loop)。DEL: 冪等 |
| 2 | PORT 未作成 / `bridge_port_id == SAI_NULL_OBJECT_ID` | `addFdbEntry()` `fdborch.cpp:1297-1304` | `saved_fdb_entries[port_name]` に push → `return true`（`m_toSync` から消える） | あり (`updateVlanMember(add=true)` で自動 replay) |
| 3 | PORT が VLAN メンバーでない (`isVlanMember()` 失敗) | `addFdbEntry()` `fdborch.cpp:1312-1319` | 同上 `saved_fdb_entries` 保留 | あり (同上) |
| 4 | 不正 `type` 値 | `doTask()` `fdborch.cpp:830` `assert()` | **orchagent プロセスクラッシュ**（NDEBUG 無効ビルド） | なし (fail-fast) |
| 5 | SAI `create_fdb_entry()` 失敗 | `addFdbEntry()` `fdborch.cpp:1534` | `SWSS_LOG_ERROR` → `handleSaiCreateStatus()` 経由 | あり (一時エラー) / プロセス終了 (恒久エラー) |
| 6 | SAI `set_fdb_entry_attribute()` 失敗 (MAC update) | `addFdbEntry()` `fdborch.cpp:1510` | `handleSaiSetStatus()` | 同上 |
| 7 | SAI `remove_fdb_entry()` 失敗 | `removeFdbEntry()` `fdborch.cpp:1701-1710` | `handleSaiRemoveStatus()` | 状況依存 (FIXME コメントあり) |
| 8 | DEL で `m_entries` に存在しない MAC | `removeFdbEntry()` `fdborch.cpp:1646-1654` | `SWSS_LOG_INFO` のみ。`saved_fdb_entries` クリーンアップして `return true` (冪等) | n/a |
| 9 | DEL で `fdbData.origin != origin` | `removeFdbEntry()` `fdborch.cpp:1666-1690` | `deleteFdbEntryFromSavedFDB()` のみ。**silently ignored** | なし (設計上の silent ignore) |
| 10 | 不明 op_type | `doTask()` `fdborch.cpp:917-918` | `SWSS_LOG_ERROR` → `m_toSync.erase` で破棄 | なし |

## 2. VLAN 未解決 retry コード証跡

```cpp
// fdborch.cpp:739-745
if (!m_portsOrch->getPort(keys[0], vlan)) {
    if (op == DEL_COMMAND) {
        deleteFdbEntryFromSavedFDB(...);
        it = consumer.m_toSync.erase(it);
    } else {
        it++;          // SET は erase せず次周回再評価
    }
    continue;
}
```

VLAN が後から作成されると orchagent select-loop 次回スケジュールで `getPort()` が成功する。
明示的な backoff / sleep は無く、orchagent の select-loop 駆動。

## 3. PORT 未解決 → saved_fdb_entries コード証跡

```cpp
// fdborch.cpp:1297-1320  (addFdbEntry 経路)
if (!m_portsOrch->getPort(port_name, port) || (port.m_bridge_port_id == SAI_NULL_OBJECT_ID)) {
    saved_fdb_entries[port_name].push_back({entry.mac, vlan.m_vlan_info.vlan_id, fdbData});
    return true;       // 呼出側からは成功扱い → m_toSync から消える
}
if (!m_portsOrch->isVlanMember(vlan, port, end_point_ip)) {
    saved_fdb_entries[port_name].push_back({...});
    return true;
}
```

observer 登録 (`fdborch.cpp:39`: `m_portsOrch->attach(this)`) により
`updateVlanMember(add=true)` 到着時に自動 replay される (`fdborch.cpp:1240-1275`)。

## 4. SAI 失敗 コード証跡

```cpp
// fdborch.cpp:1530-1545  (create_fdb_entry 失敗)
status = sai_fdb_api->create_fdb_entry(&fdb_entry, (uint32_t)attrs.size(), attrs.data());
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create %s FDB %s in %s on %s, rv:%d",
            fdbData.type.c_str(), entry.mac.to_string().c_str(),
            vlan.m_alias.c_str(), port_name.c_str(), status);
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_FDB, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

`handleSaiCreateStatus` / `handleSaiSetStatus` / `handleSaiRemoveStatus` は
`Orch` 基底クラスで定義され、status code 別に `task_success` / `task_need_retry` /
`task_failed` を返す。それ以外は `parseHandleSaiStatusFailure()` でプロセス終了。

## 5. 不正 type → assert コード証跡

```cpp
// fdborch.cpp:830
assert(type == "dynamic" || type == "dynamic_local" || type == "static");
```

NDEBUG 無効（デバッグビルド）では orchagent がクラッシュ。
リリースビルドでは assert が消え、その後の SAI type mapping で未定義動作になり得る。

## 6. silent ignore パターン

| 経路 | 箇所 | 理由 |
|---|---|---|
| DEL with `m_entries` 未登録 MAC | L1646 | 二重 DEL / 学習前 DEL の冪等性確保 |
| DEL with `fdbData.origin != origin` | L1666 | クロス origin 削除を抑止 (BGP remote → local 移行 MAC を保護) |

## 7. STATE_DB への失敗反映

`FdbOrch` は STATE_DB の `ERROR_*` 系には書込まない。失敗時の参照点は syslog のみ。
成功したローカル MAC のみ STATE_DB `FDB_TABLE` (`m_fdbStateTable`) に書込まれる
(`fdborch.cpp:1569-1582`)。

## 8. 観測手段

```bash
# 失敗ログ抽出
docker logs swss 2>&1 | grep -iE 'fdborch|fdb.*fail|Failed to (create|remove) FDB|Saving a fdb entry'

# saved_fdb の確認 (orchagent 再起動時の warm restart ログ)
docker logs swss 2>&1 | grep -i 'saved.*fdb\|Add warm input FDB State'
```
