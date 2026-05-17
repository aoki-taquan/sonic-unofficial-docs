# smart-switch — Phase E: failure / invalid-input handling

調査日: 2026-05-17
調査対象: dhcp_cfggen.py, dhcprelayd.py, dhcp_lease.py, sonic-smart-switch.yang, sonic-dhcp-server-ipv4.yang

---

## 1. YANG バリデーション失敗（書き込み拒否）

### MID_PLANE_BRIDGE — bridge フィールドのパターン違反

`sonic-smart-switch.yang:63-69` の `pattern "bridge-midplane"` により、`bridge` フィールドに
`"bridge-midplane"` 以外の文字列を書き込むと CLI 経由の書き込みが即座に拒否される。
`must "(current()/../ip_prefix)"` 制約（行 68）により `bridge` のみを書いて `ip_prefix` を
省略した場合もバリデーション違反となる。

### DHCP_SERVER_IPV4_PORT — leafref 解決失敗

`sonic-dhcp-server-ipv4.yang:217-219` の leafref は `DHCP_SERVER_IPV4` のキー（`name`）を参照する。
`DHCP_SERVER_IPV4|bridge-midplane` が存在しない状態で `DHCP_SERVER_IPV4_PORT|bridge-midplane|dpu0`
を書き込むと YANG バリデーション違反で拒否される。

同様に `sonic-dhcp-server-ipv4.yang:231-233` の `port` → `DPUS.midplane_interface` leafref が
解決できない場合（`DPUS|dpu0` が存在しない等）も書き込みが拒否される。

---

## 2. dhcpservd — サイレント失敗パターン

### subtype != SmartSwitch の場合の静かなスキップ

`dhcp_cfggen.py:67,76`:
```python
smart_switch = is_smart_switch(device_metadata)  # subtype == "SmartSwitch" のみ True
mid_plane, dpus = self._parse_dpu(dpus_table, mid_plane_table) if smart_switch else ({}, {})
```
`subtype` が `"SmartSwitch"` でない場合、`_parse_dpu()` は呼ばれず空辞書が返る。
`MID_PLANE_BRIDGE` / `DPUS` / `DHCP_SERVER_IPV4_PORT` の内容は完全に無視される。
エラーログは出力されない（サイレント失敗）。

### bridge または ip_prefix 欠落時のスキップ

`dhcp_cfggen.py:84`:
```python
if smart_switch and "bridge" in mid_plane and "ip_prefix" in mid_plane:
```
`MID_PLANE_BRIDGE|GLOBAL` に `bridge` または `ip_prefix` のどちらか一方が欠如すると、
ミッドプレーンブリッジが `dhcp_interfaces` に登録されず DPU への IP 払い出しが停止する。
エラーログは出力されない（サイレント失敗）。

### port が dhcp_members に含まれない場合

`dhcp_cfggen.py:424-425`:
```python
if port_key not in dhcp_members:
    syslog.syslog(syslog.LOG_WARNING, f"Port {splits[1]} is not in {splits[0]}")
    continue
```
`DHCP_SERVER_IPV4_PORT` のキーが `dhcp_members` に含まれない（`DPUS.midplane_interface` と不一致等）
場合、`LOG_WARNING` を出力してそのポートエントリをスキップする。他のポートの処理は継続される。

### dhcp_interface に IPv4 アドレスなしの場合

`dhcp_cfggen.py:432-433`:
```python
if dhcp_interface_name not in dhcp_interfaces:
    syslog.syslog(syslog.LOG_WARNING, f"Interface {dhcp_interface_name} doesn't have IPv4 address")
    continue
```
`MID_PLANE_BRIDGE|GLOBAL.ip_prefix` が未設定の場合に相当する。`LOG_WARNING` を出力してスキップ。

### ips と ranges の同時指定

`dhcp_cfggen.py:418-420`:
```python
if "ips" in port_config and len(port_config["ips"]) != 0 and "ranges" in port_config \
   and len(port_config["ranges"]) != 0:
    syslog.syslog(syslog.LOG_WARNING, f"Port config for {port_key} contains both ips and ranges, skip")
    continue
```
YANG `must` 制約で書き込み時に弾かれるべきだが、万一両フィールドが存在した場合は
`LOG_WARNING` を出力してスキップ。YANG バリデーション外（直接 Redis 書き込み等）で起こりうる。

### hostname 取得失敗

`dhcp_cfggen.py:171-174`:
```python
if localhost_entry is None or "hostname" not in localhost_entry:
    syslog.syslog(syslog.LOG_ERR, "Cannot get hostname")
    raise Exception("Cannot get hostname")
```
`DEVICE_METADATA|localhost.hostname` が未設定の場合、`LOG_ERR` を出力した後に例外を送出する。
`generate()` 全体が失敗し Kea 設定ファイルが更新されない。

---

## 3. dhcprelayd — dhcrelay/dhcpmon プロセス起動失敗

### dhcrelay がゾンビ状態で起動した場合

