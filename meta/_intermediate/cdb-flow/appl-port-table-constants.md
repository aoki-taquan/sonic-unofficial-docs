# APPL_DB PORT_TABLE — ハードコード定数 (Phase E)

orchagent (PortsOrch / porthlpr) と portmgrd / port.h に埋め込まれた、APPL_DB `PORT_TABLE` のフィールド値解釈に関わるハードコード定数の精読結果。

参照ソース:

- `sonic-net/sonic-swss` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
  - `orchagent/portsorch.cpp`
  - `orchagent/portsorch.h`
  - `orchagent/port.h`
  - `orchagent/port/porthlpr.cpp`
  - `cfgmgr/portmgr.h`

## 1. admin_status / oper_status 文字列

### portmgrd 側 admin_status のデフォルト

- `cfgmgr/portmgr.h:14`
  - `#define DEFAULT_ADMIN_STATUS_STR "down"`
- portmgrd は初回 SET 時に CONFIG_DB に `admin_status` フィールドが無いと `"down"` を APPL_DB に注入する (`cfgmgr/portmgr.cpp:175`)。

### oper_status の SAI ↔ 文字列マップ

`orchagent/portsorch.h:48-55` `oper_status_strings`:

| SAI 列挙値 | APPL_DB 文字列 |
|---|---|
| `SAI_PORT_OPER_STATUS_UNKNOWN` | `"unknown"` |
| `SAI_PORT_OPER_STATUS_UP` | `"up"` |
| `SAI_PORT_OPER_STATUS_DOWN` | `"down"` |
| `SAI_PORT_OPER_STATUS_TESTING` | `"testing"` |
| `SAI_PORT_OPER_STATUS_NOT_PRESENT` | `"not present"` |

逆向きマップ `string_oper_status` (`portsorch.h:57-64`) も同じ 5 値を持ち、warmboot 初期化で APPL_DB の文字列を SAI 列挙に戻す際に使われる。`"unknown"` も含まれるため、`SAI_PORT_OPER_STATUS_UNKNOWN` を受信しても `std::out_of_range` にはならない。

## 2. MTU 関連の定数

| 定数 | 値 | 場所 | 用途 |
|---|---|---|---|
| `DEFAULT_MTU_STR` | `"9100"` | `cfgmgr/portmgr.h:15` | portmgrd が CONFIG_DB に mtu が無いとき APPL_DB に注入するフォールバック |
| `DEFAULT_MTU` | `1492` | `orchagent/port.h:27` | orchagent 内部 `Port` 構造体の `m_mtu` 初期値 (SAI default 1514 − header/FCS 22) |
| `DEFAULT_SYSTEM_PORT_MTU` | `9100` | `orchagent/portsorch.cpp:79` | VOQ system port 初期化時の MTU |
| `minPortMtu` / `maxPortMtu` | `68` / `9216` | `orchagent/port/porthlpr.cpp:34-35` | porthlpr が MTU 値を検証する範囲 |

## 3. 速度 (speed) の範囲

`orchagent/port/porthlpr.cpp:31-32`:

- `minPortSpeed = 1`
- `maxPortSpeed = 1600000` (Mbps、1.6Tbps 相当の上限)

`APPL_DB PORT_TABLE` の `speed` フィールドは `[1, 1600000]` の uint。CONFIG_DB から portsyncd でパススルーされる際、porthlpr が APPL_DB consumer 側で再パースして範囲チェックする。

## 4. FEC モードの enum

`orchagent/port/porthlpr.cpp:77-90`:

`portFecMap` (string → SAI):

| 文字列 (`PORT_FEC_*`) | SAI 列挙 |
|---|---|
| `"none"` | `SAI_PORT_FEC_MODE_NONE` |
| `"rs"` | `SAI_PORT_FEC_MODE_RS` |
| `"fc"` | `SAI_PORT_FEC_MODE_FC` |
| `"auto"` | `SAI_PORT_FEC_MODE_NONE` (auto はネゴ後決定、初期値 NONE) |

`portFecOverrideMap` (`porthlpr.cpp:92-98`): `"none"/"rs"/"fc"` → `true` (明示指定)、`"auto"` → `false`。APPL_DB の `fec` フィールドが `"auto"` の場合だけ SAI への FEC 明示設定を抑止する識別子として用いる。

逆向き `portFecRevMap` (`porthlpr.cpp:85-90`) は `auto` を含まない 3 値のみ。STATE_DB 書き戻し用。

## 5. autoneg / link_training / on-off 系の enum

| マップ | 場所 | 文字列 | SAI / bool |
|---|---|---|---|
| `autoneg_mode_map` | `portsorch.cpp:174-178` | `"on"` / `"off"` | `1` / `0` |
| `portModeMap` | `porthlpr.cpp:37-41` | `PORT_MODE_ON` / `PORT_MODE_OFF` | `true` / `false` |
| `portStatusMap` | `porthlpr.cpp:43-47` | `PORT_STATUS_UP` / `PORT_STATUS_DOWN` | `true` / `false` |
| `portPfcAsymMap` | `porthlpr.cpp:100-104` | `"on"` / `"off"` | `SAI_PORT_PRIORITY_FLOW_CONTROL_MODE_SEPARATE` / `..._COMBINED` |

`autoneg` / `link_training` / `pfc_asym` の APPL_DB 値は **`"on"` / `"off"` の 2 値固定**。それ以外の文字列は porthlpr がパース失敗を返し、SAI 反映前に弾かれる。

## 6. interface_type の enum

`orchagent/port/porthlpr.cpp:49-75` `portInterfaceTypeMap` は 24 種類:

