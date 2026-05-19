# MCLAG_INTERFACE — Phase D 失敗挙動調査

調査対象ソース:
- `sonic-swss/orchagent/mlagorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/mclagsyncd/mclaglink.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/mclagsyncd/mclagsyncd.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## MlagOrch (orchagent) 側の失敗パス

### 重複 ADD (`addMlagInterface` L193-213)

```cpp
if (m_mlagIntfs.find(if_name) != m_mlagIntfs.end())
{
    SWSS_LOG_ERROR("MLAG adds duplicate MLAG interface %s", if_name.c_str());
}
```

- `m_mlagIntfs` にすでに同名エントリが存在する場合 → SWSS_LOG_ERROR + notify なし
- addMlagInterface は常に `return true` するため、エントリはキューから除去される（retry なし）
- evidence: `mlagorch.cpp:196-213`

### 未知 DEL (`delMlagInterface` L215-234)

```cpp
if (m_mlagIntfs.find(if_name) == m_mlagIntfs.end())
{
    SWSS_LOG_ERROR("MLAG deletes unknown MLAG interface %s", if_name.c_str());
}
```

- `m_mlagIntfs` に存在しないインターフェースを DEL しようとした場合 → SWSS_LOG_ERROR + notify なし
- delMlagInterface は常に `return true` するため、エントリはキューから除去される（retry なし）
- evidence: `mlagorch.cpp:219-234`

### 不明 op_type (doMlagInterfaceTask L149-152)

```cpp
SWSS_LOG_ERROR("MLAG receives unknown operation type %s", op.c_str());
it = consumer.m_toSync.erase(it);
```

- SET/DEL 以外の op が来た場合 → SWSS_LOG_ERROR + erase（retry なし、サイレント廃棄）
- evidence: `mlagorch.cpp:149-153`

### PortsOrch 未起動時の遅延処理

`doTask()` L49-52:
```cpp
if (!gPortsOrch->allPortsReady())
{
    return;
}
```

- 全ポート初期化完了前は doTask() を早期 return → エントリはキューに保留
- これは「失敗」ではなく「保留」。PortsOrch 起動後に自動的に再処理される
- evidence: `mlagorch.cpp:49-52`

---

## mclagsyncd 側の失敗パス（MCLAG_INTERFACE 関連）

### 不正キーフォーマット (`mclagsyncdSendMclagIfaceCfg` L1023-1027)

```cpp
mclag_ifaces = key.substr(delimiter_pos+1);
if (mclag_ifaces.empty())
{
    SWSS_LOG_ERROR("Invalid Key %s Format. No mclag iface specified", key.c_str()); 
    continue;
}
```

- `MCLAG_INTERFACE|<domain_id>|<if_name>` の key から `<if_name>` が空の場合 → エラーログ + `continue`（そのエントリをスキップ）
- iccpd へは送信されない。STATE_DB への書込みなし
- evidence: `mclaglink.cpp:1022-1027`

### iccpd への IPC 書き込み失敗（バッファフル）(L1057-1060)

```cpp
if (write <= 0)
{
    SWSS_LOG_ERROR("mclagsycnd to ICCPD, mclag iface cfg send, buffer full; write to m_connection_socket failed");
}
```

- mclag iface config の IPC メッセージがバッファ境界を超えた場合の中間送信失敗
- SWSS_LOG_ERROR のみ。バッファ内の未送信分は次のループで送信試行される
- evidence: `mclaglink.cpp:1055-1063`

### iccpd への IPC 書き込み失敗（最終送信）(L1081-1084)

```cpp
if (write <= 0)
{
    SWSS_LOG_ERROR("mclagsycnd to ICCPD, mclag iface cfg send; write to m_connection_socket failed");
}
```

- mclag_iface_cfg_info の最終 write が失敗した場合
- SWSS_LOG_ERROR のみ。retry なし。iccpd 側は MCLAG_INTERFACE 情報を受け取れないため、ICCP ネゴシエーションが不完全になる
- evidence: `mclaglink.cpp:1078-1085`

### IPC 接続断（MclagConnectionClosedException）

`mclagsyncd.cpp:112-115`:
```cpp
catch (MclagLink::MclagConnectionClosedException &e)
{
    cout << "Connection lost, reconnecting..." << endl;
}
```

- `readData()` で `read == 0` の場合 `MclagConnectionClosedException` が throw される
- mclagsyncd は外側の `while(1)` で再接続ループを回す → accept() → `mclagsyncdFetchMclagInterfaceConfigFromConfigdb()` で CONFIG_DB の全 MCLAG_INTERFACE を再読み込みして iccpd へ再送
- iccpd 切断・再接続時は MCLAG_INTERFACE 設定が自動的に再同期される
- evidence: `mclagsyncd.cpp:112-115`, `mclaglink.cpp:1884-1887`

### malformed メッセージ受信

`mclaglink.cpp:1901-1902`:
```cpp
if (!mclag_msg_ok(hdr, left))
    throw system_error(make_error_code(errc::bad_message), "Malformed MCLAG message received");
```

- iccpd からの受信メッセージが不正フォーマットの場合 → `system_error` throw
- mclagsyncd.cpp の `catch (const exception& e)` がキャッチして **daemon 終了** (`return 0`)
- **重要**: 通常の `MclagConnectionClosedException` と異なり、`exception` catch は `return 0` で mclagsyncd プロセスが終了する。systemd が restart する
- evidence: `mclagsyncd.cpp:116-120`, `mclaglink.cpp:1901-1902`

---

## 失敗時の STATE_DB / ERROR_TABLE 記録

- MlagOrch は STATE_DB / ERROR_TABLE への書き込みを行わない
- mclagsyncd も MCLAG_INTERFACE 失敗時は STATE_DB への書き込みなし（iccpd からの応答受信後に STATE_DB へ書く仕組みのため、iccpd 側で受け取れなければ STATE_DB も更新されない）
- すべての失敗は syslog のみ

```bash
# orchagent ログで MCLAG_INTERFACE 失敗確認
docker exec swss cat /var/log/swss/orchagent.log | grep -i "MLAG"

# mclagsyncd ログ確認
docker exec iccpd cat /var/log/swss/mclagsyncd.log | grep -i "mclag iface"
```
