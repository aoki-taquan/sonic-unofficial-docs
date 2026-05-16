# DEVICE_METADATA SET/DEL 副次 DB 書込 分析 (Phase F)

ソース調査ファイル:
- `sonic-swss/cfgmgr/buffermgr.cpp` — BufferMgr::doBufferMetaTask()
- `sonic-swss/orchagent/flexcounterorch.cpp` — FlexCounterOrch::handleDeviceMetadataTable()
- `sonic-swss/fpmsyncd/fpmsyncd.cpp` + `routesync.cpp` — suppress-fib-pending 動的切替
- `sonic-host-services/scripts/hostcfgd` — DeviceMetaCfg.*

## DEVICE_METADATA|localhost SET 操作

### 1. BufferMgr (buffermgr.cpp:373-410)

`buffer_model` フィールドの変化を監視し、内部フラグ `dynamic_buffer_model` を更新する。
DB 書込は発生しないが、フラグ更新後の **後続の BUFFER_POOL/PG/QUEUE/PROFILE SET/DEL** に影響する:

- `dynamic_buffer_model = true` のとき → BUFFER_POOL / BUFFER_PG / BUFFER_QUEUE / BUFFER_PROFILE の変化を **APPL_DB に転写しない**（buffermgrd.cpp:476-479）
- `dynamic_buffer_model = false` のとき → 上記テーブルを `m_applBufferPoolTable.set()` 等で APPL_DB に転写する（buffermgrd.cpp:481-495）

`buffer_model = dynamic` SET → DEL 時は `dynamic_buffer_model = false` にリセット（buffermgrd.cpp:406）。

### 2. FlexCounterOrch (flexcounterorch.cpp:488-523)

`create_only_config_db_buffers` フィールドの変化を監視し、内部フラグ `m_createOnlyConfigDbBuffers` を更新する。
DB 書込は発生しない（フラグのみ変更）。このフラグは `getQueueConfigurations()` の挙動を変え、カウンタ設定の分岐に使用される。

### 3. fpmsyncd — suppress-fib-pending (fpmsyncd.cpp:260-304)

`suppress-fib-pending` フィールドの動的変化を監視する:

| 変化 | 副次操作 | 対象 DB / テーブル |
|------|---------|-----------------|
| `disabled → enabled` | `routeResponseChannel` を APPL_STATE_DB に接続し suppression を有効化 | APPL_STATE_DB / `ROUTE_TABLE` (受信チャネル登録) |
| `enabled → disabled` | `RouteSync::markRoutesOffloaded(db)` 呼び出し → `APP_ROUTE_TABLE` の全エントリを "offloaded" として応答送信 | APPL_DB / `APP_ROUTE_TABLE` (各ルートエントリのレスポンス処理) |

`markRoutesOffloaded` は `routesync.cpp:3291-3296` で `sendOffloadReply(db, APP_ROUTE_TABLE_NAME)` を呼び出し、APPL_DB の全ルートエントリを走査して `onRouteResponse()` で FRR に通知する。

### 4. hostcfgd — DeviceMetaCfg (hostcfgd:1485-)

| フィールド | 副次操作 | 対象 (DB ではなく Linux) |
|-----------|---------|----------------------|
| `hostname` | `sudo service hostname-config restart` + `sudo monit reload` | `/etc/hostname` (hostname-config サービス経由) |
| `timezone` | `timedatectl set-timezone <tz>` | `/etc/localtime` symlink |
| `syslog_with_osversion` | `systemctl restart rsyslog-config` | rsyslog.conf 再生成 |

これらは DB 書込ではなく Linux システム呼び出しであるため、CONFIG_DB 以外の DB への副次書込は発生しない。

## DEVICE_METADATA|localhost DEL 操作

### 1. BufferMgr (buffermgr.cpp:404-407)

DEL 時は `dynamic_buffer_model = false` にリセット。DB 書込なし。

### 2. FlexCounterOrch

DEL は `key == "localhost"` かつ `op == SET_COMMAND` の条件を満たさないため処理をスキップ (flexcounterorch.cpp:501)。DB 書込なし。

### 3. fpmsyncd

DEL イベントは `op != SET_COMMAND` のため continue (fpmsyncd.cpp:263-265)。suppress-fib-pending の無効化も起きない。

### 4. hostcfgd

DEL イベントに対応するハンドラなし (`hostname_update`, `apply_timezone_if_needed`, `rsyslog_config` はいずれも SET 専用)。

## DEVICE_METADATA|bmc SET/DEL 操作

