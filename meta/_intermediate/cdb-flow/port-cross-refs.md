# PORT 暗黙参照調査 (Phase C)

対象ページ: `docs/reference/config-db/port.md`
調査日: 2026-05-15

## 調査方法

1. YANG leafref 網羅: `sonic-buildimage/src/sonic-yang-models/yang-models/` 全 yang ファイルで `PORT_LIST` への leafref path を grep
2. orchagent コード精読: `portsorch.cpp` の `increasePortRefCount` / `decreasePortRefCount` 呼び出し元を追跡
3. macsecmgr: `macsecmgr.cpp` で `CFG_PORT_TABLE_NAME` 購読ロジックを確認
4. bufferorch.cpp の `isPortReady` / `increasePortRefCount` 呼び出し確認

---

## 1. YANG leafref (PORT.name を参照するテーブル)

以下のテーブルが `sonic-port/PORT/PORT_LIST/name` を leafref で参照する。
PORT エントリが存在しないとこれらのテーブルへの書き込みが YANG バリデーション失敗になる。

| 参照元テーブル | YANG ファイル |
|---|---|
| `VLAN_MEMBER` | sonic-vlan.yang:292 |
| `PORTCHANNEL_MEMBER` | sonic-portchannel.yang:151 |
| `INTERFACE` (INTERFACE_LIST / INTERFACE_IPPREFIX_LIST) | sonic-interface.yang:58,128 |
| `BUFFER_PG` | sonic-buffer-pg.yang:43 |
| `BUFFER_QUEUE` | sonic-buffer-queue.yang:51 |
| `BUFFER_PORT_INGRESS_PROFILE_LIST` | sonic-buffer-port-ingress-profile-list.yang:41 |
| `BUFFER_PORT_EGRESS_PROFILE_LIST` | sonic-buffer-port-egress-profile-list.yang:41 |
| `PORT_QOS_MAP` | sonic-port-qos-map.yang:78 |
| `QUEUE` | sonic-queue.yang:67 |
| `CABLE_LENGTH` | sonic-cable-length.yang:47 |
| `PFCWD` | sonic-pfcwd.yang:38 |
| `LLDP_PORT_TABLE` | sonic-lldp.yang:109 |
| `MUX_CABLE` | sonic-mux-cable.yang:38 |
| `MIRROR_SESSION` (dst_port) | sonic-mirror-session.yang:149 |
| `SFLOW_SESSION` | sonic-sflow.yang:110,169 |
| `BGP_NEIGHBOR` | sonic-bgp-neighbor.yang:85 |
| `BGP_PEER_RANGE` | sonic-bgp-common.yang:220 |
| `NEIGH` | sonic-neigh.yang:48 |
| `DEVICE_NEIGHBOR` | sonic-device_neighbor.yang:55 |
| `MCLAG_INTF` | sonic-mclag.yang:66 |
| `PBH_RULE` | sonic-pbh.yang:246 |
| `STORM_CONTROL` | sonic-storm-control.yang:41 |
| `FINE_GRAINED_ECMP` | sonic-fine-grained-ecmp.yang:173 |
| `DHCPV4_RELAY` | sonic-dhcpv4-relay.yang:83 |
| `DHCP_SERVER_IPV4` | sonic-dhcp-server-ipv4.yang:226 |
| `ROUTE_MAP` | sonic-route-map.yang:51,207 |
| `HIGH_FREQUENCY_TELEMETRY` | sonic-high-frequency-telemetry.yang:96 |
| `RADIUS_SERVER` | sonic-system-radius.yang:186 |
| `TACACS_SERVER` | sonic-system-tacacs.yang:166 |
| `NTP_SERVER` | sonic-ntp.yang:98 |

---

## 2. orchagent コード上の暗黙参照 (increasePortRefCount)

`m_port_ref_count` は PORT DEL の先行依存を強制する仕組み。
以下のコンポーネントが PORT の ref_count を保持する:

| 呼び出し元ファイル | テーブル | 備考 |
|---|---|---|
| `intfsorch.cpp:498` | `INTERFACE` | L3 IP 設定時に ref_count++ |
| `bufferorch.cpp:1175` | `BUFFER_PG` | PG 設定時に ref_count++ |
| `bufferorch.cpp:1546` | `BUFFER_QUEUE` | Queue 設定時に ref_count++ |
| `portsorch.cpp:2071` | sub-interface | sub-interface 作成時に親 port の ref_count++ |
| `portsorch.cpp:2943` | VLAN_MEMBER (bridge port) | bridge_port 作成時に ref_count++ |
| `portsorch.cpp:8205` | LAG member | LAG メンバ追加時に ref_count++ |
| `p4orch/router_interface_manager.cpp:354` | P4 Router Interface | P4 RIF 作成時に ref_count++ |
| `p4orch/acl_rule_manager.cpp:2077,2081` | P4 ACL Rule | port bind 時に ref_count++ |
| `p4orch/l3_admit_manager.cpp:283` | P4 L3 Admit | L3 admit 設定時に ref_count++ |
| `p4orch/mirror_session_manager.cpp:387` | P4 Mirror Session | ミラーセッション設定時に ref_count++ |
| `p4orch/l3_multicast_manager.cpp:1844` | P4 L3 Multicast | マルチキャストレプリカ設定時に ref_count++ |

