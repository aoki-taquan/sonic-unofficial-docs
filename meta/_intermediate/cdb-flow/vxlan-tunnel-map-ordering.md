# VXLAN_TUNNEL_MAP — Phase B 書込み順依存スキャンノート

対象テーブル: `VXLAN_TUNNEL_MAP`
Consumer: `orchagent` / `VxlanTunnelMapOrch`
スキャン範囲: `sonic-swss/orchagent/vxlanorch.cpp` (VxlanTunnelMapOrch::addOperation, delOperation)

---

## 検出した順序依存・タイミング依存

### 1. VXLAN_TUNNEL が先行必須（isTunnelExists チェック）

- `VxlanTunnelMapOrch::addOperation()` (vxlanorch.cpp:2047) は `tunnel_orch->isTunnelExists(tunnel_name)` で親トンネルを確認する。
- VXLAN_TUNNEL が存在しない場合は `SWSS_LOG_WARN("Vxlan tunnel '%s' doesn't exist")` → `return false`（リトライ待ち）。
- **必須順序**: `VXLAN_TUNNEL|<name>` → `VXLAN_TUNNEL_MAP|<name>|<map-name>`
- evidence: `vxlanorch.cpp:2047-2051`

### 2. VLAN が先行必須（getVlanByVlanId チェック）

- `VxlanTunnelMapOrch::addOperation()` (vxlanorch.cpp:2030) は `gPortsOrch->getVlanByVlanId(vlan_id, tempPort)` で VLAN の存在を確認する。
- VLAN が存在しない場合は `SWSS_LOG_WARN("Vxlan tunnel map vlan id doesn't exist: %d")` → `return false`（リトライ待ち）。
- **必須順序**: `VLAN|<id>` → `VXLAN_TUNNEL_MAP|<tunnel>|<map>`
- evidence: `vxlanorch.cpp:2030-2034`

### 3. VXLAN_TUNNEL_MAP 受信が SAI tunnel HW 作成をトリガーする

- `VxlanTunnelMapOrch::addOperation()` (vxlanorch.cpp:2063) は `tunnel_obj->isActive()` が false の場合に `createTunnelHw()` を呼び出す。
- **初回 MAP エントリ書込みで SAI トンネルオブジェクト（mapper → tunnel → tunnel-term）が一括生成される**。
- VXLAN_TUNNEL 単体ではハードウェアオブジェクトは作成されない点に注意。
- VRF マッパー（`VIRTUAL_ROUTER_ID_TO_VNI` / `VNI_TO_VIRTUAL_ROUTER_ID`）も VLAN マップ追加時に先行生成（over-provision）される（vxlanorch.cpp:2065-2072）。
- evidence: `vxlanorch.cpp:2063-2087`

### 4. del_tnl_hw_pending フラグによる書込みブロック

- 親トンネルの HW 削除処理が保留中（`del_tnl_hw_pending == true`）の場合、MAP 追加もブロックされ `return false`（リトライ待ち）。
- evidence: `vxlanorch.cpp:2057-2061`

### 5. 削除順序 — MAP を先に削除してから TUNNEL を削除

- トンネル削除時は DIP トンネル（EVPN remote 動的トンネル）が 0 件になるまで `del_tnl_hw_pending = true` のまま HW 削除が遅延される（vxlanorch.cpp:952-964）。
- VXLAN_TUNNEL_MAP が残った状態で VXLAN_TUNNEL を削除しようとすると HW 削除保留状態が継続する。
- **推奨削除順序**: `VXLAN_TUNNEL_MAP` 全削除 → `VXLAN_TUNNEL` 削除
- evidence: `vxlanorch.cpp:952-964`, `vxlanorch.cpp:1648-1671`

---

## 推奨 CONFIG_DB 書込み順序まとめ

```
作成順:
1. VLAN|<id>                           ← getVlanByVlanId チェック
2. VXLAN_TUNNEL|<tunnel-name>          ← isTunnelExists チェック
3. VXLAN_TUNNEL_MAP|<tunnel>|<map>     ← 初回エントリで SAI HW 作成トリガー
   （複数マップは順不同で書込み可能、VLAN/TUNNEL さえ存在すればよい）
4. VXLAN_EVPN_NVO|<nvo>               ← VTEP active 後に設定推奨

削除順（逆順）:
4. VXLAN_EVPN_NVO 削除
3. VXLAN_TUNNEL_MAP 全削除
2. VXLAN_TUNNEL 削除
1. VLAN 削除
```

source: `sonic-swss/orchagent/vxlanorch.cpp`
