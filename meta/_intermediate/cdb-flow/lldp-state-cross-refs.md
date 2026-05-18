# LLDP_ENTRY_TABLE / LLDP_LOC_CHASSIS — Phase C テーブル間クロスリファレンス スキャンノート

対象テーブル: `LLDP_ENTRY_TABLE`, `LLDP_LOC_CHASSIS` (APPL_DB)
Consumer: `sonic-snmpagent` (`ieee802_1ab.py`), `sonic-mgmt-common` (`lldp_app.go`), `lldpmgrd`
スキャン範囲: `ieee802_1ab.py` 全行、`lldp_app.go` 全行、`lldpmgrd` 全行精読

---

## 検出したクロスリファレンス

### 1. PORT_TABLE (APPL_DB) ← OID/IF マッピング (sonic-snmpagent)

`LLDPRemTableUpdater.reinit_data()` は `Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_interface_tables, ...)` を呼び、
APPL_DB の `PORT_TABLE:*` から interface 名 → OID マッピングを構築する。
この OID マッピングが存在しないポート名で `LLDP_ENTRY_TABLE:<ifname>` が存在しても SNMP OID に変換されず、SNMP walk に現れない。

**参照関係**: `LLDP_ENTRY_TABLE` の有効な SNMP OID インデックス化は `PORT_TABLE` (APPL_DB) の OID マッピングに依存する。

evidence: `ieee802_1ab.py:416-423`, `mibs/__init__.py:276-333`

### 2. MGMT_PORT_TABLE (CONFIG_DB) ← 管理ポート OID マッピング (sonic-snmpagent)

`LocPortUpdater._get_if_entry()` は、インターフェース名が `mgmt_oid_name_map` に含まれる場合 CONFIG_DB の `MGMT_PORT_TABLE` から取得する。
通常のデータプレーンポートは APPL_DB の `PORT_TABLE` から取得する (db=APPL_DB)。
管理ポート (`eth0` 等) のエントリは CONFIG_DB 経由となる。

evidence: `ieee802_1ab.py:206-215`

### 3. DEVICE_METADATA|localhost (CONFIG_DB) ← hostname → lldpcli 設定 (lldpmgrd)

`lldpmgrd` は `DEVICE_METADATA` テーブル (`CFG_DEVICE_METADATA_TABLE_NAME`) を購読する。
`lldp_process_device_table_event()` が `hostname` / `chassis_hostname` フィールドの変化を検知して
`lldpcli configure system hostname <hostname>` を呼び出す。
この hostname が lldpd の送信 LLDPDU の system name TLV に反映され、
対向ノードの `LLDP_ENTRY_TABLE:<if>` の `lldp_rem_sys_name` として現れる。

**参照関係**: 自ノードの `LLDP_ENTRY_TABLE` が対向ノードの APPL_DB に書かれる内容は `DEVICE_METADATA|localhost.hostname` に間接依存する。

evidence: `lldpmgrd:74, 247-256, 308-310`

### 4. MGMT_INTERFACE (CONFIG_DB) ← 管理 IP → lldpcli 設定 (lldpmgrd)

`lldpmgrd` は `MGMT_INTERFACE` テーブル (`CFG_MGMT_INTERFACE_TABLE_NAME`) を購読する。
`lldp_process_mgmt_info_change()` が IP アドレス変化を検知して
`lldpcli configure system ip management pattern <ip>` を呼び出す。
この管理 IP が LLDPDU の Management Address TLV として対向ノードの
`LLDP_ENTRY_TABLE:<if>` の `lldp_rem_man_addr` フィールドに伝播する。

**参照関係**: `lldp_rem_man_addr` の値は `MGMT_INTERFACE` (CONFIG_DB) の IP アドレスに間接依存する。

evidence: `lldpmgrd:76, 228-245, 304-306`

### 5. PORT_TABLE (APPL_DB) ← port oper_status → lldpcli 設定 (lldpmgrd)

`lldpmgrd` は APPL_DB の `PORT_TABLE` (`APP_PORT_TABLE_NAME`) を購読する。
`lldp_process_port_table_event()` はポートの `oper_status=up` を検知して
`generate_pending_lldp_config_cmd_for_port()` を呼び、ポートの alias / description を
`lldpcli configure ports <port> lldp portidsubtype local <alias>` で lldpd に設定する。
ポートの alias が LLDPDU の port ID TLV として対向ノードの `lldp_rem_port_id` に伝播する。

また、PortInitDone / PortConfigDone を STATE_DB の PORT_TABLE から受け取り `lldpcli resume` を実行する。

**参照関係**: 対向ノードの `lldp_rem_port_id` は自ノードの `PORT_TABLE.alias` に間接依存する。

evidence: `lldpmgrd:77, 258-273, 300-325`

### 6. LLDP_LOC_CHASSIS (APPL_DB) ← SNMP MIB: lldpLocalSystemData (sonic-snmpagent)

`LLDPLocalSystemDataUpdater.reinit_data()` は APPL_DB の `LLDP_LOC_CHASSIS` を `dbs_get_all` で全フィールド取得する。
これを `lldpLocalChassisIdSubtype`, `lldpLocalChassisId` 等の SNMP OID にマッピングする。
`LLDPLocManAddrUpdater` は `LLDP_LOC_CHASSIS` の `lldp_loc_man_addr` フィールドから管理 IPv4 アドレスを取得して
`lldpLocManAddrTable` SNMP MIB に返す。

**参照関係**: SNMP `lldpLocalSystemData` / `lldpLocManAddrTable` は `LLDP_LOC_CHASSIS` に直接依存。

evidence: `ieee802_1ab.py:114-146, 302-345`

---

## クロスリファレンスサマリ

| 参照元 | 参照先テーブル | 参照方向 | 条件 | evidence |
|--------|--------------|---------|------|----------|
| `LLDP_ENTRY_TABLE` OID インデックス | `PORT_TABLE` (APPL_DB) | 読み取り: OID→IF マップ | 常時。マップ不在ポートは SNMP に出現しない | `ieee802_1ab.py:416-423` |
| `LLDP_ENTRY_TABLE` (管理ポート参照) | `MGMT_PORT_TABLE` (CONFIG_DB) | 読み取り: alias | 管理ポート (`eth0` 等) に限る | `ieee802_1ab.py:206-215` |
| `lldp_rem_sys_name` (対向の APPL_DB) | `DEVICE_METADATA\|localhost.hostname` (CONFIG_DB) | 間接: lldpmgrd → lldpcli → LLDPDU | 常時。hostname 変更時 lldpcli 再設定 | `lldpmgrd:247-256` |
| `lldp_rem_man_addr` (対向の APPL_DB) | `MGMT_INTERFACE` (CONFIG_DB) | 間接: lldpmgrd → lldpcli → LLDPDU | 常時。管理 IP 変更時 lldpcli 再設定 | `lldpmgrd:228-245` |
| `lldp_rem_port_id` (対向の APPL_DB) | `PORT_TABLE.alias` (APPL_DB) | 間接: lldpmgrd → lldpcli → LLDPDU | ポート up 時。alias なき場合はポート名を使用 | `lldpmgrd:136-166` |
| SNMP `lldpLocalSystemData` | `LLDP_LOC_CHASSIS` (APPL_DB) | 直接読み取り | 常時。lldp-syncd 起動後 | `ieee802_1ab.py:114-146` |
