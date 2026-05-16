# bgp-globals — Phase E ハードコード定数調査

対象ハンドラ: `frrcfgd.py` (`bgp_global_handler`, `global_key_map`, `bgp_table_handler_common` の `BGP_GLOBALS` 分岐) および `bgpd.conf.db.j2` (Jinja2 テンプレート)

## 抽出した定数

### FRR コマンド literal (`global_key_map`)

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `bgp router-id` コマンド | `{no:no-prefix}bgp router-id {}` | `router_id` フィールドを FRR に反映 | `frrcfgd.py:1784` |
| `sid vpn per-vrf export explicit` コマンド | `{no:no-prefix}sid vpn per-vrf export explicit {}` | `sid_vpn_per_vrf_export_explicit` フィールド | `frrcfgd.py:1785` |
| `bgp bestpath as-path multipath-relax` コマンド | `{no:no-prefix}bgp bestpath as-path multipath-relax {:mp-as-set}` | `load_balance_mp_relax` + `as_path_mp_as_set` の組み合わせ | `frrcfgd.py:1786` |
| `bgp always-compare-med` コマンド | `{no:no-prefix}bgp always-compare-med` | `always_compare_med=true` で異 AS の MED を比較 | `frrcfgd.py:1787` |
| `bgp bestpath compare-routerid` コマンド | `{no:no-prefix}bgp bestpath compare-routerid` | `external_compare_router_id` フィールド | `frrcfgd.py:1788` |
| `bgp bestpath as-path ignore` コマンド | `{no:no-prefix}bgp bestpath as-path ignore` | `ignore_as_path_length` フィールド | `frrcfgd.py:1789` |
| `bgp graceful-restart` コマンド | `{no:no-prefix}bgp graceful-restart` | `graceful_restart_enable=true` で GR を有効化 | `frrcfgd.py:1790` |
| `bgp graceful-restart restart-time` コマンド | `{no:no-prefix}bgp graceful-restart restart-time {}` | `gr_restart_time` フィールド (秒) | `frrcfgd.py:1791` |
| `bgp graceful-restart stalepath-time` コマンド | `{no:no-prefix}bgp graceful-restart stalepath-time {}` | `gr_stale_routes_time` フィールド (秒) | `frrcfgd.py:1792` |
| `bgp graceful-restart preserve-fw-state` コマンド | `{no:no-prefix}bgp graceful-restart preserve-fw-state` | `gr_preserve_fw_state=true` で F-bit を設定 | `frrcfgd.py:1793` |
| `bgp log-neighbor-changes` コマンド | `{no:no-prefix}bgp log-neighbor-changes` | `log_nbr_state_changes` フィールド | `frrcfgd.py:1794` |
| `bgp cluster-id` コマンド | `{no:no-prefix}bgp cluster-id {}` | `rr_cluster_id` フィールド | `frrcfgd.py:1795` |
| `bgp route-reflector allow-outbound-policy` コマンド | `{no:no-prefix}bgp route-reflector allow-outbound-policy` | `rr_allow_out_policy` フィールド | `frrcfgd.py:1796` |
| `bgp disable-ebgp-connected-route-check` コマンド | `{no:no-prefix}bgp disable-ebgp-connected-route-check` | `disable_ebgp_connected_rt_check` フィールド | `frrcfgd.py:1797` |
| `bgp fast-external-failover` コマンド | `{no:no-prefix}bgp fast-external-failover` | `fast_external_failover` フィールド (FRR デフォルト: 有効) | `frrcfgd.py:1798` |
| `bgp network import-check` コマンド | `{no:no-prefix}bgp network import-check` | `network_import_check` フィールド | `frrcfgd.py:1799` |
| `bgp graceful-shutdown` コマンド | `{no:no-prefix}bgp graceful-shutdown` | `graceful_shutdown=true` で GSHUT を有効化 | `frrcfgd.py:1800` |
| `bgp client-to-client reflection` コマンド | `{no:no-prefix}bgp client-to-client reflection` | `rr_clnt_to_clnt_reflection` フィールド (FRR デフォルト: 有効) | `frrcfgd.py:1801` |
| `bgp listen limit` コマンド | `{no:no-prefix}bgp listen limit {}` | `max_dynamic_neighbors` フィールド (上限: 5000) | `frrcfgd.py:1802` |
| `read-quanta` コマンド | `{no:no-prefix}read-quanta {}` | `read_quanta` フィールド (I/O サイクルあたりパケット数) | `frrcfgd.py:1803` |
| `write-quanta` コマンド | `{no:no-prefix}write-quanta {}` | `write_quanta` フィールド | `frrcfgd.py:1804` |
| `coalesce-time` コマンド | `{no:no-prefix}coalesce-time {}` | `coalesce_time` フィールド (ms) | `frrcfgd.py:1805` |
| `bgp route-map delay-timer` コマンド | `{no:no-prefix}bgp route-map delay-timer {}` | `route_map_process_delay` フィールド (秒) | `frrcfgd.py:1806` |
| `bgp deterministic-med` コマンド | `{no:no-prefix}bgp deterministic-med` | `deterministic_med` フィールド | `frrcfgd.py:1807` |
| `bgp bestpath med confed` コマンド | `{no:no-prefix}bgp bestpath med confed` | `med_confed` フィールド | `frrcfgd.py:1808` |
| `bgp bestpath med missing-as-worst` コマンド | `{no:no-prefix}bgp bestpath med missing-as-worst` | `med_missing_as_worst` フィールド | `frrcfgd.py:1809` |
| `bgp bestpath as-path confed` コマンド | `{no:no-prefix}bgp bestpath as-path confed` | `compare_confed_as_path` フィールド | `frrcfgd.py:1810` |
| `bgp default ipv4-unicast` コマンド | `{no:no-prefix}bgp default ipv4-unicast` | `default_ipv4_unicast` フィールド | `frrcfgd.py:1811` |
| `bgp default local-preference` コマンド | `{no:no-prefix}bgp default local-preference {}` | `default_local_preference` フィールド | `frrcfgd.py:1812` |
| `bgp default show-hostname` コマンド | `{no:no-prefix}bgp default show-hostname` | `default_show_hostname` フィールド | `frrcfgd.py:1813` |
| `bgp default shutdown` コマンド | `{no:no-prefix}bgp default shutdown` | `default_shutdown` フィールド | `frrcfgd.py:1814` |
| `bgp default subgroup-pkt-queue-max` コマンド | `{no:no-prefix}bgp default subgroup-pkt-queue-max {}` | `default_subgroup_pkt_queue_max` フィールド | `frrcfgd.py:1815` |
| `bgp max-med on-startup` コマンド | `{no:no-prefix}bgp max-med on-startup {} {}` | `max_med_time` + `max_med_val` の組み合わせ | `frrcfgd.py:1816` |
| `update-delay` コマンド | `{no:no-prefix}update-delay {} {}` | `max_delay` + `establish_wait` の組み合わせ | `frrcfgd.py:1817` |
| `bgp confederation identifier` コマンド | `{no:no-prefix}bgp confederation identifier {}` | `confed_id` フィールド | `frrcfgd.py:1818` |
| `bgp confederation peers` コマンド | `{no:no-prefix}bgp confederation peers {}` | `confed_peers` フィールド (hdl_confed_peers で空白区切りに展開) | `frrcfgd.py:1819` |
| `timers bgp` コマンド | `{no:no-prefix}timers bgp {} {}` | `keepalive` + `holdtime` の組み合わせ (両方必須) | `frrcfgd.py:1820` |
| `bgp max-med administrative` コマンド | `{no:no-prefix}bgp max-med administrative {}` | `max_med_admin=true` + `max_med_admin_val` | `frrcfgd.py:1821` |

