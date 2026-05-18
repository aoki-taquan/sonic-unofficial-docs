# 調査ノート: APPL_DB VRF_TABLE (VRFOrch) — Phase B 書込み順依存

調査日: 2026-05-18  
対象ファイル: `sonic-swss/orchagent/vrforch.cpp`, `sonic-swss/cfgmgr/vrfmgr.cpp`

## 主要な順序依存

### SET 依存

1. **EVPN VTEP 先行（VNI 付きのみ）**
   - `updateVrfVNIMap()` が `evpn_orch->getEVPNVtep()` を呼び、null なら false を返す
   - `vrforch.cpp:225-230`
   - 対策: `VXLAN_EVPN_NVO` を先に投入

2. **VRF デバイス作成（vrfmgrd 側）**
   - `getFreeTable()` が 0 を返す（プール枯渇）と APPL_DB に書かれない
   - `vrfmgr.cpp:185-188`
   - 最大 4096 VRF

### DEL 依存

1. **ref_count == 0 必須**
   - RouteOrch, IntfsOrch, Srv6Orch が `increaseVrfRefCount()`/`decreaseVrfRefCount()` で参照カウント管理
   - `vrforch.cpp:169-170`

2. **STATE_VRF_OBJECT_TABLE 削除待ち**
   - vrfmgrd の DEL ハンドラが `isVrfObjExist()` を使って待機
   - `vrfmgr.cpp:331-346`, `vrforch.cpp:193`

## 自動調停

- `addOperation` / `delOperation` が `false` → `m_toSync` に残留 → 次ループで再試行（無限ポーリング）
- VNI 変更は差分更新のため冪等 (`vrforch.cpp:212`)
