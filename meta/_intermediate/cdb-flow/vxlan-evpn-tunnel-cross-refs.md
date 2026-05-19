# EVPN DIP トンネル (vxlan-evpn-tunnel) — Phase C 暗黙参照抽出ノート

ソース: `sonic-swss/orchagent/vxlanorch.cpp`, `sonic-swss/orchagent/vxlanorch.h`
対象ページ: `docs/reference/config-db/vxlan-evpn-tunnel.md`
抽出日: 2026-05-19

## 対象テーブルの性質

`VXLAN_EVPN_TUNNEL` というテーブルは CONFIG_DB に存在しない。
本ページが扱うのは `orchagent` の `VxlanTunnelOrch::createDynamicDIPTunnel()` が動的生成する per-remote-VTEP P2P トンネルである。
YANG leafref も CONFIG_DB テーブルエントリも存在しないため、全依存は実装レベルの暗黙参照となる。

## YANG leafref 状況

`sonic-vxlan.yang` 内の leafref は以下の 2 点のみ:

| テーブル | フィールド | leafref 先 |
|---------|-----------|-----------|
| `VXLAN_TUNNEL_MAP` | `name` | `VXLAN_TUNNEL_LIST/svxlan:name` (`sonic-vxlan.yang:75-76`) |
| `VXLAN_EVPN_NVO` | `source_vtep` | `VXLAN_TUNNEL_LIST/svxlan:name` (`sonic-vxlan.yang:123-124`) |

EVPN DIP トンネル (動的生成) に対する YANG leafref は存在しない。
`VXLAN_TUNNEL_MAP.name` への leafref は `// type leafref` としてコメントアウト (`sonic-vxlan.yang:89-90`) されており、VLAN テーブルへの leafref は現状未実施。

## 暗黙参照 (実装レベル)

### 1. VXLAN_EVPN_NVO (EvpnNvoOrch 経由 — 最強制)

- **参照先テーブル**: `CONFIG_DB VXLAN_EVPN_NVO`
- **参照方向**: 読み取り (EvpnNvoOrch インスタンス + `getEVPNVtep()` 経由)
- **条件**: 常時。DIP トンネル生成の第一ガード
- **意味**: `VxlanTunnelOrch::addTunnelUser()` (`vxlanorch.cpp:1685`) が `evpn_orch->getEVPNVtep()` を呼び、返値が NULL (VXLAN_EVPN_NVO 未設定) なら `SWSS_LOG_WARN("Unable to find EVPN VTEP")` を出力して即 `return false`。
  VTEP ポインタが非 NULL でも `isActive()` が false の場合は `SWSS_LOG_WARN("VTEP not yet active")` で `return false`。
- **evidence**: `vxlanorch.cpp:1685-1699`

### 2. VXLAN_TUNNEL (VTEP エントリ — source_vtep_ptr の active 状態)

- **参照先テーブル**: `CONFIG_DB VXLAN_TUNNEL`
- **参照方向**: 読み取り (VxlanTunnel::isActive() 呼び出し)
- **条件**: VXLAN_EVPN_NVO の source_vtep フィールドが指す VXLAN_TUNNEL エントリが active でなければならない
- **意味**: `VXLAN_EVPN_NVO.source_vtep` の値を `VxlanTunnelOrch::getVxlanTunnel(vtep_name)` で解決し、VTEP が active でないと DIP トンネルは生成されない。YANG では `VXLAN_EVPN_NVO_LIST.source_vtep` が `VXLAN_TUNNEL_LIST.name` を leafref 参照 (`sonic-vxlan.yang:123-124`)。
- **evidence**: `vxlanorch.cpp:1694-1699`

### 3. VXLAN_TUNNEL_MAP (VNI-VLAN マップ — 処理続行の前提)

- **参照先テーブル**: `CONFIG_DB VXLAN_TUNNEL_MAP`
- **参照方向**: 読み取り (`VxlanTunnelMapOrch::isVniVlanMapExists()`)
- **条件**: `EVPN_REMOTE_VNI_TABLE` (APP_DB) 処理時に必須
- **意味**: `EvpnRemoteVnip2pOrch::addOperation()` (`vxlanorch.cpp:2490-2494`) が `vxlan_tun_map_orch->isVniVlanMapExists(vni_id, ...)` を呼び、VNI-VLAN マップが未存在なら `SWSS_LOG_WARN("Vxlan tunnel map is not created for vni:%d")` を出力して `return false`。コメントには `"Remote end point can be added only after local VLAN to VNI map gets created"` と明記されている。
  YANG では `VXLAN_TUNNEL_MAP.name` → `VXLAN_TUNNEL.name` の leafref はあるが、VLAN への leafref はコメントアウトされている (`sonic-vxlan.yang:89-90`)。
- **evidence**: `vxlanorch.cpp:2483-2494`

### 4. VLAN (PortsOrch::getVlanByVlanId — VLAN 存在確認)

