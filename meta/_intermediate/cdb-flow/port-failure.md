# PORT 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/port.md` Phase D block.

## 調査対象ソース

- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/cfgmgr/portmgr.cpp`

---

## 失敗パス一覧

### 0a. lanes 不一致 → `return false` (ポート作成失敗)

`portsorch.cpp:4025-4031` (`initPort()`):

```cpp
if (m_portListLaneMap.find(lane_set) == m_portListLaneMap.end())
{
    SWSS_LOG_ERROR("Failed to locate port lane combination alias:%s", alias.c_str());
    return false;
}
```

CONFIG_DB の `lanes` フィールドが HW の lane map に存在しない場合、`initPort()` は即 `false` を返してポートを作成しない。
**retry なし。CONFIG_DB の値は残る。`lanes` を正しい値に修正して再設定が必要。**

---

### 0b. SAI `create_ports()` 一括失敗 → `SWSS_LOG_THROW` (orchagent abort)

`portsorch.cpp:1450-1479` (`addPortBulk()`):

```cpp
// バッチ全体失敗
SWSS_LOG_ERROR("Failed to create ports with bulk operation, rv:%d", status);
if (handle_status != task_process_status::task_success)
{
    SWSS_LOG_THROW("PortsOrch bulk create failure");
}

// 個別ポート失敗
SWSS_LOG_ERROR("Failed to create port %s with bulk operation, rv:%d",
    portList.at(i).key.c_str(), statusList.at(i));
