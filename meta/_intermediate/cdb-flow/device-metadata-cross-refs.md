# DEVICE_METADATA — Phase C 暗黙参照 (daemon 起動時参照) 調査メモ

## 調査目的

各 daemon が起動時に `DEVICE_METADATA|localhost` を読み出す箇所を網羅的に列挙する。
Phase C: `<!-- cross-refs -->` セクション用。

## 1. 起動時参照の一覧 (ソース精読結果)

### orchagent (sonic-swss/orchagent/main.cpp)

| 読み取りフィールド | 行 | 用途 |
|---|---|---|
| `switch_type` | L248 | SAI `sai_switch_api->create_switch()` に渡す switch type を決定。未設定時は `"switch"` (= npu) とみなす |
| `subtype` | L269 | switch subtype を取得 (DualToR / SmartSwitch 等) |
| `switch_id` | L305 | VoQ スイッチの switch ID (VoQ 時のみ) |
| `max_cores` | L321 | VoQ シャーシの最大 core 数 (VoQ 時のみ) |
| `hostname` | L337 | VoQ 時のシステム hostname を SAI 属性に使用 |
| `asic_name` | L351 | VoQ 時の ASIC 名を SAI 属性に使用 |
| `switch_id` (2nd) | L748 | `gVoqMySwitchId` の初期値として再取得 |

evidence: `sonic-swss/orchagent/main.cpp:244-355,746-754`

### orchagent 起動スクリプト (sonic-buildimage/dockers/docker-orchagent/orchagent.sh)

| 読み取りフィールド | 行 | 用途 |
|---|---|---|
| `switch_type` | L22 | `LOCALHOST_SWITCHTYPE` に格納。`dpu` 判定で `-z zmq_sync -k 65536` を付加 |
| `asic_id` | L44-55 | `-i <asic_id>` オプションを orchagent に渡す |
| `async_swss_rec` | L66-68 | `enabled` のとき `-A` フラグ (swss.rec 非同期書き込み) を追加 |
| `subtype` | L106 | `DualToR` のとき tunnel_packet_handler 追加起動フラグ判定 |
| `ring_thread_enabled` | L121-123 | `true` のとき `-R` フラグ (ring thread 有効) を追加 |

evidence: `sonic-buildimage/dockers/docker-orchagent/orchagent.sh:22,44-68,106,121-123`

### orchagent docker-init.j2 (sonic-buildimage/dockers/docker-orchagent/docker-init.j2)

| 読み取りフィールド | 行 | 用途 |
|---|---|---|
| `subtype` | L28 | `DualToR` のとき tunnel_packet_handler を supervisord に登録 |
| `switch_type` | L29 | container 起動シーケンス制御 |

evidence: `sonic-buildimage/dockers/docker-orchagent/docker-init.j2:28-29`

### orchagent swss_vars.j2 (Jinja2 起動時生成)

| 読み取りフィールド | 用途 |
|---|---|
| `synchronous_mode` | 非 disable → `-s` フラグ (orchagent synchronous mode) |

evidence: `sonic-buildimage/dockers/docker-orchagent/swss_vars.j2:9; orchagent.sh:40`

### orchagent FlexCounterOrch (sonic-swss/orchagent/flexcounterorch.cpp)

| 読み取りフィールド | 行 | 用途 |
|---|---|---|
| `create_only_config_db_buffers` | L488-521 | カウンタ設定生成モードを切り替える |

ConsumerStateTable で動的更新あり (create-only ではない)。
evidence: `sonic-swss/orchagent/orchdaemon.cpp:622; flexcounterorch.cpp:149-152,488-521`

### buffermgrd.sh (sonic-buildimage/dockers/docker-orchagent/buffermgrd.sh)

| 読み取りフィールド | 行 | 用途 |
|---|---|---|
| `buffer_model` | L5-13 | `dynamic`: `buffermgrd -a asic_table.json` 起動。それ以外: `buffermgrd -l pg_profile_lookup.ini` 起動 |

evidence: `sonic-buildimage/dockers/docker-orchagent/buffermgrd.sh:5-13`

### buffermgr (sonic-swss/cfgmgr/buffermgrd.cpp, buffermgr.cpp)

| 読み取りフィールド | 行 | 用途 |
|---|---|---|
| `buffer_model` | buffermgr.cpp:470-478 | `dynamic` → APPL_DB 書き込み抑制。`traditional` → APPL_DB 転写 |

