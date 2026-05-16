# VXLAN トンネルポート (Port::TUNNEL) — Phase B 書込み順依存スキャンノート

対象: ランタイムオブジェクト `Port::TUNNEL`
Consumer: `VxlanTunnelOrch` / `VxlanTunnelMapOrch` / `EvpnNvoOrch` (`orchagent/vxlanorch.cpp`)
スキャン範囲: `addTunnelUser()`, `addOperation()` (VxlanTunnelMapOrch, VxlanVrfMapOrch), `EvpnNvoOrch::addOperation()`, `createTunnelHw()` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. VXLAN_TUNNEL → VXLAN_TUNNEL_MAP / EVPN_REMOTE_VNI（SAI トンネル先行必須）

- `VxlanTunnelMapOrch::addOperation` (vxlanorch.cpp:2063) は `tunnel_obj->isActive()` を確認する。
- `isActive()` は `createTunnelHw()` が成功した後に `active_ = true` となる (vxlanorch.cpp:939)。
- `VXLAN_TUNNEL` エントリ追加だけでは SAI トンネルオブジェクトは生成されない。SAI 生成は `VXLAN_TUNNEL_MAP` 追加時に初めて実行される。
- **順序依存**: `VXLAN_TUNNEL_MAP` を先に書いても `tunnel_obj` がまだ存在しない場合は `return false` でキューに残り再試行される。結果的に `VXLAN_TUNNEL` が先行していれば動作するが、`VXLAN_TUNNEL_MAP` 追加時点で参照先 `VXLAN_TUNNEL` エントリが CONFIG_DB に存在していることが前提。
- evidence: `vxlanorch.cpp:2042-2063`

### 2. VXLAN_EVPN_NVO → addTunnelUser()（EVPN VTEP ポインタ先行必須）

- `VxlanTunnelOrch::addTunnelUser` (vxlanorch.cpp:1685) は `evpn_orch->getEVPNVtep()` を呼ぶ。
- `EvpnNvoOrch::addOperation` (vxlanorch.cpp:2776) が `source_vtep_ptr` を設定する処理であり、`VXLAN_EVPN_NVO` エントリが CONFIG_DB に書かれて orchagent に処理されることで初めて `getEVPNVtep()` が非 NULL を返す。
- `getEVPNVtep() == NULL` の場合: `SWSS_LOG_WARN("Unable to find EVPN VTEP")` を出力して `return false`。トンネルポートは生成されない。
- **順序依存（強制先行必須）**: `VXLAN_EVPN_NVO` が処理済みでなければ EVPN DIP トンネルポートは生成されない。BGP が EVPN リモート VTEP を学習してきても、`VXLAN_EVPN_NVO` が未設定の間は `Port_EVPN_*` ポートが作られない。
- evidence: `vxlanorch.cpp:1685-1692`

### 3. VTEP の isActive() 確認 — SAI トンネル生成完了待ち

- `addTunnelUser` 呼び出し前に `vtep_ptr->isActive()` チェックがある (vxlanorch.cpp:1694)。
- `!isActive()` の場合: `SWSS_LOG_WARN("VTEP not yet active")` を出力して `return false`。再試行キューに戻る。
- `VTEP` が `active_` になるのは `createTunnelHw()` の SAI `create_tunnel()` が成功したとき (vxlanorch.cpp:939)。
- `createTunnelHw()` は `VxlanTunnelMapOrch::addOperation` または `VxlanVrfMapOrch::addOperation` から呼ばれる。
- **順序依存（推奨先行順序）**: `VXLAN_TUNNEL` → `VXLAN_TUNNEL_MAP`（SAI 生成 → `active_=true`）→ `VXLAN_EVPN_NVO` → EVPN リモート VTEP 学習 → `Port_EVPN_*` 生成。`VXLAN_TUNNEL_MAP` 書き込み前に `VXLAN_EVPN_NVO` を書くと、`isActive() == false` で `addTunnelUser` が一時的に失敗するが、再試行で回復する。
- evidence: `vxlanorch.cpp:1694-1699`

### 4. DIP トンネル非サポート時の Local SRC VTEP ポート — VXLAN_TUNNEL_MAP 先行必須

- DIP トンネル非サポート (`isDipTunnelsSupported() == false`) の場合、`Port_SRC_VTEP_*` ポートは `VxlanTunnelMapOrch::addOperation` (vxlanorch.cpp:2079) 内でのみ生成される。
- 生成条件: `tunnel_obj->isActive()` の直後ブロック、`isDipTunnelsSupported() == false` の分岐。
- `VXLAN_TUNNEL_MAP` エントリが存在しなければ生成トリガーがない。
- **順序依存**: `VXLAN_TUNNEL` → `VXLAN_TUNNEL_MAP`（この順でなければ `Port_SRC_VTEP_*` が生成されない）。
- evidence: `vxlanorch.cpp:2076-2088`

### 5. トンネルポートの二重生成防止ガード

- `addTunnelUser` (vxlanorch.cpp:1715) および `addOperation` (vxlanorch.cpp:2080) はともに `getTunnelPort()` で既存ポートを確認し、存在する場合は `addTunnel()` を呼ばない。
- **順序依存なし**（冪等性保証）: 同じ remote VTEP に対して `addTunnelUser` が複数回呼ばれても 1 つのポートしか生成されない。

---

## 順序依存サマリ

| # | 先行必須 | 後続処理 | 違反時の動作 | 自動回復 |
|---|----------|----------|-------------|---------|
| 1 | `VXLAN_TUNNEL` 追加 | `VXLAN_TUNNEL_MAP` 処理 | `tunnel_obj` null → `return false` → 再試行 | あり（再試行） |
| 2 | `VXLAN_EVPN_NVO` 処理済み | `addTunnelUser` による `Port_EVPN_*` 生成 | `getEVPNVtep()==NULL` → warn + `return false` | あり（再試行） |
| 3 | `VXLAN_TUNNEL_MAP` 処理による `active_=true` | `addTunnelUser` の `isActive()` ガード通過 | `isActive()==false` → warn + `return false` | あり（再試行） |
| 4 | `VXLAN_TUNNEL_MAP` 存在 | `Port_SRC_VTEP_*` 生成 (DIP 非サポート時) | 生成トリガーなし（永続的） | なし（手動追加が必要） |
| 5 | — | 二重生成防止 | なし（冪等）| N/A |
