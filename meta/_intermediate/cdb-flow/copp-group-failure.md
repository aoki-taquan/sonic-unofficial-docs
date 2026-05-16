# COPP_GROUP 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/copp-group.md` Phase D block.

## 調査対象ソース

- `sonic-swss/orchagent/copporch.cpp` (全行スキャン)
- `sonic-swss/cfgmgr/coppmgr.cpp` (全行スキャン)

スキャン範囲:
- `processCoppTrapGroup()` L737-877
- `doCoppTask()` L880-933
- `trapGroupUpdatePolicer()` L1297-1368
- `parseTrapGroupAttribute()` L1200-1294
- `createPolicer()` L597-654
- `createGenetlinkHostIf()` L657-692
- `CoppMgr::parseInitFile()` L22-57
- `CoppMgr::mergeConfig()` L196-257

---

## 失敗パス一覧

### 1. 未知フィールド名 → `parseTrapGroupAttribute()` false → `task_failed` → orchagent 終了

`copporch.cpp:1290-1291`:

```cpp
SWSS_LOG_ERROR("Unknown copp field specified:%s\n", fvField(*i).c_str());
return false;
```

`parseTrapGroupAttribute()` が false を返すと `processCoppTrapGroup()` の SET 処理が `task_failed` を返す。`doCoppTask()` の dispatch ループで:

```cpp
case task_process_status::task_failed:
    it = consumer.m_toSync.erase(it);
    SWSS_LOG_ERROR("Processing copp task item failed, exiting. ");
    return;   // L922-923 — doTask() 全体から即 return
```

**エントリを queue から除去し orchagent の `doTask()` ループを終了（事実上の処理停止）。retry なし。rollback なし。orchagent プロセス自体は継続するが、当該 Consumer の pending キュー処理は再起動まで停止。**

---

### 2. SAI `create_hostif_trap_group` 失敗 → `handleSaiCreateStatus()` 経由で task_failed またはリトライ

`copporch.cpp:781-788`:

```cpp
sai_status = sai_hostif_api->create_hostif_trap_group(...);
if (sai_status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create host interface trap group %s, rc=%d", ...);
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_HOSTIF, sai_status);
    if (handle_status != task_process_status::task_success)
    {
        return handle_status;  // task_failed or task_need_retry
    }
}
```

`handleSaiCreateStatus()` の戻り値に応じて:

- `task_need_retry` → `doCoppTask()` で `it++` (無制限 retry)
- `task_failed` → orchagent の doTask() ループ終了

SAI 側の一時エラー（リソース不足等）は `task_need_retry`、恒久的エラーは `task_failed` となる傾向。

---

### 3. policer の meter / mode / color 変更不可 → エラーログのみ・他属性は更新継続

`copporch.cpp:1327-1350`:

```cpp
// CREATE_ONLY 属性の変更はクラッシュ原因となるため、エラーログを出力してスキップ
if(policer_attr.id == SAI_POLICER_ATTR_METER_TYPE)
{
    if (policer_object.meter != (sai_meter_type_t)policer_attr.value.s32)
        SWSS_LOG_ERROR("Trying to modify policer attribute: (meter), trap group: (%s)", ...);
    continue;  // skip, 他属性の更新は続行
}
// mode, color も同様
```

**task_failed にはならない。エラーログのみ出力し、変更可能な他属性（`cir`/`cbs`/`pir`/`pbs`/`*_action`）の更新は継続する。meter/mode/color を変更するには DEL + 再 SET が必要。**

---

### 4. policer の SAI set 失敗 → `handleSaiSetStatus()` 経由で task_failed またはリトライ

`copporch.cpp:1354-1363`:

```cpp
sai_status_t sai_status = sai_policer_api->set_policer_attribute(policer_id, &policer_attr);
if (sai_status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to apply attribute[%d].id=%d to policer for trap group:%s, error:%d\n", ...);
    task_process_status handle_status = handleSaiSetStatus(SAI_API_POLICER, sai_status);
    if (handle_status != task_success)
        return parseHandleSaiStatusFailure(handle_status);
}
```

`parseHandleSaiStatusFailure()` は `handle_status` を `bool` (false) に変換 → `trapGroupUpdatePolicer()` が false を返す → `processCoppTrapGroup()` で `task_failed` → doTask() ループ終了。

---

### 5. Genetlink hostif が既存 → `task_failed` (二重登録拒否)