if (handle_status != task_process_status::task_success)
{
    SWSS_LOG_THROW("PortsOrch bulk create failure");
}
```

SAI `sai_port_api->create_ports()` が `SAI_STATUS_SUCCESS` 以外を返した場合、またはバッチ内の個別ポートが失敗した場合、`handleSaiCreateStatus` 判定後に `SWSS_LOG_THROW` でプロセス abort。
**retry なし。orchagent は supervisor により再起動される。**

---

### 0c. 非サポート speed → タスク削除 (erase, no retry)

`portsorch.cpp:5024-5033`:

```cpp
if (!isSpeedSupported(p.m_alias, p.m_port_id, pCfg.speed.value))
{
    SWSS_LOG_ERROR("Unsupported port %s speed %u", p.m_alias.c_str(), pCfg.speed.value);
    // Speed not supported, dont retry
    it = taskMap.erase(it);
    continue;
}
```

`isSpeedSupported()` が SAI の速度能力リスト (`SAI_PORT_ATTR_SUPPORTED_SPEED`) を取得できないプラットフォームでは `SWSS_LOG_WARN "Unable to validate speed ..."` を出して検証をスキップし、任意値を SAI に渡す (`portsorch.cpp:3144-3148`)。
**retry なし (erase)。portmgrd 経由で APP_DB は更新されても SAI への speed 設定は行われない。**

---

### 1. `m_pendingPortSet` — Buffer Not Ready → 保留 (暗黙 retry)

`portsorch.cpp:4779-4784`:

```cpp
if (!gBufferOrch->isPortReady(pCfg.key))
{
    m_pendingPortSet.emplace(pCfg.key);
    it++;   // タスクを保留キューに積んでスキップ
    continue;
}
```

BUFFER_PG/BUFFER_POOL が未設定の間、PORT の SAI 反映を保留し `m_pendingPortSet` に追加する。
`isPortReady()` が true になる次の doTask() サイクルで自動的にリトライされる。
**retry: 無制限（BUFFER 系が設定されるまで）。rollback なし。**

---

### 2. `autoneg` 非サポート HW → task_failed 相当 (erase + no retry)

`portsorch.cpp:4817-4822`:

```cpp
if (p.m_cap_an < 1)
{
    SWSS_LOG_ERROR("%s: autoneg is not supported (cap=%d)", p.m_alias.c_str(), p.m_cap_an);
    // autoneg is not supported, don't retry
    it = taskMap.erase(it);
    continue;
}
```

autoneg の HW 能力フラグが非サポート (`m_cap_an < 1`) の場合、タスクをキューから即座に削除。
**retry なし。rollback なし (CONFIG_DB の値は残る)。**

---

### 3. `setPortAdminStatus` 失敗 (autoneg 変更前 down 操作) → it++ retry

`portsorch.cpp:4827-4835`:

```cpp
if (!setPortAdminStatus(p, false))
{
    SWSS_LOG_ERROR(
        "Failed to set port %s admin status DOWN to set port autoneg mode",
        p.m_alias.c_str()
    );
    it++;   // タスクを次サイクルにリトライ
    continue;
}
```

speed/fec/autoneg 変更時の「一時 DOWN」操作が SAI で失敗した場合、タスクを次のサイクルに持ち越す。
**retry: 無制限 (it++ pattern)。rollback なし。**

---

### 4. `setPortAutoNeg` 失敗 → task_need_retry / task_failed 分岐

`portsorch.cpp:4841-4856`:

```cpp
auto status = setPortAutoNeg(p, pCfg.autoneg.value);
if (status != task_success)
{
    SWSS_LOG_ERROR("Failed to set port %s AN from %d to %d", ...);
    if (status == task_need_retry)
    {
        it++;               // 次サイクルにリトライ
    }
    else
    {
        it = taskMap.erase(it);  // task_failed: 永続エラー、タスク削除
    }
    continue;
}
```

SAI `set_port_attribute(SAI_PORT_ATTR_AUTO_NEG_MODE)` の結果で分岐:
- `task_need_retry`: 一時的エラー、次サイクルで再試行
- `task_failed`: 永続エラー (`SAI_STATUS_NOT_SUPPORTED` など)、タスク削除

---

### 5. `link_training` 非サポート → SWSS_LOG_WARN + erase (no retry)

`portsorch.cpp:4881-4886`:

```cpp
if (p.m_cap_lt < 1)
{
    SWSS_LOG_WARN("%s: LT is not supported(cap=%d)", p.m_alias.c_str(), p.m_cap_lt);
    // Don't retry
    it = taskMap.erase(it);
    continue;
}
```

link_training 非サポート HW では WARN レベル (autoneg と異なり ERROR でない) でタスク削除。
**retry なし。rollback なし。**

---

### 6. `setPortLinkTraining` 失敗 → task_need_retry / task_failed 分岐

`portsorch.cpp:4889-4904`: autoneg と同パターン。SAI 結果に応じて it++ or erase。

---

### 7. `fast_linkup` 失敗 → task_failed 固定 (erase)

`portsorch.cpp:4929-4935`:

```cpp
// For fast_linkup attribute, task_need_retry is not a meaningful return,
// so treat any failure as a permanent failure and erase the task.
if (status != task_success)
{
    SWSS_LOG_ERROR("Failed to set port %s fast_linkup to %s", ...);
    it = taskMap.erase(it);
    continue;
}
```

`fast_linkup` は `task_need_retry` を永続失敗と同様に扱い、常にタスク削除。
**retry なし。rollback なし。**

---

### 8. `speed` 変更 — setPortAdminStatus 失敗 → it++ retry

`portsorch.cpp:5040-5045`: speed 変更前の一時 DOWN 失敗は it++ (autoneg と同パターン)。

---

### 9. `setPortSpeed` 失敗 → task_need_retry / task_failed 分岐

`portsorch.cpp:5052-5067`:

```cpp
auto status = setPortSpeed(p, pCfg.speed.value);
if (status != task_success)
{
    SWSS_LOG_ERROR("Failed to set port %s speed from %u to %u", ...);
    if (status == task_need_retry) { it++; }
    else { it = taskMap.erase(it); }
    continue;
}
```

SAI speed 設定の `task_need_retry` / `task_failed` 分岐。`isSpeedSupported()` が false の場合は
この手前で SWSS_LOG_ERROR + erase (portsorch.cpp 付近の isSpeedSupported チェック)。

---

### 10. `setPortAdvSpeeds` 失敗 → task_need_retry / task_failed 分岐

`portsorch.cpp:5103-5118`: 同パターン。

---

### 11. `setPortInterfaceType` 失敗 → task_need_retry / task_failed 分岐

`portsorch.cpp:5153-5168`: 同パターン。

---

### 12. `MTU` 設定失敗 → it++ retry (永続)

`portsorch.cpp:5257-5265`:

```cpp
if (!setPortMtu(p, pCfg.mtu.value))
{
    SWSS_LOG_ERROR("Failed to set port %s MTU to %u", ...);
    it++;   // 次サイクルにリトライ
    continue;
}
```

SAI `set_port_attribute(SAI_PORT_ATTR_MTU)` 失敗は task_need_retry 相当で常にリトライ。
`task_failed` 扱いはなし。**retry: 無制限。rollback なし。**

---

### 13. `TPID` 設定失敗 → it++ retry

`portsorch.cpp:5292-5299`: MTU と同パターン。it++ で無制限リトライ。

---

### 14. `fec=auto` 非サポート → SWSS_LOG_ERROR + erase (no retry)

`portsorch.cpp:5317-5321`:

```cpp
if (!pCfg.fec.override_fec && !fec_override_sup)
{
    SWSS_LOG_ERROR("Auto FEC mode is not supported");
    it = taskMap.erase(it);
    continue;
}
```

`SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE` 非サポートプラットフォームで `fec=auto` を設定すると永続失敗。
**retry なし。rollback なし (CONFIG_DB に `fec: auto` が残り続ける)。**

---

### 15. `fec` 非サポートモード → erase (no retry)

`portsorch.cpp:5323-5331`:

```cpp
if (!isFecModeSupported(p, pCfg.fec.value))
{
    SWSS_LOG_ERROR("Unsupported port %s FEC mode %s", ...);
    // FEC mode is not supported, don't retry
    it = taskMap.erase(it);
    continue;
}
```

---

### 16. `setPortFec` 失敗 → it++ retry

`portsorch.cpp:5356-5364`: SAI FEC 設定失敗は it++ リトライ。

---

### 17. `setPortAdminStatus` 失敗 (最終ステップ) → it++ retry

`portsorch.cpp:5511-5518`: 最終 admin_status 設定失敗も it++ リトライ。

---

### 18. `pfc_asym` 失敗 → it++ retry (サポート HW のみ)

`portsorch.cpp:5413-5421`: `m_portCap.isPortPfcAsymSupported()` が false なら WARN + スキップ(silent)。
サポート HW で setPortPfcAsym 失敗 → it++ リトライ。

---

### 19. `adv_interface_types` 失敗 → task_need_retry / task_failed 分岐

`portsorch.cpp:5224-5239`: 同パターン。

---

### 20. portmgrd: MTU netdev 設定失敗 → SWSS_LOG_WARN + return false (no retry)

`portmgr.cpp:43-44`:

```cpp
SWSS_LOG_WARN("Setting mtu to alias:%s netdev failed with cmd:%s, rc:%d, error:%s", ...);
return false;
```

portmgrd が `ip link set dev <alias> mtu <mtu>` を実行した際:
- `isPortStateOk(alias) == false` (ポートが STATE_DB に未登録): WARN + return false
- `isPortStateOk(alias) == true` かつ ip コマンド失敗: WARN + return false
- 呼び出し元 `doTask()` は戻り値を無視してタスクを `it = consumer.m_toSync.erase(it)` で削除
- **retry なし。APP_DB への書き込みは行われない (writeConfigToAppDb は呼ばれない)。**

---

### 21. portmgrd: admin_status netdev 設定失敗 → SWSS_LOG_WARN + return false / throw

`portmgr.cpp:73-82`:

```cpp
else if (!isPortStateOk(alias))
{
    SWSS_LOG_WARN("Setting admin_status to alias:%s netdev failed ...", ...);
    return false;
}
else
{
    throw runtime_error(cmd_str + " : " + res);
}
```

- `isPortStateOk == false` → WARN + return false (portOk 未確立時の競合)
- `isPortStateOk == true` かつ ip コマンド失敗 → `runtime_error` throw → portmgrd プロセスが abort → 上位 supervisor が restart

---

### 22. portmgrd: PortStateOk = false (ポート未初期化) → 保留 + it++ retry

`portmgr.cpp:180-184`:

```cpp
else if (!portOk)
{
    it++;
    continue;
}
```

ポートが STATE_DB に未登録 (`isPortStateOk == false`) かつ既に configured 済みの場合、タスクを次サイクルに保留。
**retry: 無制限 (PortsOrch が PortInitDone を通知するまで)。**

---

### 23. `setPortLinkTraining` — PHY 以外のポート → task_failed

`portsorch.cpp:3712-3716`:

```cpp
if (port.m_type != Port::PHY)
{
    return task_failed;
}
```

link_training は PHY タイプ以外には設定できない。task_failed を返し、呼び出し元でタスク削除。

---

## 失敗時の admin_status restore (replay) 挙動

`portsorch.cpp:5499-5504`:

```cpp
// Restore admin status if the port was brought down
if (admin_status != p.m_admin_state_up && pCfg.admin_status.is_set == false)
{
    pCfg.admin_status.is_set = true;
    pCfg.admin_status.value = admin_status;
}
```

speed/fec/autoneg 変更のために一時 DOWN したポートは、処理失敗でも次サイクルに restore replay される。
- 処理途中で `continue` した場合でも、次の doTask() で同 pCfg が再処理されると admin_status が最終ステップで復元される
- **ただし continue したサイクルでは admin_status 復元は行われない** — ポートが DOWN のまま残る可能性がある

---

## STATE_DB / ERROR_TABLE への記録

- PortsOrch は失敗時に STATE_DB の `PORT_TABLE` へ error フィールドを書き込まない (ERROR_TABLE 不使用)
- link_training ステータスは `m_portStateTable.hset(p.m_alias, "link_training_status", ...)` に記録 (成功時のみ)
- 失敗はすべて SWSS_LOG_ERROR / SWSS_LOG_WARN のみ。syslog に記録される

---

## サマリ: retry パターン分類

| パターン | 対象フィールド | 挙動 |
|---|---|---|
| `m_pendingPortSet` 保留 | 全フィールド | BUFFER 未設定中は無制限保留 |
| `it++` (無制限 retry) | MTU, TPID, admin_status, setPortAdminStatus 一時 DOWN, pfc_asym (supported HW), setPortFec, portmgrd portOk 待ち | 永続リトライ |
| `task_need_retry` → `it++` | autoneg, link_training, speed, adv_speeds, interface_type, adv_interface_types | SAI 一時エラー時にリトライ |
| `task_failed` → `erase` | autoneg 非サポート HW, link_training 非サポート HW, fast_linkup, fec=auto 非サポート, fec 非サポートモード, link_training on non-PHY port | 永続エラー、タスク削除 (CONFIG_DB の値は残る) |
| portmgrd `return false` | MTU netdev, admin_status netdev (isPortStateOk=false) | WARN + タスク消去 (retry なし) |
| portmgrd `throw` | admin_status netdev (isPortStateOk=true, ip コマンド失敗) | プロセス abort → supervisor restart |
