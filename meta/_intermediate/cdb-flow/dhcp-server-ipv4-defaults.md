# dhcp-server-ipv4 — Phase A: コード由来の暗黙デフォルト調査メモ

調査日: 2026-05-14  
対象: `DHCP_SERVER_IPV4` テーブル  
主要ソース:
- `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py`
- `dockers/docker-dhcp-server/cli/config/plugins/dhcp_server.py`
- `src/sonic-yang-models/yang-models/sonic-dhcp-server-ipv4.yang`

---

## フィールド別 fallback / 暗黙デフォルト

### `lease_time`

| 種別 | 詳細 |
|------|------|
| YANG default | なし（`mandatory true`、range 1..4294967295） |
| CLI 書込み時 default | `--lease_time` オプションの Python デフォルト = `"900"`（dhcp_server.py:70）。CLI 省略時は 900 秒が DB に書き込まれる |
| 実行時 fallback | `dhcp_cfggen.py:255`: `dhcp_config.get("lease_time", DEFAULT_LEASE_TIME)` で `DEFAULT_LEASE_TIME = 900`（dhcp_cfggen.py:25）。つまり DB に lease_time が存在しない場合も 900 秒で kea-dhcp4 設定を生成する |
| YANG-実装乖離 | YANG は `mandatory true` だが実装はフォールバックで動作継続する。silent substitution |
| 検出種類 | CLI 書込み時デフォルト / 実行時 fallback / YANG-実装 discrepancy |

### `state`

| 種別 | 詳細 |
|------|------|
| YANG default | なし（`mandatory true`） |
| CLI 書込み時 default | `config dhcp_server ipv4 add` コマンドは常に `"state": "disabled"` を書き込む（dhcp_server.py:105）。`enable` サブコマンドで明示的に `enabled` へ変更するまで disabled |
| 実行時挙動 | `dhcp_cfggen.py:199`: `if "state" not in dhcp_config or dhcp_config["state"] != "enabled": continue`。state が absent の場合も enabled 以外と同等に扱い、そのインタフェースをスキップ |
| 検出種類 | CLI 書込み時デフォルト（disabled）/ dead consumer（state absent 時は silent skip） |

### `gateway`

| 種別 | 詳細 |
|------|------|
| YANG default | なし（任意フィールド） |
| CLI 書込み時 | `add` コマンドで `--gateway` 省略時は DB に書き込まれない。`--dup_gw_nm` フラグで VLAN_INTERFACE の IPv4 から自動取得可能（dhcp_server.py:86-91） |
| 実行時挙動 | `dhcp_cfggen.py:258-259`: `if "gateway" in dhcp_config: subnet_obj["gateway"] = dhcp_config["gateway"]`。gateway が absent の場合は kea 設定に routers オプションが含まれない（クライアントへのデフォルトゲートウェイ通知なし）。silent omission |
| 検出種類 | 前提条件依存（dup_gw_nm フラグ）/ silent omission |

### `netmask`

| 種別 | 詳細 |
|------|------|
| YANG default | なし（`mandatory true`） |
| 実行時挙動 | dhcp_cfggen は subnet を VLAN_INTERFACE の ip_prefix から `ipaddress.ip_network()` で計算し、netmask フィールド自体は kea 設定の subnet 文字列に使用しない（subnet は VLAN_INTERFACE から導出）。netmask は CLI での入力検証用途が主 |
| YANG-実装乖離 | YANG は mandatory だが実行時の subnet 計算は VLAN_INTERFACE の prefix から行われ、netmask フィールドの値は kea-dhcp4 設定生成で直接参照されない（dead field 相当） |
| 検出種類 | dead field / YANG-実装 discrepancy |

### `mode`

| 種別 | 詳細 |
|------|------|
| YANG default | なし（`mandatory true`、enum PORT のみ） |
| 実行時挙動 | `dhcp_cfggen.py:202`: `if dhcp_config["mode"] == "PORT":` のみ処理。他の値は処理されず subscribe_table が PORT_MODE_CHECKER 系に更新されないが、enabled_dhcp_interfaces には追加される（inconsistent state）。ただし YANG では PORT のみ定義のため現実には発生しない |
| 検出種類 | ハードコード固定値（PORT のみ実装）/ dead consumer（PORT 以外は事実上 dead） |

### `customized_options` (leaf-list)

| 種別 | 詳細 |
|------|------|
| YANG default | なし（任意） |
| 実行時 fallback | `dhcp_cfggen.py:210-215`: option 名が customized_options_ipv4 に定義されていない場合、LOG_WARNING を出力してそのオプションをスキップ（silent drop）。他オプションは継続 |
| always_send の fallback | `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS` の `always_send` フィールド: YANG では `default true`（yang:168）。dhcp_cfggen.py:151 でも `config.get("always_send", "true")` でフォールバック。DB absent 時は `"true"` として扱う |
| 検出種類 | silent drop+fallback / YANG default（always_send = true） |

---

## 複合制約

- `state=enabled` かつ `mode=PORT` かつ `DHCP_SERVER_IPV4_PORT` エントリが存在しない場合: LOG_WARNING を出力してその interface をスキップ（dhcp_cfggen.py:204-207）
- `state=enabled` でも `DEVICE_METADATA.localhost.dhcp_server` が設定されていない場合: dhcpservd コンテナ自体が起動しないため全設定が無効（前提条件依存）
- VLAN_INTERFACE に IPv4 アドレスが設定されていない場合: dhcp_cfggen.py:432-433 で LOG_WARNING を出力しスキップ（前提条件依存）

---

## dhcp_server_id_option の自動生成

`dhcp_cfggen.py:245-249`: `customized_options` に option ID `"54"` (DHCP Server Identifier) が設定されていない場合、VLAN_INTERFACE の IPv4 アドレス（prefix なし）を `always_send=true` で自動生成してデフォルト注入する。ユーザー設定で上書き可能。

検出種類: ランタイム注入 / 暗黙デフォルト / silent substitution

---

## subnet ID の計算

`dhcp_cfggen.py:251`: 通常 VLAN の subnet ID は `dhcp_interface_name.replace("Vlan", "")` で VLAN 番号を整数変換して使用。SmartSwitch の場合は `MID_PLANE_BRIDGE_SUBNET_ID = 10000`（定数）にハードコード固定。

検出種類: ハードコード固定値（SmartSwitch 時）

---

## 書込み順依存

CLI `add` → `enable` の 2 ステップが必要。`add` 時点では必ず `state=disabled` で書き込まれる。`enable` を忘れた場合は dhcpservd が有効インタフェースとして認識しない（silent skip）。

---

## Evidence

- `dhcp_cfggen.py:25`: `DEFAULT_LEASE_TIME = 900`
- `dhcp_cfggen.py:40-42`: コンストラクタデフォルト `lease_path=DEFAULT_LEASE_PATH`、`lease_update_script_path=LEASE_UPDATE_SCRIPT_PATH`
- `dhcp_cfggen.py:199`: state absent = skip
- `dhcp_cfggen.py:245-249`: dhcp_server_id auto-inject
- `dhcp_cfggen.py:255`: `lease_time` fallback to 900
- `dhcp_cfggen.py:258-259`: gateway absent = omit
- `dhcp_server.py:70`: `--lease_time` CLI default `"900"`
- `dhcp_server.py:105`: `add` writes `state=disabled`
- `dhcp_server.py:86-91`: `--dup_gw_nm` copies from VLAN_INTERFACE
- `sonic-dhcp-server-ipv4.yang:168`: `always_send` default true
