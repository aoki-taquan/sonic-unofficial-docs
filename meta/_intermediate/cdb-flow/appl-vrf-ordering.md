# APPL_DB `VRF_TABLE` — Phase B 書込み順依存スキャンノート

対象テーブル: APPL_DB `VRF_TABLE`
producer: `vrfmgrd` (`sonic-swss/cfgmgr/vrfmgr.cpp`)
consumer: `orchagent` / `VRFOrch` (`sonic-swss/orchagent/vrforch.cpp`)
スキャン範囲: `vrforch.cpp` 全行 (1-290) + `vrfmgr.cpp::doTask` (217-360)

---

## 検出した順序依存・タイミング依存

### 1. mgmt VRF の特別扱い — `vrfmgrd` 段で経路分岐し、`VRFOrch` 側でも明示 ignore

- `vrfmgr.cpp:13-16` で `MGMT_VRF_TABLE_ID = 6000`, `MGMT_VRF = "mgmt"` がリザーブされる。通常 VRF の `VRF_TABLE_START..VRF_TABLE_END` (1001..5097) とは別レンジ。
- `VrfMgr::setLink` (`vrfmgr.cpp:164-201`) は `vrfName == "mgmt"` の場合、`hostcfgd` が既に Linux 側 mgmt VRF を作成済みである前提で `ip link add` を呼ばずに `MGMT_VRF_TABLE_ID` を `m_vrfTableMap` に登録するだけ。
- `VrfMgr::delLink` (`vrfmgr.cpp:136-162`) も `vrfName == "mgmt"` の場合 `ip link del` を呼ばず table id だけ recycle する（コメント: `// No deletion of mgmt table from kernel`、`vrfmgr.cpp:73-76`）。
- `VrfMgr::doTask` (`vrfmgr.cpp:228-271`) の冒頭で `CFG_MGMT_VRF_CONFIG_TABLE_NAME` (`MGMT_VRF_CONFIG`) を受けた場合、`mgmtVrfEnabled` / `in_band_mgmt_enabled` の両方が `true` でない限り `op` を強制的に `DEL_COMMAND` に書き換え、`vrfName` を `"mgmt"` に固定する。
- 結果として `APPL_DB|VRF_TABLE|mgmt` への書き込みは「CONFIG_DB `MGMT_VRF_CONFIG` の両フラグが `true`」かつ「`hostcfgd` が Linux mgmt VRF 作成済み」の二条件が揃った後にのみ発生する。
- 受信側 `VRFOrch::addOperation` も `mgmtVrfEnabled` / `in_band_mgmt_enabled` フィールドを `continue` で読み飛ばす (`vrforch.cpp:74-78`)。SAI 属性へは絶対に到達しない。
- **順序依存**: `hostcfgd` が mgmt VRF 用 netdev を構成する **前** に `MGMT_VRF_CONFIG` を書き込むと、`vrfmgrd` 側で `m_vrfTableMap` への登録は走るが `state VRF_TABLE|mgmt = ok` 書き込みのみで、ハード VRF オブジェクトは生まれない（`m_appVrfTableProducer.set` まで到達するため SAI Virtual Router 自体は作成されるが、Linux 側 mgmt VRF との接続が不整合のまま残る）。
- evidence: `vrfmgr.cpp:13-16, 73-84, 136-201, 228-271`、`vrforch.cpp:74-78`

### 2. EVPN VTEP 先行必須 — `vni != 0` の VRF 書込前に `VXLAN_EVPN_NVO` が必要

- `VRFOrch::updateVrfVNIMap` (`vrforch.cpp:225-230`) は `gDirectory.get<EvpnNvoOrch*>()->getEVPNVtep()` を呼び、戻り値が空ポインタの場合 `false` を返して `addOperation` 全体を失敗させる:

  ```cpp
  auto evpn_vtep_ptr = evpn_orch->getEVPNVtep();
  if(!evpn_vtep_ptr) {
      SWSS_LOG_NOTICE("updateVrfVNIMap unable to find EVPN VTEP");
      return false;
  }
  ```