- **参照先テーブル**: `CONFIG_DB VLAN`
- **参照方向**: 読み取り (`gPortsOrch->getVlanByVlanId()`)
- **条件**: `EVPN_REMOTE_VNI_TABLE` 処理時に必須
- **意味**: `EvpnRemoteVnip2pOrch::addOperation()` (`vxlanorch.cpp:2483-2487`) が `gPortsOrch->getVlanByVlanId(vlan_id, vlanPort)` を呼び、VLAN が存在しない場合は `SWSS_LOG_WARN("Vxlan tunnel map vlan id doesn't exist: %d")` を出力して `return false`。DIP トンネルを VLAN flood domain に参加させる `addVlanMember()` (`vxlanorch.cpp:2525`) の前提。
- **evidence**: `vxlanorch.cpp:2483-2487`, `vxlanorch.cpp:2525`

### 5. EVPN_REMOTE_VNI_TABLE (APP_DB — DIP トンネル生成トリガ)

- **参照先テーブル**: `APP_DB EVPN_REMOTE_VNI_TABLE`
- **参照方向**: 読み取り (EvpnRemoteVnip2pOrch subscribe)
- **条件**: BGP EVPN がリモート VTEP を学習した際
- **意味**: `fpmsyncd` が BGP EVPN type-2/3 を APP_DB `EVPN_REMOTE_VNI_TABLE` に書き込み、`EvpnRemoteVnip2pOrch` が購読して `addTunnelUser()` を呼ぶことで DIP トンネルが生成される。このテーブルは CONFIG_DB ではなく APP_DB 経由のフロー。
- **evidence**: `vxlanorch.cpp:2447-2520`

### 6. STATE_DB VXLAN_TUNNEL_TABLE (DIP トンネルの書き込み先)

- **参照先テーブル**: `STATE_DB VXLAN_TUNNEL_TABLE`
- **参照方向**: 書き込み (`m_stateVxlanTable.set()`)
- **条件**: DIP トンネル作成・削除時
- **意味**: DIP トンネル生成後に `addRemoveStateTableEntry()` が `STATE_VXLAN_TUNNEL_TABLE_NAME` (`m_stateVxlanTable`) に `src_ip`, `dst_ip`, `tnl_src="EVPN"`, `operstatus` を書き込む (`vxlanorch.cpp:1910`, `vxlanorch.cpp:1940-1947`)。削除時は `m_stateVxlanTable.del(tunnel_name)` (`vxlanorch.cpp:1953`)。
- **evidence**: `vxlanorch.cpp:1910`, `vxlanorch.cpp:1928-1953`

## 参照関係サマリ

```
EVPN DIP トンネル (動的生成)
  (書き手: orchagent VxlanTunnelOrch のみ)

入力依存 (暗黙参照):
  ├─ [暗黙・必須] CONFIG_DB VXLAN_EVPN_NVO        (EVPN VTEP ポインタ; NULL → silent drop)
  ├─ [暗黙・必須] CONFIG_DB VXLAN_TUNNEL           (VTEP active 状態; false → silent drop)
  │     ↑ YANG leafref: VXLAN_EVPN_NVO.source_vtep → VXLAN_TUNNEL.name
  ├─ [暗黙・必須] CONFIG_DB VXLAN_TUNNEL_MAP       (VNI-VLAN マップ; 未存在 → return false)
  │     ↑ YANG leafref: VXLAN_TUNNEL_MAP.name → VXLAN_TUNNEL.name (VLAN への leafref はコメントアウト)
  ├─ [暗黙・必須] CONFIG_DB VLAN (PortsOrch)        (VLAN 存在; 未存在 → return false)
  ├─ [暗黙] APP_DB EVPN_REMOTE_VNI_TABLE           (DIP トンネル生成トリガ; fpmsyncd が書き込み)
  └─ [書き込み先] STATE_DB VXLAN_TUNNEL_TABLE      (DIP トンネルのオペレーショナル状態)
```

## evidence

- `vxlanorch.cpp:1685-1699` (addTunnelUser — EVPN VTEP NULL / not active ガード)
- `vxlanorch.cpp:2447-2520` (EvpnRemoteVnip2pOrch::addOperation — 全依存チェック連鎖)
- `vxlanorch.cpp:2483-2494` (VLAN存在確認 + VNI-VLAN マップ存在確認)
- `vxlanorch.cpp:2516` (addTunnelUser 呼び出し)
- `vxlanorch.cpp:2525-2527` (addVlanMember — VLAN flood domain 参加)
- `vxlanorch.cpp:1910`, `vxlanorch.cpp:1928-1953` (STATE_DB VXLAN_TUNNEL_TABLE への書き込み / 削除)
- `sonic-vxlan.yang:75-76` (VXLAN_TUNNEL_MAP.name → VXLAN_TUNNEL leafref)
- `sonic-vxlan.yang:89-90` (VLAN leafref コメントアウト)
- `sonic-vxlan.yang:123-124` (VXLAN_EVPN_NVO.source_vtep → VXLAN_TUNNEL leafref)
