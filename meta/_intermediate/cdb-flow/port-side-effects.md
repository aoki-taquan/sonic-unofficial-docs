# PORT SET/DEL 副次 DB 書込 分析 (Phase F)

生成日: 2026-05-15  更新日: 2026-05-16
ソース:
- `sonic-swss/cfgmgr/portmgr.cpp` / `portmgr.h`
- `sonic-swss/orchagent/portsorch.cpp` / `portsorch.h`
- `sonic-swss/portsyncd/portsyncd.cpp`

## 調査対象 DB 適用可否確認

| DB / テーブル名 | portsorch.cpp での使用 | 備考 |
|----------------|----------------------|------|
| APPL_DB / `PORT_TABLE` | 使用あり (`m_portTable`) | portmgrd 転送・oper_status・flap_count |
| APPL_DB / `PORT_TABLE_TX_READY` | **使用なし** | このテーブル名は portsorch.cpp に存在しない。`host_tx_ready` フィールドは STATE_DB の `PORT_TABLE` に書き込まれる (`m_portStateTable.hset(..., "host_tx_ready", ...)`, `portsorch.cpp:2274`) |
| STATE_DB / `PORT_TABLE` | 使用あり (`m_portStateTable`) | supported_speeds, supported_fecs, host_tx_ready, link_training_status 等 |
| APPL_STATE_DB | **使用なし** | portsorch は `ResponsePublisher m_publisher{"APPL_STATE_DB"}` を持つ (`orch.h:382`) が、PORT テーブル処理に対して `m_publisher.publish()` を呼び出していないため書き込みは発生しない |
| COUNTERS_DB | 使用あり (`m_counter_db`) | COUNTERS_PORT_NAME_MAP, Queue/PG マップ群 |

---

## portmgrd (cfgmgr/portmgr.cpp)

portmgrd は CONFIG_DB の PORT テーブルを購読し、APPL_DB への書き込みと netdev 操作を行う。
STATE_DB への直接書き込みは行わない（portmgrd は STATE_DB を読み取り専用で参照する）。

### SET (PORT|<name>)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_appPortTable.set(alias, field_values)` | APPL_DB / `PORT_TABLE` | `<name>` | 常時 (writeConfigToAppDb) |
| `m_appPortTable.set(alias, {mtu})` | APPL_DB / `PORT_TABLE` | `<name>` field=`mtu` | mtu フィールドが存在する場合 (または初回でデフォルト 9100) |
| `m_appPortTable.set(alias, {admin_status})` | APPL_DB / `PORT_TABLE` | `<name>` field=`admin_status` | admin_status フィールドが存在する場合 (または初回でデフォルト "down") |

カーネル変更 (副次 DB 書込ではなくカーネル操作):
- `ip link set <alias> mtu <mtu>` — MTU 設定 (`setPortMtu()`)
- `ip link set <alias> up/down` — admin_status 反映 (`setPortAdminStatus()`)

### DEL (PORT|<name>)

| 操作 | 対象 DB / テーブル | キー | 条件 |
|------|------------------|------|------|
| `m_appPortTable.del(alias)` | APPL_DB / `PORT_TABLE` | `<name>` | 常時 |

---

## PortsOrch (orchagent/portsorch.cpp)

PortsOrch は APPL_DB の PORT_TABLE を購読し、SAI 呼び出し後に STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB へ書き込む。

