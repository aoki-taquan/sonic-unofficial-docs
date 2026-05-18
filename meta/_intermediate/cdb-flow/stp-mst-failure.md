# STP_MST_INST / STP_MST_PORT — 失敗挙動調査 (Phase D)

調査対象: `sonic-swss/cfgmgr/stpmgr.cpp`
ref: 4305596156d70e9797e8a881b3d19b46de0bce0d

## 調査方法

stpmgr.cpp の `doStpMstGlobalTask()` / `doStpMstInstTask()` / `doStpMstInstPortTask()` を
静的解析し、各処理パスの失敗モードを特定した。

## doStpMstGlobalTask の失敗パス

### 起動ガード失敗 (stpGlobalTask == false)

```cpp
// stpmgr.cpp:344-345
if (stpGlobalTask == false)
    return;
```

`STP|GLOBAL` 未受信の場合、即 `return` でタスクを終了。`m_toSync` の内容は消費されずに残り、
次回 `doTask()` 呼び出し時（1秒タイムアウト後）に再処理される。ログ出力なし。

### 不明フィールド → SWSS_LOG_ERROR (silent drop)

```cpp
// stpmgr.cpp:391-394
else
{
    SWSS_LOG_ERROR("Invalid field: %s", fvField(i).c_str());
}
```

不明フィールドは syslog ERROR のみ出力し、処理を続行する（break しない）。
メッセージ自体は `sendMsgStpd()` で送信される（0 値のフィールドとして）。

### sendMsgStpd の通信失敗

```cpp
// stpmgr.cpp:1218-1254
int StpMgr::sendMsgStpd(STP_MSG_TYPE msgType, uint32_t msgLen, void *data)
{
    tx_msg = (STP_IPC_MSG *)calloc(1, len);
    if (tx_msg == NULL)
    {
        SWSS_LOG_ERROR("tx_msg mem alloc error\n");
        return -1;
    }
    rc = (int)sendto(stpd_fd, ...);
    if (rc == -1)
    {
        SWSS_LOG_ERROR("tx_msg send error\n");
    }
    free(tx_msg);
    return rc;
}
```

`sendMsgStpd` の戻り値はすべての呼び出し元で**チェックされない**。
メモリアロケーション失敗や Unix ソケット送信失敗は syslog ERROR のみで、
stpmgrd は処理を続行してエントリを `m_toSync.erase()` する。
→ イベントはサイレントに失われる（リトライなし）。

## doStpMstInstTask の失敗パス

### 起動ガード (複合条件)

```cpp
// stpmgr.cpp:1027-1028
if (stpGlobalTask == false || (stpPortTask == false && !isStpPortEmpty()))
    return;
```

前提未満足時は `return` で保留（消費なし）。次回ループで再試行。

### calloc 失敗 → return (エントリ消費なし)

```cpp
// stpmgr.cpp:1073-1078 (SET パス)
msg = (STP_MST_INST_CONFIG_MSG *)calloc(1, len);
if (!msg)
{
    SWSS_LOG_ERROR("Memory allocation failed for STP_MST_INST_CONFIG_MSG");
    return;
}
```

```cpp
// stpmgr.cpp:1096-1101 (DEL パス)
msg = (STP_MST_INST_CONFIG_MSG *)calloc(1, len);
if (!msg)
{
    SWSS_LOG_ERROR("Memory allocation failed for MST_INST_CONFIG_MSG");
    return;
}
```

calloc 失敗時は `return` でタスクを終了。エントリは `m_toSync` に残るため
次回 doTask() 呼び出し時に再試行される。`updateVlanInstanceMap()` は
SET パスでは calloc 前に呼ばれているため（`stpmgr.cpp:1067`）、
calloc 失敗時にインメモリ m_vlanInstMap が更新済みになっている不整合が発生する可能性がある。

### キー解析 (サブ文字列抽出)

`key.substr(13)` でプレフィックス `"MST_INSTANCE|"` を除去してインスタンス ID を抽出。
キー形式が不正な場合（e.g. `stoi` 例外）は C++ 例外が発生し、
`stpmgrd.cpp:119-122` のトップレベル catch で stpmgrd が終了する。

```cpp
// stpmgrd.cpp:119-122
catch (const exception &e)
{
    SWSS_LOG_ERROR("Runtime error: %s", e.what());
}
```

## doStpMstInstPortTask の失敗パス

### 起動ガード (三重条件)

```cpp
// stpmgr.cpp:1160-1161
if (stpGlobalTask == false || stpMstInstTask == false || stpPortTask == false)
    return;
```

### 無効キー形式 → erase (サイレントドロップ)

```cpp
// stpmgr.cpp:1185-1189
else
{
    SWSS_LOG_ERROR("Invalid key format %s", kfvKey(t).c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```

`MST_INSTANCE|<id>|<intf>` の形式でセパレータが見つからない場合、
syslog ERROR を出力してエントリを破棄（リトライなし）。

### DEL: l2ProtoEnabled == L2_NONE → erase (サイレントドロップ)

```cpp
// stpmgr.cpp:1204-1207
if (l2ProtoEnabled == L2_NONE || !(isInstanceMapped(mst_id)))
{
    it = consumer.m_toSync.erase(it);
    continue;
}
```

DEL 操作時に MST が無効化済み、またはインスタンスが m_vlanInstMap に存在しない場合、
ログ出力なしでエントリを破棄。

### SET: l2ProtoEnabled == L2_NONE → 保留

```cpp
// stpmgr.cpp:1195-1200
if ((l2ProtoEnabled == L2_NONE))
{
    // Wait till STP/MST instance is configured
    it++;
    continue;
}
```

SET 操作で l2ProtoEnabled が L2_NONE の場合（MST 未有効化）、エントリを保留してイテレータを進める。

## 失敗パス サマリー表

| # | 失敗トリガー | ハンドラ | 処置 | リトライ |
|---|---|---|---|---|
| 1 | 起動ガード未満足 (stpGlobalTask等) | 全 MST ハンドラ共通 | return (保留) | あり（次回ループ） |
| 2 | 不明フィールド (SET) | doStpMstGlobalTask | syslog ERROR のみ、処理続行 | なし（0値送信） |
| 3 | sendMsgStpd: calloc 失敗 | sendMsgStpd | syslog ERROR, return -1 (呼び元無視) | なし（エントリ消費） |
| 4 | sendMsgStpd: sendto 失敗 | sendMsgStpd | syslog ERROR, return -1 (呼び元無視) | なし（エントリ消費） |
| 5 | calloc 失敗 (MST_INST_CONFIG_MSG) | doStpMstInstTask | syslog ERROR, return (保留) | あり (m_vlanInstMap 不整合の可能性) |
| 6 | 無効キー形式 (MST_INST_PORT) | doStpMstInstPortTask | syslog ERROR, erase | なし |
| 7 | DEL: l2Proto == L2_NONE / インスタンス未マップ | doStpMstInstPortTask | erase (ログなし) | なし |
| 8 | SET: l2Proto == L2_NONE | doStpMstInstPortTask | 保留 (it++) | あり |
| 9 | stoi 例外 (不正インスタンス ID) | doStpMstInstTask | 未キャッチ → stpmgrd 終了 | なし（プロセス再起動要） |