### vtysh コマンドプレフィクス定数 (local_asn 書き込み時)

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `local_asn` 新規設定時の初期コマンド | `no bgp default ipv4-unicast` | 新規 BGP インスタンス生成直後に IPv4 unicast を無効化 | `frrcfgd.py:2700` |
| vtysh コマンド prefix | `configure terminal` | すべての設定投入の先頭 | `frrcfgd.py:2700` |
| router bgp フォーマット | `router bgp {} vrf {}` | `local_asn` と `vrf` を埋め込んだ BGP インスタンス選択 | `frrcfgd.py:2716` |

### FRR ハードコード既定値 (FRR ソース)

| 定数名 | 値 | 適用モード | 用途 | evidence |
|-------|-----|----------|------|---------|
| `BGP_DEFAULT_KEEPALIVE` (`DFLT_BGP_KEEPALIVE`) | **60 秒** (standard) / **3 秒** (datacenter) | `!HAVE_DATACENTER` / `HAVE_DATACENTER` | keepalive 未設定時の FRR 組み込み既定 | `sonic-frr/defaults.h:44,31` / `sonic-frr/bgpd/bgpd.h:1401` |
| `BGP_DEFAULT_HOLDTIME` (`DFLT_BGP_HOLDTIME`) | **180 秒** (standard) / **9 秒** (datacenter) | `!HAVE_DATACENTER` / `HAVE_DATACENTER` | holdtime 未設定時の FRR 組み込み既定 | `sonic-frr/defaults.h:43,30` / `sonic-frr/bgpd/bgpd.h:1400` |
| `BGP_DEFAULT_CONNECT_RETRY` (`DFLT_BGP_TIMERS_CONNECT`) | **120 秒** (standard) / **10 秒** (datacenter) | `!HAVE_DATACENTER` / `HAVE_DATACENTER` | connect-retry 未設定時の FRR 組み込み既定 | `sonic-frr/defaults.h:42,29` / `sonic-frr/bgpd/bgpd.h:1404` |
| `BGP_DEFAULT_RESTART_TIME` | **120 秒** | 全モード | graceful-restart restart-time 未設定時の FRR 既定 | `sonic-frr/bgpd/bgpd.h:1417` |
| `BGP_DEFAULT_STALEPATH_TIME` | **360 秒** | 全モード | graceful-restart stalepath-time 未設定時の FRR 既定 | `sonic-frr/bgpd/bgpd.h:1418` |
| `BGP_DEFAULT_LOCAL_PREF` | **100** | 全モード | `default_local_preference` 未設定時の FRR 既定 | `sonic-frr/bgpd/bgpd.h:1407` |
| `BGP_GSHUT_LOCAL_PREF` | **0** | 全モード | `graceful_shutdown=true` 時に広告する local-preference | `sonic-frr/bgpd/bgpd.h:1411` |
| `BGP_DEFAULT_SUBGROUP_PKT_QUEUE_MAX` | **40** | 全モード | `default_subgroup_pkt_queue_max` 未設定時の FRR 既定 | `sonic-frr/bgpd/bgpd.h:1414` |
| `BGP_DYNAMIC_NEIGHBORS_LIMIT_DEFAULT` | **100** | 全モード | `max_dynamic_neighbors` 未設定時の FRR 既定 | `sonic-frr/bgpd/bgpd.h:1431` |

