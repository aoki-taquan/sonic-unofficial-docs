# DHCPV4_RELAY — Phase C 暗黙参照スキャンノート

対象テーブル: `DHCPV4_RELAY`
Consumer: `sonic-dhcpv4-relay` (`dhcp4relay` / `dhcp4relay_mgr`)
スキャン範囲: `dhcp4relay/src/dhcp4relay_mgr.cpp` 全行、`dhcp4relay/src/dhcp4relay.cpp` の関連箇所

---

## 検出した暗黙参照テーブル

### 1. CONFIG_DB — subscribe (SubscriberStateTable) で常時監視

| テーブル | 参照箇所 | 用途 | evidence |
|---|---|---|---|
| `INTERFACE` | dhcp4relay_mgr.cpp:58,139-145 | 物理ポート・SVI の IP イベント → `prepare_relay_interface_config()` で giaddr / src IP を更新 | dhcp4relay_mgr.cpp:58,140 |
| `LOOPBACK_INTERFACE` | dhcp4relay_mgr.cpp:59,142-144 | Loopback IP イベント → `source_interface` が Loopback のとき src IP 解決に使用 | dhcp4relay_mgr.cpp:59,143 |
| `PORTCHANNEL_INTERFACE` | dhcp4relay_mgr.cpp:60,145-146 | PortChannel IP イベント → src IP 解決 | dhcp4relay_mgr.cpp:60,145 |
| `DEVICE_METADATA` | dhcp4relay_mgr.cpp:61,159-162 | `subtype` (DualToR / SmartSwitch) / `hostname` / `mac` / `deployment_id` の変化を監視 | dhcp4relay_mgr.cpp:61,159 |
| `VLAN_MEMBER` | dhcp4relay_mgr.cpp:62,162-165 | VLAN メンバ変化 → `prepare_vlan_sockets()` / `prepare_relay_interface_config()` を再実行 | dhcp4relay_mgr.cpp:62,163 |
| `FEATURE` | dhcp4relay_mgr.cpp:63,168-171 | `dhcp_server.state` が `enabled` になると `DHCPV4_RELAY` の watch を停止し `delete_all_relay_configs()` を呼ぶ | dhcp4relay_mgr.cpp:63,169 |
| `VLAN` | dhcp4relay_mgr.cpp:64,171-174 | VLAN 存在チェック — SET 処理前に `vlan_tbl.hget(vlan, "vlanid")` で VLAN が存在しないエントリを skip | dhcp4relay_mgr.cpp:64,735-796 |
| `DHCP_SERVER_IPV4` | dhcp4relay_mgr.cpp:65 | `FEATURE.dhcp_server = enabled` 時に切替わる — relay は config UPDATE ではなく dhcp_server の IP を使うモードに変わる | dhcp4relay_mgr.cpp:65,150-155 |
| `PORT` | dhcp4relay_mgr.cpp:67,174-177 | PortChannel メンバの物理ポート更新 → relay socket / interface mapping を更新 | dhcp4relay_mgr.cpp:67,175 |
| `DPUS` | dhcp4relay_mgr.cpp:68,177-179 | SmartSwitch DPU 構成変化 → midplane socket を再設定 | dhcp4relay_mgr.cpp:68,178 |
| `MID_PLANE_BRIDGE` | dhcp4relay_mgr.cpp:200-244 | SmartSwitch: `DEVICE_METADATA.subtype = SmartSwitch` のとき `MID_PLANE_BRIDGE|GLOBAL.bridge` を direct read で取得 | dhcp4relay_mgr.cpp:201,244 |

### 2. CONFIG_DB — direct read (Table::hget) でイベント処理中に参照

| テーブル | 参照箇所 | 用途 | evidence |
|---|---|---|---|
| `VLAN_INTERFACE` (`CFG_VLAN_INTF_TABLE_NAME`) | dhcp4relay_mgr.cpp:425-430 | `DHCPV4_RELAY` SET 処理時に `server_vrf` 未設定なら `VLAN_INTERFACE[vlan].vrf_name` を読んで `relay_msg->vrf` を決定。空なら `"default"` を使用 | dhcp4relay_mgr.cpp:424-430 |
| `VLAN_INTERFACE` | dhcp4relay.cpp:885-892 | VLAN_MEMBER UPDATE 処理時にも同 VRF 解決ロジックを実行 | dhcp4relay.cpp:888-892 |
| `DHCPV4_RELAY` | dhcp4relay.cpp:1380-1385 | `VLAN_INTERFACE_UPDATE` 受信時に `SERVER_VRF_FIELD` を direct read して、`server_vrf` が空の場合だけ VRF ソケットを更新 | dhcp4relay.cpp:1378-1390 |
| `VLAN` | dhcp4relay_mgr.cpp:735-796 | VLAN table direct read で `vlanid` フィールドの有無を確認。VLAN が存在しない場合は relay config を skip | dhcp4relay_mgr.cpp:735,796 |

### 3. STATE_DB — subscribe (SubscriberStateTable) で監視

| テーブル | 参照箇所 | 用途 | evidence |
|---|---|---|---|
| `DHCP_SERVER_IPV4_SERVER_IP` | dhcp4relay_mgr.cpp:66,763-766 | `dhcp_server` モード時にサーバ IP が STATE_DB に登録されるのを監視し、relay の転送先 IP として使用 | dhcp4relay_mgr.cpp:66,763 |
| `INTERFACE_TABLE` | dhcp4relay_mgr.cpp:69 | STATE_DB の INTERFACE テーブル — IP アドレスの active/inactive 状態を監視して socket bind を再試行 | dhcp4relay_mgr.cpp:69 |

---

## 依存関係サマリ

| # | 依存テーブル | 方向 | 参照理由 |
|---|---|---|---|
| 1 | `VLAN_INTERFACE` | direct read (SET 処理時) | client VRF の解決 (`server_vrf` 未設定フォールバック) |
| 2 | `DEVICE_METADATA` | subscribe | DualToR / SmartSwitch 判定・hostname・MAC 取得 |
| 3 | `FEATURE` | subscribe | `dhcp_server.state` が enabled になったとき relay watch を無効化 |
| 4 | `VLAN` | subscribe + direct read | VLAN 存在チェック (vlanid フィールド) |
| 5 | `VLAN_MEMBER` | subscribe | VLAN メンバ変化で socket と src IP を再構築 |
| 6 | `INTERFACE` / `LOOPBACK_INTERFACE` / `PORTCHANNEL_INTERFACE` | subscribe | `source_interface` / giaddr の IP 解決 |
| 7 | `DHCP_SERVER_IPV4` | subscribe (条件付き) | `dhcp_server` 機能 ON 時の転送先 IP ソース |
| 8 | `MID_PLANE_BRIDGE` | direct read (SmartSwitch のみ) | midplane bridge 名の取得 |
| 9 | STATE_DB `DHCP_SERVER_IPV4_SERVER_IP` | subscribe (条件付き) | `dhcp_server` モードのサーバ IP 取得 |
