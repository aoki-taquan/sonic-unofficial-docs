# LLDP_PORT — Phase C 暗黙参照テーブルスキャンノート

対象テーブル: `LLDP_PORT|<ifname>`
Consumer: `lldpmgrd` (`sonic-buildimage/dockers/docker-lldp/lldpmgrd`)
スキャン範囲: sonic-lldp.yang, lldpmgrd 全行精読, lldpd.conf.j2, sonic-port.yang

---

## 検出した暗黙参照・被参照

### 1. PORT テーブルへの leafref（YANG 明示参照）

- `sonic-lldp.yang:107-110`:
  ```yang
  leaf ifname {
      type leafref {
          path "/prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name";
      }
  }
  ```
- `LLDP_PORT.ifname` は `PORT|<ifname>` への正式 leafref。
- mgmt-framework 経由のバリデーション有効時、`PORT` に存在しないインターフェース名は拒否される。
- 参照方向: `LLDP_PORT` → `PORT`（順参照）
- evidence: `sonic-lldp.yang:107-110`

### 2. lldpmgrd が実行時に参照する PORT テーブル（暗黙 runtime 参照）

- `lldpmgrd:75`: `self.port_table = swsscommon.Table(self.config_db, swsscommon.CFG_PORT_TABLE_NAME)`
- `lldpmgrd:140-150`: `generate_pending_lldp_config_cmd_for_port()` が `PORT.alias` と `PORT.description` を読む。
  - `port_alias = port_table_dict.get("alias")` → lldpcli の `portidsubtype local <alias>` に使用
  - `port_desc = port_table_dict.get("description")` → lldpcli の `description <desc>` に使用
- LLDP_PORT 自体のフィールドは読まれないが、対応する `PORT` エントリの `alias` / `description` が lldpcli コマンドに反映される。
- 参照方向: lldpmgrd → `CONFIG_DB: PORT` (runtime 読み取り)
- evidence: `lldpmgrd:75,140-162`

### 3. STATE_DB PORT_TABLE への参照（oper_status ゲート）

- `lldpmgrd:78`: `self.state_port_table = swsscommon.Table(self.state_db, swsscommon.STATE_PORT_TABLE_NAME)`
- `lldpmgrd:116-134`: `is_port_up()` が `STATE_DB: PORT_TABLE|<ifname>.netdev_oper_status` を読んで up/down を判定。
- `LLDP_PORT` 設定の lldpcli 発行は `STATE_DB PORT_TABLE` の `netdev_oper_status=up` に依存。
- 参照方向: lldpmgrd → `STATE_DB: PORT_TABLE`（runtime 読み取り）
- evidence: `lldpmgrd:78,116-134`

### 4. APPL_DB PORT_TABLE への参照（PortInitDone / PortConfigDone）

- `lldpmgrd:77`: `self.app_port_table = swsscommon.Table(self.appl_db, swsscommon.APP_PORT_TABLE_NAME)`
- `lldpmgrd:301`: `sst_appdb = swsscommon.SubscriberStateTable(self.appl_db, swsscommon.APP_PORT_TABLE_NAME)`
- `lldpmgrd:259-273`: `PortInitDone` および `PortConfigDone` キーを APPL_DB PORT_TABLE から受信するまで `lldpcli resume` を保留。
- 参照方向: lldpmgrd → `APPL_DB: PORT_TABLE`（subscribe + runtime 読み取り）
- evidence: `lldpmgrd:77,301,259-273`

### 5. DEVICE_METADATA テーブルへの参照（hostname）

- `lldpmgrd:73`: `self.device_table = swsscommon.Table(self.config_db, swsscommon.CFG_DEVICE_METADATA_TABLE_NAME)`
- `lldpmgrd:319-320`: `sst_device_confdb` を購読し `DEVICE_METADATA|localhost.hostname` または `chassis_hostname` が変化すると `lldpcli configure system hostname` を発行。
- `LLDP_PORT` 自体の処理には直接関与しないが、同一デーモン内で管理されるグローバル hostname 設定のソース。
- 参照方向: lldpmgrd → `CONFIG_DB: DEVICE_METADATA`（subscribe）
- evidence: `lldpmgrd:73,319-320`

### 6. MGMT_INTERFACE テーブルへの参照（Management Address TLV）

- `lldpmgrd:74`: `self.mgmt_table = swsscommon.Table(self.config_db, swsscommon.CFG_MGMT_INTERFACE_TABLE_NAME)`
- `lldpmgrd:317-318`: `sst_mgmt_ip_confdb` を購読し IP 変化で `lldpcli configure system ip management pattern` を更新。
- `LLDP_PORT` 直接の依存ではないが、lldpmgrd が同一 event ループで管理する。
- 参照方向: lldpmgrd → `CONFIG_DB: MGMT_INTERFACE`（subscribe）
- evidence: `lldpmgrd:74,317-318`

---

## 参照サマリ

| # | 依存方向 | 参照元 | 参照先テーブル | 参照先キー形式 | 依存内容 | 強度 |
|---|----------|--------|--------------|--------------|---------|------|
| 1 | 順参照（YANG leafref） | `LLDP_PORT.ifname` | `CONFIG_DB: PORT` | `PORT\|<ifname>` | バリデーション有効時の存在確認 | 強（mgmt-fw 経由） |
| 2 | runtime 読み取り | lldpmgrd | `CONFIG_DB: PORT` | `PORT\|<ifname>` | `alias`→portidsubtype, `description`→lldpcli description | 強（実際の LLDP 動作に影響） |
| 3 | runtime 読み取り | lldpmgrd | `STATE_DB: PORT_TABLE` | `PORT_TABLE\|<ifname>` | `netdev_oper_status=up` ゲート | 強（up まで lldpcli スキップ） |
| 4 | subscribe + 読み取り | lldpmgrd | `APPL_DB: PORT_TABLE` | `PORT_TABLE\|PortInitDone` 等 | lldpcli resume のゲート | 強（resume 前は PDU 送出なし） |
| 5 | subscribe | lldpmgrd | `CONFIG_DB: DEVICE_METADATA` | `DEVICE_METADATA\|localhost` | hostname → lldpcli system hostname | 間接（LLDP_PORT 直接影響なし） |
| 6 | subscribe | lldpmgrd | `CONFIG_DB: MGMT_INTERFACE` | `MGMT_INTERFACE\|*` | mgmt IP → Management Address TLV | 間接（LLDP_PORT 直接影響なし） |