`copporch.cpp:835-840`:

```cpp
if (m_trap_group_hostif_map.find(m_trap_group_map[trap_group_name]) !=
        m_trap_group_hostif_map.end())
{
    SWSS_LOG_ERROR("Genetlink hostif exists for the trap group %s", trap_group_name.c_str());
    return task_process_status::task_failed;
}
```

`genetlink_name` フィールドを持つエントリを SET し直す場合、既存の genetlink hostif が map に残っていると即 `task_failed`。**retry なし。rollback なし。DEL して再 SET でリカバリ。**

---

### 6. DEL で default グループ削除試行 → `task_ignore` (サイレント拒否)

`copporch.cpp:860-864`:

```cpp
if (trap_group_name == default_trap_group)
{
    SWSS_LOG_WARN("Cannot remove default trap group");
    return task_process_status::task_ignore;
}
```

`doCoppTask()` では `task_ignore` は `task_success` と同扱いで erase される。エラーにはならないがハードウェアへの反映も行われない。**WARNログのみ。エントリは queue から除去される。**

---

### 7. 未知 op type → `task_invalid_entry` → erase (no retry)

`copporch.cpp:873-876`:

```cpp
SWSS_LOG_ERROR("Unknown copp operation type %s\n", op.c_str());
return task_process_status::task_invalid_entry;
```

`doCoppTask()`:

```cpp
case task_process_status::task_invalid_entry:
    SWSS_LOG_ERROR("Invalid copp task item was encountered, removing from queue.");
    it = consumer.m_toSync.erase(it);
    break;
```

**エントリを除去して次へ。retry なし。doTask() ループは継続。**

---

### 8. out_of_range / exception 例外 → `task_invalid_entry` → erase (no retry)

`copporch.cpp:900-908`:

```cpp
catch(const out_of_range& e)
{
    SWSS_LOG_ERROR("processing copp rule threw out_of_range exception:%s", e.what());
    task_status = task_process_status::task_invalid_entry;
}
catch(exception& e)
{
    SWSS_LOG_ERROR("processing copp rule threw exception:%s", e.what());
    task_status = task_process_status::task_invalid_entry;
}
```

`m_trap_group_map` / `m_trap_group_policer_map` 等への未存在キーアクセスなどで発生しうる。**erase して続行。**

---

### 9. init ファイル未検出 → coppmgr の初期設定スキップ

`coppmgr.cpp:26-30`:

```cpp
if (ifs.fail())
{
    SWSS_LOG_ERROR("COPP init file %s not found", m_coppCfgfile.c_str());
    return;
}
```

`/etc/sonic/copp_cfg.json` が存在しない場合、`parseInitFile()` が即 return する。この場合 `m_coppGroupInitCfg` が空のまま `mergeConfig()` が呼ばれ、CONFIG_DB のユーザー設定だけが APPL_DB に書き込まれる。デフォルト CoPP ポリシーが適用されず、意図しないトラフィック通過が発生しうる。

---

## retry パターンサマリ

| パターン | 対象ケース | 挙動 | 影響範囲 |
|---|---|---|---|
| `doTask() return` (実質停止) | 未知フィールド / policer SAI 恒久エラー | doTask ループ終了 | 当該 Consumer の後続処理が停止 |
| `task_need_retry` → `it++` | SAI 一時エラー (create/set) | 無制限 retry | 正常完了まで繰り返す |
| `task_invalid_entry` → erase | unknown op / exception | erase して次へ進む | 当該エントリのみ破棄 |
| `task_ignore` → erase | default グループ DEL 試行 | WARN ログ、erase | ハードウェア変更なし |
| エラーログのみ / continue | policer meter/mode/color 変更試行 | スキップして他属性更新 | 当該属性のみ無視 |

---

## config rollback 挙動

- CONFIG_DB のエントリは erase 後も残る（orchagent / coppmgr は CONFIG_DB を書き戻さない）
- `task_failed` 後は orchagent の doTask() ループが終了し、後続の COPP 更新が処理されない
- `meter` / `mode` / `color` の変更は黙示的にスキップされる（ハードウェアへの反映ゼロ）
- CoPP 設定の変更は `DEL` → `SET` の順で再投入するとリカバリ可能
- `COPP_GROUP` に対する STATE_DB / ERROR_TABLE への書き込みはなし（syslog のみ）
