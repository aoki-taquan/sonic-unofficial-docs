# DHCP_RELAY 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/dhcp-relay.md` Phase D block.

## 調査対象ソース

- `sonic-dhcp-relay/dhcp6relay/src/relay.cpp`
- `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp`
- `sonic-dhcp-relay/dhcp6relay/src/sender.cpp`
- `sonic-dhcp-relay/dhcp6relay/src/main.cpp`

---

## 失敗パス一覧

### 1. 起動時: メモリ割り当て失敗 → exit(1)

`relay.cpp:168-172` — `RelayMsg::MarshalBinary()` 内で `new uint8_t[BUFFER_SIZE]` が失敗 (`std::nothrow`) した場合:

```cpp
syslog(LOG_ERR, "Failed to init relay msg buffer\n");
exit(1);
```

同様に `DHCPv6Msg::MarshalBinary()` でも同様 `exit(1)` (`relay.cpp:223-226`)。
**retry なし・rollback なし。即 exit。**

### 2. libevent base 生成失敗 → exit(EXIT_FAILURE)

`relay.cpp:1241-1245` — `event_base_new()` が NULL:

```cpp
syslog(LOG_ERR, "libevent: Failed to create event base\n");
exit(EXIT_FAILURE);
```

### 3. raw socket 生成・bind 失敗 → exit(EXIT_FAILURE)

`relay.cpp:1253-1267` — `sock_open()` 失敗時:
- `socket()` 失敗: `LOG_ERR "socket: Failed to create socket\n"` → return -1
- `bind()` 失敗: `LOG_ERR "bind: Failed to bind to specified interface\n"` → close + return -1
- BPF filter attach 失敗: `LOG_ERR "setsockopt: Failed to attach filter\n"` → close + return -1
- `loop_relay()` 側で filter == -1 なら `exit(EXIT_FAILURE)`

### 4. VLAN ソケット bind retry → 最大 6 回リトライ → 失敗時 exit(EXIT_FAILURE)

`relay.cpp:604-658` — `prepare_vlan_sockets()`:
- VLAN インタフェースの GUA/LLA アドレスが取得できない場合、5 秒 sleep × 最大 6 回リトライ
- `LOG_WARNING "Retry #%d to bind to sockets on interface %s\n"`
- 6 回全失敗後:
  - `LOG_ERR "bind: Failed to bind socket to global ipv6 address on interface %s after %d retries..."`
  - return -1 → `lla_check_callback()` 内で `exit(EXIT_FAILURE)`
- **retry 回数: 6, retry 間隔: 5s**

### 5. LLA 未完了 VLAN の定期チェック (60s タイマー)

`relay.cpp:1288-1310` — `loop_relay()` 内:
- `lla_check_callback()` を 60s 周期 EV_PERSIST タイマーで呼び出し
- 起動直後にも即時 `lla_check_callback()` を手動呼び出し
- VLAN の LLA が未準備の場合: `LOG_WARNING "Link local address for %s is not ready\n"` → スキップ（drop せず保留）
- 全 VLAN の LLA 準備完了で `event_del(timer_event)` タイマー解除
- LLA 未準備 VLAN への server reply は `LOG_WARNING "Link local address for %s is not ready, packet will be dropped\n"` でドロップ

### 6. CONFIG_DB SELECT エラー → return (継続)

`config_interface.cpp:67-70` — `get_dhcp()`:
- `swssSelect.select()` が `Select::ERROR` を返した場合:
  - `LOG_WARNING "Select: returned ERROR"` → return (プロセス継続・retry なし)
- TIMEOUT は無視して継続

### 7. 設定変更は再起動が必要 (hot-reload 不可)

`config_interface.cpp:76-78` — `get_dhcp()`:
- `dynamic == true` (ランタイム中の変更通知) の場合:
  - `LOG_WARNING "relay config changed, need restart container to take effect"`
  - 変更は適用されない。CONFIG_DB への書き込みは正常完了するが dhcp6relay は無視する。
  - **ロールバックなし。DB 状態と実動作が乖離する。**

### 8. パケット送信失敗 → LOG_ERR + カウンタ未加算

`sender.cpp:21-27` — `send_udp()`:
- `sendto()` 失敗:
  - `LOG_ERR "sendto: Failed to send to target address: %s, error: %s\n"`
  - return false → 呼び出し元で `increase_counter()` が呼ばれない（カウンタ未加算）
  - retry なし

### 9. マルフォームパケット → Malformed カウンタ加算 + drop

`relay.cpp:679-686` — `relay_client()`:
- DHCPv6 オプション invalid: `LOG_WARNING "DHCPv6 option is invalid or contains malformed payload from %s\n"`
- `STATE_DB DHCPv6_COUNTER_TABLE|<ifname>` の `Malformed` カウンタを +1
- パケット drop (return)

