# lldp-state cross-refs 調査メモ

対象テーブル: `LLDP_ENTRY_TABLE` / `LLDP_LOC_CHASSIS` (APPL_DB)

## 調査対象ソース

- `sonic-net/sonic-snmpagent` `src/sonic_ax_impl/mibs/ieee802_1ab.py` (ref: 329f1cc)
- `sonic-net/sonic-snmpagent` `src/sonic_ax_impl/mibs/__init__.py` (ref: 329f1cc)
- `sonic-net/sonic-mgmt-common` `translib/lldp_app.go` (ref: f71cf82)

## 発見した暗黙参照

### 1. lldp-syncd → lldpd (書き込み元)

`lldp-syncd` が `lldpctl -f json` をポーリングして lldpd から PDU 受信データを取得し、
`APPL_DB:LLDP_ENTRY_TABLE|<ifname>` に HSET で書き込む。
CONFIG_DB は直接参照しない。

### 2. LLDP / LLDP_PORT → lldpmgrd → lldpd → LLDP_ENTRY_TABLE (間接)

CONFIG_DB `LLDP|GLOBAL` / `LLDP_PORT|<ifname>` を lldpmgrd が `lldpcli configure lldp ...` コマンドで
lldpd に設定する。これにより自ノードの LLDPDU の内容（portidsubtype = ifname 等）が決まる。
対向ノードが受信する LLDPDU の内容 → 対向の LLDP_ENTRY_TABLE に反映される（間接的）。

### 3. sonic-snmpagent → PORT_TABLE (APPL_DB)

`ieee802_1ab.py` `LLDPLocalSystemDataUpdater._get_if_entry()` (L200-213):
- データプレーンポート (Ethernet*): `APPL_DB:PORT_TABLE:<ifname>` を `hgetall` で参照
- 管理ポート (eth0 等): CONFIG_DB `MGMT_PORT|<name>` を参照
- OID ↔ ifname マップ: `mibs.init_sync_d_interface_tables()` → COUNTERS_DB or APPL_DB で解決

### 4. sonic-mgmt-common lldp_app.go → OpenConfig LLDP YANG

`lldp_app.go` L82: `app.neighTs = &db.TableSpec{Name: "LLDP_ENTRY_TABLE"}`
`lldp_app.go` L327: `app.appDb.GetTable(app.neighTs)` で LLDP_ENTRY_TABLE 全体を取得。
CONFIG_DB は参照しない。

### 5. YANG スキーマ

APPL_DB の LLDP_ENTRY_TABLE / LLDP_LOC_CHASSIS に対応する YANG モデルは存在しない。
CONFIG_DB 側の LLDP/LLDP_PORT は `sonic-lldp.yang` で定義されている。

## 結論

LLDP_ENTRY_TABLE の主な暗黙参照:
- 書き込み元: lldpd (open-lldp) 経由 lldp-syncd
- 読み取り元: sonic-snmpagent (LLDP-MIB)、sonic-mgmt-common (REST/gNMI)
- 間接依存: APPL_DB PORT_TABLE (SNMP OID マッピング)、CONFIG_DB MGMT_PORT (管理ポート)
- 間接書き込み制御: CONFIG_DB LLDP / LLDP_PORT → lldpmgrd → lldpd の LLDPDU 内容を制御
