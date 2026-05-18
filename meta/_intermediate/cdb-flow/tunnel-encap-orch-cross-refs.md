# tunnel-encap-orch: Phase C 暗黙参照テーブル 調査ノート

## 調査対象
- `orchagent/vxlanorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/vxlanorch.h`

## 検出された暗黙参照

### gUnderlayIfId (グローバル変数)
- Line 32: `extern sai_object_id_t gUnderlayIfId;`
- Line 907: `ids_.tunnel_id = create_tunnel(&ids_, &ips, ip, gUnderlayIfId, p2p, decap_ttl_mode_, encap_ttl);`
- `main.cpp:967` で `gUnderlayIfId` が初期化される
- VxlanTunnelOrch は `VXLAN_TUNNEL` 追加時には SAI 呼び出しを行わないが、
  `VXLAN_TUNNEL_MAP` / `VRF_MAP` 追加時の `createTunnelHw()` で `gUnderlayIfId` を参照する。
  未初期化の場合は SAI エラー。

### gDirectory → VxlanTunnelOrch 参照
- `VxlanTunnelMapOrch::addOperation` (line 2046): `gDirectory.get<VxlanTunnelOrch*>()` で VxlanTunnelOrch を取得
- `VxlanVrfMapOrch::addOperation` (line 2260): 同様に取得
- `orchdaemon.cpp:350-351` で VxlanTunnelOrch が gDirectory に先に登録されている必要がある

### gDirectory → VRFOrch 参照
- `VxlanTunnelMapOrch::addOperation` (line 2095): `gDirectory.get<VRFOrch*>()` で VRFOrch を取得
- L3VNI かどうかの判定に使用 (`vrf_orch->isL3VniVlan(vni_id)`)
- VRF が存在しない場合の挙動: `isL3Vni == false` として処理される（エラーではなく条件分岐）

### gDirectory → EvpnNvoOrch 参照
- `VxlanTunnelOrch::addTunnelUser` (line 1678): `gDirectory.get<EvpnNvoOrch*>()`
- `VxlanTunnelOrch::delTunnelUser` (line 1733): 同様
- `VxlanTunnelOrch::deleteTunnelPort` (line 1795): 同様
- EVPN DIP トンネルの作成・削除時に EvpnNvoOrch を参照

### STATE_DB 書込 (STATE_VXLAN_TUNNEL_TABLE)
- `m_stateVxlanTable` (line 1247): `STATE_VXLAN_TUNNEL_TABLE_NAME`
- `addRemoveStateTableEntry()` (line 1913-1955):
  - トンネル作成時に `src_ip`, `dst_ip`, `tnl_src`, `operstatus=down` を STATE_DB に書き込む
  - `updateDbTunnelOperStatus()` (line 1893): トンネルの operstatus を STATE_DB に更新

### VXLAN_TUNNEL (CONFIG_DB → APPL_DB → orchagent) の前提
- VxlanTunnelMapOrch の `addOperation` は `findTunnel()` で VxlanTunnelOrch が管理するトンネルを参照 (line 2030)
- VXLAN_TUNNEL エントリが先に存在しなければ処理失敗

## 参照方向まとめ

| 参照先 | 参照方向 | 条件 | evidence |
|--------|---------|------|---------|
| `gUnderlayIfId` (global RIF) | 読み取り (SAI create_tunnel) | VXLAN_TUNNEL_MAP / VRF_MAP 追加時 | `vxlanorch.cpp:907` |
| `VxlanTunnelOrch` (via gDirectory) | 読み取り (findTunnel) | VxlanTunnelMapOrch/VxlanVrfMapOrch が処理するとき | `vxlanorch.cpp:2046, 2046, 2260` |
| `VRFOrch` (via gDirectory) | 読み取り (isL3VniVlan) | VxlanTunnelMapOrch が VRF map を処理するとき | `vxlanorch.cpp:2095` |
| `EvpnNvoOrch` (via gDirectory) | 読み取り/通知 | addTunnelUser / delTunnelUser 時 | `vxlanorch.cpp:1678, 1733, 1795` |
| `STATE_VXLAN_TUNNEL_TABLE` (STATE_DB) | 書き込み | トンネル作成・oper-status 変化時 | `vxlanorch.cpp:1910, 1943, 1953` |