### SET — ポート新規作成 (addPort / initPort)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_counterNameMapUpdater->setCounterNameMap(alias, port_id)` | COUNTERS_DB / `COUNTERS_PORT_NAME_MAP` | `""` field=`<alias>` | ポート作成時 (常時) |
| `m_portSerdesIdToPortIdTable->set("", fields)` | COUNTERS_DB / `COUNTERS_PORT_SERDES_ID_TO_PORT_ID_MAP` | `""` field=`<serdes_oid>=<port_oid>` | port_serdes_id が有効な場合 |
| `port_stat_manager.setCounterIdList(port_id, PORT, stats)` | FLEX_COUNTER_DB / `PORT_STAT_COUNTER_FLEX_COUNTER_GROUP:<oid>` | `<oid>` | PortCountersState が有効な場合 |
| `gb_port_stat_manager.setCounterIdList(system_side_id, ...)` | FLEX_COUNTER_DB (GB_COUNTERS_DB) | `<system_side_oid>` | Gearbox system_side_id が存在する場合 |
| `gb_port_stat_manager.setCounterIdList(line_side_id, ...)` | FLEX_COUNTER_DB (GB_COUNTERS_DB) | `<line_side_oid>` | Gearbox line_side_id が存在する場合 |
| `port_phy_attr_manager.setCounterIdList(port_id, PORT_PHY_ATTR, stats)` | FLEX_COUNTER_DB / `PORT_PHY_ATTR_FLEX_COUNTER_GROUP:<oid>` | `<oid>` | PortPhyAttrCounterState が有効かつ PHY タイプの場合 |
| `port_phy_serdes_attr_manager.setCounterIdList(serdes_id, ...)` | FLEX_COUNTER_DB / `PORT_PHY_SERDES_ATTR_FLEX_COUNTER_GROUP:<serdes_oid>` | `<serdes_oid>` | PhySerdesAttrCountersState が有効かつ PHY タイプで serdes_id が有効な場合 |
| `port_buffer_drop_stat_manager.setCounterIdList(port_id, PORT, stats)` | FLEX_COUNTER_DB / `PORT_BUFFER_DROP_STAT_FLEX_COUNTER_GROUP:<oid>` | `<oid>` | PortBufferDropCountersState が有効な場合 |
| `wred_port_stat_manager.setCounterIdList(port_id, PORT, stats)` | FLEX_COUNTER_DB / `WRED_PORT_STAT_COUNTER_FLEX_COUNTER_GROUP:<oid>` | `<oid>` | WredPortCountersState が有効な場合 |
| `addPortBufferQueueCounters(p, 0, maxQ-1, false)` | COUNTERS_DB / `COUNTERS_QUEUE_NAME_MAP`, `COUNTERS_QUEUE_PORT_MAP`, `COUNTERS_QUEUE_INDEX_MAP`, `COUNTERS_QUEUE_TYPE_MAP` | `""` | QueueCountersState または QueueWatermarkCountersState が有効な場合 |
| `addPortBufferPgCounters(p, 0, maxPG-1)` | COUNTERS_DB / `COUNTERS_PG_NAME_MAP`, `COUNTERS_PG_PORT_MAP`, `COUNTERS_PG_INDEX_MAP` | `""` | PgCountersState または PgWatermarkCountersState が有効な場合 |
| `generateQueueMapPerPort(p, ...)` | COUNTERS_DB / `COUNTERS_QUEUE_PORT_MAP`, `COUNTERS_QUEUE_INDEX_MAP`, `COUNTERS_QUEUE_TYPE_MAP` | `""` | QueueFcEnabled かつ queue_ids が空でない場合 |

SAI 呼び出し (ASIC_DB へ反映):
- `sai_port_api->create_ports(...)` (bulk) または `create_port(...)` — ASIC_DB に PORT OID エントリ生成

### SET — ポート属性変更 (doPortTask / フィールド dispatch)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_portStateTable.set(alias, {supported_speeds})` | STATE_DB / `PORT_TABLE` | `<alias>` field=`supported_speeds` | initPortSupportedSpeeds() — SAI からサポート速度リストを取得できた場合 |
| `m_portStateTable.set(alias, {supported_fecs})` | STATE_DB / `PORT_TABLE` | `<alias>` field=`supported_fecs` | initPortSupportedFecModes() — SAI からサポート FEC リストを取得できた場合 |
| `m_portStateTable.hset(alias, "host_tx_ready", status)` | STATE_DB / `PORT_TABLE` | `<alias>` field=`host_tx_ready` | admin_status 変更時 — cmisModuleAsyncNotifSupported が false の場合 |
| `m_portStateTable.hset(alias, "link_training_status", status)` | STATE_DB / `PORT_TABLE` | `<alias>` field=`link_training_status` | link_training フィールド処理時 |
| `m_portStateTable.hset(alias, "phy_ctrl_unreliable_los", ...)` | STATE_DB / `PORT_TABLE` | `<alias>` field=`phy_ctrl_unreliable_los` | speed 変更時に LOS 信頼性フラグを更新 |
| `m_portStateTable.hdel(alias, "rmt_adv_speeds")` | STATE_DB / `PORT_TABLE` | `<alias>` field=`rmt_adv_speeds` | autoneg off 設定時に remote advertised speeds をクリア |

