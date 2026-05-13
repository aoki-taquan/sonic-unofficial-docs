# DEVICE_METADATA tier_high 値別挙動 詳細調査 (v2)

slug: device-metadata  
調査日: 2026-05-13  
対象 enum フィールド: 12 フィールド (うち `type` は 35 値)  

---

## grep カバレッジ証跡

### フィールド: `default_bgp_status` (2値)

| 値 | grep hits | 主要ファイル |
|----|-----------|------------|
| `up` | 8 | sonic-utilities/tests/config_test.py (テスト), sonic-utilities/scripts/teamd_increase_retry_count.py:150 |
| `down` | 8 (テスト) | sonic-utilities/tests/config_test.py:880,901,922,961,980,999 |

**挙動詳細**:
- `up`: teamd_increase_retry_count.py:150 — `defaultBgpStatus = value == "up"` → True → BGP neighbor を admin up 状態で扱う
- `down`: 同行 — `defaultBgpStatus = False` → BGP neighbor の admin_up=False で起動 (メンテナンス用)
- 実際に bgp daemon の状態を操作するのは teamd_increase_retry_count.py であり、bgpcfgd ではない (bgpcfgd に直接参照なし)

### フィールド: `docker_routing_config_mode` (4値)

| 値 | grep hits (非テスト) | 主要ファイル |
|----|---------------------|------------|
| `separated` | 4 | sonic-buildimage/src/sonic-config-engine/minigraph.py:1630,2008 (デフォルト値); frrcfgd.py:2170 |
| `unified` | 2 | frrcfgd.py:2344 |
| `split` | 0 (コード) | — |
| `split-unified` | 0 (コード) | — |

**挙動詳細**:
- `separated` (デフォルト): minigraph.py:1630 でデフォルト値として設定。frrcfgd.py:2170 `else: self.config_mode = "separated"` — frrcfgd は separated として動作
- `unified`: frrcfgd.py:2344 `if self.config_mode == "unified":` → 起動時に全 BGP テーブルをリプレイしてから変更を監視
- `split` / `split-unified`: frrcfgd.py に分岐なし → separated と同等動作 (frrcfgd は config_mode == "unified" のみ特別扱い)
- db_migrator.py:742-754 で migrate_routing_config_mode() が旧→新DBへ値を引き継ぐ

### フィールド: `default_pfcwd_status` (2値)

| 値 | grep hits (非テスト) | 主要ファイル |
|----|---------------------|------------|
| `disable` | — | sonic-utilities/config/main.py:2427,2433 |
| `enable` | 1 | sonic-utilities/config/main.py:2434 |

**挙動詳細**:
- `enable`: config/main.py:2434 `if default_pfcwd_status == 'enable': run_command(['pfcwd', 'start_default'])` — config reload 後に pfcwd 自動起動
- `disable`: 同 if が成立しないため pfcwd 起動スキップ
- **複合条件**: type が `MgmtToRRouter` / `MgmtTsToR` / `BmcMgmtToRRouter` / `EPMS` のとき config/main.py:2425 でチェック自体をスキップ → pfcwd 呼び出しなし

### フィールド: `type` (35値)

**grep hits (非テスト, sonic-buildimage)**:

