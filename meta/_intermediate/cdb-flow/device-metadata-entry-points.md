# DEVICE_METADATA 書き込み入り口 詳細 trace (Direction A)

生成日: 2026-05-14  
対象テーブル: `DEVICE_METADATA` (tier_high, max_card=35)

---

## 1. CLI 経由 (sonic-utilities)

### 1-1. config hostname (main.py:2733)
```python
config_db.mod_entry(swsscommon.CFG_DEVICE_METADATA_TABLE_NAME, 'localhost', {'hostname': new_hostname})
```
コマンド: `config hostname <new_hostname>`  
書き込みフィールド: `hostname`  
制約: 任意文字列

### 1-2. config synchronous_mode (main.py:2763)
```python
config_db.mod_entry('DEVICE_METADATA', 'localhost', {"synchronous_mode": sync_mode})
```
コマンド: `config synchronous_mode <enable|disable>`  
書き込みフィールド: `synchronous_mode`  
値: `enable` / `disable`

### 1-3. config suppress-fib-pending (main.py:2792)
```python
config_db.mod_entry('DEVICE_METADATA', 'localhost', {"suppress-fib-pending": state})
```
コマンド: `config suppress-fib-pending <enabled|disabled>`  
書き込みフィールド: `suppress-fib-pending`  
値: `enabled` / `disabled`  
Note: multi-asic 時は全 namespace に適用

### 1-4. config yang_config_validation (main.py:2807)
```python
config_db.mod_entry('DEVICE_METADATA', 'localhost', {"yang_config_validation": yang_config_validation})
```
コマンド: `config yang_config_validation <enable|disable>`  
書き込みフィールド: `yang_config_validation`  
値: `enable` / `disable`

### 1-5. config clock timezone (main.py:9789)
```python
config_db.mod_entry(swsscommon.CFG_DEVICE_METADATA_TABLE_NAME, 'localhost', {'timezone': timezone})
```
コマンド: `config clock timezone <timezone_name>`  
書き込みフィールド: `timezone`  
制約: pytz 有効タイムゾーン文字列

### 1-6. config qos reload (main.py:3649, 関数 _update_buffer_calculation_model)
```python
config_db.set_entry('DEVICE_METADATA', 'localhost', device_metadata)  # buffer_model を書き込む
```
コマンド: `config qos reload [--no-dynamic-buffer]`  
書き込みフィールド: `buffer_model`  
値: `dynamic` / `traditional`  
条件: `--no-dynamic-buffer` → `traditional`、省略 → `dynamic`

### 1-7. config platform barefoot profile (plugins/barefoot.py:50)
```python
config_db.mod_entry('DEVICE_METADATA', 'localhost', {'p4_profile': profile + '_profile'})
```
コマンド: `config platform barefoot profile <profile>`  
書き込みフィールド: `p4_profile`  
条件: asic_type == 'barefoot' のときのみプラグイン登録  
Note: YANG schema に `p4_profile` フィールド定義なし → **未文書フィールド**

---

## 2. minigraph 経由 (sonic-config-engine)

ファイル: `sonic-buildimage/src/sonic-config-engine/minigraph.py`  
関数: `parse_xml()` 内の results 組み立てブロック (L2146〜)

| フィールド | minigraph ソース | L# |
|---|---|---|
| `hostname` | `<Device name=...>` | L2152 |
| `hwsku` | `<Device Hwsku=...>` | L2153 |
| `type` | `<Device type=...>` | L2154 |
| `region` | Device attr: region | L2147 |
| `cloudtype` | Device attr: cloudtype | L2148 |
| `docker_routing_config_mode` | Device attr: dockerRoutingConfigMode (default: separated) | L2149 |
| `synchronous_mode` | hard-coded `'enable'` | L2155 |
| `yang_config_validation` | hard-coded `'disable'` | L2156 |
| `bgp_asn` | `<BGP><DeviceBGPInfo ASN=...>` | L2159 |
| `chassis_hostname` | chassis topology | L2162 |
| `deployment_id` | Device attr: deploymentId | L2165 |
| `rack_mgmt_map` | Device attr: rackMgmtMap | L2168 |
| `cluster` | Device attr: cluster | L2172 |
| `slice_type` | Device attr: sliceType (chassis のみ) | L2176 |
| `subtype` | 計算: DualToR/UpstreamLC/DownstreamLC/Supervisor | L2189-2200 |
| `peer_switch` | PEER_SWITCH keys | L2193 |
| `asic_name` | namespace (multi-asic) | L2218 |
| `sub_role` | asic sub_role (BackEnd/FrontEnd/Fabric) | L2226-2230 |
| `switch_type` | chassis_type / voq switch_type | L2233-2241 |
| `switch_id` | Voq switch_id / slot_index 計算 | L2250 |
| `max_cores` | chassis max_cores | L2253-2257 |
| `resource_type` | Device attr: resourceType | L2266 |
| `downstream_subrole` | Device attr: downstreamSubrole | L2271 |
| `storage_device` | `"true"` (storage chassis のみ) | L2602 |
| `dhcp_server` | `"enabled"` (dhcpServerEnabled=True) | L2736 |
| `suppress-fib-pending` | `"enabled"` | L2744 |

### sonic-cfggen プラットフォーム情報注入 (sonic-cfggen L479〜)
```python
hardware_data = {'DEVICE_METADATA': {'localhost': {'platform': platform, 'mac': mac}}}
# 追加: asic_id, sub_role (multi-asic)
```
書き込みフィールド: `platform`, `mac`, `asic_id`, `sub_role`  
トリガー: `sonic-cfggen --platform-info` オプション