SAI 呼び出し (ASIC_DB へ反映):
- `sai_port_api->set_port_attribute(SAI_PORT_ATTR_SPEED)` など各フィールドに対応する SAI 属性

### SET — oper_status 非同期通知受信 (handleNotification / updateDbPortOperStatus)

syncd から `port_state_change` 通知を受けた場合に発生する副次書き込み:

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_portTable->set(alias, {oper_status})` | APPL_DB / `PORT_TABLE` | `<alias>` field=`oper_status` | port_state_change 通知受信時 (常時) |
| `m_portTable->hset(alias, "flap_count", count)` | APPL_DB / `PORT_TABLE` | `<alias>` field=`flap_count` | oper_status が DOWN に遷移した場合 |
| `m_portStateTable.hset(alias, "rmt_adv_speeds", adv_speeds)` | STATE_DB / `PORT_TABLE` | `<alias>` field=`rmt_adv_speeds` | autoneg on 時にリモート広告速度を取得できた場合 |
| `m_portStateTable.hset(alias, "link_training_status", status)` | STATE_DB / `PORT_TABLE` | `<alias>` field=`link_training_status` | link_training 状態変化時 |

注意: `m_portTable` は APPL_DB の `PORT_TABLE` を指す。oper_status は STATE_DB ではなく APPL_DB に書き込まれる。

### DEL — ポート削除 (deInitPort / removePort)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_counterNameMapUpdater->delCounterNameMap(alias)` | COUNTERS_DB / `COUNTERS_PORT_NAME_MAP` | `""` field=`<alias>` 削除 | 常時 |
| `m_portSerdesIdToPortIdTable->hdel("", serdes_oid)` | COUNTERS_DB / `COUNTERS_PORT_SERDES_ID_TO_PORT_ID_MAP` | `""` | serdes_id が存在する場合 |
| `port_stat_manager.clearCounterIdList(port_id)` | FLEX_COUNTER_DB / `PORT_STAT_COUNTER_FLEX_COUNTER_GROUP:<oid>` 削除 | `<oid>` | PortCountersState が有効な場合 |
| `port_buffer_drop_stat_manager.clearCounterIdList(port_id)` | FLEX_COUNTER_DB / `PORT_BUFFER_DROP_STAT_FLEX_COUNTER_GROUP:<oid>` 削除 | `<oid>` | PortBufferDropCountersState が有効な場合 |
| `wred_port_stat_manager.clearCounterIdList(port_id)` | FLEX_COUNTER_DB / `WRED_PORT_STAT_COUNTER_FLEX_COUNTER_GROUP:<oid>` 削除 | `<oid>` | WredPortCountersState が有効な場合 |
| `port_phy_attr_manager.clearCounterIdList(port_id)` | FLEX_COUNTER_DB / `PORT_PHY_ATTR_FLEX_COUNTER_GROUP:<oid>` 削除 | `<oid>` | phy_attrs が有効かつ PHY タイプの場合 |
| `port_phy_serdes_attr_manager.clearCounterIdList(serdes_id)` | FLEX_COUNTER_DB / `PORT_PHY_SERDES_ATTR_FLEX_COUNTER_GROUP:<serdes_oid>` 削除 | `<serdes_oid>` | PHY タイプで serdes_id が有効な場合 |
| `deletePortBufferQueueCounters(p, 0, maxQ-1, false)` | COUNTERS_DB / Queue マップテーブル群 削除 | `""` | QueueCountersState または QueueWatermarkCountersState が有効な場合 |
| `deletePortBufferPgCounters(p, 0, maxPG-1)` | COUNTERS_DB / PG マップテーブル群 削除 | `""` | PgCountersState または PgWatermarkCountersState が有効な場合 |
| `m_stateBufferMaximumValueTable->del(alias)` | STATE_DB / `BUFFER_MAX_PARAM_TABLE` | `<alias>` | 常時 |