- 失敗時 `addOperation` は `m_stateVrfObjectTable.hset(..., "state", "ok")` まで到達せず、`vrf_vni_map_table_[vrf_name] = vni` も書かれない。
- ただし **SAI Virtual Router の create は `if (vni != 0)` ブロックの手前 (`vrforch.cpp:93-110`) で先に成功している**。`gFlowCounterRouteOrch->onAddVR(router_id)` も先に呼ばれる。結果として「SAI VR は存在するが VNI map と STATE_DB state が無い」半作成状態が発生する。
- リトライキュー (`Orch::doTask`) には残るため、後から `VXLAN_EVPN_NVO` を書けば次回 tick で `updateVrfVNIMap` が成功し、ただし `vrf_table_[vrf_name]` には既存 SAI OID が登録済みなので update パス (`vrforch.cpp:123-152`) に入る。
- **必要な先行順**: `CONFIG_DB|VXLAN_EVPN_NVO|<nvo>` → (`vrfmgrd::doVrfEvpnNvoAddTask` 経由で `EvpnNvoOrch` に VTEP 登録) → `APPL_DB|VRF_TABLE|<vrf>` (`vni != 0`)。
- 加えて L3 VNI が実際にデータプレーンに反映されるためには `VLAN ↔ VNI` マップ (`VxlanTunnelOrch::getVlanMappedToVni(vni) != 0`) も必要 (`vrforch.cpp:233-241`)。VLAN-VNI map 未投入だと `updateL3VniStatus` は呼ばれず、`l3vni_table_[vni].vlan_id = 0` のまま保留される（半設定状態）。
- evidence: `vrforch.cpp:200-247`、`vrfmgr.cpp:275-278, 319-322`

### 3. VRF と VNET の独立性 — APPL_DB 上の経路は別、producer も別

- `vrfmgrd` は CONFIG_DB の **3 つのテーブル** を購読する: `VRF`, `MGMT_VRF_CONFIG`, `VNET` (`vrfmgr.cpp:22-26` で `m_appVrfTableProducer` / `m_appVnetTableProducer` / `m_appVxlanVrfTableProducer` の 3 つの producer を保持)。
- `doTask` (`vrfmgr.cpp:292-309`) は consumer table 名で分岐し、`CFG_VRF_TABLE_NAME` または `CFG_MGMT_VRF_CONFIG_TABLE_NAME` の場合のみ `m_appVrfTableProducer.set` (`APPL_DB|VRF_TABLE`) に書き込む。`CFG_VNET_TABLE_NAME` の場合は `m_appVnetTableProducer.set` (`APPL_DB|VNET_TABLE`) に書く。両者は **同じ APPL_DB の別テーブル** であり、orchagent 側でも `VRFOrch` (`VRF_TABLE` 専属) と `VnetOrch` (`VNET_TABLE` 専属) が別ハンドラとして処理する。
- ただし、Linux 側 netdev (`m_vrfTableMap` の table id 払い出し) は VRF と VNET で **共有プール** (`vrfmgr.cpp:28-30`、`VRF_TABLE_START..VRF_TABLE_END`)。同名キーは衝突するが、命名規則（VNET は `Vnet_*` プレフィックス）で実際の衝突は回避される。
- `VRFOrch::addOperation` 内で `v4` / `v6` / `src_mac` を実際に使うのは VNET 経路のみ（YANG `sonic-vrf.yang` には未定義のため `config vrf add` では書かれない）。VRF 経路と VNET 経路が同じ `VRF_TABLE` ハンドラで処理されることに依存。
- **順序依存なし**: VRF と VNET 間の書込順制約はない。`VNET` を先に書いても `VRF` を先に書いても独立に処理される。`VNET` 内で `vrf_name` 参照（`Vnet` キーが VRF を指す）は orchagent 側の VnetOrch が解決し、VRFOrch とは別経路。
- **罠**: 同じ `VRFOrch::addOperation` ロジックが VNET 由来のエントリを処理するため、VNET 書込時にのみ `v4` / `v6` が SAI に渡る。通常の `config vrf add` 経路では到達しない dead 経路扱い。
- evidence: `vrfmgr.cpp:22-26, 273-310`、`vrforch.cpp:38-47`

