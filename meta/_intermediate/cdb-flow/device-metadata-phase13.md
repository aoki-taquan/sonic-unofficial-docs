# device-metadata Phase 13 中間ファイル (Directory-sibling exhaustive scan)

## スキャン対象 enum フィールド (tier_high)

| フィールド | 値数 | 現引用ファイル数 | Phase13 新規発見 |
|---|---|---|---|
| `docker_routing_config_mode` | 4 | frrcfgd.py, minigraph.py | +2 (docker_init.sh, supervisord.conf.j2) |
| `type` | 35 | minigraph.py, peer-group.conf.j2, init_cfg.json.j2, bgpd.main.conf.j2 | +2 (switch.json.j2, general/policies.conf.j2) |
| `switch_type` | 6 | orchagent.sh, minigraph.py, bgpd.main.conf.j2 | +3 (critical_processes.j2, supervisord.conf.j2, switch.json.j2) |
| `subtype` | 5 | bgpd.main.conf.j2, docker-init.j2 | +1 (docker-init.j2 DualToR arp_update) |
| `buffer_model` | 2 | buffers_config.j2 | +1 (buffermgrd.sh) |
| `synchronous_mode` | 2 | orchagent.sh | 0 (既引用が包含) |
| `default_pfcwd_status` | 2 | config/main.py, init_cfg.json.j2 | 0 |
| `suppress-fib-pending` | 2 | managers_bgp.py, fpmsyncd.cpp | 0 |
| `async_swss_rec` | 2 | orchagent.sh | 0 |
| `nexthop_group` | 2 | zebra.conf.j2 | 0 |
| `zebra_nexthop` | 2 | zebra.conf.j2 | 0 |
| `default_bgp_status` | 2 | teamd_increase_retry_count.py | 0 |

## ディレクトリ別 sibling 未引用ファイル

### `dockers/docker-fpm-frr/` (docker_init.sh, frr/supervisord/supervisord.conf.j2)

**引用済み**: orchagent.sh (docker-orchagent)、frrcfgd.py (sonic-frr-mgmt-framework)  
**未引用 siblings**:
- `dockers/docker-fpm-frr/docker_init.sh` — `docker_routing_config_mode` の 4 値全てに明示的 if/elif 分岐
- `dockers/docker-fpm-frr/frr/supervisord/supervisord.conf.j2:224` — `unified` または `split-unified` のとき `[program:vtysh_b]` を有効化

### `dockers/docker-orchagent/` (switch.json.j2, buffermgrd.sh, critical_processes.j2, supervisord.conf.j2)

**引用済み**: orchagent.sh (synchronous_mode/async_swss_rec/switch_type=dpu), ipinip.json.j2 (switch_type=dpu/BackEndToRRouter)  
**未引用 siblings**:
- `switch.json.j2` — `type` 値別に ECMP hash_seed を設定 (ToRRouter/EPMS/MgmtTsToR=0, LeafRouter=10, SpineRouter=25, FabricSpineRouter=40, UpperSpineRouter=50, LowerRegionalHub=60, FabricRegionalHub=70, UpperRegionalHub=80); `switch_type != 'dpu'` と `!= 'chassis-packet'` で ecmp_hash_offset 制御; LeafRouter のとき `ordered_ecmp: true`
- `buffermgrd.sh` — `buffer_model == 'dynamic'` なら `-a /etc/sonic/asic_table.json` (dynamic buffer mgr); それ以外は `-l pg_profile_lookup.ini` (静的 lookup)
- `critical_processes.j2` — `switch_type == 'fabric'` のとき portsyncd/neighsyncd 等の非 fabric 系プロセスを critical_processes から除外
- `supervisord.conf.j2:35-41` — `switch_type == 'fabric'` のとき `is_fabric_asic=1` → `orchagent_dependent_startup_wait_for = "rsyslogd:running"` (通常は portsyncd:running)

### `dockers/docker-fpm-frr/frr/bgpd/templates/general/` (policies.conf.j2)

**引用済み**: general/peer-group.conf.j2 (type==ToRRouter/LeafRouter/SpineRouter+UpstreamLC), general/instance.conf.j2 (SpineChassisFrontendRouter)  
**未引用 siblings**:
- `general/policies.conf.j2:41-57` — `type='SpineRouter' AND subtype='UpstreamLC'` かつ `switch_type != 'chassis-packet'` のとき `FROM_BGP_PEER_V4/V6 permit 13` に `set tag {{ constants.bgp.route_do_not_send_appdb_tag }}` (=202) + `set community {{ constants.bgp.internal_fallback_community }}` (=22222:22222) を付与; `switch_type == 'chassis-packet'` のとき `set tag {{ constants.bgp.route_eligible_for_fallback_to_default_tag }}` (=203)

### `dockers/docker-fpm-frr/frr/bgpd/templates/monitors/` (peer-group.conf.j2)

