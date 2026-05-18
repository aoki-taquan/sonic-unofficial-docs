# STP/ICCP 連携 — Redis 通知メカニズム調査 (Phase G)

調査日: 2026-05-18
対象ページ: docs/reference/config-db/stp-iccp.md
担当: batch281-next

## 調査コード

### iccpd メインループ — epoll_wait ベース (scheduler.c)

iccpd は Redis keyspace notification を直接 subscribe しない。
CONFIG_DB の変更は mclagsyncd 経由で IPC として届く。

```c
// scheduler.c:462-488
void scheduler_loop()
{
    while (1) {
        if (sys->sync_fd <= 0)
            iccp_connect_syncd();   /* mclagsyncd 接続待ち */

        iccp_handle_events(sys);    /* epoll_wait(EPOLL_TIMEOUT_MSEC=100ms) */
        scheduler_transit_fsm();    /* FSM 状態遷移チェック */
    }
}
```

### iccp_handle_events — epoll_wait (iccp_netlink.c:2168)

```c
// iccp_netlink.c:2182
nfds = epoll_wait(sys->epoll_fd, events, max_nfds, EPOLL_TIMEOUT_MSEC);
```

- `EPOLL_TIMEOUT_MSEC = 100` ms (`scheduler.h:44`)
- イベント源: netlink socket (ネットワーク状態), sync_fd (mclagsyncd IPC), ICCP peer TCP socket, シグナルパイプ

### mclagsyncd → iccpd のイベント経路

```
CONFIG_DB (SubscriberStateTable + keyspace PSUBSCRIBE)
    ↓  keyspace 通知
mclagsyncd (mclagsyncd.cpp:66-110, blocking s.select())
    ↓  Unix ドメインソケット IPC (sync_fd, port 2626)
iccpd (iccp_mclagsyncd_msg_handler → iccp_mclagsyncd_mclag_domain_cfg_handler)
    ↓
scheduler_check_csm_config() → iccp_csm_stp_role_count()
```

mclagsyncd が購読する CONFIG_DB テーブル:
- `MCLAG` (MCLAG_DOMAIN): `__keyspace@4__:MCLAG|*`
- `MCLAG_INTERFACE`: `__keyspace@4__:MCLAG_INTERFACE|*`
- `MCLAG_UNIQUE_IP`: `__keyspace@4__:MCLAG_UNIQUE_IP|*`

実装: `mclagsyncd.cpp:41`, `mclaglink.cpp:912-921`

### iccpd 内 STP ロール通知の出力先

STP ロール確定後の通知は Redis ではなく mclagsyncd へ IPC で返される:

```c
// mlacp_link_handler.c:654-716
MCLAG_MSG_TYPE_SET_ICCP_ROLE → mclagsyncd → STATE_DB.STATE_MCLAG_TABLE
```

mclagsyncd が STATE_DB に書き込む (`mclagsyncdSetIccpRole()`)。
iccpd 自身は Redis への直接書き込みを行わない。

### ハートビートタイマー

ICCP セッションのハートビートは TCP keepalive ではなく iccpd 独自タイマー:

```c
// scheduler.c:82-86
if ((time(NULL) - csm->heartbeat_update_time) > csm->session_timeout)
    scheduler_session_disconnect_handler(csm);
```

`session_timeout` は CONFIG_DB `MCLAG_DOMAIN.session_timeout` (YANG デフォルト 30 秒) から受け取るが、CSM 初期化時は `HEARTBEAT_TIMEOUT_SEC = 15` 秒で初期化される。

## 結論

STP/ICCP 連携の通知メカニズムまとめ:

1. **CONFIG_DB → iccpd**: mclagsyncd が keyspace notification を受けて IPC で転送 (間接)
2. **iccpd 内イベントループ**: epoll_wait + 100 ms タイムアウトのポーリング (直接 Redis 購読なし)
3. **STP ロール決定後の通知**: iccpd → mclagsyncd (IPC) → STATE_DB (ProducerStateTable 経由)
4. **ハートビート**: iccpd 内部タイマー (`session_timeout` 秒)

証跡:
- `scheduler.c:462-488, 806` (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `iccp_netlink.c:2168-2182`
- `mlacp_link_handler.c:654-716`
- `mclagsyncd.cpp:41, 66-110` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `mclaglink.cpp:912-921, 1357-1420`
