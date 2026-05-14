#!/usr/bin/env python3
"""
Generate Direction A entry-points blocks for 60 tier_low CONFIG_DB pages.
Output:
  - meta/_intermediate/cdb-flow/<slug>-entry-points.md  (intermediate)
  - Appends <!-- entry-points --> block to docs/reference/config-db/<slug>.md
"""

import os
import json
import re
import subprocess

WT = "/home/coder/sonic-unofficial-docs/.claude/worktrees/q64-c-direction-a-low-1"
CACHE = "/home/coder/sonic-unofficial-docs/.cache/sonic-sources"
DOCS_DIR = f"{WT}/docs/reference/config-db"
INTERMEDIATE_DIR = f"{WT}/meta/_intermediate/cdb-flow"

os.makedirs(INTERMEDIATE_DIR, exist_ok=True)

# ─── Entry-points knowledge base ─────────────────────────────────────────────
# Each entry: slug -> dict with
#   table: CONFIG_DB table name(s)
#   cli: list of CLI commands that write this table
#   cli_file: source file(s)
#   minigraph: bool - is written by minigraph
#   rest_gnmi: description or None
#   db_migrator: description or None
#   build_time: description or None (init_cfg.json.j2 or static defaults)
#   hard_coded: description or None
#   runtime_injection: description or None

