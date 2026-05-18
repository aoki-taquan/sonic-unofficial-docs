# STP/ICCP 連携 — 失敗挙動調査 (Phase D)

調査日: 2026-05-18
対象ページ: docs/reference/config-db/stp-iccp.md
担当: batch225

## 調査コード

### scheduler.c — heartbeat_check() / scheduler_session_disconnect_handler()

```c
// scheduler.c:82-87
if ( (time(NULL) - csm->heartbeat_update_time) > csm->session_timeout)
{
    /* hearbeat timeout*/
    ICCPD_LOG_WARN("ICCP_FSM", "iccpd connection timeout (heartbeat)");
    scheduler_session_disconnect_handler(csm);
}

// scheduler.c:831-858: scheduler_session_disconnect_handler()
void scheduler_session_disconnect_handler(struct CSM* csm)
{
    ...
    mlacp_peer_disconn_handler(csm);
    MLACP(csm).current_state = MLACP_STATE_INIT;
    iccp_csm_status_reset(csm, 0);  // all=0: partial reset
    ...
}
```

### iccp_csm.c — iccp_csm_status_reset()

```c
// iccp_csm.c:130-149
void iccp_csm_status_reset(struct CSM* csm, int all)
{
    if (all)
    {
        bzero(csm, sizeof(struct CSM));  // full wipe (init time only)
    }
    csm->sock_fd = -1;
    ...
    csm->role_type = STP_ROLE_NONE;  // role is RESET on disconnect
    ...
}
```

### scheduler.c — scheduler_check_csm_config(): 接続拒否条件

```c
// scheduler.c:768-808
int scheduler_check_csm_config(struct CSM* csm)
{
    if (csm->mlag_id <= 0)
        ret = MCLAG_ERROR;
    else if (strlen(csm->peer_ip) <= 0)
        ret = MCLAG_ERROR;
    else if (strlen(csm->sender_ip) <= 0)
        ret = MCLAG_ERROR;
    else if (strlen(csm->peer_itf_name) != 0)
    {
        lif = local_if_find_by_name(csm->peer_itf_name);
        if (lif == NULL)
            return MCLAG_ERROR;  /* peer-link IF が存在しない場合は即リターン */
        ...
    }
    /* Decide STP role*/
    iccp_csm_stp_role_count(csm);   // 接続成功時のみ到達
    return ret;
}
```

### iccp_csm.c — iccp_csm_stp_role_count(): 再接続時ロール再決定

```c
// iccp_csm.c:845-871
void iccp_csm_stp_role_count(struct CSM *csm)
{
    /* decide the role, lower ip to be active & socket client*/
    if (csm->role_type == STP_ROLE_NONE)   // reset されている場合のみ再実行
    {
        if (inet_addr(csm->sender_ip) < inet_addr(csm->peer_ip))
        {
            csm->role_type = STP_ROLE_ACTIVE;
            mlacp_link_set_iccp_role(csm->mlag_id, true, MLACP(csm).system_id);
        }
        else
        {
            csm->role_type = STP_ROLE_STANDBY;
            mlacp_link_set_iccp_role(csm->mlag_id, false, NULL);
        }
    }
}
```

### scheduler.h — タイムアウト定数

```c
// scheduler.h:40,42
#define CONNECT_INTERVAL_SEC        1   // 接続リトライ間隔
#define HEARTBEAT_TIMEOUT_SEC       15  // ハートビートタイムアウト (csm->session_timeout の初期値)
```

## 調査結果

### 失敗シナリオ一覧

| # | 失敗原因 | 動作 | 自動回復 |
|---|----------|------|---------|
| 1 | ハートビートタイムアウト (15 秒) | セッション切断 → `role_type = STP_ROLE_NONE` リセット → 1 秒ごとに再接続試行 | あり (自動再接続 + STP ロール再決定) |
| 2 | TCP 接続ドロップ (`sock_fd <= 0`) | `ICCP_NONEXISTENT` 状態へ遷移 → `role_type` リセット | あり (CONNECT_INTERVAL_SEC=1 ごとにリトライ) |
| 3 | `source_ip == peer_ip` | セッション確立不可 (WARN ログのみ) | なし (設定変更が必要) |
| 4 | `peer_link` 設定済みだが IF が存在しない | `MCLAG_ERROR` 即リターン → 接続拒否 | あり (IF が作成されれば次の `scheduler_check_csm_config()` で回復) |
| 5 | `mclagsyncd` が iccpd から切断 | STP ロール通知 (`mlacp_link_set_iccp_role()`) がサイレントスキップ | あり (mclagsyncd 再接続後に最初のロール変更で再通知) |

### ロールリセットの重要な挙動

`scheduler_session_disconnect_handler()` → `iccp_csm_status_reset(csm, 0)` によって
`role_type` は **セッション切断のたびに `STP_ROLE_NONE` へリセット** される。

再接続時に `scheduler_check_csm_config()` → `iccp_csm_stp_role_count()` が
`role_type == STP_ROLE_NONE` を検出して **STP ロールを再決定** する。
`source_ip` / `peer_ip` が変わらない限りロールは同じになるが、
CONFIG_DB 変更（例: IP 入れ替え）があれば再接続後に異なるロールになる。

## evidence refs

- `scheduler.c:82-87` (heartbeat timeout)
- `scheduler.c:831-858` (scheduler_session_disconnect_handler)
- `iccp_csm.c:130-149` (iccp_csm_status_reset, role_type = STP_ROLE_NONE)
- `iccp_csm.c:845-871` (iccp_csm_stp_role_count, guard: role_type == STP_ROLE_NONE)
- `scheduler.c:768-808` (scheduler_check_csm_config, failure conditions)
- `scheduler.h:40,42` (CONNECT_INTERVAL_SEC=1, HEARTBEAT_TIMEOUT_SEC=15)
