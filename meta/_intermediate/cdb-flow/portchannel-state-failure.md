# portchannel-state — Phase D 失敗挙動調査ノート

調査日: 2026-05-18
調査対象:
- `sonic-swss/teamsyncd/teamsync.cpp`
- `sonic-swss/cfgmgr/teammgr.cpp`
- `sonic-swss/cfgmgr/intfmgr.cpp`

---

## teamsyncd の失敗パターン

### TeamPortSync コンストラクタ失敗 (teamsync.cpp:L208-213)

`TeamSync::addLag()` は `TeamPortSync` コンストラクタを `try-catch` で囲んでいる。
コンストラクタ内では最大 3 回リトライ (`max_retries = 3`, L286) を行い、すべて失敗すると
`system_error` をリスローする。

失敗ケース:
| 原因 | errno | ログ |
|------|-------|------|
| `team_alloc()` 失敗 | EADDRNOTAVAIL | `teamsync.cpp:L295` |
| `team_init()` 失敗 | EADDRNOTAVAIL | `teamsync.cpp:L304` |
| `team_change_handler_register()` 失敗 | EADDRNOTAVAIL | `teamsync.cpp:L313` |
| `teamdctl_alloc()` 失敗 | EADDRNOTAVAIL | `teamsync.cpp:L322` |
| `teamdctl_connect()` 失敗 | ECONNREFUSED | `teamsync.cpp:L332` |
| `teamdctl_config_get_raw_direct()` 失敗 | EIO | `teamsync.cpp:L344` |

各リトライ間は `sleep(1)` で待機する (L363)。

**挙動**: 3 回リトライ後に `system_error` がスローされ、`addLag()` の外側 catch (L208-213) が
`SWSS_LOG_ERROR` を記録し STATE_DB への書き込みをスキップして return する。
LAG_TABLE に `state=ok` は書かれない。次の `RTM_NEWLINK` イベントで再試行される。

コードコメント (L183-193):
> "On container restart, teamsyncd may receive RTM_NEWLINK for pre-existing team devices from
> the kernel's initial dump before teammgrd has had a chance to recreate them via 'teamd -r'.
> The recreate deletes the old kernel device first, so team_init() fails with EADDRNOTAVAIL."

### warm-restart 時の遅延書き込み (teamsync.cpp:L197-203)

warm-restart 中は STATE_DB への書き込みが `applyState()` まで保留される。
タイムアウト (デフォルト: `DEFAULT_WR_PENDING_TIMEOUT`) 後に一括反映。

## teammgrd の失敗パターン

### teamd 起動失敗 (teammgr.cpp:L640-644)

`exec(cmd.str(), res) != 0` のとき `task_need_retry` を返す。
LAG_TABLE には書かれない（teamsyncd が RTM_NEWLINK を受け取らないため）。

```cpp
if (exec(cmd.str(), res) != 0)
{
    SWSS_LOG_INFO("Failed to start port channel %s with teamd, retry...", alias.c_str());
    return task_need_retry;
}
```

Consumer ループが task_need_retry を受けてキューにタスクを残し自動リトライする。

### SIGTERM 送信失敗 (teammgr.cpp:L672-674)

`removeLag()` 内で `kill(pid, SIGTERM)` が失敗すると `SWSS_LOG_ERROR` を記録し `false` を返す。
teamd プロセスが残存する可能性があるが、LAG_TABLE は teamsyncd が RTM_DELLINK を受信するまで
削除されない（孤立エントリが残る可能性）。

## intfmgrd の影響

`intfmgr.cpp:L661-668, L833` で `isIntfStateOk(alias)` が `m_stateLagTable.get(alias)` を
チェックし、エントリが存在しなければ `PORTCHANNEL_INTERFACE` の処理をスキップしてリトライ。
LAG_TABLE の `state=ok` がなければ IP アドレス付与など後続処理は保留される。

## まとめ

| 失敗シナリオ | 結果 | 自動回復 |
|------------|------|---------|
| teamsyncd TeamPortSync 初期化失敗 (1-2 回) | 3 回まで自動リトライ | あり (sleep 1s × 3) |
| teamsyncd TeamPortSync 初期化失敗 (3 回) | `SWSS_LOG_ERROR`, STATE_DB 書き込みスキップ, 次 RTM_NEWLINK を待つ | あり (次イベント) |
| teammgrd teamd 起動失敗 | `task_need_retry`, Consumer が自動リトライ | あり |
| teammgrd SIGTERM 失敗 | `SWSS_LOG_ERROR`, teamd 残存の可能性 | なし |
| warm-restart 中の遅延 | `applyState()` タイムアウト後に書き込み | あり (タイムアウト後) |
