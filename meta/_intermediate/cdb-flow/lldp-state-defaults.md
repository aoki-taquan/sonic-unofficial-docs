# Phase A — LLDP_ENTRY_TABLE (APPL_DB) コード由来デフォルト調査

## 調査対象

`APPL_DB:LLDP_ENTRY_TABLE|<ifname>` — lldpd が受信した LLDP neighbor 情報を lldp-syncd 経由で APPL_DB に書き込むテーブル。

> 注意: テーブル名に "STATE" が含まれないが、実質的に STATE 系テーブルと同等の役割（read-only neighbor cache）。CONFIG_DB には存在しない。

## 根拠コード

| ファイル | 内容 |
|---------|------|
| `sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py` | `lldp_entry_table(if_name)` 関数が `'LLDP_ENTRY_TABLE:' + if_name` を返す。DB は APPL_DB |
| `sonic-snmpagent/src/sonic_ax_impl/mibs/ieee802_1ab.py` | フィールド名列挙 (LLDPRemoteTables, LLDPLocalChassis) + フィールド読み取りロジック |
| `sonic-mgmt-common/translib/lldp_app.go` | const 定義 (LLDP_REMOTE_*) + APPL_DB からの読み取りロジック |
| `sonic-snmpagent/tests/mock_tables/appl_db.json` | 実際のフィールドセット（テスト用モックデータ） |
| `sonic-sairedis/unittest/saidump/dump.json` | 本番相当のフィールドセット |
| `sonic-mgmt-common/tools/test/dbinit.py` | `create_lldp_entry()` 関数でフィールド一覧確認 |

## フィールド一覧と書き込み主体

すべてのフィールドは **lldp-syncd** (lldpd の出力を購読して APPL_DB に書く) が自動書き込み。
外部から直接 CONFIG_DB に書くフィールドは存在しない。

| フィールド | 型 | 典型値 | 出所 |
|-----------|----|--------|------|
| `lldp_rem_chassis_id` | string | `"6a:c1:1c:fc:f7:38"` | LLDP PDU の Chassis ID TLV から |
| `lldp_rem_chassis_id_subtype` | string (int) | `"4"` (= MAC Address) | LLDP PDU の Chassis ID subtype |
| `lldp_rem_port_id` | string | `"Ethernet1"` | LLDP PDU の Port ID TLV |
| `lldp_rem_port_id_subtype` | string (int) | `"5"` (= Interface Name) / `"7"` (= Locally Assigned) | LLDP PDU の Port ID subtype |
| `lldp_rem_port_desc` | string | `""` / `"Port 1/1"` | LLDP PDU の Port Description TLV |
| `lldp_rem_sys_name` | string | `"ARISTA01T1"` | LLDP PDU の System Name TLV |
| `lldp_rem_sys_desc` | string | `"SONiC..."` | LLDP PDU の System Description TLV |
| `lldp_rem_sys_cap_supported` | string | `"28 00"` | System Capabilities TLV (hex) |
| `lldp_rem_sys_cap_enabled` | string | `"28 00"` | System Capabilities TLV (enabled, hex) |
| `lldp_rem_man_addr` | string | `"10.250.2.55"` / `"10.x.x.x,2001:db8::1"` | Management Address TLV (複数の場合カンマ区切り) |
| `lldp_rem_time_mark` | string (int) | `"1765"` | LLDP TimeMark (SNMP sysUpTime 単位 = 10ms) |
| `lldp_rem_index` | string (int) | `"1"` / `"2"` | Remote systems index (LLDP-MIB lldpRemIndex) |

## デフォルト値とコード由来挙動

### フィールド不在時の挙動

- `lldp_rem_port_desc` が空文字列 `""` → SNMP agent は MIB エントリを返すが値が空。`show lldp neighbors detail` 出力に PortDesc 欄が空になる
- `lldp_rem_man_addr` が空文字列 `""` → sonic-snmpagent の `update_rem_if_mgmt()` が `lldp_rem_man_addr` not in lldp_kvs として early return。Management Address MIB エントリが欠落
- `lldp_rem_sys_cap_*` → `parse_sys_capability()` 関数でビットマスク解析。フィールド欠落時は `KeyError` をキャッチして警告ログのみ (ieee802_1ab.py 行 490)