`dhcprelayd.py:306-313`:
```python
popen_res = subprocess.Popen(cmds)
proc = psutil.Process(popen_res.pid)
time.sleep(1)
if proc.status() == psutil.STATUS_ZOMBIE:
    syslog.syslog(syslog.LOG_ERR, "Failed to start dhcrelay process with: {}".format(cmds))
    terminate_proc(proc)
    sys.exit(1)
```
dhcrelay プロセスが起動直後にゾンビになった場合、`LOG_ERR` を出力してプロセスを終了し、
`sys.exit(1)` で `dhcprelayd` 自体も終了する。コンテナが再起動する。

### dhcp_server IP が STATE_DB に存在しない場合

`dhcprelayd.py:375-385`:
```python
for _ in range(10):
    state, ip = dhcp_server_ip_table.hget(DHCP_SERVER_INTERFACE, "ip")
    if state:
        return ip
    else:
        syslog.syslog(syslog.LOG_INFO, "Cannot get dhcp server ip")
        time.sleep(10)
syslog.syslog(syslog.LOG_ERR, "Cannot get dhcp_server ip from state_db")
sys.exit(1)
```
10 回（合計 100 秒）リトライして STATE_DB に `DHCP_SERVER_IPV4_SERVER_IP|eth0.ip` が
存在しない場合、`LOG_ERR` を出力して `sys.exit(1)` する。コンテナが再起動する。

### supervisorctl 操作の不正な op

`dhcprelayd.py:215-217`:
```python
if op not in ["stop", "start"]:
    syslog.syslog(syslog.LOG_ERR, "Error operation: {}".format(op))
    sys.exit(1)
```
内部コードバグ相当。`LOG_ERR` + `sys.exit(1)`。

---

## 4. dhcp_lease — lease ファイル不在

`dhcp_lease.py:116-121`:
```python
try:
    with open(self.lease_file, "r", encoding="utf-8") as fb:
        dq = deque(fb)
except FileNotFoundError as err:
    syslog.syslog(syslog.LOG_ERR, "Cannot find lease file: {}".format(self.lease_file))
    raise err
```
Kea の lease ファイル（デフォルト `/var/lib/kea/kea-lease.csv`）が存在しない場合、
`LOG_ERR` を出力して例外を再送出する。STATE_DB の `DHCP_SERVER_IPV4_LEASE` テーブルは更新されない。

---

## 5. CONFIG_DB への影響（まとめ）

| 障害シナリオ | ログレベル | CONFIG_DB への影響 | 挙動 |
|---|---|---|---|
| YANG pattern/must 制約違反 | — | 書き込み拒否 | CLI がエラーを返す（詳細は YANG 制約による） |
| `subtype != SmartSwitch` | なし | 不変（読み取りスキップ） | サイレント。DHCP 設定不生成 |
| `bridge`/`ip_prefix` 片欠落 | なし | 不変（スキップ） | サイレント。midplane DHCP 停止 |
| port が dhcp_members に不在 | WARNING | 不変（当該ポートスキップ） | 他ポートは処理継続 |
| IPv4 アドレスなし dhcp_interface | WARNING | 不変（スキップ） | 他インターフェースは処理継続 |
| `ips` + `ranges` 同時指定 | WARNING | 不変（当該ポートスキップ） | YANG が通常弾くが防御コードあり |
| hostname 未設定 | ERR | 不変 | `generate()` 全体失敗。Kea 設定未更新 |
| dhcrelay ゾンビ起動 | ERR | 不変 | `dhcprelayd` が `sys.exit(1)` → コンテナ再起動 |
| dhcp_server IP 取得タイムアウト | ERR | 不変 | `dhcprelayd` が `sys.exit(1)` → コンテナ再起動 |
| lease ファイル不在 | ERR | 不変 | `DHCP_SERVER_IPV4_LEASE` 更新停止 |

---

## 証拠コード参照

- `dhcp_cfggen.py:67,76` — smart_switch フラグ + サイレントスキップ
- `dhcp_cfggen.py:84` — bridge/ip_prefix 欠落スキップ
- `dhcp_cfggen.py:171-174` — hostname 取得失敗 (LOG_ERR + raise)
- `dhcp_cfggen.py:418-425` — ips+ranges 同時指定 / port不在 (LOG_WARNING)
- `dhcp_cfggen.py:432-433` — IPv4 アドレスなし (LOG_WARNING)
- `dhcprelayd.py:306-313` — dhcrelay ゾンビ (LOG_ERR + sys.exit)
- `dhcprelayd.py:375-385` — dhcp_server IP タイムアウト (LOG_ERR + sys.exit)
- `dhcp_lease.py:116-121` — lease ファイル不在 (LOG_ERR + raise)
- `sonic-smart-switch.yang:63-69` — bridge pattern + ip_prefix must
- `sonic-dhcp-server-ipv4.yang:217-219,231-233` — DHCP_SERVER_IPV4_PORT leafref