| 値 | hits | 主要ファイル/挙動 |
|----|------|----------------|
| `ToRRouter` | 35 | bgpd.main.conf.j2:118 (graceful-restart 条件), peer-group.conf.j2:7,22 (allowas-in 1), buffers_config.j2, qos_config.j2, init_cfg.json.j2:76 (dhcp_relay 除外) |
| `LeafRouter` | 42 | peer-group.conf.j2:9,24 (BBR 有効時 allowas-in 1), ipinip.json.j2:12 (Broadcom 限定追加エントリ), init_cfg.json.j2:85 (restapi 無効), qos_config.j2:109,150 |
| `SpineChassisFrontendRouter` | 2 | bgpd.conf.j2:17 (FRR BGP iBGP 設定), instance.conf.j2:38 (FRR instance iBGP) |
| `ChassisBackendRouter` | 1 | minigraph.py:49 (chassis_backend_role 定数) |
| `ASIC` | 14 | minigraph.py:95,109,332,339,347 (ASIC 名前生成), health_checker/hardware_checker.py |
| `MgmtToRRouter` | 3 | config/main.py:2425 (pfcwd スキップ), init_cfg.json.j2:76 (dhcp_relay 無効), minigraph.py:54 (mgmt_device_types) |
| `MgmtLeafRouter` | 0 | コード参照なし (YANG 定義のみ) |
| `MgmtSpineRouter` | 0 | コード参照なし (YANG 定義のみ) |
| `MgmtAccessRouter` | 0 | コード参照なし (YANG 定義のみ) |
| `LowerMgmtAggregator` | 0 | コード参照なし |
| `UpperMgmtAggregator` | 0 | コード参照なし |
| `SpineRouter` | 16 | init_cfg.json.j2:69 (pmon has_per_asic_scope=False), init_cfg.json.j2:90 (macsec 条件), peer-group.conf.j2:17,32 (UpstreamLC subtype との複合条件で table-map) |
| `UpperSpineRouter` | 4 | peer-group.conf.j2:17,32 (SpineRouter+UpstreamLC と同等の table-map 適用), init_cfg.json.j2:90 (macsec 有効化対象), minigraph.py (test) |
| `FabricSpineRouter` | 0 | bgpd.main.conf.j2:20 で lowercase 比較 `in ['lowerspinerouter', 'upperspinerouter', 'fabricspinerouter']` → disagg_t2=true (J2変数のみ, コード参照なし) |
| `LowerSpineRouter` | 0 | 同上 disagg_t2=true |
| `BackEndToRRouter` | 12 | minigraph.py:1828 (BackEndToRRouter+storage_device → ACL特殊バインド), ipinip.json.j2:68 (BackEnd型+storage_device なし → IPinIP生成スキップ), qos_config.j2:164 |
| `BackEndLeafRouter` | 13 | minigraph.py:51 (backend_device_types), ipinip.json.j2:68, init_cfg.json.j2:85 (restapi 無効), qos_config.j2:164 |
| `EPMS` | 2 | config/main.py:2425 (pfcwd スキップ), init_cfg.json.j2:76 (dhcp_relay 無効) |
| `MgmtTsToR` | 4 | config/main.py:2425 (pfcwd スキップ), init_cfg.json.j2:76 (dhcp_relay 無効), minigraph.py:52 (console_device_types), minigraph.py:54 (mgmt_device_types) |
| `BmcMgmtToRRouter` | 5 | config/main.py:2425 (pfcwd スキップ), init_cfg.json.j2:76 (dhcp_relay 無効), minigraph.py:53 (dhcp_server_enabled_device_types), minigraph.py:54 (mgmt_device_types) |
| `MiniTs` | 0 | コード参照なし |
| `LeafTs` | 0 | コード参照なし |
| `SpineTs` | 0 | コード参照なし |
| `CoreTs` | 0 | コード参照なし |
| `ConsoleServer` | 0 | コード参照なし |
| `TerminalServer` | 0 | コード参照なし |
| `SonicHost` | 0 | コード参照なし |
| `SmartSwitchDPU` | 2 | config_samples.py:155 (switch_type='dpu' 設定), chrony.conf.j2:58 (SmartSwitch subtype + type != SmartSwitchDPU) |
| `FilterLeaf` | 0 | コード参照なし |
| `NetworkBmc` | 0 | コード参照なし |
| `MseeRouter` | 0 | コード参照なし |
| `not-provisioned` | 0 | コード参照なし |
| `LowerRegionalHub` | 1 | bgpd.main.conf.j2:27 (disagg_rh=true), init_cfg.json.j2:90 (macsec 有効) |
| `FabricRegionalHub` | 0 | bgpd.main.conf.j2:27 (lowercase比較 `in ['lowerregionalhub', 'fabricregionalhub', 'upperregionalhub']`) |
| `UpperRegionalHub` | 0 | 同上 disagg_rh=true |

