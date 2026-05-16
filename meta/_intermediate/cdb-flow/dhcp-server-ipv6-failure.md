# DHCP_SERVER_IPV6 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/dhcp-server-ipv6.md` Phase D block.

## 調査対象ソース

- `sonic-dhcp-relay/dhcp6relay/src/relay.cpp`
- `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp`

---

## 失敗パス一覧

### 1. 不正 server_ip（dhcpv6_servers）→ LOG_WARNING + 不正アドレスのまま送信継続

`relay.cpp:476-486` — `prepare_relay_config()`:

`inet_pton()` が 1 を返さない（不正 IPv6 文字列）場合でも `servers_sock.push_back(tmp)` が実行される。エラー時に `continue` / `return` がなく、不正アドレスへの送信を試みる。送信失敗は `sendto()` で `LOG_ERR` が出るが retry なし。

servers が空の VLAN は `LOG_WARNING "No servers found for VLAN %s, skipping configuration."` でスキップ（`config_interface.cpp:176-179`）。

### 2. VLAN 未解決 → LOG_WARNING + VLAN スキップ

`config_interface.cpp:130-148` — `processRelayNotification()`:

- `VLAN_INTERFACE` テーブルにキーなし: `LOG_WARNING "%s doesn't exist in VLAN_INTERFACE table, skip it"`
- IPv6 アドレスなし: `LOG_WARNING "%s doesn't have IPv6 address configured, skip it"`
- いずれも `continue` でスキップ。該当 VLAN への DHCPv6 リレー不提供。

### 3. dhcrelay 起動失敗 → exit(EXIT_FAILURE) または retry 後 exit

`relay.cpp:588-658` — `prepare_vlan_sockets()`:
- GUA/LLA ソケット生成失敗 → return -1 → exit(EXIT_FAILURE)
- アドレス取得失敗: 5 秒 sleep × 最大 6 回リトライ後 `LOG_ERR "bind: Failed to bind socket to global/link local ipv6 address on interface %s after %d retries"` → exit(EXIT_FAILURE)

`relay.cpp:412-434` — `sock_open()`:
- L2 raw ソケット生成・bind・BPF filter attach 失敗 → `LOG_ERR` + return -1

ERROR_TABLE への書き込みなし。supervisord/systemd 自動再起動に委ねる。

### 4. runtime 設定変更は再起動まで反映されない

`config_interface.cpp:76-78`:
- `LOG_WARNING "relay config changed, need restart container to take effect"`
- DB 状態と実動作が乖離したまま継続。rollback なし。

---

## 備考

- `DHCP_SERVER_IPV6` テーブル自体は未実装。上記は関連する `dhcp6relay` プロセスの失敗挙動（将来実装時に継承される前提条件）。
- orchagent/SAI 関与なし（Linux カーネル UDP relay）。
- task_need_retry / task_failed は存在しない。
