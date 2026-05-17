# control-plane-acl — Phase H: プラットフォーム差異 (中間トレース)

調査対象: `sonic-host-services/scripts/caclmgrd`

## 調査手順

1. `device_info.is_chassis()`, `device_info.is_smartswitch()`, `device_info.is_multi_npu()`, `DualToR` フラグを grep
2. 各分岐の効果を抽出
3. `orchdaemon.cpp` の `AclOrch` 登録コードを確認

## 抽出結果

### is_multi_npu() (multi-ASIC プラットフォーム)

- `__init__()` L147: `is_multi_npu()` == True なら `SonicDBConfig.load_sonic_global_db_config()` でグローバル DB 設定をロード
- `__init__()` L169-190: front_ns / back_ns / fabric_ns を全列挙し、各 namespace の ConfigDB コネクタを確立。`update_docker_mgmt_ip_acl(namespace)` で namespace ごとの docker mgmt IP を取得
- `run()` L1124: `is_multi_npu()` == True なら `SonicDBConfig.initializeGlobalConfig()` でグローバル設定を初期化
- `run()` L1169-1184: 全 namespace (DEFAULT + front_ns + back_ns) で `update_control_plane_acls()` を実行し、その後 `subscribe_acl_table` / `subscribe_acl_rule_table` を namespace ごとに購読
- `generate_fwd_traffic_from_namespace_to_host_commands()` L476-516: namespace != '' のとき SNAT/DNAT ルールを生成（front panel → host NAT）。`multi_asic_ns_to_host_fwd` が True なサービス (SNMP, SSH) のみ対象

### DualToR (subtype=DualToR)

- `__init__()` L165-167: DEVICE_METADATA.localhost.subtype == 'DualToR' のとき `self.DualToR = True`
- `run()` L1143-1154: DualToR == True のとき `subscribe_mux_cable` (STATE_DB:MUX_CABLE_TABLE) / `subscribe_dhcp_packet_mark` を購読し、`setup_dhcp_chain(namespace)` で DHCP カスタムチェーンを作成
- `get_acl_rules_and_translate_to_iptables_commands()` L644: DualToR == True のとき chain flush 対象から "DHCP" を除外（`get_chain_list(exclude_list=["DHCP"])`）
- `get_acl_rules_and_translate_to_iptables_commands()` L707-708: DualToR == True のとき `iptables -A INPUT -p udp --dport 67 -j DHCP` を追加
- `update_control_plane_nat_acls()` L935-940: DualToR == True のとき `generate_fwd_traffic_from_host_to_soc()` + `generate_block_bgp_loopback1()` を実行

### is_chassis() (ラインカードシャーシ)

- `generate_allow_internal_chasis_midplane_traffic()` L358-363: `is_chassis() and not namespace` のとき midplane インターフェース (eth1-midplane) の IP を取得し、自己 IP → 自己 IP の INPUT ACCEPT ルールと、midplane デバイス全 INPUT ACCEPT ルールを追加

### is_smartswitch() (SmartSwitch)

- `generate_allow_internal_chasis_midplane_traffic()` L365-368: `is_smartswitch()` のとき `MID_PLANE_BRIDGE|GLOBAL|ip_prefix` から midplane bridge IP を取得し、その IP への INPUT ACCEPT ルールを追加（fallback: `169.254.200.254`）

### AclOrch: プラットフォーム非依存

- `orchdaemon.cpp:533-534`: `gAclOrch = new AclOrch(...)` はプラットフォーム条件なしで無条件に登録される
- CTRLPLANE ACL の `m_ctrlAclTables` 登録も platform 非依存

## 結論

| プラットフォーム | 影響範囲 | 条件ソース |
|---|---|---|
| multi-ASIC | 全 namespace で独立した iptables ルールセット + NAT ルール | `device_info.is_multi_npu()` |
| DualToR | DHCP カスタムチェーン + MUX_CABLE_TABLE 購読 + SoC 向け NAT + BGP Loopback1 drop | `DEVICE_METADATA.localhost.subtype` |
| Chassis (ラインカード) | midplane (eth1-midplane) の INPUT ACCEPT ルール追加 | `device_info.is_chassis()` |
| SmartSwitch | MID_PLANE_BRIDGE bridge IP への INPUT ACCEPT ルール追加 | `device_info.is_smartswitch()` |
| 単一 ASIC 標準スイッチ | 上記いずれも非適用。デフォルト namespace のみ | — |
| orchagent AclOrch | platform 非依存で常時登録 | `orchdaemon.cpp:533` |