---

## 3. macsecmgrd の暗黙参照

`macsecmgr.cpp` が `CFG_PORT_TABLE_NAME`（= `PORT`）を直接 SET/DEL で購読する:

```
{ CFG_PORT_TABLE_NAME, SET_COMMAND } → MACsecMgr::enableMACsec
{ CFG_PORT_TABLE_NAME, DEL_COMMAND } → MACsecMgr::disableMACsec
```

`enableMACsec` は `PORT` エントリの `macsec` フィールドを読み取り、対応する `MACSEC_PROFILE` を参照して `wpa_supplicant` プロセスを起動する。
`MACSEC_PROFILE` エントリが存在しない場合は `enableMACsec` が早期 return する。

証跡: `macsecmgr.cpp:296-299`, `macsecmgr.cpp:480`, `macsecmgr.cpp:543-557`

---

## 4. PORT DEL の削除順制約 (ref_count)

PORT DEL が ref_count > 0 の場合は `SWSS_LOG_WARN` を出して削除を拒否する (`portsorch.cpp:5649-5651`)。
以下の順序で先行削除が必要:

1. `VLAN_MEMBER` DEL (bridge_port oid 解放)
2. `PORTCHANNEL_MEMBER` DEL (LAG member 解放)
3. `INTERFACE` DEL (intfsorch が ref_count--)
4. `BUFFER_PG` / `BUFFER_QUEUE` DEL (bufferorch が ref_count--)
5. 最後に `PORT` DEL

`PORT_SERDES` は `removePort()` 内部で自動削除 (`portsorch.cpp:1526`)。

---

## 5. 暗黙的な runtime 参照 (leafref 外)

| 参照先 | 方向 | 機構 | 備考 |
|---|---|---|---|
| `MACSEC_PROFILE` | PORT → | macsecmgrd: PORT.macsec フィールドがプロファイル名を参照。wpa_supplicant 起動 | leafref で強制。MACSEC_PROFILE が存在しないと enableMACsec が silent return |
| `BUFFER_PG` / `BUFFER_QUEUE` | PORT ← | bufferorch が isPortReady() で PORT の準備完了を待機 | BUFFER 系テーブルの PORT_KEY と PORT エントリが一致している必要あり |
| `MUX_CABLE` | PORT ← / → | linkmgrd が PORT.mux_cable=true を検知。MuxOrch に通知 | minigraph.py が MUX_CABLE エントリ存在時に PORT.mux_cable="true" を派生 |
| `ACL_TABLE` (port bind) | PORT ← | aclorch が PORT を bind 対象として参照。createAclTableGroup() 時に PORT SAI oid を取得 | portsorch.cpp:2796-2807 (ACL group on port) |
| `STATE_PORT_TABLE` | PORT → | portsorch が STATE_DB の STATE_PORT_TABLE にポートの oper_status / speed を書き込む | warm reboot 時の引き継ぎに使用 (portsorch.cpp:6609-6648) |
| `PORT_SERDES` | PORT → | PORT DEL 時に自動削除 (portsorch.cpp:1526) | CONFIG_DB の PORT_SERDES エントリが存在する場合は連動削除 |
| `allPortsReady()` | PORT → 他テーブル | PORT 全エントリ初期化完了で VLAN / INTERFACE / LAG / ACL orch がアンブロック | 最後のポートが ready になるまで他テーブルの doTask() は保留される |
| `SFLOW_SESSION` | PORT ← | sfloworch が SFLOW_SESSION に PORT 名で参照エントリを持つ | YANG leafref + runtime sfloworch 購読 |
| `MIRROR_SESSION` (dst_port) | PORT ← | mirrororch が MIRROR_SESSION.dst_port で PORT を参照 | YANG leafref + runtime mirrororch 購読 |

---

## まとめ

PORT テーブルは SONiC CONFIG_DB の根幹テーブルであり:
- **27 テーブル以上** が YANG leafref で PORT.name を参照
- **11 コンポーネント** が orchagent コードレベルで ref_count を保持
- macsecmgrd が PORT テーブルを直接購読する非 orch パターン
- `allPortsReady()` により PORT は他テーブル全体の初期化ゲートになっている

leafref 違反は YANG バリデーション時点で reject されるが、ref_count 違反は runtime SWSS_LOG_WARN のみで silent 失敗になる点に注意。
