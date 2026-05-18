# MGMT_PORT — Phase C 暗黙参照テーブル調査

調査日: 2026-05-18

## 調査対象

- `sonic-buildimage/files/image_config/monit/mgmt_oper_status.py`
- `sonic-buildimage/dockers/docker-lldp/lldpd.conf.j2`
- `sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mgmt_port.yang`

## 検出した暗黙参照

### 1. MGMT_INTERFACE → lldpd.conf.j2 からの間接参照

`lldpd.conf.j2` は `MGMT_INTERFACE` テーブルを `pfx_filter` でループし `mgmt_if.port_name` を取得する。
その後 `MGMT_PORT[mgmt_if.port_name].alias` を参照し、`alias` が存在すれば `configure ports eth0 lldp portidsubtype local {{ alias }}` に使用する（`lldpd.conf.j2:17-18`）。

つまり MGMT_PORT の `alias` フィールドは「MGMT_INTERFACE が存在するとき」のみ LLDP 設定に反映される。
MGMT_INTERFACE が空の場合、`mgmt_if` dict が空になり LLDP 側の管理 IF 設定ブロック自体が生成されない。

### 2. MGMT_PORT → STATE_DB MGMT_PORT_TABLE（mgmt_oper_status.py）

`mgmt_oper_status.py` は CONFIG_DB の `MGMT_PORT|*` エントリを元に `STATE_DB MGMT_PORT_TABLE|<port>` に全フィールドを同期する。
この STATE_DB テーブルを SNMP エージェント (`sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py:196-202`) が `MGMT_PORT_TABLE|<if>` として読み取り OID マップ・エイリアスマップを構築する。

### 3. SNMP エージェントの MGMT_PORT (CONFIG_DB) 直接参照

`sonic_ax_impl/mibs/__init__.py:256-270` は CONFIG_DB の `MGMT_PORT|*` キーを列挙し `alias` フィールドを取得する (`if_alias_map`)。
STATE_DB の `MGMT_PORT_TABLE` ではなく CONFIG_DB を直接参照している点が特徴。

### 4. DEVICE_METADATA.hostname → lldpd.conf.j2

`lldpd.conf.j2:29` は `DEVICE_METADATA['localhost']['hostname']` を参照して `configure system hostname` を設定する。
MGMT_PORT とは直接関係しないが、同一テンプレートで読まれる暗黙依存。

## まとめ

| 参照元 | 参照先 | 内容 |
|--------|--------|------|
| `lldpd.conf.j2:17` | `MGMT_PORT[name].alias` | LLDP portidsubtype local に alias を設定（MGMT_INTERFACE 存在時のみ） |
| `lldpd.conf.j2:2-12` | `MGMT_INTERFACE` (pfx_filter) | port_name を解決するために MGMT_INTERFACE を先読み |
| `mgmt_oper_status.py:16` | `CONFIG_DB MGMT_PORT|*` | STATE_DB MGMT_PORT_TABLE へ同期するためのキー列挙 |
| `sonic_ax_impl/mibs/__init__.py:256` | `CONFIG_DB MGMT_PORT|*` (alias) | SNMP MIB の if_alias_map 構築 |
| `sonic_ax_impl/mibs/__init__.py:196` | `STATE_DB MGMT_PORT_TABLE|*` | SNMP oper_status 読み取り |