### lldp_rem_chassis_id_subtype の値体系

| 値 | 意味 | 出現条件 |
|----|------|--------|
| `"4"` | MAC Address | 最多。lldpd デフォルト |
| `"5"` | Network Address | IP ベースの chassis ID |
| `"7"` | Locally Assigned | ベンダー独自 |

### lldp_rem_port_id_subtype の値体系

| 値 | 意味 | 出現条件 |
|----|------|--------|
| `"5"` | Interface Name | SONiC 同士の接続でよく見える |
| `"7"` | Locally Assigned | 一部のベンダー装置 |

### lldp_rem_man_addr の複数値フォーマット

IPv4/IPv6 が両方ある場合、カンマ区切り文字列として格納。例: `"10.224.25.100,2603:10e2:290:5016::"`。
sonic-snmpagent は先頭の IPv4 アドレスを優先して SNMP MIB に返す (`parse_sys_capability` ではなく split(',') 処理)。

### LLDP_LOC_CHASSIS テーブル (APPL_DB)

近接テーブルとして `APPL_DB:LLDP_LOC_CHASSIS` (単一エントリ) も存在。こちらは **自ノードの** ローカル LLDP 情報を保持。

| フィールド | 典型値 | 説明 |
|-----------|-------|------|
| `lldp_loc_chassis_id_subtype` | `"5"` | ローカル chassis ID subtype |
| `lldp_loc_chassis_id` | `"00:11:22:AB:CD:EF"` | ローカル chassis ID (MAC) |
| `lldp_loc_sys_name` | `"SONiC"` | ローカルシステム名 |
| `lldp_loc_sys_desc` | `"SONiC Software Version..."` | ローカルシステム説明 |
| `lldp_loc_sys_cap_supported` | `"28 00"` | サポート capability ビットマスク |
| `lldp_loc_sys_cap_enabled` | `"28 00"` | 有効 capability ビットマスク |
| `lldp_loc_man_addr` | `"10.224.25.26,fe80::..."` | ローカル管理アドレス (カンマ区切り) |

`LLDP_LOC_CHASSIS` は lldpd 起動時に `lldpd.conf.j2` / `lldpmgrd` が設定する。SNMP agent が lldpLocalSystemData MIB として提供。

## 書き込み主体と参照主体

| 主体 | 役割 |
|-----|------|
| `lldpd` (open-lldp フォーク, docker-lldp) | LLDP PDU 送受信、内部 DB 保持 |
| `lldp-syncd` | lldpd の JSON 出力を購読して APPL_DB LLDP_ENTRY_TABLE / LLDP_LOC_CHASSIS に書き込む |
| `sonic-snmpagent` (ieee802_1ab.py) | APPL_DB を読んで LLDP-MIB (RFC8516) を SNMP で提供 |
| `sonic-mgmt-common lldp_app.go` | APPL_DB を読んで OpenConfig LLDP (REST/gNMI) を提供 |
| `show lldp` CLI (lldpshow) | lldpctl XML 出力を直接 parse (APPL_DB 非経由) |

## dead field / 欠落フィールド

- LLDP_ENTRY_TABLE に **書き込み側フィールドは存在しない**。すべて lldpd からの受信データ
- `lldp_rem_time_mark` は SNMP TimeMark (10ms 単位 sysUpTime)。現在時刻との差分で TTL 相当を計算可能だが SONiC コードは TTL 超過時のエントリ自動削除を行わない（lldpd 側で管理）
- `lldp_rem_index` は LLDP-MIB の lldpRemIndex に対応するが、SONiC は常に 1 または 2 を設定しており、multi-neighbor per port のシナリオは基本的に考慮していない

## 参考 SHA

- sonic-snmpagent: `329f1cc` (sonic-net/sonic-snmpagent)
- sonic-mgmt-common: `f71cf82` (sonic-net/sonic-mgmt-common)