### sonic-cfggen BMC 注入 (sonic-cfggen L369)
```python
deep_update(data, {'DEVICE_METADATA': {'bmc': {key:value}}})
```
書き込みキー: `DEVICE_METADATA|bmc`  
書き込みフィールド: `bmc_if_name`, `bmc_if_addr`, `bmc_addr`, `bmc_net_mask`  
ソース: `device_info.get_bmc_data()`

### sonic-cfggen namespace_id 注入 (sonic-cfggen L384)
```python
deep_update(data, {'DEVICE_METADATA': {'localhost': {'namespace_id': namespace_id}}})
```
書き込みフィールド: `namespace_id`  
条件: 環境変数 `NAMESPACE_ID` が設定されている場合

---

## 3. REST/gNMI (mgmt-common translib)

ソースディレクトリ `sonic-mgmt-common/translib/transformer/` はこの worktree の clone 範囲外。  
確認結果: `sonic-mgmt-common` リポジトリは `.cache/sonic-sources/` に含まれない。  
→ **REST/gNMI 経路は現ソースから確認不可**  
（sonic-yang-mgmt の YANG binding から DEVICE_METADATA への path: `/sonic-device-metadata:sonic-device-metadata/DEVICE_METADATA` と推定されるが、transformer 実装は未確認）

---

## 4. db_migrator 経由 (sonic-utilities)

ファイル: `sonic-utilities/scripts/db_migrator.py`

| メソッド | 条件 | 書き込みフィールド | L# |
|---|---|---|---|
| `migrate_device_metadata()` | `synchronous_mode` が DB に存在しない | `synchronous_mode` (元設定から補完) | L678 |
| `migrate_routing_config_mode()` | `docker_routing_config_mode` が DB に存在しないか minigraph 値と不一致 | `docker_routing_config_mode` | L755 |
| `version_1_0_4()` | Mellanox 非 dynamic buffer 環境 | `buffer_model: 'traditional'` | L1096 |

### mellanox_buffer_migrator.py (L828)
```python
self.configDB.set_entry('DEVICE_METADATA', 'localhost', metadata)
```
書き込みフィールド: `buffer_model: 'traditional'`  
条件: Mellanox 環境で dynamic buffer 設定移行失敗時のフォールバック

---

## 5. build-time default (init_cfg.json.j2)

ファイル: `sonic-buildimage/files/build_templates/init_cfg.json.j2`

```json
"DEVICE_METADATA": {
    "localhost": {
        "buffer_model": "<dynamic|traditional>",  // make var: default_buffer_model
        "synchronous_mode": "enable",              // if include_p4rt == "y" のみ
        "default_bgp_status": "<up|down>",         // make var: shutdown_bgp_on_start
        "default_pfcwd_status": "<enable|disable>",// make var: enable_pfcwd_on_start
        "timezone": "UTC"
    }
}
```

書き込みフィールド: `buffer_model`, `synchronous_mode`(条件付き), `default_bgp_status`, `default_pfcwd_status`, `timezone`  
タイミング: `config-setup` で `sonic-cfggen -j init_cfg.json` 読み込み時

---

## 6. hard-coded / setdefault (sonic-config-engine)

### config_samples.py (各 generate_* 関数)
| 関数 | フィールド | 値 |
|---|---|---|
| `generate_sample_tor_router_config` | `hostname`, `type`, `bgp_asn` | `sonic`, `LeafRouter`, `65100` |
| `generate_sample_smartswitch_config` | `subtype` | `SmartSwitch` |
| `generate_sample_dpu_config` | `hostname`, `switch_type`, `type`, `subtype`, `bgp_asn` | SmartSwitch 系 |
| `(共通フォールバック)` | `hostname` if absent | `sonic` |
| `(共通フォールバック)` | `type` if absent | `LeafRouter` |

---

## 7. runtime injection (orchagent / daemon)

orchagent (`flexcounterorch.cpp:106`, `main.cpp:244,292,746`) は DEVICE_METADATA を **読み取り専用** で参照。  
cfgmgr (buffermgr, vlanmgrd 等) も同様に読み取りのみ。  
hostcfgd (`sonic-host-services/scripts/hostcfgd`) は DEVICE_METADATA を subscribe して hostname / timezone 変更に反応するが **書き込みは行わない**。  
→ **orchagent / cfgmgr / hostcfgd からの CONFIG_DB への逆書きは DEVICE_METADATA には存在しない**

---

## 特記: 未文書フィールド

| フィールド | 書き込み元 | YANG 定義 | 説明 |
|---|---|---|---|
| `p4_profile` | `config platform barefoot profile` | なし | Barefoot/Tofino ASIC 専用プロファイル名。YANG schema に leaf なし |
| `namespace_id` | sonic-cfggen (env var) | なし | multi-asic namespace 識別子。YANG schema に leaf なし |
| `storage_device` | minigraph.py L2602 | なし | storage chassis 用フラグ (`"true"`) |
| `rack_mgmt_map` | minigraph.py L2168 | なし | rack-level mgmt mapping |
| `slice_type` | minigraph.py L2176 | なし | T2/Chassis slice role |
| `downstream_subrole` | minigraph.py L2271 | なし | downstream ASIC の sub role |
| `dhcp_server` | minigraph.py L2736 | なし | DHCP server enabled flag |
