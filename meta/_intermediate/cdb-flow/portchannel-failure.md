# PORTCHANNEL 失敗挙動調査 (Phase D)

調査日: 2026-05-15
対象: `docs/reference/config-db/portchannel.md`
ソース: `sonic-swss/cfgmgr/teammgr.cpp`

## 1. addLag() 失敗 → task_need_retry

### コード証跡: `teammgr.cpp:640-644`

```cpp
if (exec(cmd.str(), res) != 0)
{
    SWSS_LOG_INFO("Failed to start port channel %s with teamd, retry...",
            alias.c_str());
    return task_need_retry;
}
```

- `teamd` プロセス起動コマンド失敗時に `task_need_retry` を返す。
- 呼び出し元 `doLagTask()` (line 303-308) は `addLag()` が `task_need_retry` を返した場合、
  孤立した teamd プロセスをクリーンアップするため `removeLag(alias)` を呼び出した後に `it++` して次ループへ。
- エントリは `m_toSync` から消去されず、次の select ループで再試行される。

### doLagTask() での処理 (line 301-311):

```cpp
if (m_lagList.find(alias) == m_lagList.end())
{
    if (addLag(alias, min_links, fallback, fast_rate) == task_need_retry)
    {
        // If LAG creation fails, we need to clean up any potentially orphaned teamd processes
        removeLag(alias);
        it++;
        continue;
    }
    m_lagList.insert(alias);
}
```

## 2. addLagMember() 失敗 → task_need_retry / task_failed

### コード証跡: `teammgr.cpp:769-788`

```cpp
if (exec(cmd.str(), res) != 0)
{
    if (checkPortIffUp(member))
    {
        SWSS_LOG_INFO("Failed to add %s to port channel %s, retry...",
                member.c_str(), lag.c_str());
        return task_need_retry;
    }
    else
    {
        SWSS_LOG_ERROR("Failed to add %s to port channel %s",
                member.c_str(), lag.c_str());
        return task_failed;
    }
}
```

- `teamdctl port add` が失敗した場合、ポートが admin-up 状態にある (`IFF_UP` フラグ確認) かを `checkPortIffUp()` で判定。
- **admin-up の場合**: portmgrd 等の競合処理中とみなし `task_need_retry` → 再試行。
- **admin-down の場合**: 根本的エラーと判断し `task_failed` → SWSS_LOG_ERROR ログ出力、エントリ破棄。

### doLagMemberTask() / doPortUpdateTask() での処理 (line 367-371, 467-472):

```cpp
if (addLagMember(lag, member) == task_need_retry)
{
    it++;
    continue;
}
```

## 3. doLagMemberTask() での前提条件チェック

### コード証跡: `teammgr.cpp:357-366`

```cpp
if (!isPortStateOk(member) || !isLagStateOk(lag))
{
    it++;
    continue;
}
if (isMACsecAttached(member) && !isMACsecIngressSAOk(member))
{
    it++;
    continue;
}
```

- ポートの STATE_DB 状態が OK でない場合 → 暗黙 retry（ログなし、エントリ保持）。
- LAG の STATE_DB 状態が OK でない場合 → 暗黙 retry。
- MACsec 付きポートで Ingress SA 未確立 → 暗黙 retry（SWSS_LOG_INFO のみ）。

## 4. doPortUpdateTask() — ポート再作成後の自動再スレーブ

### コード証跡: `teammgr.cpp:439-472`

ポートが削除・再作成された場合、STATE_DB 更新通知で `doPortUpdateTask()` が呼ばれ、
`findPortMaster()` で該当 LAG を特定して `addLagMember()` を再試行する。
これはポート flap / kernel netdev 再作成 (e.g., SFP 抜差し) 後のリカバリ機構。

## 5. removeLag() 失敗条件

### コード証跡: `teammgr.cpp:657-676`

```cpp
ifstream pidfile("/var/run/teamd/" + alias + ".pid");
if (pidfile.is_open())
{
    pidfile >> pid;
}
else
{
    SWSS_LOG_NOTICE("Failed to remove non-existent port channel %s pid...", alias.c_str());
    return false;
}

if (kill(pid, SIGTERM))
{
    SWSS_LOG_ERROR("Failed to send SIGTERM to port channel %s pid %d: %s", alias.c_str(), pid, strerror(errno));
    return false;
}
```

