# VXLAN_EVPN_NVO — Phase B 書込み順依存スキャンノート

対象テーブル: `VXLAN_EVPN_NVO`
Consumer: `orchagent` / `EvpnNvoOrch`
スキャン範囲: `sonic-swss/orchagent/vxlanorch.cpp` (EvpnNvoOrch::addOperation, EvpnNvoOrch::delOperation)

---

## 検出した順序依存・タイミング依存

### 1. VXLAN_TUNNEL が先行必須（source_vtep 参照）

- `EvpnNvoOrch::addOperation()` (vxlanorch.cpp:2775) は `tunnel_orch->getVxlanTunnel(vtep_name)` で `source_vtep` フィールドが参照する VTEP 名をルックアップする。
- `VXLAN_TUNNEL|<name>` が `vxlan_tunnel_table_` に存在しない場合は null ポインタが `source_vtep_ptr` に格納される。
- null ポインタのまま後続の EVPN 処理（`addTunnelUser()` 等）が走ると `SWSS_LOG_WARN("Unable to find EVPN VTEP")` → `return false` となりリトライ待ちになる。
- **必須順序**: `VXLAN_TUNNEL|<name>` → `VXLAN_EVPN_NVO|<nvo-name>`（source_vtep が参照するトンネル名と一致）
- evidence: `vxlanorch.cpp:2775-2788`

### 2. VXLAN_TUNNEL_MAP を 1 件以上書いてから NVO を有効活用する

- `EvpnNvoOrch::addOperation()` は source_vtep を取得するのみで SAI には触れない。
- EVPN remote VTEP 動的トンネルが機能するには VTEP が `isActive() == true` である必要がある。
- `isActive()` は `createTunnelHw()` 完了後（vxlanorch.cpp:939）にセットされる。
- `createTunnelHw()` は `VXLAN_TUNNEL_MAP` の最初のエントリ受信時（vxlanorch.cpp:2063-2074）にトリガーされる。
- **推奨順序**: `VXLAN_TUNNEL` → `VXLAN_TUNNEL_MAP`（1 件以上）→ `VXLAN_EVPN_NVO`
- evidence: `vxlanorch.cpp:939`, `vxlanorch.cpp:2063-2074`, `vxlanorch.cpp:1694-1699`

### 3. 削除順序 — NVO を先に削除してから TUNNEL を削除

- `EvpnNvoOrch::delOperation()` (vxlanorch.cpp:2791) は `del_tnl_hw_pending` が true なら `return false` でリトライ（vxlanorch.cpp:2803-2807）。
- `del_tnl_hw_pending` は DIP トンネルが残存するうちは true のまま。
- TUNNEL 削除を先に行っても NVO 削除が保留状態でスタックするリスクあり。
- **推奨削除順序**: EVPN remote VTEP 削除 → `VXLAN_EVPN_NVO` 削除 → `VXLAN_TUNNEL_MAP` 全削除 → `VXLAN_TUNNEL` 削除
- evidence: `vxlanorch.cpp:2791-2813`, `vxlanorch.cpp:952-964`

---

## 推奨 CONFIG_DB 書込み順序まとめ

```
作成順:
1. VRF テーブルエントリ（VNET / VRF が必要な場合）
2. VXLAN_TUNNEL|<name>               ← メモリ登録のみ（SAI 未作成）
3. VXLAN_TUNNEL_MAP|<name>|<map>     ← 初回 MAP で SAI tunnel HW 作成トリガー
4. VXLAN_EVPN_NVO|<nvo-name>         ← source_vtep 参照先は step 2 で存在必須
5. EVPN remote VTEP 設定（step 3 完了 = VTEP active 後）

削除順（逆順）:
5. EVPN remote VTEP 削除
4. VXLAN_EVPN_NVO 削除
3. VXLAN_TUNNEL_MAP 全削除
2. VXLAN_TUNNEL 削除
1. VRF 削除
```

source: `sonic-swss/orchagent/vxlanorch.cpp`
