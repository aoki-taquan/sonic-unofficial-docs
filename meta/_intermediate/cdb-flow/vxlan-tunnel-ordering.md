# VXLAN_TUNNEL — Phase B 書込み順依存スキャンノート

対象テーブル: `VXLAN_TUNNEL`
Consumer: `orchagent` / `VxlanTunnelOrch` / `VxlanTunnelMapOrch` / `VxlanVrfMapOrch` / `EvpnNvoOrch`
スキャン範囲: `sonic-swss/orchagent/vxlanorch.cpp` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. VXLAN_TUNNEL が MAP/NVO より先行必須（lazy HW 作成）

- `VxlanTunnelOrch::addOperation()` (vxlanorch.cpp:1591) は `VXLAN_TUNNEL` エントリを受け取った時点では **SAI トンネルオブジェクトを作成しない**。`vxlan_tunnel_table_` にメモリオブジェクトを登録するだけ。
- SAI HW 作成 (`createTunnelHw`) は `VXLAN_TUNNEL_MAP` の最初のエントリ受信時 (`VxlanTunnelMapOrch::addOperation()` vxlanorch.cpp:2063) または `VXLAN_EVPN_NVO` からの VRF マップ受信時 (`VxlanVrfMapOrch::addOperation()` vxlanorch.cpp:2292) にトリガーされる。
- **順序依存**: `VXLAN_TUNNEL` エントリが存在しない状態で `VXLAN_TUNNEL_MAP` / `VXLAN_EVPN_NVO` を書くと、`getVxlanTunnel()` がヌルを返しアサーション失敗になる。必ず `VXLAN_TUNNEL` を先に書くこと。
- evidence: `vxlanorch.cpp:1591-1645`, `vxlanorch.cpp:2012-2126`, `vxlanorch.cpp:2252-2355`

### 2. SAI tunnel_map → SAI tunnel → SAI tunnel_term の順序保証

- `createTunnelHw()` (vxlanorch.cpp:885) の内部では以下の順で SAI オブジェクトを生成する:
  1. `createMapperHw()` — `sai_tunnel_api->create_tunnel_map()` (VLAN/VRF/Bridge 各方向の encap・decap mapper)
  2. `create_tunnel()` — `sai_tunnel_api->create_tunnel()` (mapper OID リストを `SAI_TUNNEL_ATTR_DECAP_MAPPERS` / `SAI_TUNNEL_ATTR_ENCAP_MAPPERS` に渡す)
  3. `create_tunnel_termination()` — `sai_tunnel_api->create_tunnel_term_table_entry()` (with_term=true の場合のみ)
- **順序依存**: `create_tunnel()` は mapper OID を参照するため、mapper が存在しない状態でトンネルを作成しようとすると SAI エラーになる。このシーケンスはコード内で厳密に保証されており、外部 CONFIG_DB 操作で影響しないが、直接 SAI 操作時は留意する。
- **エラーロールバック**: `create_tunnel()` 失敗時は `deleteMapperHw()` でマッパーを削除し、`active_ = false` にリセット (vxlanorch.cpp:913-921)。`create_tunnel_termination()` 失敗時は `remove_tunnel()` → `deleteMapperHw()` で全ロールバック (vxlanorch.cpp:927-936)。
- evidence: `vxlanorch.cpp:885-950`

### 3. VRF が VXLAN_TUNNEL_MAP / VXLAN_VRF_MAP より先行必須

- `VxlanVrfMapOrch::addOperation()` (vxlanorch.cpp:2290) は `vrf_orch->isVRFexists(vrf_name)` をチェックし、VRF が未作成なら `SWSS_LOG_WARN("Vrf '%s' hasn't been created yet")` を出力して `return false` (vxlanorch.cpp:2315-2316)。
- `return false` は orchagent がエントリをキューに戻して**再処理を試みる**ことを意味する。VRF 作成後に自動でリトライされる設計だが、リトライ間隔は orchagent の主ループ周期依存（通常 ms 〜数秒）。
- VRF 先行書き込みが保証されていれば即時成功。保証がない場合はリトライが発生し、その間は VNI→VRF マッピングが SAI に入っていない（データプレーン疎通なし）。
- **推奨順序**: `VRF` テーブルエントリ → `VXLAN_TUNNEL` → `VXLAN_TUNNEL_MAP` / `VXLAN_EVPN_NVO`
- evidence: `vxlanorch.cpp:2285-2316`

