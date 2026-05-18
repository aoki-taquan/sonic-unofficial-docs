# LLDP_PORT — Phase F 副次 DB 書込スキャンノート

対象テーブル: `LLDP_PORT`
Consumer: `lldpmgrd` (`sonic-buildimage/dockers/docker-lldp/lldpmgrd`)
スキャン範囲: 全行 grep `set(` / `hset` / `Producer` / `Notification` / `Table` による DB 書込確認

---

## スキャン結果

### APPL_DB 書込確認

`lldpmgrd` の `self.appl_db` (lldpmgrd:60-63) は読み取り専用接続。
- `sst_appdb = swsscommon.SubscriberStateTable(self.appl_db, APP_PORT_TABLE_NAME)` (lldpmgrd:301) — subscribe のみ
- `self.app_port_table = swsscommon.Table(self.appl_db, APP_PORT_TABLE_NAME)` (lldpmgrd:77) — `Table.get()` 参照のみ
- APPL_DB への `set()` / `hset()` / `ProducerStateTable` 呼び出し: **0 件**

### STATE_DB 書込確認

`lldpmgrd` の `self.state_db` (lldpmgrd:66-68) と `self.state_port_table` (lldpmgrd:78) は読み取り専用。
- `self.state_port_table.get(port_name)` (lldpmgrd:122) — `is_port_up()` 内の読み取りのみ
- STATE_DB への書込: **0 件**

### CONFIG_DB 書込確認

`lldpmgrd` の CONFIG_DB 接続 (lldpmgrd:56-59) は Table を読み取り専用で使用。
- `self.device_table.get()` / `self.port_table.get()` / `self.mgmt_table.getKeys()` — 読み取りのみ
- CONFIG_DB への書込: **0 件**

### 外部プロセス呼び出し

唯一の副作用は `subprocess.Popen(["lldpcli", ...])` の呼び出し:
- `update_hostname()` (lldpmgrd:90): `lldpcli configure system hostname <hostname>`
- `update_mgmt_addr()` (lldpmgrd:108): `lldpcli configure/unconfigure system ip management pattern <ip>`
- `process_pending_cmds()` (lldpmgrd:184): `lldpcli configure ports <ifname> lldp portidsubtype local <alias> [description <desc>]`
- `run()` (lldpmgrd:338): `lldpcli resume`

いずれも lldpd プロセスへの設定注入のみで、Redis DB には一切書き込まない。

## 結論

副次 DB 書込: **なし**（全 DB において書込コードが存在しない）