**複合条件まとめ (type フィールド)**:
1. `type == 'BackEndToRRouter' AND storage_device IN DEVICE_METADATA` → minigraph.py:1828 filter_acl_table_for_backend 適用
2. `type IN backend_device_types AND 'storage_device' NOT IN DEVICE_METADATA` → ipinip.json.j2:69 IPinIP decap エントリ生成スキップ
3. `type == 'SpineRouter' AND subtype == 'UpstreamLC'` → peer-group.conf.j2:17 table-map SELECTIVE_ROUTE_DOWNLOAD 適用
4. `type == 'ToRRouter' AND constants.bgp.graceful_restart.enabled` → bgpd.main.conf.j2:118 graceful-restart 設定
5. `type == 'SpineRouter' AND DEVICE_RUNTIME_METADATA['MACSEC_SUPPORTED']` → init_cfg.json.j2:90 macsec 有効化
6. `type == 'LeafRouter' AND DEVICE_NEIGHBOR[port].type == 'ToRRouter'` → buffers_config.j2:209, qos_config.j2:150 downlink 判定
7. `type NOT IN ['ToRRouter','EPMS','MgmtTsToR','MgmtToRRouter','BmcMgmtToRRouter']` → dhcp_relay feature 有効化 (init_cfg.json.j2:76)
8. `subtype == 'SmartSwitch' AND type != 'SmartSwitchDPU'` → chrony.conf.j2:58 追加設定

### フィールド: `buffer_model` (2値)

| 値 | grep hits | 主要ファイル |
|----|-----------|------------|
| `dynamic` | 多数 (device 固有 j2) | sonic-buildimage/files/build_templates/buffers_config.j2 |
| `traditional` | 多数 | buffers_config.j2, 各 device buffer j2 |

**挙動詳細**:
- `dynamic`: buffermgr が CONFIG_DB の BUFFER_POOL/PROFILE 変更を無視。Mellanox/BRCM dynamic buffer mgr が SAI を直接更新 (buffermgr.cpp:476-478 参照)
- `traditional` (またはその他): buffermgr が CONFIG_DB の設定を APPL_DB に転写

### フィールド: `synchronous_mode` (2値)

| 値 | grep hits | 主要ファイル |
|----|-----------|------------|
| `enable` | orchagent.sh:40 | dockers/docker-orchagent/orchagent.sh |
| `disable` | — | — |

**挙動詳細**:
- `enable`: orchagent.sh:40 `elif [ "$SYNC_MODE" == "enable" ]: ORCHAGENT_ARGS+="-s"` → SAI 操作をブロッキング
- `disable`: -s フラグなし → 非同期 SAI モード
- **複合条件**: `switch_type == 'dpu'` のとき orchagent.sh:38-39 で zmq_sync モードが優先 → synchronous_mode に関係なく "-z zmq_sync -k 65536" が使われる

### フィールド: `subtype` (5値)

| 値 | grep hits (非テスト) | 主要ファイル |
|----|---------------------|------------|
| `DualToR` | 10+ | bgpd.main.conf.j2:110 (coalesce-time 10000), dhcpv4-relay.agents.j2:14 (-U Loopback0 -dt), dhcpv6-relay.agents.j2:16 (-u Loopback0), buffers_config.j2:210, dhcp-relay.monitors.j2:27, docker-pmon.supervisord.conf.j2:157, init_cfg.json.j2:81 (mux feature enabled), zebra.interfaces.conf.j2:28 |
| `SmartSwitch` | 3 | chrony.conf.j2:58 (type != SmartSwitchDPU 条件), interfaces.j2:145,147 |
| `Supervisor` | 0 | コード参照なし (YANG定義のみ) |
| `UpstreamLC` | 4 | peer-group.conf.j2:17,32 (type==SpineRouter との複合条件で table-map), voq_chassis/policies.conf.j2:19,54 (FROM_VOQ route-map deny), internal/policies.conf.j2:42,67 (DownstreamLC との対比) |
| `DownstreamLC` | 2 | internal/policies.conf.j2:42,67 (FROM_VOQ route-map permit/set) |