### 4. EVPN_NVO は VXLAN_TUNNEL の後、かつ source_vtep 参照先が存在必須

- `EvpnNvoOrch::addOperation()` (vxlanorch.cpp:2775) は `tunnel_orch->getVxlanTunnel(vtep_name)` で `source_vtep` フィールドが指す VTEP 名を引く。
- VTEP が `vxlan_tunnel_table_` に存在しない場合は null ポインタが `source_vtep_ptr` に格納され、後続の `addTunnelUser()` (vxlanorch.cpp:1685) で `getEVPNVtep()` → null → `SWSS_LOG_WARN("Unable to find EVPN VTEP")` → `return false` となる。
- **順序依存**: `VXLAN_EVPN_NVO` の `source_vtep` 属性が参照する `VXLAN_TUNNEL|<name>` が先に存在しなければ、EVPN 動的トンネルユーザー追加が全て失敗しリトライ待ちになる。
- evidence: `vxlanorch.cpp:2775-2788`, `vxlanorch.cpp:1685-1692`

### 5. VTEP isActive() チェック — MAP 書込み前にトンネル HW が必要な場面

- `addTunnelUser()` (vxlanorch.cpp:1694) は `vtep_ptr->isActive()` を確認し、false なら `SWSS_LOG_WARN("VTEP not yet active")` → `return false`。
- `isActive()` は `createTunnelHw()` 完了後に `active_ = true` (vxlanorch.cpp:939) にセットされる。
- `VXLAN_TUNNEL_MAP` エントリが届く前に少なくとも 1 件の MAP または VRF マップが届くと `createTunnelHw()` が呼ばれて active になる。
- **タイミング依存**: EVPN remote VTEP 追加 (`EvpnRemoteVnip2mpOrch::addOperation()` 等) は VTEP が active になった後でなければ成功しない。`VXLAN_TUNNEL_MAP` を 1 件書いてから EVPN remote VTEP を設定する順序が推奨。
- evidence: `vxlanorch.cpp:1694-1699`, `vxlanorch.cpp:939`

### 6. 削除順序 — MAP / NVO を先に削除してから TUNNEL を削除

- `VxlanTunnelOrch::delOperation()` (vxlanorch.cpp:1648) は `vxlan_tunnel_table_` からエントリを削除するだけ（SAI HW 削除は `del_tnl_hw_pending` フラグで遅延）。
- `deletePendingSIPTunnel()` (vxlanorch.cpp:952) は `getDipTunnelCnt() == 0 && del_tnl_hw_pending` の両方が成立したときのみ HW 削除を実行する。
- DIP トンネル（動的 EVPN remote）がすべて削除される前に SIP トンネルを削除しようとすると HW 削除が保留される。
- `EvpnNvoOrch::delOperation()` (vxlanorch.cpp:2803) は `del_tnl_hw_pending` が true なら `return false` でリトライ。
- **推奨削除順序**: `VXLAN_TUNNEL_MAP` / `VXLAN_EVPN_NVO` → `VXLAN_TUNNEL`
- evidence: `vxlanorch.cpp:1648-1671`, `vxlanorch.cpp:952-964`, `vxlanorch.cpp:2797-2808`

---

## 推奨 CONFIG_DB 書込み順序まとめ

```
1. VRF テーブルエントリ（VNET / VRF が必要な場合）
2. VXLAN_TUNNEL|<name>          ← SAI 未作成、メモリ登録のみ
3. VXLAN_TUNNEL_MAP|<name>|<map>  ← 初回 MAP で SAI tunnel HW 作成がトリガー
4. VXLAN_EVPN_NVO|<name>        ← source_vtep 参照先は step 2 で存在必須
5. （EVPN remote VTEP 設定は step 3 完了 ＝ VTEP active 後）

削除は逆順:
5. EVPN remote VTEP 削除
4. VXLAN_EVPN_NVO 削除
3. VXLAN_TUNNEL_MAP 全削除
2. VXLAN_TUNNEL 削除
1. VRF 削除（他の参照がなくなってから）
```
