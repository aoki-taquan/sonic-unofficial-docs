# Phase A: MGMT_PORT 暗黙デフォルト調査

## 調査対象

- YANG: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mgmt_port.yang`
- Consumer: `sonic-host-services/scripts/hostcfgd`, `sonic-snmpagent`, `sonic-buildimage/dockers/docker-lldp/lldpd.conf.j2`, `sonic-buildimage/files/image_config/monit/mgmt_oper_status.py`
- Writer: `sonic-buildimage/src/sonic-config-engine/minigraph.py`

## フィールド別デフォルト検出結果

### `admin_status`

- **YANG default**: `up` (`sonic-mgmt_port.yang:74`)
- **minigraph 注入値**: `"up"` ハードコード (`minigraph.py:2294` — `'admin_status': 'up'` を常時設定)
- **暗黙挙動**: フィールド未設定時も YANG が `up` をフォールバックとして返す
- **discrepancy**: なし。YANG default と minigraph 注入値が一致

### `mtu`

- **YANG default**: `1500` (`sonic-mgmt_port.yang:68`)
- **実装コンシューマ**: `mgmt_oper_status.py` は CONFIG_DB の値をそのまま STATE_DB に同期するだけ。実際の MTU 適用は `interfaces.j2` / `ifupdown2` 経由
- **interfaces.j2**: `MGMT_PORT.mtu` を参照しない。MTU は Linux の ifupdown2 デフォルト (1500) に依存
- **暗黙挙動**: MGMT_PORT の `mtu` フィールドが設定されていても `/etc/network/interfaces` には展開されない。eth0 の実 MTU はカーネルデフォルト (1500) のまま
- **discrepancy 候補**: `mtu` フィールドは YANG に存在し STATE_DB に同期されるが、実際のカーネル MTU 変更コードパスが存在しない (interfaces.j2 が MGMT_PORT.mtu を無視)

### `speed`

- **YANG default**: なし (optional field)
- **minigraph 注入**: `port_speeds_default[alias]` が存在する場合のみ設定 (`minigraph.py:2295-2296`)
  - `port_speeds_default` は `parse_deviceinfo()` が minigraph XML の `ManagementInterfaces/ManagementInterface/Speed` 要素から取得 (`minigraph.py:1683-1690`)
  - HwSku が一致しない場合や Speed 要素がない場合は `port_speeds_default` に alias が存在せず、`speed` フィールドは CONFIG_DB に書き込まれない
- **実装コンシューマ**: `mgmt_oper_status.py` が速度を STATE_DB に同期 (読み取りのみ)
- **実際の速度設定コード**: `interfaces.j2` も `hostcfgd` も MGMT_PORT.speed を使って ethtool/ifconfig を発行しない
- **discrepancy 候補**: `speed` フィールドが CONFIG_DB に設定されていても、実際の eth0 速度設定には使われていない (カーネル/NIC の autoneg/デフォルト任せ)

### `autoneg`

- **YANG default**: なし (optional field, pattern `on|off`)
- **実装コンシューマ**: なし。`hostcfgd`・`interfaces.j2`・`portmgrd` のいずれも `MGMT_PORT.autoneg` を読まない
- **dead field**: `autoneg` は YANG に存在し CONFIG_DB に書き込み可能だが、実装上のコンシューマが存在しない。ethtool 発行コードなし
- **discrepancy**: `autoneg on/off` を設定しても eth0 のオートネゴシエーション設定は変化しない

### `alias`

- **YANG default**: なし (optional string)
- **minigraph 注入**: 常に alias (port_alias_map またはそのまま) を設定 (`minigraph.py:2294` — `'alias': alias`)
- **実際の消費**:
  - `lldpd.conf.j2:17-18`: `MGMT_PORT[mgmt_if.port_name].alias` が存在すれば LLDP portidsubtype local に設定
  - `sonic-snmpagent/mibs/__init__.py:270`: `if_entry.get('alias', if_name)` — alias 未設定時は if_name (eth0) がフォールバック
- **暗黙フォールバック**: SNMP MIB では alias 未設定時に if_name を返す (コード由来フォールバック)

### `description`

- **YANG default**: なし (optional string)
- **実装コンシューマ**: なし。SNMP agent, lldpd.conf.j2, interfaces.j2, hostcfgd のいずれも `MGMT_PORT.description` を消費しない
- **dead field**: `description` は YANG に存在するが実装上無視される

### `name` (key)

- **YANG constraint**: `pattern 'eth([1-3][0-9]{3}|[1-9][0-9]{2}|[1-9][0-9]|[0-9])'`
- **minigraph 生成規則**: `'eth' + str(mgmt_intf_count)` で 0 からカウントアップ (`minigraph.py:2291-2292`)
- 名前空間の一意性はカウンターで保証

## portmgr.cpp との関係 (YANG-実装 discrepancy)

Phase 8 の既存記述では「portmgr.cpp が MGMT_PORT を処理する」とあるが、**これは誤り**:

- `portmgrd` は `CFG_PORT_TABLE_NAME` (= `"PORT"`, データポート) を購読する (`portmgrd.cpp:28`)
- `MGMT_PORT` テーブルは portmgrd/portmgr.cpp では一切処理されない
- `portmgr.h:14-15` の定数 `DEFAULT_ADMIN_STATUS_STR="down"`, `DEFAULT_MTU_STR="9100"` はデータポート (Ethernet0 等) のデフォルトであり、MGMT_PORT とは無関係

## 実際の MGMT_PORT コンシューマ一覧

| コンシューマ | 読むフィールド | 用途 |
|---|---|---|
| `minigraph.py` | (書き込み側) | alias, admin_status, speed を CONFIG_DB に投入 |
| `mgmt_oper_status.py` | 全フィールド | CONFIG_DB → STATE_DB 同期 + oper_status 取得 |
| `lldpd.conf.j2` | `alias` | LLDP portidsubtype local 設定 |
| `sonic-snmpagent/mibs/__init__.py` | `alias` | SNMP インタフェーステーブル |
| `interfaces.j2` | 参照なし | MGMT_PORT は interfaces.j2 で使用されない |
| `hostcfgd` | 参照なし (`MGMT_INTERFACE` は処理するが `MGMT_PORT` は未購読) | - |

## 検出した discrepancy / 暗黙デフォルト サマリ

| フィールド | 種別 | 内容 |
|---|---|---|
| `admin_status` | YANG default + hardcode | YANG default `up`、minigraph も常時 `"up"` を注入。YANG-実装一致 |
| `mtu` | dead write | YANG default `1500`、STATE_DB 同期はされるが eth0 実 MTU には反映されない |
| `speed` | dead write + platform-dependent | minigraph が HwSku 定義から取得し書き込む場合あり。実際の ethtool 発行なし |
| `autoneg` | dead field | YANG 定義あり、コンシューマなし。設定しても ethtool 発行されない |
| `description` | dead field | YANG 定義あり、コンシューマなし |
| `alias` | implicit fallback | SNMP で alias 未設定時に if_name (eth0) をフォールバック返却 |
| Phase 8 記述 | YANG-実装 discrepancy | portmgr.cpp は MGMT_PORT を処理しない（PORT テーブルのみ） |

## 証跡ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mgmt_port.yang:37-75`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py:2281-2296`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py:1675-1711` (parse_deviceinfo)
- `sonic-buildimage/files/image_config/monit/mgmt_oper_status.py:16-51`
- `sonic-buildimage/dockers/docker-lldp/lldpd.conf.j2:17-18`
- `sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py:269-270`
- `sonic-buildimage/files/image_config/interfaces/interfaces.j2` (MGMT_PORT 参照なしを確認)
- `sonic-host-services/scripts/hostcfgd` (MGMT_PORT 未購読を確認)
- `sonic-swss/cfgmgr/portmgr.h:14-15` (DEFAULT_ADMIN_STATUS_STR="down", DEFAULT_MTU_STR="9100" はデータポート専用)
- `sonic-swss/cfgmgr/portmgrd.cpp:28` (CFG_PORT_TABLE_NAME="PORT" のみ購読)