`relay.cpp:807-812` — `relay_relay_reply()`:
- relay-reply のオプション invalid: `LOG_WARNING "Relay-reply option is invalid or contains malformed payload\n"`
- Malformed カウンタ +1 + drop

### 10. relay-reply に OPTION_RELAY_MSG 欠如 → Unknown カウンタ + drop

`relay.cpp:814-819`:
- `LOG_WARNING "Option relay-msg not found"`
- `Unknown` カウンタ +1 + drop

### 11. hop count 超過 → silent drop (LOG_INFO)

`relay.cpp:747-753` — `relay_relay_forw()`:
- `hop_count >= HOP_LIMIT` (32 固定): `LOG_INFO "Dropping relay-forward message from %s with hop count %d over limit"`
- drop、カウンタ未加算

### 12. DualToR: loopback socket 生成失敗 → exit(EXIT_FAILURE)

`relay.cpp:1271-1286` — `loop_relay()`:
- `prepare_lo_socket()` が -1 を返すと `exit(EXIT_FAILURE)`
- `LOG_ERR "Failed to create dualtor loopback listen socket"`

### 13. DualToR: loopback での invalid パケット → continue (drop + log)

`relay.cpp:1078-1096` — `server_callback_dualtor()`:
- 短すぎるパケット: `LOG_WARNING "Invalid DHCPv6 packet length..."`
- 非 RELAY_REPL: `LOG_WARNING "Invalid DHCPv6 message type %d received on loopback interface\n"`
- リンクアドレスからの VLAN 特定失敗: `LOG_WARNING "Invalid DHCPv6 header content on loopback socket, packet will be dropped\n"`
- LLA 未準備: `LOG_WARNING "Link local address for %s is not ready, packet will be dropped\n"` 

### 14. VLAN の link_address 特定失敗 (vlan_map / addr_vlan_map miss) → LOG_WARNING + NULL return

`relay.cpp:1038-1048` — `get_relay_int_from_relay_msg()`:
- addr_vlan_map に IPv6 なし: `LOG_WARNING "DHCPv6 type %d can't find vlan info from link address %s\n"`
- vlans に vlan_name なし: `LOG_WARNING "DHCPv6 can't find vlan %s config\n"`
- NULL return → 呼び出し元でパケット drop

### 15. getifaddrs 失敗 → exit(1) または LOG_WARNING で継続

- `prepare_relay_config()` (`relay.cpp:489`): `getifaddrs()` 失敗 → `LOG_WARNING "getifaddrs: Unable to get network interfaces\n"` → `exit(1)`
- `prepare_vlan_sockets()` (`relay.cpp:608`): 同 → `LOG_WARNING` + retry ループ継続

### 16. libevent イベント生成失敗 → LOG_ERR (exit なし or exit)

- client listen event 生成失敗: `LOG_ERR "libevent: Failed to create client listen event\n"` → `exit(EXIT_FAILURE)`
- server listen event 生成失敗 (per VLAN): `LOG_ERR "libevent: Failed to create server listen libevent\n"` → exit なし (そのまま継続、対象 VLAN のサーバ応答受信不可)

### 17. main: 未捕捉例外 → LOG_ERR + return 1 (プロセス終了)

`main.cpp:40-43`:
```cpp
catch (std::exception &e) {
    syslog(LOG_ERR, "An exception occurred.\n");
    return 1;
}
```
プロセス終了後は systemd / supervisord による restart に委ねる。

---

## STATE_DB への障害記録

- `DHCPv6_COUNTER_TABLE|<ifname>` に以下のカウンタを管理:
  - `Malformed`, `Unknown`, `Solicit`, `Advertise`, `Request`, `Confirm`, `Renew`, `Rebind`, `Reply`, `Release`, `Decline`, `Reconfigure`, `Information-Request`, `Relay-Forward`, `Relay-Reply`
- 送信失敗時はカウンタ加算されない
- `ERROR_TABLE` への書き込みはなし（dhcp6relay は ERROR_TABLE を使用しない）

## config rollback / partial failure

- CONFIG_DB への書き込みは `sonic-utilities` / `sonic-cfggen` が行う。dhcp6relay は読み取り専用。
- **config 変更 (dhcpv6_servers 追加/削除) はコンテナ再起動まで反映されない**（hot-reload 不可・`LOG_WARNING` のみ）
- 起動時に servers が空 VLAN はスキップ（残骸エントリとして CONFIG_DB に残る可能性あり）
- 部分成功: 複数 VLAN のうち一部がソケット bind 失敗で `is_lla_ready=false` のまま運用継続可能

## orchagent/SAI

DHCP_RELAY は SAI 経由でなく Linux カーネル UDP relay (L4)。orchagent は関与しない。
task_need_retry / task_failed は存在しない。
