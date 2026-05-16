# FEATURE — Phase H プラットフォーム差分析

調査対象: `FEATURE` テーブルの consumer (`featured` / `hostcfgd` / `dhcprelayd` 等) が
プラットフォーム (multi-asic / VOQ chassis / SmartSwitch DPU / ベンダー) に応じて
挙動を変えるかを分析する。

## 結論

**プラットフォーム差あり**。以下 4 軸で挙動が分岐する:

1. **multi-asic (is_multi_npu == True)**: namespace ごとの CONFIG_DB / STATE_DB 同期、ASIC 数分のインスタンス生成
2. **SmartSwitch / DPU**: `has_per_dpu_scope` によって DPU ごとにインスタンスを生成
3. **SpineRouter**: `syncd` / `gbsyncd` の `auto_restart` を CONFIG_DB 値に関わらず `Restart=no` に強制
4. **init_cfg.json.j2 ビルド時条件**: device type / subtype / ASIC platform / ビルドフラグに応じて `state` / `has_per_asic_scope` / `has_global_scope` が変化

---

## 詳細分析

### 1. multi-asic (is_multi_npu == True)

**ソース**: `sonic-host-services/scripts/featured:142,151-162,353-355,570-573,588-591`

`FeatureHandler.__init__()` で `device_info.is_multi_npu()` を確認し、
multi-asic 環境の場合は namespace ごとに `ConfigDBConnector` と `Table (STATE_DB)` を
初期化する:

```python
if self.is_multi_npu:
    SonicDBConfig.initializeGlobalConfig()
    namespaces = device_info.get_namespaces()
    for ns in namespaces:
        self.ns_cfg_db[ns] = ConfigDBConnector(namespace=ns)
        self.ns_cfg_db[ns].connect(wait_for_init=True, retry_on=True)
        db_conn = DBConnector(STATE_DB, 0, False, ns)
        self.ns_feature_state_tbl[ns] = Table(db_conn, FEATURE_TBL)
```

**影響する操作**:

| 操作 | single-asic | multi-asic |
|------|-------------|-----------|
| `resync_feature_state()` | host CONFIG_DB のみ更新 | host + 全 namespace の CONFIG_DB を更新 (`featured:570-573`) |
| `sync_feature_delay_state()` | host CONFIG_DB のみ更新 | host + 全 namespace の CONFIG_DB を更新 (`featured:583-584`) |
| `set_feature_state()` | host STATE_DB のみ更新 | host + 全 namespace の STATE_DB を更新 (`featured:588-591`) |
| `sync_feature_scope()` | scope 更新をスキップ（`is_multi_npu == False` で early return） | CONFIG_DB の `has_per_asic_scope` / `has_global_scope` を更新し、不要インスタンスを stop/disable/mask |

`sync_feature_scope()` (`featured:312-355`) は `if not self.is_multi_npu: continue` で
single-asic 環境では全ての scope 同期処理をスキップする。

### 2. feature インスタンス名の生成 (`get_multiasic_feature_instances`)

**ソース**: `sonic-host-services/scripts/featured:408-415`

```python
feature_names = (
    ([feature.name] if feature.has_global_scope or all_instance or not self.is_multi_npu else []) +
    ([(feature.name + '@' + str(asic_inst)) for asic_inst in range(device_info.get_num_npus())
        if self.is_multi_npu and (all_instance or feature.has_per_asic_scope)]) +
    ([(feature.name + '@' + device_info.DPU_NAME_PREFIX + str(dpu_inst)) for dpu_inst in range(self.num_dpus)
        if all_instance or feature.has_per_dpu_scope])
)
```

| フィールド | インスタンス名パターン | 条件 |
|-----------|----------------------|------|
| `has_global_scope = True` | `<feature>` | single-asic でも multi-asic でも host インスタンスを生成 |
| `has_per_asic_scope = True` | `<feature>@0`, `<feature>@1`, ... | multi-asic (`is_multi_npu == True`) のみ |
| `has_per_dpu_scope = True` | `<feature>@dpu0`, `<feature>@dpu1`, ... | SmartSwitch 構成 (`num_dpus > 0`) |
| multi-asic かつ global_scope = False | インスタンスなし | host インスタンスが省略される |

**single-asic の場合**: `is_multi_npu == False` なら `not self.is_multi_npu == True` により、
`has_global_scope` の値に関わらず常に `[feature.name]` がリストに含まれる。

### 3. SmartSwitch / DPU (`has_per_dpu_scope`)

**ソース**: `sonic-host-services/scripts/featured:148,414-415`

`FeatureHandler.__init__()` で `device_info.get_num_dpus()` を取得。
SmartSwitch 構成 (DPU カードを持つプラットフォーム) では `num_dpus > 0` となり、
`has_per_dpu_scope = True` の feature は DPU ごとにインスタンスが生成される:

```
feature_name = "xxx@dpu0", "xxx@dpu1", ...
```

- `has_per_dpu_scope` は `sonic_package_manager` の `get_non_configurable_feature_entries`
  管理外であり、manifest ではなく CONFIG_DB の値をそのまま参照する (`featured:86`)。
- init_cfg.json.j2 には `has_per_dpu_scope = "True"` を持つ標準 feature のエントリは存在しない。
  SmartSwitch 固有 feature (例: `gnmi@dpu0` 等) はプラットフォーム固有パッケージで別途登録される。

### 4. SpineRouter — `syncd` / `gbsyncd` の auto_restart 強制