`none, cr, cr2, cr4, cr8, sr, sr2, sr4, sr8, lr, lr4, lr8, kr, kr4, kr8, caui, gmii, sfi, xlaui, kr2, caui4, xaui, xfi, xgmii`

`orchagent/portsorch.cpp:195-210` の `interface_type_map` は gearbox 用に縮小されており 13 種類のみ (none, cr, cr4, cr8, sr, sr4, sr8, lr, lr4, lr8, kr, kr4, kr8)。**通常ポートと gearbox ポートで許容値が異なる**点に注意。

## 7. media_type / loopback / learn_mode

`orchagent/portsorch.cpp:160-172`:

- `media_type_map`: `"fiber"` / `"copper"` / `"backplane"` → `SAI_PORT_MEDIA_TYPE_*`
- `loopback_mode_map`: `"none"` / `"phy"` / `"mac"` → `SAI_PORT_INTERNAL_LOOPBACK_MODE_*`

`orchagent/portsorch.cpp:150-158` `learn_mode_map`: `"drop"`, `"disable"`, `"hardware"`, `"cpu_trap"`, `"cpu_log"`, `"notification"` (PORT ではなく VLAN_MEMBER で使われる)。

## 8. link training failure / rx status

`orchagent/portsorch.cpp:180-192`:

`link_training_failure_map` (SAI → APPL_DB 文字列、STATE_DB `link_training_status` 経由で公開): `"none"`, `"frame_lock"`, `"snr_low"`, `"timeout"`。

`link_training_rx_status_map`: `"not_trained"`, `"trained"`。

注: これらは APPL_DB ではなく **STATE_DB** `PORT_TABLE` に書かれる (Phase F の副次書込先)。APPL_DB `PORT_TABLE.link_training` は `"on"` / `"off"` のみ。

## 9. Path Tracing timestamp template

`orchagent/portsorch.cpp:213-219` および `porthlpr.cpp:125-131`:

`pt_timestamp_template_map` / `portPtTimestampTemplateMap`: `"template1"` ... `"template4"` → `SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_8_15` ... `_20_27`。

## 10. Port::Role (内部識別)

`orchagent/port.h:158-165` `Port::Role` 列挙:

| 文字列 (`PORT_ROLE_*`) | enum | 意味 |
|---|---|---|
| `"Ext"` | `Ext` | 外部 (フロントパネル) ポート |
| `"Int"` | `Int` | 内部ポート |
| `"Inb"` | `Inb` | inband ポート |
| `"Rec"` | `Rec` | recirculation ポート |
| `"Dpc"` | `Dpc` | SmartSwitch DPU Connect Port |

`portRoleMap` (`porthlpr.cpp:116-123`)。これは CONFIG_DB `PORT.role` フィールド (APPL_DB にもパススルー) のハードコード許容値で、5 値以外は porthlpr が拒否する。

## 11. Port::Type (内部分類、非 APPL_DB)

`orchagent/port.h:145-156`:

`CPU, PHY, MGMT, LOOPBACK, VLAN, LAG, TUNNEL, SUBPORT, SYSTEM, UNKNOWN`。

APPL_DB には書かれないが、`PortsOrch` の各種ハンドラ分岐で多用される (`portsorch.cpp:2953, 2959, 2972, 2990, 3037, 3047, 3051, 3920, 4122` 等)。`PORT_TABLE` のエントリは原則 `Type::PHY`、`PORTCHANNEL_TABLE` 経由のものが `LAG`、Gearbox VOQ 環境で `SYSTEM` を扱う。

## 12. Queue type 文字列マップ

`orchagent/portsorch.cpp:221-227` `sai_queue_type_string_map`:

`SAI_QUEUE_TYPE_ALL` → `"SAI_QUEUE_TYPE_ALL"`、`UNICAST`, `MULTICAST`, `UNICAST_VOQ` 同様。COUNTERS_DB `COUNTERS_QUEUE_TYPE_MAP` に書かれる文字列。

## 13. その他の prefix / 命名規約

`orchagent/port/porthlpr.cpp:28-29`:

- `GB_LINE_PREFIX = "gb_line_"`
- `GB_SYSTEM_PREFIX = "gb_system_"`

Gearbox 用の port alias prefix。STATE_DB / COUNTERS_DB の gearbox port 名に使われる。

## サマリ

APPL_DB `PORT_TABLE` から見て **直接の許容値を縛るハードコード定数**:

| フィールド | 許容値 (ハードコード) | 定義位置 |
|---|---|---|
| `admin_status` | `"up"` / `"down"` (+ デフォルト `"down"`) | `portmgr.h:14`, `porthlpr.cpp:43-47` |
| `oper_status` | `"up"` / `"down"` / `"unknown"` / `"testing"` / `"not present"` | `portsorch.h:48-55` |
| `mtu` | `[68, 9216]` (デフォルト `"9100"`) | `porthlpr.cpp:34-35`, `portmgr.h:15` |
| `speed` | `[1, 1600000]` Mbps | `porthlpr.cpp:31-32` |
| `fec` | `"none"` / `"rs"` / `"fc"` / `"auto"` | `porthlpr.cpp:77-83` |
| `autoneg` | `"on"` / `"off"` | `porthlpr.cpp:37-41` |
| `link_training` | `"on"` / `"off"` | 同上 |
| `pfc_asym` | `"on"` / `"off"` | `porthlpr.cpp:100-104` |
| `interface_type` | 24 種 (通常) / 13 種 (gearbox) | `porthlpr.cpp:49-75`, `portsorch.cpp:195-210` |
| `role` | `Ext` / `Int` / `Inb` / `Rec` / `Dpc` | `port.h:158-165`, `porthlpr.cpp:116-123` |