- `/var/run/teamd/<alias>.pid` が存在しない場合: SWSS_LOG_NOTICE で false 返却（エラーではない）。
- SIGTERM 送信失敗: SWSS_LOG_ERROR で false 返却。

## 6. 不正 MAC / DEVICE_METADATA 取得失敗 — デーモン起動時クラッシュ

### コード証跡: `teammgr.cpp:52-64`

```cpp
// Get the MAC address from configuration database
auto it = find_if(fvVector.begin(), fvVector.end(),
    [](const FieldValueTuple& fv) { return fv.first == "mac"; });
if (it == fvVector.end())
{
    throw runtime_error("Failed to get MAC address from configuration database");
}
m_mac = MacAddress(it->second);
```

- `DEVICE_METADATA|localhost` に `mac` フィールドが存在しない場合、コンストラクタで `std::runtime_error` を throw。
- `teammgrd` プロセスがクラッシュし、全 PORTCHANNEL エントリの処理が停止する。
- 対策: `DEVICE_METADATA` テーブルを正しく設定した上で `teammgrd` を再起動。

## 7. SAI LAG 作成失敗 (orchagent / LagOrch)

### コード証跡: `portsorch.cpp` (LagOrch)

```cpp
// LAG ID 払い出し失敗 (VoQ 環境)
SWSS_LOG_ERROR("Failed to allocate unique LAG id for local lag %s rv:%d",
               alias.c_str(), rv);

// SAI create_lag() 失敗
SWSS_LOG_ERROR("Failed to create LAG %s lid:", alias.c_str());
```

- VoQ スイッチ環境で `LagIdAllocator` がユニーク ID を払い出せない場合: SWSS_LOG_ERROR + エントリ破棄。
- ASIC/SAI が `create_lag()` を拒否した場合 (リソース枯渇等): SWSS_LOG_ERROR + エントリ破棄。
- 失敗したエントリは orchagent によって再試行されない。`config portchannel del` → `config portchannel add` で再投入が必要。

## 8. retry ループ上限

`teammgrd` の select ループには `task_need_retry` のリトライ上限カウンタは存在しない。
`m_toSync` はエントリを保持し続け、次の select イテレーションで再試行される（無限リトライ）。
ただし、依存状態 (teamd 起動環境、ポート状態) が解消されれば自然に成功する設計。

## まとめ

| 失敗シナリオ | 戻り値 | ログ | リカバリ |
|---|---|---|---|
| `teamd` 起動失敗 | `task_need_retry` | SWSS_LOG_INFO + orphan cleanup | 次ループで再試行 |
| `teamdctl port add` 失敗 + port admin-up | `task_need_retry` | SWSS_LOG_INFO | 次ループで再試行 |
| `teamdctl port add` 失敗 + port admin-down | `task_failed` | SWSS_LOG_ERROR | エントリ破棄（手動介入必要） |
| ポート STATE_DB 未準備 | 暗黙 continue | なし | STATE_DB 更新待ち |
| LAG STATE_DB 未準備 | 暗黙 continue | なし | STATE_DB 更新待ち |
| MACsec Ingress SA 未確立 | 暗黙 continue | SWSS_LOG_INFO | SA 確立後自動再試行 |
| SIGTERM 送信失敗 | false | SWSS_LOG_ERROR | 手動介入必要 |
| PID ファイル不在 | false | SWSS_LOG_NOTICE | 無害（非存在なら OK） |
| MAC 取得失敗 (DEVICE_METADATA) | プロセスクラッシュ | runtime_error → syslog | DEVICE_METADATA 修正 + teammgrd 再起動 |
| SAI LAG ID 払い出し失敗 | エントリ破棄 | SWSS_LOG_ERROR | LAG 再投入 (del→add) |
| SAI create_lag() 失敗 | エントリ破棄 | SWSS_LOG_ERROR | ASIC リセットまたはシステム再起動 |
