# device-metadata: Phase 6/7 Derivation Grep Evidence

## Phase 6: Assignment scan (minigraph.py 2967 lines, device_metadata assignment hits)

### minigraph.py — DEVICE_METADATA['localhost'] assignment summary

全 DEVICE_METADATA['localhost'] への代入は `get_sonic_output()` 関数内 (L2146-L2602) に集中。

```
L2146: results['DEVICE_METADATA'] = {'localhost': {...}}   # 初期化
L2159: ['bgp_asn'] = bgp_asn
L2162: ['chassis_hostname'] = chassis_hostname
L2165: ['deployment_id'] = deployment_id
L2168: ['rack_mgmt_map'] = rack_mgmt_map
L2172: ['cluster'] = cluster
L2176: ['slice_type'] = current_device['slice_type']
L2189: ['subtype'] = 'DualToR'                            # if PEER_SWITCH present
L2193: ['peer_switch'] = list(results['PEER_SWITCH'].keys())[0]  # DualToR派生
L2194: if type == 'SpineRouter':
L2196:   ['subtype'] = 'UpstreamLC'   # macsec_enabled=='True'
L2198:   ['subtype'] = 'DownstreamLC' # macsec_enabled=='False'
L2200:   ['subtype'] = 'Supervisor'   # else
L2206: elif type.lower()=='leafrouter' and gemini/libra redundancy → enable_tunnel_qos_map=True
L2208: elif type.lower()=='torrouter' and gemini/libra → enable_tunnel_qos_map=True
L2212: SYSTEM_DEFAULTS['tunnel_qos_remap']['status']='enabled'   # 派生先は別テーブル
L2218: ['asic_name'] = asic_name
L2221-2223: if switch_type=='voq' or chassis==VOQ → ['asic_name']='Asic0'
L2226: ['sub_role'] = sub_role (explicit)
L2228: elif switch_type=='voq' or chassis==VOQ and card_type=='Supervisor' → ['sub_role']='fabric'
L2229-2230: elif chassis_type=='chassis-packet' → ['sub_role']=BACKEND_ASIC_SUB_ROLE
L2232-2233: if chassis==VOQ and sub_role==FABRIC → ['switch_type']='fabric'
L2237: elif chassis_type is not None → ['switch_type']=chassis_type.lower()
L2241: if switch_type is not None → ['switch_type']=switch_type
L2250: ['switch_id'] = switch_id (voq)
L2253: ['max_cores'] = max_cores
L2257: ['max_cores'] = max_num_cores
L2266: ['resource_type'] = resource_type
L2271: ['downstream_subrole'] = downstream_subrole
L2602: ['storage_device'] = 'true'  # BackEndToRRouter/BackEndLeafRouter条件
```

device_metadata assignment ヒット数: 約 30 箇所

### config_samples.py — hwsku/type依存派生

```
L155-158: type='SmartSwitchDPU' のとき switch_type='dpu', subtype='SmartSwitch' を同時設定
L179-184: hwsku に 'pensando' を含む場合 SYSTEM_DEFAULTS['polaris']['status']='enabled' を派生
L186-188: SmartSwitchDPU config で SYSTEM_DEFAULTS['software_bfd']['status']='enabled'
```

### db_migrator.py — フィールド移行派生

```
L669-678 migrate_device_metadata(): synchronous_mode が新DBに欠如のとき旧DBから補完
L742-755 migrate_routing_config_mode(): docker_routing_config_mode を旧DB→新DBへ移行（既存値優先）
```

### init_cfg.json.j2 — type/subtype 値で feature enabled/disabled を派生

```
L69:  pmon has_per_asic_scope: type=='SpineRouter' → False, それ以外 → True
L76:  dhcp_relay feature: type NOT IN [ToRRouter,EPMS,MgmtTsToR,MgmtToRRouter,BmcMgmtToRRouter] → enabled
L81:  mux feature: subtype=='DualToR' → enabled, else → always_disabled
L85:  restapi feature: type NOT IN [LeafRouter,BackEndLeafRouter] → enabled
L90:  macsec feature: type IN [SpineRouter,UpperSpineRouter,LowerRegionalHub] AND MACSEC_SUPPORTED → enabled
```

---

## Phase 7: 条件付き module/manager 登録

### bgpcfgd/main.py (total managers.append: 5 conditional)

常時登録マネージャ (20件):
- BGPDataBaseMgr ×2, InterfaceMgr ×5, ZebraSetSrc, BGPPeerMgrBase ×5, BGPAllowListMgr,
  BBRMgr, StaticRouteMgr ×2, AdvertiseRouteMgr, RouteMapMgr, DeviceGlobalCfgMgr,
  AggregateAddressMgr, SRv6Mgr ×2

条件付き登録 (5件):
```
L112-113: if device_info.is_chassis():
            managers.append(ChassisAppDbMgr(..., "CHASSIS_APP_DB", "BGP_DEVICE_GLOBAL"))

L118-120: if sys_defaults['software_bfd']['status'] == 'enabled':
            managers.append(BfdMgr(..., "STATE_DB", STATE_BFD_SOFTWARE_SESSION_TABLE_NAME))
            ※ SYSTEM_DEFAULTS.software_bfd で制御 (直接 DEVICE_METADATA ではない)

L124-130: is_upstream_lc = type=='SpineRouter' AND subtype=='UpstreamLC'
           is_upper_spine_router = type=='UpperSpineRouter'
           if is_upstream_lc or is_upper_spine_router:
             managers.append(AsPathMgr(..., "CONFIG_DB", "DEVICE_METADATA"))
             # AS-PATH Manager は SpineRouter/UpstreamLC または UpperSpineRouter のみ

L132: managers.append(PrefixListMgr(...))  # 常時登録（条件なし）
```

合計 条件付き: 3件 (ChassisAppDbMgr, BfdMgr, AsPathMgr)
うち DEVICE_METADATA.type/subtype で直接条件: 1件 (AsPathMgr)

### docker-pmon.supervisord.conf.j2 (条件付き daemon 起動)

```
L157: if subtype == 'DualToR':
        ycabled (MUX cable daemon) を起動
```

### init_cfg.json.j2 (feature 状態で間接的に daemon 起動)

type/subtype 値が FEATURE テーブルの enabled/always_disabled を決定し、
featuremgrd がその状態に基づいてコンテナ起動/停止を制御。
直接 daemon 起動の if 文ではないが実質同等。

---

## grep カバレッジサマリ

- minigraph.py 行数: 2967、DEVICE_METADATA assignment ヒット: 約 30 件
- bgpcfgd/main.py managers.append 総数: 25、条件付き: 3 件、DEVICE_METADATA.type条件付き: 1 件 (AsPathMgr)
- db_migrator.py: migrate_device_metadata (L669) + migrate_routing_config_mode (L742) で 2 フィールド補完派生
- init_cfg.json.j2: type/subtype で 5 種 feature を条件派生