**複合条件まとめ (subtype フィールド)**:
1. `type == 'SpineRouter' AND subtype == 'UpstreamLC'` → peer-group.conf.j2 table-map 適用
2. `subtype == 'DualToR'` → mux feature enabled, DHCPv4/v6 relay に -U/-u Loopback0 フラグ追加, BGP coalesce-time 10000
3. `subtype == 'SmartSwitch' AND type != 'SmartSwitchDPU'` → chrony.conf.j2 追加時刻同期設定

### フィールド: `switch_type` (6値)

| 値 | grep hits (非テスト) | 主要ファイル |
|----|---------------------|------------|
| `chassis-packet` | 10 | minigraph.py:86,1342,1348,2229, bgpd.main.conf.j2:63,141,170,176,198, fpmsyncd.cpp |
| `fabric` | 3 | minigraph.py:2233 (SAI_SWITCH_TYPE_FABRIC), orchagent.sh |
| `npu` | 0 | デフォルト (明示参照なし) |
| `voq` | 8 | minigraph.py:2221,2227,2237, bgpd.main.conf.j2:59, qos_config.j2:28 |
| `dpu` | 8 | orchagent.sh:27,38-39 (zmq_sync + bulk 65536), bfdmon.py:24-25 (BFD monitor skip), ipinip.json.j2:1 (if dpu → 別エントリ), enable_counters.py:43, config_samples.py:155 |
| `dummy-sup` | 0 | コード参照なし |

**挙動詳細**:
- `dpu`: orchagent.sh:38-39 `-z zmq_sync -k 65536` (synchronous_mode に関係なく ZMQ 強制)、bfdmon.py:25 でBFD監視スキップ
- `voq`: minigraph.py:2221 switch_id を SAI に渡す、qos_config.j2:28 voq ホスト名/ASIC 名設定
- `chassis-packet`: minigraph.py:2229 sub_role='fabric' 設定せず通常起動、bgpd.main.conf.j2:63,141 multi-ASIC bgp 設定有効化
- `fabric`: minigraph.py:2233 switch_type='fabric' 設定、SAI_SWITCH_TYPE_FABRIC で作成

### フィールド: `suppress-fib-pending` (2値)

| 値 | grep hits | 主要ファイル |
|----|-----------|------------|
| `enabled` | 5 | managers_bgp.py:502, fpmsyncd.cpp:114, route_check.py:387, config/main.py:2792, show/main.py:2765 |
| `disabled` | 2 | fpmsyncd.cpp:278 (コメント), config/main.py |

**挙動詳細**:
- `enabled`: managers_bgp.py:502 `enable_bgp_suppress_fib_pending_cmd = 'bgp suppress-fib-pending'` → FRR に適用; fpmsyncd.cpp:114 で有効化確認してルート待機モードに入る
- `disabled`: suppress-fib-pending 無効; fpmsyncd.cpp:278 でルートを即座に通知
- **YANG must 条件**: sonic-device_metadata.yang:250 `must "(current() = 'disabled') or (current() = 'enabled' and ../synchronous_mode = 'enable')"` → `enabled` かつ `synchronous_mode != 'enable'` は YANG バリデーションで reject

### フィールド: `async_swss_rec` (2値)

| 値 | grep hits | 主要ファイル |
|----|-----------|------------|
| `enabled` | 1 | dockers/docker-orchagent/orchagent.sh:66 |
| `disabled` | — | orchagent.sh (else branch) |

**挙動詳細**:
- `enabled`: orchagent.sh:66 でフラグ設定 → orchagent が swss.rec を非同期で書き込み
- `disabled`: 同期書き込み (デフォルト)

### フィールド: `nexthop_group` (2値)

| 値 | grep hits | 主要ファイル |
|----|-----------|------------|
| `enabled` | 1 | dockers/docker-fpm-frr/frr/zebra/zebra.conf.j2:20-22 |
| `disabled` | — | zebra.conf.j2 (else branch) |

**挙動詳細**:
- `enabled`: zebra.conf.j2:20 `if nexthop_group == 'enabled': fpm use-next-hop-groups` → FPM が next-hop group を使用
- `disabled` または未設定: `no fpm use-next-hop-groups` → 従来の RTM_NEWROUTE にネクストホップ情報埋め込み方式

### フィールド: `zebra_nexthop` (2値)