ConsumerStateTable で動的更新あり。
evidence: `sonic-swss/cfgmgr/buffermgrd.cpp:200; buffermgr.cpp:464-499`

### buffermgrdyn (dynamic buffer manager: sonic-swss/cfgmgr/buffermgrdyn.cpp)

| 読み取りフィールド | 行 | 用途 |
|---|---|---|
| `platform` (via vlanmgrd 連鎖) | L87 | Mellanox platform 文字列から SN 番号を抽出してモデル判定 |

evidence: `sonic-swss/cfgmgr/buffermgrdyn.cpp:41,87-95`

### vlanmgr (sonic-swss/cfgmgr/vlanmgrd.cpp)

| 読み取りフィールド | 行 | 用途 |
|---|---|---|
| `mac` | L56-61 | システムベース MAC を取得して VLAN インタフェースの MAC に設定。未設定時は `runtime_error` |

起動時 1 回のみ読み出し (static)。
evidence: `sonic-swss/cfgmgr/vlanmgrd.cpp:56-61`

### teammgr (sonic-swss/cfgmgr/teammgr.cpp)

| 読み取りフィールド | 行 | 用途 |
|---|---|---|
| `mac` | L54-57 | PortChannel の switch MAC に使用。未設定時は起動失敗 |

起動時 1 回のみ読み出し (static)。
evidence: `sonic-swss/cfgmgr/teammgr.cpp:31,54-57`

### stpmgr (sonic-swss/cfgmgr/stpmgrd.cpp)

| 読み取りフィールド | 行 | 用途 |
|---|---|---|
| `mac` | L81-88 | STP Bridge ID に使用するシステム MAC を取得。未設定時は起動失敗 |

起動時 1 回のみ読み出し (static)。
evidence: `sonic-swss/cfgmgr/stpmgrd.cpp:81-88`

### vxlanmgr (sonic-swss/cfgmgr/vxlanmgrd.cpp)

| 読み取りフィールド | 行 | 用途 |
|---|---|---|
| `mac` | L65-72 | VXLAN トンネルの内部 switch MAC として設定。未設定時は起動失敗 |

起動時 1 回のみ読み出し (static)。
evidence: `sonic-swss/cfgmgr/vxlanmgrd.cpp:65-72`

### nbrmgr (sonic-swss/cfgmgr/nbrmgr.cpp)

| 読み取りフィールド | 行 | 用途 |
|---|---|---|
| `switch_type` | L73-78 | `voq` のとき SYSTEM_NEIGH 購読を有効化 (VoQ 向けカーネル static neigh 設定) |

起動時 1 回のみ読み出し (static)。
evidence: `sonic-swss/cfgmgr/nbrmgr.cpp:73-78`

### intfmgr (sonic-swss/cfgmgr/intfmgr.cpp)

| 読み取りフィールド | 行 | 用途 |
|---|---|---|
| `switch_type` | L71-74 | `mySwitchType` に格納。インタフェース設定の分岐に使用 |

起動時 1 回のみ読み出し (static)。
evidence: `sonic-swss/cfgmgr/intfmgr.cpp:71-74`

### fpmsyncd (sonic-swss/fpmsyncd/fpmsyncd.cpp)

| 読み取りフィールド | 行 | 用途 |
|---|---|---|
| `suppress-fib-pending` | L82-83, L113-114 | SubscriberStateTable + Table 両方購読。起動時に `suppress-fib-pending = enabled` ならルート FIB 応答待機モードへ。動的切り替え (L265-300) も対応 |

evidence: `sonic-swss/fpmsyncd/fpmsyncd.cpp:82-83,113-114,265-300`

### bgpcfgd / frrcfgd (sonic-buildimage)

| Manager | 読み取りフィールド | 用途 |
|---|---|---|
| `BGPDataBaseMgr` (main.py:75) | 全フィールド | DEVICE_METADATA ディレクトリスロットを初期化 |
| `BgpPeerMgr` (managers_bgp.py:119) | `bgp_asn`, `type` | ピア追加の必須依存 |
| `BgpPeerMgr` (managers_bgp.py:143) | `deployment_id` | deployment_id チェック有効時のみ依存追加 |
| `DeviceGlobalCfgMgr` (managers_device_global.py:33) | `type` | subscribe → switch_role (IDF isolation 判定) |
| `AsPathMgr` (main.py:124-129) | `type`, `subtype` | SpineRouter+UpstreamLC / UpperSpineRouter のとき登録 |
| `StaticRouteMgr` (managers_static_rt.py:25) | `bgp_asn` | subscribe → static route の AS 番号解決 |
| `BbrMgr` (managers_bbr.py:25) | `bgp_asn` | subscribe |
| `AdvertiseRouteMgr` (managers_advertise_rt.py:26) | `bgp_asn` | subscribe |
| `PrefixListMgr` (managers_prefix_list.py:42) | `type`, `bgp_asn` | subscribe |
| `frrcfgd` (frrcfgd.py:2162,2295) | `bgp_asn`, `docker_routing_config_mode` | 設定生成モード初期化 |

