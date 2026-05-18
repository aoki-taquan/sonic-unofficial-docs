# STP/ICCP 連携 — 書込み順序依存調査 (Phase B)

調査日: 2026-05-18
対象ページ: docs/reference/config-db/stp-iccp.md
担当: batch176

## 調査コード

### scheduler.c — scheduler_check_csm_config()

```c
// scheduler.c:768-810
int scheduler_check_csm_config(struct CSM* csm)
{
    ...
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
            return MCLAG_ERROR;  /* peer-link が未存在なら接続拒否 */
        ...
    }
    /* Decide STP role*/
    iccp_csm_stp_role_count(csm);
    return ret;
}
```

呼び出し箇所:
- `scheduler.c:302` — サーバー accept 時 (passive 側)
- `scheduler.c:682` — クライアント connect 時 (active 側、`scheduler_prepare_session()`)

### scheduler.c — scheduler_prepare_session() — クライアント判定

```c
// scheduler.c:686-695
local_ip = inet_addr(csm->sender_ip);
peer_ip = inet_addr(csm->peer_ip);
if (local_ip > peer_ip)
    goto time_update;           /* 大きい方が server 側 → connect しない */
else if (local_ip == peer_ip)
    ICCPD_LOG_WARN(...);        /* 同一 IP は警告して skip */
/* 小さい方が client → session_client_conn_handler() を呼ぶ */
```

### mclaglink.cpp — 初期ロード順序

```cpp
// mclagsyncd.cpp:51-58
mclag.mclagsyncdFetchSystemMacFromConfigdb();   // DEVICE_METADATA.localhost.mac
mclag.accept();                                  // iccpd ソケット待受
mclag.mclagsyncdFetchMclagConfigFromConfigdb();  // MCLAG_DOMAIN ダンプ → processMclagDomainCfg
mclag.mclagsyncdFetchMclagInterfaceConfigFromConfigdb(); // MCLAG_INTERFACE ダンプ
```

### mlacp_link_handler.c — sync_fd ガード

```c
// mlacp_link_handler.c:654-660
if (!sys || sys->sync_fd <= 0)
{
    ICCPD_LOG_DEBUG(__FUNCTION__, "iccpd to mclagsyncd sync_fd not ready");
    return;
}
```

mclagsyncd への MCLAG_MSG_TYPE_SET_ICCP_ROLE 送信は `sync_fd > 0`（mclagsyncd が接続済み）でなければスキップされる。

## 結論

### 書込み/起動順序

1. **MCLAG_DOMAIN の `source_ip` / `peer_ip` / `peer_link` が CONFIG_DB に存在すること**が ICCP セッション確立の前提条件
   - `scheduler_check_csm_config()` が `peer_ip` と `sender_ip` の空文字チェック → 空なら ERROR で ICCP 接続拒否
   - `peer_link` が設定されているのにインターフェースが存在しない場合も接続拒否

2. **mclagsyncd → iccpd の接続確立 (sync_fd)**が STP ロール通知より先行必須
   - `mlacp_link_set_iccp_role()` は `sync_fd <= 0` ならロールを送信しない (サイレントスキップ)
   - mclagsyncd は iccpd の accept() に接続してから `Fetch` を実行するため、mclagsyncd 起動は iccpd 起動後が基本

3. **IP アドレス大小比較でクライアント/サーバー役が決定**
   - `source_ip < peer_ip` の小さいノードが TCP client (→ `CONNECT` を開始)
   - `source_ip > peer_ip` の大きいノードが TCP server (→ `LISTEN` で待つ)
   - 同値の場合は WARN ログのみでセッション未確立

4. **STP ロール (`iccp_csm_stp_role_count()`) は ICCP セッション確立時に 1 回だけ実行**
   - サーバー accept 時 または クライアント connect 完了時に呼ばれる
   - 一度 role が `ACTIVE` or `STANDBY` になると再実行しない (`role_type != STP_ROLE_NONE` ガード)
   - セッション切断・再接続では role がリセットされないため注意

証跡:
- `scheduler.c:302, 682, 768-810` (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `mclagsyncd.cpp:51-58`
- `mclaglink.cpp:137-185`
- `mlacp_link_handler.c:654-660`