| 値 | grep hits | 主要ファイル |
|----|-----------|------------|
| `enabled` | — | zebra.conf.j2 (else/default branch) |
| `disabled` | 1 | dockers/docker-fpm-frr/frr/zebra/zebra.conf.j2:11 |

**挙動詳細**:
- `disabled`: zebra.conf.j2:11 `if zebra_nexthop == 'disabled': no zebra nexthop kernel enable` → カーネル nexthop を無効化
- `enabled` または未設定: `zebra nexthop kernel enable` (デフォルト)

---

## 複合条件サマリ (全フィールド)

| # | 条件 | 挙動 | ソース |
|---|------|------|--------|
| 1 | `type='BackEndToRRouter' AND storage_device in DEVICE_METADATA` | ACL テーブルを特殊バインドに変更 | minigraph.py:1828 |
| 2 | `type IN ['BackEndToRRouter','BackEndLeafRouter','BackEndSpineRouter'] AND 'storage_device' NOT IN DEVICE_METADATA` | IPinIP decap エントリ生成スキップ | ipinip.json.j2:69 |
| 3 | `type='SpineRouter' AND subtype='UpstreamLC'` | BGP peer-group に SELECTIVE_ROUTE_DOWNLOAD table-map 適用 | peer-group.conf.j2:17,32 |
| 4 | `type='ToRRouter' AND constants.bgp.graceful_restart.enabled` | FRR BGP graceful-restart 設定 | bgpd.main.conf.j2:118 |
| 5 | `type='SpineRouter' AND MACSEC_SUPPORTED` | macsec feature 有効化 | init_cfg.json.j2:90 |
| 6 | `switch_type='dpu'` | synchronous_mode 無視、zmq_sync+bulk 65536 モード強制 | orchagent.sh:38-39 |
| 7 | `suppress-fib-pending='enabled' AND synchronous_mode != 'enable'` | YANG must 違反 → reject | sonic-device_metadata.yang:250 |
| 8 | `subtype='DualToR'` | mux feature 有効、DHCP relay に Loopback0 フラグ追加、BGP coalesce-time 10000 | 複数 j2 |
| 9 | `type='LeafRouter' AND neighbor.type='ToRRouter'` | buffer/QoS downlink ポートとして設定 | buffers_config.j2:209, qos_config.j2:150 |
| 10 | `subtype='SmartSwitch' AND type != 'SmartSwitchDPU'` | chrony 追加時刻同期設定 | chrony.conf.j2:58 |
| 11 | `type IN ['MgmtToRRouter','MgmtTsToR','BmcMgmtToRRouter','EPMS']` | pfcwd 呼び出しスキップ | config/main.py:2425 |
| 12 | `type NOT IN ['ToRRouter','EPMS','MgmtTsToR','MgmtToRRouter','BmcMgmtToRRouter']` | dhcp_relay feature disabled | init_cfg.json.j2:76 |

---

## 値別 grep カバレッジサマリ

- 合計 grep 実行値数: 35 (type) + 2*9 (他フィールド) = 53 値
- 合計 hits (非テスト): 約 180 件
- 0 ヒット値: 15 値 (MgmtLeafRouter, MgmtSpineRouter, MgmtAccessRouter, LowerMgmtAggregator, UpperMgmtAggregator, MiniTs, LeafTs, SpineTs, CoreTs, ConsoleServer, TerminalServer, SonicHost, FilterLeaf, NetworkBmc, MseeRouter, not-provisioned, FabricRegionalHub, UpperRegionalHub — ただし bgpd.main.conf.j2 の lowercase 比較で一部カバー)
- 最頻ファイル TOP 5:
  1. `sonic-buildimage/files/build_templates/init_cfg.json.j2` — type/subtype で 5+ 分岐
  2. `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/general/peer-group.conf.j2` — type/subtype で 4 分岐
  3. `sonic-buildimage/src/sonic-config-engine/minigraph.py` — type/switch_type で多数分岐
  4. `sonic-buildimage/dockers/docker-orchagent/orchagent.sh` — switch_type/synchronous_mode/async_swss_rec
  5. `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/bgpd.main.conf.j2` — type/subtype/switch_type