SAI 呼び出し (ASIC_DB から削除):
- `sai_port_api->remove_port(port_id)` — ASIC_DB の PORT OID エントリ削除
- `removePortSerdesAttribute(port_id)` — PORT_SERDES エントリも自動削除 (`portsorch.cpp:1526`)

---

## portsyncd (portsyncd/portsyncd.cpp)

portsyncd は起動時に CONFIG_DB から PORT を読み取り APPL_DB へ転送する。PORT 操作そのものの副次書き込みではなく初期化シグナルとして機能する。

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `p.set(key, attrs)` (ProducerStateTable) | APPL_DB / `PORT_TABLE` | `<Ethernet*>` | 通常起動時 (warm=false) に全 PORT エントリを転送 |
| `p.set("PortConfigDone", {count})` | APPL_DB / `PORT_TABLE` | `PortConfigDone` field=`count` | 全ポート転送完了後 (通常起動時のみ) |
| `p.set("PortInitDone", attrs)` | APPL_DB / `PORT_TABLE` | `PortInitDone` | kernel netlink でネットワークデバイス生成完了後 |

注意: warm reboot 中は `p.set(key, ...)` および `notifyPortConfigDone()` をスキップする (`portsyncd.cpp:205,211`)。

---

## 副次書き込みサマリ

| DB | 副次書き込みテーブル | SET 時 | DEL 時 |
|----|---------------------|--------|--------|
| APPL_DB | `PORT_TABLE` | SET (portmgrd → 各フィールド転送) | DEL |
| APPL_DB | `PORT_TABLE.oper_status` | SET (portsorch, port_state_change 受信時) | — |
| APPL_DB | `PORT_TABLE.flap_count` | SET (opsorch, DOWN 遷移時) | — |
| STATE_DB | `PORT_TABLE.supported_speeds` | SET (portsorch, SAI 能力取得時) | — |
| STATE_DB | `PORT_TABLE.supported_fecs` | SET (portsorch, SAI 能力取得時) | — |
| STATE_DB | `PORT_TABLE.host_tx_ready` | SET (opsorch, admin_status 変更時) | — |
| STATE_DB | `PORT_TABLE.link_training_status` | SET (portsorch) | — |
| STATE_DB | `PORT_TABLE.phy_ctrl_unreliable_los` | SET (opsorch, speed 変更時) | — |
| STATE_DB | `PORT_TABLE.rmt_adv_speeds` | SET/DEL (portsorch, autoneg on/off) | — |
| STATE_DB | `BUFFER_MAX_PARAM_TABLE` | — | DEL |
| COUNTERS_DB | `COUNTERS_PORT_NAME_MAP` | SET (portsorch, ポート作成時) | DEL (deInitPort) |
| COUNTERS_DB | `COUNTERS_PORT_SERDES_ID_TO_PORT_ID_MAP` | SET (opsorch, serdes 有効時) | DEL |
| COUNTERS_DB | `COUNTERS_QUEUE_NAME_MAP` 等 Queue マップ群 | SET (opsorch, QueueFcEnabled 時) | DEL |
| COUNTERS_DB | `COUNTERS_PG_NAME_MAP` 等 PG マップ群 | SET (opsorch, PgFcEnabled 時) | DEL |
| FLEX_COUNTER_DB | `PORT_STAT_COUNTER_FLEX_COUNTER_GROUP` 等 | SET (opsorch, FlexCounter 有効時) | DEL (clearCounterIdList) |
| ASIC_DB | PORT OID エントリ (syncd 経由) | create_ports / create_port (SAI) | remove_port (SAI) |
| ASIC_DB | PORT_SERDES OID エントリ | 自動作成 (initPort 内) | 自動削除 (removePort 内) |