> **注記**: SONiC の FRR ビルドが `--enable-datacenter` フラグを使用するかは `sonic-frr/debian/rules` に明示なし。SONiC コミュニティでは standard モード (keepalive=60s, holdtime=180s, connect-retry=120s) が基本と想定されるが、ビルド設定によっては datacenter モード値 (3s/9s/10s) が適用される可能性がある。

### router-id 自動選択

| 動作 | 説明 | evidence |
|------|------|---------|
| `router_id` 未設定時 | FRR が起動時に `loopback0` 等の最初の IF の IP を router-id として自動選択 | FRR bgpd 起動ロジック (bgpd.c) |
| `router_id` 設定時 | `bgp router-id <ip>` を vtysh 経由で発行 | `frrcfgd.py:1784` |

### comb_attr_list (bgp_global_handler)

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| 組み合わせ制約 | `{'keepalive', 'holdtime'}` | 両フィールドが揃わないと `timers bgp <k> <h>` コマンドを発行しない | `frrcfgd.py:3936` |

### Jinja2 テンプレート固定文字列 (bgpcfgd 経由起動時)

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| IPv4 unicast デフォルト無効化 | `no bgp default ipv4-unicast` (else 節で常時発行) | `default_ipv4_unicast` 未設定時に bgpcfgd 経由では無効扱いになる | `bgpd.conf.db.j2:46-50` |
| fast-external-failover 無効化 | `no bgp fast-external-failover` (`== 'false'` 時のみ) | `fast_external_failover` 未設定の場合 FRR デフォルト (有効) が維持される | `bgpd.conf.db.j2:33-35` |
| client-to-client reflection 無効化 | `no bgp client-to-client reflection` (`== 'false'` 時のみ) | `rr_clnt_to_clnt_reflection` 未設定の場合 FRR デフォルト (有効) が維持される | `bgpd.conf.db.j2:64-66` |

## スキャン証跡

- `frrcfgd.py` L1784-1821 (`global_key_map` 全行), L2700, L2716, L3935-3936 (`bgp_global_handler`) を確認。
- `bgpd.conf.db.j2` 全行 (L1-205) 確認。
- `sonic-frr/defaults.h` 全行確認 (L29-44)。
- `sonic-frr/bgpd/bgpd.h` L1397-1434 確認。
- 抽出件数: FRR コマンド literal 38 件 + vtysh prefix 3 件 + FRR ハードコード既定値 9 件 + router-id 動作 2 件 + comb_attr_list 1 件 + J2 テンプレート固定文字 3 件 = 計 56 件。
