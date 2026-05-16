# DHCP_RELAY — Phase F 副次 DB 書込・プロセス制御 中間ファイル

生成日: 2026-05-16  
ソース: `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py`  
調査対象: `DhcpRelayd` クラス、`_start_dhcrelay_process()`, `_execute_supervisor_dhcp_relay_process()`, `_get_dhcp_server_ip()`

---

## 概要

`dhcprelayd` は `DHCP_RELAY` テーブルを**直接購読しない**。代わりに `DHCP_SERVER_IPV4` / `VLAN` / `VLAN_INTERFACE` / `FEATURE` テーブルを監視し、DHCP サーバ機能有効/無効に応じて `dhcrelay` / `dhcpmon` プロセスを制御する。DB への**書き込みは行わない**（STATE_DB の読み取りのみ）。

---

## 1. STATE_DB 読み取り（書き込みなし）

`dhcprelayd` は STATE_DB から `DHCP_SERVER_IPV4_SERVER_IP|eth0` の `ip` フィールドを読み取る。

```python
# dhcprelayd.py:376-384
dhcp_server_ip_table = swsscommon.Table(self.db_connector.state_db, DHCP_SERVER_IPV4_SERVER_IP)
for _ in range(10):
    state, ip = dhcp_server_ip_table.hget(DHCP_SERVER_INTERFACE, "ip")
    if state:
        return ip
    else:
        time.sleep(10)
sys.exit(1)
```

- 書き込み先: なし（読み取り専用）
- `DHCP_SERVER_IPV4_SERVER_IP` への書き込みは `dhcpservd.py:80` が担当

---

## 2. dhcrelay プロセス起動・停止（subprocess 副作用）

`refresh_dhcrelay()` → `_start_dhcrelay_process()` が `subprocess.Popen` で `dhcrelay` を起動する。

```python
# dhcprelayd.py:301-306
cmds = ["/usr/sbin/dhcrelay", "-d", "-m", "discard", "-a", "%h:%p", "%P",
        "--name-alias-map-file", "/tmp/port-name-alias-map.txt"]
for dhcp_interface in new_dhcp_interfaces:
    cmds += ["-id", dhcp_interface]
cmds += ["-iu", "docker0", dhcp_server_ip]
popen_res = subprocess.Popen(cmds)
```

### トリガ条件

| 条件 | 動作 |
|------|------|
| `DHCP_SERVER_IPV4[intf]['state'] == 'enabled'` かつ VLAN に存在 | dhcrelay 起動（1 プロセス、全対象 VLAN を `-id` で列挙） |
| `DEVICE_METADATA.localhost.has_sonic_dhcpv4_relay == 'False'` | dhcrelay を dhcprelayd が直接管理（True の場合は supervisord 管理に委ねる） |
| `force_kill=True`（VLAN_INTERFACE 変更時） | 既存 dhcrelay を強制終了してから再起動 |
| `new_dhcp_interfaces` が空 | dhcrelay 停止のみ（起動しない） |
| 既存 dhcrelay の `-id` セットが新 `dhcp_interfaces` と同一 かつ `force_kill=False` | `NOT_KILLED`（再起動しない） |

### プロセス終了処理

```python
# dhcprelayd.py:343-373  _kill_exist_relay_releated_process()
terminate_proc(proc)  # SIGTERM → SIGKILL
```

`psutil` で名前 `"dhcrelay"` / `"dhcpmon"` を検索し、条件不一致時に終了。

---

## 3. supervisord プログラム制御

`dhcp_server` feature が有効/無効を切り替えるとき、`supervisorctl stop/start` で supervisord 管理下の `isc-dhcpv4-relay-*` / `dhcpmon-*` プログラムを制御する。

```python
# dhcprelayd.py:219-224
cmds = ["supervisorctl", op, program]
res = subprocess.run(cmds, check=True)
```

| 遷移 | supervisorctl 操作 |
|------|--------------------|
| `disabled → enabled` | `supervisorctl stop <isc-dhcpv4-relay-*>` + `supervisorctl stop <dhcpmon-*>` |
| `enabled → disabled` | `supervisorctl start <isc-dhcpv4-relay-*>` + `supervisorctl start <dhcpmon-*>` |

`_get_dhcp_relay_config()` が `SUPERVISORD_CONF_PATH` (`/etc/supervisor/conf.d/docker-dhcp-relay.supervisord.conf`) を読み取り、対象プログラム名を取得する。

---

## 4. supervisord 設定ファイル（docker_init.sh が生成）

`dhcprelayd` 自体はファイルを**書き込まない**。  
コンテナ起動時に `docker_init.sh` が `sonic-cfggen` + Jinja2 テンプレートで生成する。

```bash
# docker_init.sh:12
sonic-cfggen -d \
  -t docker-dhcp-relay.supervisord.conf.j2,/etc/supervisor/conf.d/docker-dhcp-relay.supervisord.conf
```

生成タイミング: dhcp_relay コンテナ起動時（PID 1 の supervisord 起動前）  
テンプレート: `docker-dhcp-relay.supervisord.conf.j2`  
内容: `DHCP_RELAY` / `VLAN` / `DEVICE_METADATA` から各 VLAN の dhcrelay / dhcp6relay / dhcpmon プログラムエントリを生成。

---

## 5. COUNTERS_DB クリア（start.sh が実施）

`start.sh` がコンテナ起動時に `DHCPV4_COUNTER_TABLE:*` キーを全削除する。

```bash
# start.sh:6-9
keys=$(sonic-db-cli COUNTERS_DB keys "DHCPV4_COUNTER_TABLE:*")
for key in $keys; do
    sonic-db-cli COUNTERS_DB del "$key"
done
```

`dhcprelayd` はカウンタ操作を行わない。

---

## 副次書込なし（スコープ外）

| DB | 理由 |
|----|------|
| STATE_DB への書き込み | dhcprelayd は読み取りのみ。書き込みは dhcpservd が担当 |
| APPL_DB | 書き込みなし |
| ASIC_DB / SAI | dhcrelay は L4 UDP relay。SAI/ASIC 非経由 |

---

## Evidence 一覧

| コード | 内容 |
|--------|------|
| `dhcprelayd.py:376-384` | STATE_DB `DHCP_SERVER_IPV4_SERVER_IP` 読み取り（10 回リトライ、失敗で sys.exit） |
| `dhcprelayd.py:290-315` | `_start_dhcrelay_process()`: dhcrelay subprocess 起動 |
| `dhcprelayd.py:343-373` | `_kill_exist_relay_releated_process()`: dhcrelay/dhcpmon 終了 |
| `dhcprelayd.py:209-225` | `_execute_supervisor_dhcp_relay_process()`: supervisorctl stop/start |
| `dhcprelayd.py:264-288` | `_get_dhcp_relay_config()`: supervisord.conf 読み取り |
| `dhcprelayd.py:110-116` | `has_sonic_dhcpv4_relay` フラグで dhcrelay 管理を条件分岐 |
| `docker_init.sh:12` | supervisord.conf を sonic-cfggen で生成（コンテナ起動時） |
| `start.sh:6-9` | COUNTERS_DB `DHCPV4_COUNTER_TABLE:*` クリア（コンテナ起動時） |