evidence: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py:75,122-130; managers_bgp.py:119-143; managers_device_global.py:33-54; sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:2162,2295`

### hostcfgd (sonic-host-services/scripts/hostcfgd)

| 読み取りフィールド | 行 | 用途 |
|---|---|---|
| `hostname` | L1422 (init), L1516 (runtime) | `/etc/hostname` 更新 + `hostname-config` restart |
| `timezone` | L2247 (init), L1546 (runtime) | `timedatectl set-timezone` |
| `syslog_with_osversion` | L1590 (runtime) | rsyslog OS バージョン付加設定 |

`DeviceMetaCfg` クラスが subscribe し runtime 変更にも対応。
evidence: `sonic-host-services/scripts/hostcfgd:1422,1485-2493`

### dhcprelayd (sonic-buildimage/src/sonic-dhcp-utilities)

| 読み取りフィールド | 行 | 用途 |
|---|---|---|
| `has_sonic_dhcpv4_relay` | L64, L111-113 | `"True"` のとき旧来 dhcrelay プロセスを起動しない (新 dhcpv4-relay に委譲) |

evidence: `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py:64,111-113`

## 2. cross-refs セクション構造案

起動時参照 daemon を「参照タイミング」×「フィールド」の 2 軸で整理:

### 起動時のみ (create-only) 参照

| daemon | フィールド | 効果 |
|---|---|---|
| orchagent (main.cpp) | `switch_type`, `subtype`, `switch_id`, `max_cores`, `hostname`, `asic_name` | SAI create_switch 引数 / VoQ 初期化 |
| orchagent.sh (起動スクリプト) | `switch_type`, `asic_id`, `async_swss_rec`, `subtype`, `ring_thread_enabled` | orchagent プロセス起動引数 |
| swss_vars.j2 | `synchronous_mode` | orchagent `-s` フラグ |
| buffermgrd.sh | `buffer_model` | buffermgrd 起動引数 |
| vlanmgrd | `mac` | VLAN MAC 初期設定 |
| teammgrd | `mac` | PortChannel MAC 初期設定 |
| nbrmgrd | `switch_type` | VoQ SYSTEM_NEIGH 購読有無 |
| intfmgrd | `switch_type` | mySwitchType 初期値 |
| bgpcfgd (main.py) | `type`, `subtype` | AsPathMgr 条件付き登録 |
| stpmgrd | `mac` | STP Bridge ID MAC 初期設定 |
| vxlanmgrd | `mac` | VXLAN switch MAC 初期設定 |
| buffermgrdyn (Mellanox のみ) | `platform` | モデル番号抽出・XON 値決定 |

### runtime 更新に対応 (subscribe)

| daemon | フィールド | 効果 |
|---|---|---|
| buffermgr | `buffer_model` | APPL_DB 転写 vs 抑制 |
| FlexCounterOrch | `create_only_config_db_buffers` | カウンタ設定分岐 |
| fpmsyncd | `suppress-fib-pending` | FIB 応答待機モード切替 |
| hostcfgd | `hostname`, `timezone`, `syslog_with_osversion` | OS 設定即時反映 |
| bgpcfgd managers | `bgp_asn`, `type`, `deployment_id` | BGP ピア追加 / IDF isolation |
| frrcfgd | `bgp_asn`, `docker_routing_config_mode` | FRR 設定再生成 |

## 3. 記述上の注意

- `mac` は vlanmgrd / teammgrd / stpmgrd / vxlanmgrd の 4 daemon が起動時に読む最重要フィールド。欠如で起動失敗。
- `switch_type` は nbrmgrd / intfmgrd / orchagent main の 3 daemon が起動時に読む。VoQ 時は追加フィールドも必須。
- `bgp_asn` は bgpcfgd 内の 5+ manager が subscribe する最頻参照フィールド。
- `hostname` は hostcfgd と orchagent main (VoQ) の両方が起動時参照。