bmc ロウを購読しているコンシューマが実装上確認されていない。bmc フィールドは起動時に `sonic-cfggen` がプラットフォーム情報から生成するのみ (sonic-cfggen:369)。DB 副次書込なし。

## 副次書込サマリ

| トリガーフィールド | consumer | 対象 DB | 書込 / 副作用 | evidence |
|----------------|---------|--------|--------------|---------|
| `buffer_model = dynamic` | BufferMgr | なし (フラグ更新のみ) | 後続 BUFFER_* テーブルの APPL_DB 転写を抑制 | buffermgr.cpp:476 |
| `buffer_model = traditional` / DEL | BufferMgr | なし (フラグ更新のみ) | 後続 BUFFER_* テーブルを APPL_DB に転写 | buffermgr.cpp:482-495 |
| `create_only_config_db_buffers` | FlexCounterOrch | なし (フラグ更新のみ) | カウンタ設定分岐フラグを更新 | flexcounterorch.cpp:488-523 |
| `suppress-fib-pending: enabled → disabled` | fpmsyncd | APPL_DB / `APP_ROUTE_TABLE` | 全ルートを offloaded としてマーク (FRR 通知) | fpmsyncd.cpp:298; routesync.cpp:3291 |
| `hostname` | hostcfgd | Linux のみ | `/etc/hostname` 更新、monit reload | hostcfgd:1527-1532 |
| `timezone` | hostcfgd | Linux のみ | `/etc/localtime` symlink 更新 | hostcfgd:1556 |
| `syslog_with_osversion` | hostcfgd | Linux のみ | rsyslog-config restart | hostcfgd:1600 |

> **結論**: DEVICE_METADATA|localhost の SET/DEL が **直接** 他 DB へ書込みを行うケースは `suppress-fib-pending` 切替時の APPL_DB `APP_ROUTE_TABLE` 応答処理のみ。他は全て内部フラグ更新または Linux システム呼び出しに留まる。

---

## switchorch.cpp による起動時副次 DB 書込 (SwitchOrch 初期化)

ソース: `sonic-swss/orchagent/switchorch.cpp`, `sonic-swss/orchagent/main.cpp`

DEVICE_METADATA フィールドは runtime の consumer イベントとして SwitchOrch に届くのではなく、**orchagent 起動時の一読み出し**で消費される。その結果 SwitchOrch コンストラクタと init 関数群が以下の DB 書込を行う。

### 5. SwitchOrch → STATE_DB / `SWITCH_CAPABILITY` (起動時)

`set_switch_capability()` (switchorch.cpp:1864-1867) が `m_switchTable.set("switch", values)` を呼び出す。`m_switchTable` は `STATE_DB:SWITCH_CAPABILITY` (orchdaemon.cpp:196 で `STATE_SWITCH_CAPABILITY_TABLE_NAME` を渡して構築)。

書込タイミング・フィールド:

| 呼び出し元 | 書込フィールド | evidence |
|-----------|--------------|---------|
| `set_switch_pfc_dlr_init_capability()` (コンストラクタ) | `PFC_DLR_INIT_CAPABLE` = "true"/"false" | switchorch.cpp:137,143 |
| `initAsicSdkHealthEventNotification()` (コンストラクタ) | `ASIC_SDK_HEALTH_EVENT` / `REG_FATAL/WARNING/NOTICE_ASIC_SDK_HEALTH_CATEGORY` | switchorch.cpp:231,246,266,271 |
| `querySwitchOrderedEcmpCapability()` (doAppSwitchTableTask) | `ORDERED_ECMP_CAPABLE` = "true"/"false" | switchorch.cpp:491-502 |
| `querySwitchPortEgressSampleCapability()` (コンストラクタ) | `PORT_EGRESS_SAMPLE_CAPABLE` | switchorch.cpp:1886-1896 |
| `querySwitchPortMirrorCapability()` (コンストラクタ) | `PORT_INGRESS_MIRROR_CAPABLE`, `PORT_EGRESS_MIRROR_CAPABLE` | switchorch.cpp:1915,1939 |
| `querySwitchTpidCapability()` (コンストラクタ) | `PORT_TPID_CAPABLE`, `LAG_TPID_CAPABLE` | switchorch.cpp:1975,1995 |
| `setSwitchIcmpOffloadCapability()` (コンストラクタ) | `ICMP_OFFLOAD_CAPABLE` | switchorch.cpp:2056,2061 |
| `setFastLinkupCapability()` (コンストラクタ) | `FAST_LINKUP_CAPABLE`, `FAST_LINKUP_POLLING_TIMER_RANGE`, `FAST_LINKUP_GUARD_TIMER_RANGE` | switchorch.cpp:2107,2145 |