**引用済み**: なし (monitors/ ディレクトリ全体が未引用)  
**未引用 siblings**:
- `monitors/peer-group.conf.j2:4-12` — `switch_type='voq' AND chassisdb_conf_present` → `voq_chassis=True` → `neighbor BGPMON update-source Loopback4096`; `switch_type='chassis-packet'` → 同様 Loopback4096; それ以外 → `update-source {{ loopback0_ipv4 }}`
- `monitors/peer-group.conf.j2:23-31` — `switch_type='voq' OR switch_type='chassis-packet'` → IPv6 address-family を BGPMON peer-group に追加

### `files/image_config/rsyslog/` (rsyslog-config.sh, rsyslog.conf.j2)

**引用済み**: hostcfgd が syslog_with_osversion の変更を検知して rsyslog-config を restart する。  
**未引用 siblings**:
- `rsyslog-config.sh:28-30` — `syslog_with_osversion` が空の場合 `"false"` にデフォルト設定
- `rsyslog.conf.j2:65-68` — `forward_with_osversion == "true"` のとき `SONiCForwardFormatWithOsVersion` テンプレートで OS バージョンをログに付加; それ以外は `SONiCForwardFormat` (バージョンなし)

## 新規 evidence row 追加数

- `device-metadata.md`: **6 行** 追加
  1. `docker_routing_config_mode` テーブルに `docker_init.sh` FRR ファイル管理分岐を追加
  2. `docker_routing_config_mode` に `supervisord.conf.j2:224` vtysh_b 追加
  3. `switch_type=fabric` に critical_processes.j2 + supervisord.conf.j2 挙動追加
  4. `type` テーブルに switch.json.j2 hash_seed 挙動追加 (FabricSpineRouter, UpperSpineRouter, LowerRegionalHub, FabricRegionalHub, UpperRegionalHub)
  5. `type=LeafRouter` に switch.json.j2 ordered_ecmp 追加
  6. `buffer_model=dynamic` に buffermgrd.sh `-a asic_table.json` 追加

- `acl-rule.md`: 0 行 (sibling grep ヒットなし)
- `acl-table.md`: 0 行 (sibling grep ヒットなし)
- `wred-profile.md`: 0 行 (ecn 値は既引用 qosorch.cpp + yang のみ)

## 新規 constants 解決

| constants 参照 | 実値 (constants.yml) | 発見ファイル |
|---|---|---|
| `constants.bgp.route_do_not_send_appdb_tag` | `202` | general/policies.conf.j2:52 |
| `constants.bgp.internal_fallback_community` | `22222:22222` | constants.yml:8 |

(Phase 12 で解決済: `route_eligible_for_fallback_to_default_tag` = 203)

## 代表 3 サンプル

### 1. docker_init.sh:59-93 (docker_routing_config_mode 全 4 値)
- `separated` / 未設定: `bgpd.conf`, `zebra.conf`, `staticd.conf` を `sonic-cfggen` で個別生成; `no service integrated-vtysh-config` を設定
- `split`: `no service integrated-vtysh-config`; `bgpd.conf` 等は個別だが `sonic-cfggen` 実行なし; `write_default_zebra_config zebra.conf`
- `split-unified`: `service integrated-vtysh-config`; `bgpd.conf` 等を削除して統合 `frr.conf` に移行; `write_default_zebra_config frr.conf`
- `unified`: `gen_frr.conf.j2` で統合 `frr.conf` を `sonic-cfggen` 生成; `service integrated-vtysh-config`; 個別デーモン設定ファイルを削除

### 2. switch.json.j2:8-25 (type 値別 hash_seed)
- `ToRRouter` / `EPMS` / `MgmtTsToR`: hash_seed=0 (ECMP ハッシュシード 0 → SAI `ecmp_hash_seed`)
- `LeafRouter`: hash_seed=10; `ecmp_hash_offset=10`, `lag_hash_offset=10`; `ordered_ecmp: true`
- `SpineRouter`: hash_seed=25
- `FabricSpineRouter`: hash_seed=40 (新規発見)
- `UpperSpineRouter`: hash_seed=50 (新規発見)
- `LowerRegionalHub`: hash_seed=60 (新規発見)
- `FabricRegionalHub`: hash_seed=70 (新規発見)
- `UpperRegionalHub`: hash_seed=80 (新規発見)

### 3. critical_processes.j2:2-4 / supervisord.conf.j2:35-41 (switch_type=fabric)
- `switch_type == 'fabric'`: `is_fabric_asic=1` → portsyncd/neighsyncd/fdbsyncd/vlanmgrd/intfmgrd/portmgrd/fabricmgrd/buffermgrd/vrfmgrd/nbrmgrd/vxlanmgrd/coppmgrd/tunnelmgrd が critical_processes から除外; orchagent の dependent_startup_wait_for が `portsyncd:running` ではなく `rsyslogd:running` に変更