### 4. ref_count による DEL ブロック — インタフェース・ルートを先に削除する必要

- `VRFOrch::delOperation` (`vrforch.cpp:169-170`) は `vrf_table_[vrf_name].ref_count` が 0 でない場合 `return false`（リトライキューに残置）。
- `ref_count` は `IntfsOrch` / `RouteOrch` 等が VRF を参照する際に `VRFOrch::increaseVrfRefCount` 経由で増加する（ヘッダ宣言は本ファイル外）。
- **順序依存**: `CONFIG_DB|VRF|<vrf>` を DEL する前に、その VRF を参照する `INTERFACE` / 静的ルート / VLAN 上の IP を先に DEL する必要がある。これを怠ると VRF DEL はリトライキューに残り続け、`m_stateVrfObjectTable|<vrf>` の `state=ok` が残るため `vrfmgrd::isVrfObjExist()` が `true` を返し続け、`vrfmgrd::delLink` は `vrf netdev` を削除しない (`vrfmgr.cpp:312-360` の delay 削除ロジック)。
- evidence: `vrforch.cpp:157-198`、`vrfmgr.cpp:312-360`

### 5. SET (create) → STATE_DB → vrfmgrd delLink delay

- create 経路では SAI VR create 成功 → `gFlowCounterRouteOrch->onAddVR` → `updateVrfVNIMap` (任意) → `m_stateVrfObjectTable.hset(..., "ok")` の順 (`vrforch.cpp:93-121`)。`onAddVR` は VNI map より **前** に呼ばれる。
- DEL 経路では `sai_virtual_router_api->remove_virtual_router` → `gFlowCounterRouteOrch->onRemoveVR` → `vrf_table_.erase` → `delVrfVNIMap` → `m_stateVrfObjectTable.del` の順 (`vrforch.cpp:172-193`)。STATE_DB DEL は最後。
- `vrfmgrd::doTask` の DEL ブランチ (`vrfmgr.cpp:312-360`) は `state VRF_OBJECT_TABLE|<vrf>` が消えるのを待ってから `delLink`（Linux netdev 削除）を実行する設計（コメント `Delay delLink until vrf object deleted in orchagent`）。
- **依存**: `VRFOrch` が `STATE_VRF_OBJECT_TABLE` を最後に消すため、`vrfmgrd` の Linux netdev 削除は SAI remove 成功後にしか走らない。逆順は起きない。
- evidence: `vrforch.cpp:93-121, 172-193`、`vrfmgr.cpp:312-360`

---

## まとめ（ページに掲載する順序依存）

1. **mgmt VRF 特別扱い**: `hostcfgd` が Linux mgmt VRF を先に作成 → `MGMT_VRF_CONFIG` の両フラグ true → `vrfmgrd` が `APPL_DB|VRF_TABLE|mgmt` に書く。orchagent 側 `mgmtVrfEnabled` / `in_band_mgmt_enabled` フィールドは explicit ignore。
2. **EVPN VTEP 先行必須**: `vni != 0` の VRF を書く前に `VXLAN_EVPN_NVO` (`EvpnNvoOrch::getEVPNVtep()` が非 null) が必要。先行しない場合 SAI VR は作成されるが STATE_DB / VNI map が抜ける半作成状態。
3. **VRF と VNET は独立**: APPL_DB 上で別テーブル (`VRF_TABLE` vs `VNET_TABLE`)、別 producer、別 orchagent ハンドラ。書込順制約なし。同一 `VRFOrch::addOperation` ロジックを再利用するため `v4` / `v6` / `src_mac` は VNET 経路でのみ機能。
4. **DEL は参照クリア先行**: `ref_count > 0` の間 DEL はリトライキューに残置。先に INTERFACE / ROUTE を消す必要。
5. **delLink delay**: `vrfmgrd` の Linux netdev 削除は `STATE_VRF_OBJECT_TABLE` 消滅を待つ仕様で、SAI remove → STATE DEL → Linux netdev DEL の順が保証される。