ENTRY_POINTS = {
    "aaa": {
        "table": "AAA",
        "cli": ["`config aaa authentication login <method>`", "`config aaa authentication failthrough <enable|disable>`", "`config aaa authentication fallback <enable|disable>`", "`config aaa authorization login <method>`", "`config aaa accounting login <method>`"],
        "cli_file": "sonic-utilities/config/aaa.py",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": "あり: `migrate_aaa_table_field_sync()` で `authentication`/`accounting`/`authorization` エントリを再生成 (db_migrator.py:879,886,895)",
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "as-path-set": {
        "table": "AS_PATH_SET",
        "cli": ["`config route-map as-path-set add <name> <pattern>`", "`config route-map as-path-set delete <name>`"],
        "cli_file": "sonic-utilities/config/main.py (route-map グループ)",
        "minigraph": False,
        "rest_gnmi": "sonic-mgmt-common translib でルーティングポリシー OpenConfig モデル経由の書き込みが可能",
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "auto-techsupport-feature": {
        "table": "AUTO_TECHSUPPORT_FEATURE",
        "cli": ["`config auto-techsupport feature enable/disable <feature>`", "`config auto-techsupport feature rate-limit-interval <feature> <secs>`", "`config auto-techsupport feature available-mem-threshold <feature> <pct>`"],
        "cli_file": "sonic-utilities/config/plugins/auto_techsupport.py",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`init_cfg.json.j2` の `AUTO_TECHSUPPORT_FEATURE` セクションでデフォルト feature リスト (bgp, swss, syncd 等) が注入される",
        "hard_coded": None,
        "runtime_injection": None,
    },
    "auto-techsupport": {
        "table": "AUTO_TECHSUPPORT",
        "cli": ["`config auto-techsupport global enable/disable`", "`config auto-techsupport global max-techsupport-limit <pct>`", "`config auto-techsupport global rate-limit-interval <secs>`"],
        "cli_file": "sonic-utilities/config/plugins/auto_techsupport.py",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "banner-message": {
        "table": "BANNER_MESSAGE",
        "cli": ["`config banner motd <message>`", "`config banner login <message>`", "`config banner logout <message>`"],
        "cli_file": "sonic-utilities/config/main.py (banner グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`init_cfg.json.j2` に `BANNER_MESSAGE` セクションはないが、空エントリがデフォルト",
        "hard_coded": None,
        "runtime_injection": None,
    },
    "bgp-aggregate-address": {
        "table": "BGP_AGGREGATE_ADDRESS",
        "cli": ["`vtysh` 経由: `aggregate-address <prefix>` (FRR コンフィグ → bgpcfgd が CONFIG_DB へ書き戻し)"],
        "cli_file": "sonic-buildimage/src/sonic-frr/patch (bgpcfgd)",
        "minigraph": False,
        "rest_gnmi": "sonic-mgmt-common OpenConfig BGP ポリシー経由",
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": "`bgpcfgd` が FRR running-config を読み CONFIG_DB と同期",
    },
    "bgp-allowed-prefixes": {
        "table": "BGP_ALLOWED_PREFIXES",
        "cli": ["`config bgp allowed-prefix add/del <prefix>`"],
        "cli_file": "sonic-utilities/config/main.py (bgp グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "bgp-device-global": {
        "table": "BGP_DEVICE_GLOBAL",
        "cli": ["`config bgp device-global tsa enable/disable`", "`config bgp device-global w-ecmp enable/disable`"],
        "cli_file": "sonic-utilities/config/main.py (bgp グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`init_cfg.json.j2` に `BGP_DEVICE_GLOBAL` セクションが存在し `tsa_enabled: false` 等のデフォルト値が注入される",
        "hard_coded": None,
        "runtime_injection": None,
    },
    "bgp-globals-af-aggregate-addr": {
        "table": "BGP_GLOBALS_AF_AGGREGATE_ADDR",
        "cli": ["`vtysh` 経由 aggregate-address コマンド (bgpcfgd が CONFIG_DB へ書き戻し)"],
        "cli_file": "sonic-frr bgpcfgd",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": "`bgpcfgd` が FRR running-config を読み CONFIG_DB と同期",
    },
    "bgp-globals-af-network": {
        "table": "BGP_GLOBALS_AF_NETWORK",
        "cli": ["`vtysh` 経由 network コマンド (bgpcfgd が CONFIG_DB へ書き戻し)"],
        "cli_file": "sonic-frr bgpcfgd",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": "`bgpcfgd` が FRR running-config を読み CONFIG_DB と同期",
    },
    "bgp-globals-af": {
        "table": "BGP_GLOBALS_AF",
        "cli": ["`vtysh` 経由 address-family コマンド群 (bgpcfgd が CONFIG_DB へ書き戻し)"],
        "cli_file": "sonic-frr bgpcfgd",
        "minigraph": True,
        "rest_gnmi": "sonic-mgmt-common OpenConfig BGP 経由",
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": "`bgpcfgd` が FRR running-config を CONFIG_DB と同期",
    },
    "bgp-globals": {
        "table": "BGP_GLOBALS",
        "cli": ["`config bgp graceful-restart enable/disable`", "`vtysh` 経由 bgpcfgd が多くのグローバル設定を書き戻し"],
        "cli_file": "sonic-utilities/config/main.py, sonic-frr bgpcfgd",
        "minigraph": True,
        "rest_gnmi": "sonic-mgmt-common OpenConfig BGP global 経由",
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": "`bgpcfgd` が FRR running-config を読み CONFIG_DB と同期",
    },
    "bgp-monitors": {
        "table": "BGP_MONITORS",
        "cli": ["`config bgp monitor add/del <address>`"],
        "cli_file": "sonic-utilities/config/main.py (bgp グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "bgp-neighbor-af": {
        "table": "BGP_NEIGHBOR_AF",
        "cli": ["`vtysh` 経由 neighbor address-family コマンド群 (bgpcfgd が CONFIG_DB へ書き戻し)"],
        "cli_file": "sonic-frr bgpcfgd",
        "minigraph": True,
        "rest_gnmi": "sonic-mgmt-common OpenConfig BGP neighbor 経由",
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": "`bgpcfgd` が FRR running-config を CONFIG_DB と同期",
    },
    "bgp-neighbor": {
        "table": "BGP_NEIGHBOR",
        "cli": ["`config bgp startup/shutdown all`", "`vtysh` 経由 neighbor コマンド群 (bgpcfgd が CONFIG_DB へ書き戻し)"],
        "cli_file": "sonic-utilities/config/main.py, sonic-frr bgpcfgd",
        "minigraph": True,
        "rest_gnmi": "sonic-mgmt-common OpenConfig BGP neighbor 経由",
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": "`bgpcfgd` が FRR running-config を CONFIG_DB と同期",
    },
    "bgp-peer-group-af": {
        "table": "BGP_PEER_GROUP_AF",
        "cli": ["`vtysh` 経由 peer-group address-family コマンド群 (bgpcfgd が CONFIG_DB へ書き戻し)"],
        "cli_file": "sonic-frr bgpcfgd",
        "minigraph": False,
        "rest_gnmi": "sonic-mgmt-common OpenConfig BGP peer-group 経由",
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": "`bgpcfgd` が FRR running-config を CONFIG_DB と同期",
    },
    "bgp-peer-group": {
        "table": "BGP_PEER_GROUP",
        "cli": ["`vtysh` 経由 peer-group コマンド群 (bgpcfgd が CONFIG_DB へ書き戻し)"],
        "cli_file": "sonic-frr bgpcfgd",
        "minigraph": False,
        "rest_gnmi": "sonic-mgmt-common OpenConfig BGP peer-group 経由",
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": "`bgpcfgd` が FRR running-config を CONFIG_DB と同期",
    },
    "bgp-peer-range": {
        "table": "BGP_PEER_RANGE",
        "cli": ["`config bgp peer-range add/del <prefix>`"],
        "cli_file": "sonic-utilities/config/main.py (bgp グループ)",
        "minigraph": True,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "bmp": {
        "table": "BMP",
        "cli": ["`config bmp enable/disable`", "`config bmp table enable/disable <table>`"],
        "cli_file": "sonic-utilities/config/main.py (bmp グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "breakout-cfg": {
        "table": "BREAKOUT_CFG",
        "cli": ["`config interface breakout <port> <mode>`"],
        "cli_file": "sonic-utilities/config/main.py (interface グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "プラットフォーム提供の `platform.json` / `port_config.ini` から `sonic-cfggen` が初期値を注入",
        "hard_coded": None,
        "runtime_injection": None,
    },
    "buffer-pg": {
        "table": "BUFFER_PG",
        "cli": ["`config interface buffer priority-group set <port> <pg-range> <profile>`", "`config interface buffer priority-group remove <port> <pg-range>`"],
        "cli_file": "sonic-utilities/config/main.py (buffer グループ)",
        "minigraph": True,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`sonic-cfggen` が `buffers_config.j2` テンプレートから初期バッファ PG マッピングを生成",
        "hard_coded": None,
        "runtime_injection": "Dynamic buffer model: `buffermgrd` が LOSSLESS_TRAFFIC_PATTERN を参照してポートごとに自動再計算・書き込み",
    },
    "buffer-pool": {
        "table": "BUFFER_POOL",
        "cli": ["`config buffer pool add/del <name> ...`"],
        "cli_file": "sonic-utilities/config/main.py (buffer グループ)",
        "minigraph": True,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`buffers_config.j2` テンプレートからプラットフォーム別プールが生成",
        "hard_coded": None,
        "runtime_injection": "Dynamic buffer model では `buffermgrd` がプールサイズを自動調整",
    },
    "buffer-port-egress-profile-list": {
        "table": "BUFFER_PORT_EGRESS_PROFILE_LIST",
        "cli": ["`config interface buffer egress-profile-list set <port> <profile>`"],
        "cli_file": "sonic-utilities/config/main.py (buffer グループ)",
        "minigraph": True,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`buffers_config.j2` から生成",
        "hard_coded": None,
        "runtime_injection": "Dynamic buffer model: `buffermgrd` がポートごとに書き込み",
    },
    "buffer-port-ingress-profile-list": {
        "table": "BUFFER_PORT_INGRESS_PROFILE_LIST",
        "cli": ["`config interface buffer ingress-profile-list set <port> <profile>`"],
        "cli_file": "sonic-utilities/config/main.py (buffer グループ)",
        "minigraph": True,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`buffers_config.j2` から生成",
        "hard_coded": None,
        "runtime_injection": "Dynamic buffer model: `buffermgrd` がポートごとに書き込み",
    },
    "buffer-profile": {
        "table": "BUFFER_PROFILE",
        "cli": ["`config buffer profile add/del <name> --xon <bytes> --xoff <bytes> --size <bytes> --dynamic_th <n> --pool <pool>`"],
        "cli_file": "sonic-utilities/config/main.py (buffer グループ)",
        "minigraph": True,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`buffers_config.j2` から platform 別プロファイルが生成",
        "hard_coded": None,
        "runtime_injection": "Dynamic buffer model: `buffermgrd` が速度・ケーブル長に基づいて Lossless プロファイルを自動計算・書き込み",
    },
    "buffer-queue": {
        "table": "BUFFER_QUEUE",
        "cli": ["`config interface buffer queue set <port> <q-range> <profile>`", "`config interface buffer queue remove <port> <q-range>`"],
        "cli_file": "sonic-utilities/config/main.py (buffer グループ)",
        "minigraph": True,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`qos_config.j2` から QoS マッピングと共に生成",
        "hard_coded": None,
        "runtime_injection": None,
    },
    "community-set": {
        "table": "COMMUNITY_SET",
        "cli": ["`config route-map community-set add <name> <match-action> <community-list>`", "`config route-map community-set delete <name>`"],
        "cli_file": "sonic-utilities/config/main.py (route-map グループ)",
        "minigraph": False,
        "rest_gnmi": "sonic-mgmt-common OpenConfig routing policy 経由",
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "console-port": {
        "table": "CONSOLE_PORT",
        "cli": ["`config console add/del <port>`", "`config console connect <port>`"],
        "cli_file": "sonic-utilities/config/console.py",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "copp-group": {
        "table": "COPP_GROUP",
        "cli": ["`config copp add/del <group-name> ...`"],
        "cli_file": "sonic-utilities/config/main.py (copp グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "プラットフォーム提供の `copp_cfg.j2` が `sonic-cfggen` 経由でデフォルト COPP グループを生成",
        "hard_coded": None,
        "runtime_injection": None,
    },
    "copp-trap": {
        "table": "COPP_TRAP",
        "cli": ["`config copp trap add/del <trap-name> ...`"],
        "cli_file": "sonic-utilities/config/main.py (copp グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`copp_cfg.j2` が `sonic-cfggen` 経由でデフォルトトラップセットを生成",
        "hard_coded": None,
        "runtime_injection": None,
    },
    "crm": {
        "table": "CRM",
        "cli": ["`config crm thresholds <resource> type/low/high <value>`"],
        "cli_file": "sonic-utilities/config/main.py (crm グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`init_cfg.json.j2` にデフォルト CRM 閾値が定義されている (`CRM.Config.*`)",
        "hard_coded": None,
        "runtime_injection": None,
    },
    "debug-counter": {
        "table": "DEBUG_COUNTER",
        "cli": ["`config debug-counter add/del <name>`", "`config debug-counter add-reasons/remove-reasons <name> <reason>`"],
        "cli_file": "sonic-utilities/config/main.py (debug-counter グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "default-lossless-buffer-parameter": {
        "table": "DEFAULT_LOSSLESS_BUFFER_PARAMETER",
        "cli": None,
        "cli_file": None,
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`buffers_config.j2` がプラットフォーム別 `default_lossless_buffer_parameter` 値を生成。通常は手動変更不可",
        "hard_coded": "Dynamic buffer モデルの `sonic_platform_thrift` または `buffermgrd` が速度ごとのデフォルト値をハードコードして設定",
        "runtime_injection": None,
    },
    "device-neighbor-metadata": {
        "table": "DEVICE_NEIGHBOR_METADATA",
        "cli": None,
        "cli_file": None,
        "minigraph": True,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`sonic-cfggen -m` で minigraph.xml を処理して生成。`device_metadata.py` の `parse_device_desc_xml()` が各NeighborDevice のメタを読み出す",
        "hard_coded": None,
        "runtime_injection": None,
    },
    "device-neighbor": {
        "table": "DEVICE_NEIGHBOR",
        "cli": None,
        "cli_file": None,
        "minigraph": True,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`sonic-cfggen -m` で minigraph.xml を処理して隣接デバイス情報を生成",
        "hard_coded": None,
        "runtime_injection": None,
    },
    "device-runtime-metadata": {
        "table": "DEVICE_RUNTIME_METADATA",
        "cli": None,
        "cli_file": None,
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": "起動時に `sonic-cfggen` や `platform_env.conf` スクリプトが実行環境情報 (platform name, HW SKU 等) を注入する。YANG モデルなし・スキーマレス",
    },
    "dhcp-relay": {
        "table": "DHCP_RELAY",
        "cli": ["`config interface dhcp-relay add/del <vlan> <server-ip>`"],
        "cli_file": "sonic-utilities/config/vlan.py",
        "minigraph": True,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "dhcp-server-ipv4": {
        "table": "DHCP_SERVER_IPV4",
        "cli": ["`config dhcp-server ipv4 add/del <gateway>`", "`config dhcp-server ipv4 enable/disable <gateway>`"],
        "cli_file": "sonic-utilities/config/main.py (dhcp-server グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "dhcpv4-relay": {
        "table": "DHCPV4_RELAY",
        "cli": ["`config dhcpv4-relay add/del <vlan> <server-ip>`"],
        "cli_file": "sonic-utilities/config/main.py (dhcpv4-relay グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "dot1p-to-tc-map": {
        "table": "DOT1P_TO_TC_MAP",
        "cli": ["`config qos map dot1p-tc add/del <map-name> <dot1p> <tc>`"],
        "cli_file": "sonic-utilities/config/main.py (qos グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`qos_config.j2` から platform 別 QoS マップが生成される場合あり",
        "hard_coded": None,
        "runtime_injection": None,
    },
    "dscp-to-tc-map": {
        "table": "DSCP_TO_TC_MAP",
        "cli": ["`config qos map dscp-tc add/del <map-name> <dscp> <tc>`"],
        "cli_file": "sonic-utilities/config/main.py (qos グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`qos_config.j2` から platform 別 DSCP→TC マップが生成される場合あり",
        "hard_coded": None,
        "runtime_injection": None,
    },
    "fabric-monitor": {
        "table": "FABRIC_MONITOR",
        "cli": ["`config fabric monitoring error-threshold <val>`", "`config fabric monitoring poll-interval <secs>`"],
        "cli_file": "sonic-utilities/config/main.py (fabric グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "fabric-port": {
        "table": "FABRIC_PORT",
        "cli": ["`config fabric port status enable/disable <port>`"],
        "cli_file": "sonic-utilities/config/main.py (fabric グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "プラットフォーム `platform.json` から fabric ポート一覧が `sonic-cfggen` 経由で生成",
        "hard_coded": None,
        "runtime_injection": None,
    },
    "feature": {
        "table": "FEATURE",
        "cli": ["`config feature state <feature> enabled/disabled`", "`config feature autorestart <feature> enabled/disabled`"],
        "cli_file": "sonic-utilities/config/feature.py",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`init_cfg.json.j2` の `FEATURE` セクションでプラットフォーム対応フィーチャーがデフォルト値付きで注入",
        "hard_coded": None,
        "runtime_injection": "`featured` デーモンが systemd サービス状態を監視し FEATURE テーブルと同期",
    },
    "fg-nhg": {
        "table": "FG_NHG",
        "cli": ["`config fg-nhg add/del <nhg-name> --bucket-size <n> --match-mode <mode>`"],
        "cli_file": "sonic-utilities/config/plugins/sonic-fine-grained-ecmp_yang.py",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "fips": {
        "table": "FIPS",
        "cli": ["`config fips enable/disable`", "`config fips enforce`"],
        "cli_file": "sonic-utilities/config/main.py (fips グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": "`hostcfgd` の FIPS ハンドラが kernel モジュール設定と同期",
    },
    "flex-counter-table": {
        "table": "FLEX_COUNTER_TABLE",
        "cli": ["`config flex-counter enable/disable <group>`", "`config flex-counter interval <group> <msec>`"],
        "cli_file": "sonic-utilities/config/main.py (flex-counter グループ)",
        "minigraph": True,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`init_cfg.json.j2` に `FLEX_COUNTER_TABLE` デフォルト (各グループの `FLEX_COUNTER_STATUS: enable`) が定義。minigraph 生成時は mgmt 系グループが `disable` に変更",
        "hard_coded": None,
        "runtime_injection": None,
    },
    "heartbeat": {
        "table": "HEARTBEAT",
        "cli": None,
        "cli_file": None,
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": "`system-health` / `watchdog` 系デーモンが定期的に heartbeat タイムスタンプを書き込む。CLI 書き込みパスなし",
    },
    "interface": {
        "table": "INTERFACE",
        "cli": ["`config interface ip add/remove <port> <ip/prefix>`", "`config interface vrf bind/unbind <port> <vrf>`"],
        "cli_file": "sonic-utilities/config/main.py (interface グループ)",
        "minigraph": True,
        "rest_gnmi": "sonic-mgmt-common OpenConfig interfaces 経由 (xfmr_intf.go)",
        "db_migrator": None,
        "build_time": "`sonic-cfggen -m` で minigraph から L3 インタフェース IP を生成",
        "hard_coded": None,
        "runtime_injection": None,
    },
    "kdump": {
        "table": "KDUMP",
        "cli": ["`config kdump enable/disable`", "`config kdump memory <size>`", "`config kdump num-dumps <n>`"],
        "cli_file": "sonic-utilities/config/kdump.py",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`init_cfg.json.j2` の `KDUMP` セクションでデフォルト値 (`enabled: false`, `memory: 0M-2G:256M,2G-4G:320M,...`) が注入",
        "hard_coded": None,
        "runtime_injection": "`hostcfgd` の kdump ハンドラが kernel crashkernel 設定と同期",
    },
    "kubernetes-master": {
        "table": "KUBERNETES_MASTER",
        "cli": ["`config kubernetes server ip <ip>`", "`config kubernetes server enable/disable`"],
        "cli_file": "sonic-utilities/config/main.py (kubernetes グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": "`kubemgrd` が Kubernetes 接続状態を CONFIG_DB と同期",
    },
    "ldap-server": {
        "table": "LDAP_SERVER",
        "cli": ["`config ldap add/del <server>`", "`config ldap global <params>`"],
        "cli_file": "sonic-utilities/config/aaa.py (ldap コマンド群)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "lldp-port": {
        "table": "LLDP_PORT",
        "cli": ["`config lldp <port> enable/disable`", "`config lldp portdesc <port> <description>`", "`config lldp portid-subtype <port> <subtype>`"],
        "cli_file": "sonic-utilities/config/main.py (lldp グループ)",
        "minigraph": True,
        "rest_gnmi": "sonic-mgmt-common lldp_app.go 経由 (OpenConfig LLDP)",
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "lldp": {
        "table": "LLDP",
        "cli": ["`config lldp global txinterval <n>`", "`config lldp global sysdescr <desc>`", "`config lldp global sysdescr-type <type>`"],
        "cli_file": "sonic-utilities/config/main.py (lldp グループ)",
        "minigraph": True,
        "rest_gnmi": "sonic-mgmt-common lldp_app.go 経由 (OpenConfig LLDP)",
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "loopback-interface": {
        "table": "LOOPBACK_INTERFACE",
        "cli": ["`config interface ip add/remove Loopback<N> <ip/prefix>`"],
        "cli_file": "sonic-utilities/config/main.py (interface グループ)",
        "minigraph": True,
        "rest_gnmi": "sonic-mgmt-common OpenConfig interfaces 経由",
        "db_migrator": None,
        "build_time": "`sonic-cfggen -m` で minigraph から Loopback0 IP 等を生成",
        "hard_coded": None,
        "runtime_injection": None,
    },
    "lossless-traffic-pattern": {
        "table": "LOSSLESS_TRAFFIC_PATTERN",
        "cli": ["`config buffer lossless-traffic-pattern <mtu> <small_packet_percentage>`"],
        "cli_file": "sonic-utilities/config/main.py (buffer グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`buffers_config.j2` からデフォルト MTU / small_packet_percentage が生成される場合あり",
        "hard_coded": None,
        "runtime_injection": "`buffermgrd` がこのテーブルを読み取り Lossless バッファプロファイルを動的に算出",
    },
    "macsec-profile": {
        "table": "MACSEC_PROFILE",
        "cli": ["`config macsec profile add/del <name> --priority <n> --cipher_suite <suite> --primary_cak <key> --primary_ckn <ckn>`"],
        "cli_file": "sonic-utilities/config/main.py (macsec グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "map-pfc-priority-to-queue": {
        "table": "MAP_PFC_PRIORITY_TO_QUEUE",
        "cli": ["`config qos map pfc-priority-queue add/del <map-name> <pfc> <queue>`"],
        "cli_file": "sonic-utilities/config/main.py (qos グループ)",
        "minigraph": False,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`qos_config.j2` から platform 別 PFC→Queue マップが生成",
        "hard_coded": None,
        "runtime_injection": None,
    },
    "mclag-domain": {
        "table": "MCLAG_DOMAIN",
        "cli": ["`config mclag add/del <domain-id> --local_ip <ip> --peer_ip <ip> --peer_link <port>`"],
        "cli_file": "sonic-utilities/config/mclag.py",
        "minigraph": False,
        "rest_gnmi": "sonic-mgmt-common xfmr_mclag.go 経由 (OpenConfig MCLAG)",
        "db_migrator": None,
        "build_time": None,
        "hard_coded": None,
        "runtime_injection": None,
    },
    "mgmt-interface": {
        "table": "MGMT_INTERFACE",
        "cli": ["`config interface ip add/remove eth0 <ip/prefix> <gateway>`"],
        "cli_file": "sonic-utilities/config/main.py (interface グループ)",
        "minigraph": True,
        "rest_gnmi": None,
        "db_migrator": None,
        "build_time": "`sonic-cfggen -m` で minigraph から Management ポートの IP/GW を生成",
        "hard_coded": None,
        "runtime_injection": "`caclmgrd` / `mgmtstatsd` が eth0 の状態変化を反映",
    },
}


def slugify_table(slug):
    """Convert slug to CONFIG_DB table name guess."""
    return slug.upper().replace("-", "_")


def build_entry_points_block(slug, info):
    """Generate the entry-points markdown block."""
    table = info.get("table", slugify_table(slug))
    lines = []
    lines.append(f"## 書き込み入り口 (Direction A)")
    lines.append("")
    lines.append(f"対象テーブル: `{table}`")
    lines.append("")

    # CLI
    lines.append("### CLI")
    cli_cmds = info.get("cli")
    if cli_cmds:
        for cmd in cli_cmds:
            lines.append(f"- {cmd}")
        cli_file = info.get("cli_file")
        if cli_file:
            lines.append(f"  - ソース: `{cli_file}`")
    else:
        lines.append("- なし (CLI 書き込みパスなし)")
    lines.append("")

    # Minigraph
    lines.append("### minigraph / sonic-cfggen")
    if info.get("minigraph"):
        lines.append("- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる")
    else:
        lines.append("- なし")
    lines.append("")

    # REST / gNMI
    lines.append("### REST / gNMI (sonic-mgmt-common)")
    rg = info.get("rest_gnmi")
    if rg:
        lines.append(f"- {rg}")
    else:
        lines.append("- なし (対応 OpenConfig/SONiC YANG transformer なし)")
    lines.append("")

    # db_migrator
    lines.append("### db_migrator")
    dm = info.get("db_migrator")
    if dm:
        lines.append(f"- {dm}")
    else:
        lines.append("- なし")
    lines.append("")

    # Build-time defaults
    lines.append("### ビルド時デフォルト (init_cfg / j2 テンプレート)")
    bt = info.get("build_time")
    if bt:
        lines.append(f"- {bt}")
    else:
        lines.append("- なし")
    lines.append("")

    # Hard-coded defaults
    lines.append("### ハードコードデフォルト")
    hc = info.get("hard_coded")
    if hc:
        lines.append(f"- {hc}")
    else:
        lines.append("- なし")
    lines.append("")

    # Runtime injection
    lines.append("### ランタイム注入 (デーモン自動書き込み)")
    ri = info.get("runtime_injection")
    if ri:
        lines.append(f"- {ri}")
    else:
        lines.append("- なし")
    lines.append("")

    return "\n".join(lines)


def process_slug(slug):
    info = ENTRY_POINTS.get(slug)
    if not info:
        # Fallback for slugs without detailed info
        table = slugify_table(slug)
        info = {
            "table": table,
            "cli": None,
            "cli_file": None,
            "minigraph": False,
            "rest_gnmi": None,
            "db_migrator": None,
            "build_time": None,
            "hard_coded": None,
            "runtime_injection": None,
        }

    block = build_entry_points_block(slug, info)

    # Write intermediate file
    intermediate_path = os.path.join(INTERMEDIATE_DIR, f"{slug}-entry-points.md")
    with open(intermediate_path, "w") as f:
        f.write(f"# {slug} — Direction A 書き込み入り口\n\n")
        f.write(block)

    # Append to docs page
    docs_path = os.path.join(DOCS_DIR, f"{slug}.md")
    if not os.path.exists(docs_path):
        print(f"  SKIP (no docs file): {docs_path}")
        return False

    with open(docs_path, "r") as f:
        content = f.read()

    # Check if entry-points block already exists
    if "<!-- entry-points -->" in content:
        print(f"  SKIP (already has entry-points): {slug}")
        return False

    # Append before glossary-links-injected tag or at end
    entry_block = f"\n<!-- entry-points -->\n{block}<!-- /entry-points -->\n"

    if "<!-- glossary-links-injected" in content:
        # Insert before glossary marker
        content = content.replace(
            "\n<!-- glossary-links-injected",
            entry_block + "\n<!-- glossary-links-injected",
            1
        )
    else:
        content = content.rstrip() + entry_block

    with open(docs_path, "w") as f:
        f.write(content)

    print(f"  OK: {slug}")
    return True


def main():
    import json

    with open("/home/coder/sonic-unofficial-docs/meta/cdb-enum-cardinality.json") as f:
        d = json.load(f)

    slugs = [p["slug"] for p in d["tier_low"][:60]]
    print(f"Processing {len(slugs)} slugs...")

    ok = 0
    skip = 0
    for slug in slugs:
        result = process_slug(slug)
        if result:
            ok += 1
        else:
            skip += 1

    print(f"\nDone: {ok} updated, {skip} skipped")


if __name__ == "__main__":
    main()