`switch_type` フィールドが `fabric` のとき orchagent は SAI_SWITCH_TYPE_FABRIC で create_switch し、一部ケーパビリティが無効となる (main.cpp:740-770)。

### 6. SwitchOrch → STATE_DB / `ASIC_TEMPERATURE_INFO` (タイマー駆動)

SwitchOrch は `ASIC_SENSORS_POLL_TIMER` 割り込みで `m_asicSensorsTable->set("", values)` を定期呼び出しする (switchorch.cpp:1728,1746,1770,1841,1853,1860)。`m_asicSensorsTable` は `STATE_DB:ASIC_TEMPERATURE_INFO` (schema.h:138)。

起動時に `initSensorsTable()` (switchorch.cpp:165 呼び出し) でタイマーが開始される。DEVICE_METADATA `switch_type` が `fabric` の場合はセンサポーリング動作が変わる可能性あり。

### 7. SwitchOrch → STATE_DB / `ASIC_SDK_HEALTH_EVENT_TABLE` (イベント駆動)

SAI から ASIC SDK health event が通知されたとき `onSwitchAsicSdkHealthEvent()` (switchorch.cpp:1578) が `m_asicSdkHealthEventTable->set(time_ss.str(), values)` を呼び出す (switchorch.cpp:1661)。`m_asicSdkHealthEventTable` は `STATE_DB:ASIC_SDK_HEALTH_EVENT_TABLE` (schema.h:507)。

`DEVICE_METADATA.switch_type` = `fabric` / `dpu` 時に SAI イベントのサポート可否が異なる。

### 8. APPL_DB → ASIC_DB / SAI switch attributes (APPL_DB SWITCH_TABLE 経由)

SwitchOrch は APPL_DB `SWITCH_TABLE` を consumer として購読し (tableName == APP_SWITCH_TABLE_NAME: switchorch.cpp:1499)、フィールドごとに `sai_switch_api->set_switch_attribute(gSwitchId, &attr)` を呼び出す (switchorch.cpp:722)。

DEVICE_METADATA の `switch_type` フィールドが `voq` のとき、起動時に `switch.json.j2` などで APPL_DB `SWITCH_TABLE` に `ecmp_hash_seed`/`lag_hash_seed` を書き込む処理があり (sonic-buildimage:switch.json.j2:16-17)、それが SwitchOrch→SAI→ASIC_DB 書込につながる。

マッピング表 (switchorch.cpp:44-54):

| CONFIG_DB `switch_type` 依存の APPL_DB フィールド | SAI 属性 |
|--------------------------------------------------|---------|
| `ecmp_hash_seed` | `SAI_SWITCH_ATTR_ECMP_DEFAULT_HASH_SEED` |
| `lag_hash_seed` | `SAI_SWITCH_ATTR_LAG_DEFAULT_HASH_SEED` |
| `fdb_aging_time` | `SAI_SWITCH_ATTR_FDB_AGING_TIME` |
| `vxlan_port` | `SAI_SWITCH_ATTR_VXLAN_DEFAULT_PORT` |
| `vxlan_router_mac` | `SAI_SWITCH_ATTR_VXLAN_DEFAULT_ROUTER_MAC` |

## 更新後サマリ (switchorch 含む)

| トリガー | consumer | 対象 DB | 書込 / 副作用 | evidence |
|---------|---------|--------|--------------|---------|
| orchagent 起動 (`switch_type`/`subtype`/`switch_id` 読み出し) | SwitchOrch init | STATE_DB `SWITCH_CAPABILITY` | PFC_DLR/ECMP/Mirror/TPID/ICMP 等のケーパビリティフラグ | switchorch.cpp:145,251,276,492,502,1866,1900,1957,2009,2063,2145 |
| タイマー割り込み (`switch_type` 依存で動作変化) | SwitchOrch | STATE_DB `ASIC_TEMPERATURE_INFO` | ASIC 温度センサ値 | switchorch.cpp:1728,1746,1770 |
| SAI health event 通知 | SwitchOrch | STATE_DB `ASIC_SDK_HEALTH_EVENT_TABLE` | ASIC SDK 健全性イベント | switchorch.cpp:1661 |
| APPL_DB SWITCH_TABLE SET (`switch_type` 依存値から生成) | SwitchOrch | ASIC_DB (SAI) | ecmp_hash_seed / lag_hash_seed / fdb_aging_time 等 | switchorch.cpp:722 |