**ソース**: `sonic-host-services/scripts/featured:373-380`

```python
device_type = self._device_config.get('DEVICE_METADATA', {}).get('localhost', {}).get('type')
is_dependent_service = feature_config.name in ['syncd', 'gbsyncd']
if device_type == 'SpineRouter' and is_dependent_service:
    syslog.syslog(syslog.LOG_INFO, "Skipped setting Restart field in systemd for {}".format(feature_config.name))
    restart_field_str = "no"
else:
    restart_field_str = "always" if "enabled" in feature_config.auto_restart else "no"
```

**背景**: `syncd` / `gbsyncd` は `swss` サービスの依存として連動起動/停止するため、
SpineRouter (VOQ chassis) ではクリティカルプロセスクラッシュ時に二重停止が発生する問題がある。
また、早期 `syncd` 再起動は VOQ chassis でトラフィック断を引き起こすため、
SpineRouter 構成では `auto_restart` CONFIG_DB 設定を無視し、systemd `Restart=no` を強制する。

**結果**: SpineRouter で `config feature autorestart syncd enabled` を実行しても
systemd unit の `Restart=always` には変わらない（CONFIG_DB は更新されるが適用されない）。

### 5. init_cfg.json.j2 のビルド時プラットフォーム条件

**ソース**: `sonic-buildimage/files/build_templates/init_cfg.json.j2:67-130`

ビルド時に以下の条件でデフォルト `state` が決定される:

| feature | 条件 | state |
|---------|------|-------|
| `bgp` | `ETHERNET_PORTS_PRESENT == False` または chassis supervisor モジュール | `disabled` |
| `bgp` | 上記以外 | `enabled` |
| `teamd` | `ETHERNET_PORTS_PRESENT == False` | `disabled` |
| `teamd` | 上記以外 | `enabled` |
| `mux` | `subtype == 'DualToR'` | `enabled` |
| `mux` | 上記以外 | `always_disabled` |
| `macsec` | `type in ['SpineRouter', 'UpperSpineRouter', 'LowerRegionalHub']` かつ `MACSEC_SUPPORTED == True` | `enabled` |
| `macsec` | 上記以外 | `disabled` |
| `restapi` | `BUILD_REDUCE_IMAGE_SIZE == "y"` かつ `sonic_asic_platform == "broadcom"` かつ type が `LeafRouter` / `BackEndLeafRouter` 以外 | `enabled` |
| `dhcp_relay` | type が `ToRRouter` / `EPMS` / `MgmtTsToR` / `MgmtToRRouter` / `BmcMgmtToRRouter` に含まれる | `disabled` |
| `dhcp_relay` | 上記以外 | `enabled` |
| `pmon` | `delayed` フィールド: `type == 'SpineRouter'` → `False`、それ以外 → `True` | (delayed のみ分岐) |
| `gbsyncd` | `sonic_asic_platform == "vs"` のみ追加 | `enabled` |

`has_global_scope` / `has_per_asic_scope` はビルド時の `installer_services` 変数（`.service` /
`@.service` の有無）で自動決定される。`lldp` のみ chassis module_type に応じた Jinja2 テンプレートを使用:

```jinja
{%- if feature in ["lldp"] %}
"has_global_scope": "{% if ('CHASSIS_METADATA' in DEVICE_RUNTIME_METADATA and DEVICE_RUNTIME_METADATA['CHASSIS_METADATA']['module_type'] in ['linecard']) %}False{% else %}True{% endif %}",
"has_per_asic_scope": "{% if not DEVICE_RUNTIME_METADATA['ETHERNET_PORTS_PRESENT'] or ('CHASSIS_METADATA' in DEVICE_RUNTIME_METADATA and ...) %}False{% else %}True{% endif %}",
```

---

## まとめ表

| 観点 | 結果 | 根拠 |
|------|------|------|
| single-asic | 全 feature がホスト単一インスタンスで動作 | `get_multiasic_feature_instances`: `not is_multi_npu` でホストインスタンスを常に生成 |
| multi-asic (`is_multi_npu == True`) | namespace ごとの CONFIG_DB / STATE_DB 同期、ASIC インスタンス生成 | `featured:142-162,353-355,570-591` |
| SmartSwitch / DPU (`num_dpus > 0`) | `has_per_dpu_scope = True` の feature が DPU ごとのインスタンスを生成 | `featured:148,414-415` |
| VOQ chassis / SpineRouter | `syncd` / `gbsyncd` の `auto_restart` が `Restart=no` に強制 | `featured:373-380` |
| chassis (supervisor/linecard) | `bgp` / `lldp` の `state` / `has_global_scope` / `has_per_asic_scope` がモジュールタイプで変化 | `init_cfg.json.j2:67-130` |
| DualToR | `mux` feature の `state` が `enabled`（それ以外は `always_disabled`） | `init_cfg.json.j2:81` |
| Broadcom (ビルドフラグ) | `restapi` feature が `BUILD_REDUCE_IMAGE_SIZE == "y"` 時に有効化 | `init_cfg.json.j2:86-90` |
| ASIC ベンダー (SAI 経由) | 影響なし。FEATURE テーブルは SAI 非経由 | `featured` は systemd 操作のみ |

## Evidence

- `sonic-host-services/scripts/featured:142,148,151-162,312-355,373-380,408-415,570-591`
- `sonic-buildimage/files/build_templates/init_cfg.json.j2:67-130`
