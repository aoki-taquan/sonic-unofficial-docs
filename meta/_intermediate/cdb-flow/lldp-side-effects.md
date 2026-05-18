# lldp — Phase F 副次 DB 書込 調査メモ

調査対象: `LLDP|GLOBAL` / `LLDP_PORT|<ifname>` テーブル  
調査ソース: `dockers/docker-lldp/lldpmgrd`, `dockers/docker-lldp/supervisord.conf.j2`

## lldpmgrd の DB 書込パス

`lldpmgrd` は DB への**書込みを一切行わない**。

- `swsscommon.Table(self.state_db, swsscommon.STATE_PORT_TABLE_NAME)` — 読み取り専用 (is_port_up)
- `swsscommon.Table(self.config_db, ...)` — 読み取り専用 (device_table, port_table, mgmt_table)
- `swsscommon.Table(self.appl_db, swsscommon.APP_PORT_TABLE_NAME)` — 読み取り専用 (app_port_table)
- `swsscommon.SubscriberStateTable(...)` — イベント購読のみ

lldpmgrd が行う外部副作用は `lldpcli` サブプロセス呼び出しのみ（lldpd プロセスへのコマンド注入）。

## lldp-syncd の役割

`supervisord.conf.j2` によれば `lldp-syncd` (`python3 -m lldp_syncd`) は `lldpd` プロセスが起動後に開始される。  
`lldp-syncd` は lldpd の Unix ソケットをポーリングして LLDP ネイバー情報を `APPL_DB LLDP_ENTRY_TABLE` に書き込む責務を持つ（SNMP エージェント `sonic_ax_impl/mibs/ieee802_1ab.py:254` が APPL_DB `LLDP_ENTRY_TABLE:*` をサブスクライブして確認）。

- APPL_DB `LLDP_ENTRY_TABLE|<ifname>` — ネイバー情報を格納
  - `lldp_rem_chassis_id`, `lldp_rem_port_id`, `lldp_rem_sys_name` 等のフィールド
  - `show lldp neighbors` / `show lldp table` はここを参照

## STATE_DB への書込み

lldpmgrd も lldp-syncd も STATE_DB への書込みは行わない。  
STATE_DB は PORT_TABLE の `netdev_oper_status` を **読み取るだけ**（lldpmgrd:78, is_port_up()）。

## COUNTERS_DB / ERROR_TABLE

関与なし。

## まとめ

| コンポーネント | 書込先 DB | テーブル | evidence |
|---|---|---|---|
| lldpmgrd | なし（DB 書込ゼロ） | — | lldpmgrd 全行確認 |
| lldp-syncd | APPL_DB | `LLDP_ENTRY_TABLE|<ifname>` | ieee802_1ab.py:254, mibs/__init__.py:160 |
| lldpd (lldpcli 経由) | — | lldpd 内部ソケット状態のみ | lldpmgrd:156,184 |
