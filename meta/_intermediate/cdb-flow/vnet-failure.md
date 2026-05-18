# VNET / VNET_ROUTE — Phase D 失敗挙動スキャンノート

対象ページ: `docs/reference/config-db/vnet.md`
対象テーブル: `VNET`、`VNET_ROUTE`、`VNET_ROUTE_TUNNEL`
Producer: `VxlanMgr` (`sonic-swss/cfgmgr/vxlanmgr.cpp`)、`VNetOrch` (`sonic-swss/orchagent/vnetorch.cpp`)
スキャン範囲: `VxlanMgr::doVxlanCreateTask()` / `doVxlanDeleteTask()`、`VNetOrch::addOperation()` / `delOperation()`、`VNetVrfObject::createObj()` / `updateObj()` / `removeObj()`、`VNetOrch::addRoute()` / `delRoute()` の全行精読

---

## 検出した失敗挙動

### 1. VXLAN トンネル未作成 → VNET 処理サスペンド

- `doVxlanCreateTask()` は `m_vxlanTunnelCache.find(info.m_vxlanTunnel)` が end() を返す場合（VXLAN_TUNNEL エントリが先に処理されていない場合）`return false` でエントリを `m_toSync` に残してリトライ待ち (`vxlanmgr.cpp:322-326`)。
- **挙動**: `VXLAN_TUNNEL` エントリが作成されるまで VNET の処理が永続サスペンドする。CLI や JSON ロード順序が逆の場合も同様。

### 2. VNET フィールド不完全 → サイレントドロップ

- `vxlan_tunnel` フィールドまたは `vni` フィールドが欠けている場合 `SWSS_LOG_DEBUG("Vnet %s information is incomplete")` を記録して `return true`（m_toSync から erase）し、**永久に再処理されない** (`vxlanmgr.cpp:308-317`)。
- **挙動**: `vxlan_tunnel` / `vni` のいずれかが欠落した VNET エントリはサイレントに破棄される。エラーログはなく WARN も出ない。

### 3. VRF STATE_DB 未 ready → リトライ待ち

- `isVrfStateOk(info.m_vnet)` が false（STATE_DB の `VRF_TABLE` にエントリがない）の場合 `return false` で再キュー (`vxlanmgr.cpp:328-332`)。
- **挙動**: 対応する VRF が STATE_DB に登録されるまで VNET 処理がブロックされる。

### 4. ルータ MAC 未設定 → リトライ待ち

- `getVxlanRouterMacAddress()` の `first` フラグが false（MAC が未取得）の場合 `return false` で再キュー (`vxlanmgr.cpp:335-340`)。
- **挙動**: システム起動直後や MAC 設定前に VNET エントリを投入しても処理が遅延する。

### 5. VxLAN netdevice 作成失敗 → エラーログ + false

- `isVxlanStateOk()` が false（VXLAN netdevice 未作成）かつ作成を試みて失敗した場合 `SWSS_LOG_ERROR("Cannot create vxlan %s", info.m_vxlan.c_str())` を記録して `return false` (`vxlanmgr.cpp:368`)。
- **挙動**: カーネルの `ip link add ... type vxlan` が失敗（権限不足・既存デバイス重複など）すると VNET 処理がブロックされる。

### 6. SAI VR 作成失敗 → `std::runtime_error` → addOperation false

- `VNetVrfObject::createObj()` で `sai_virtual_router_api->create_virtual_router()` が `SAI_STATUS_SUCCESS` 以外を返した場合 `SWSS_LOG_ERROR("Failed to create virtual router name: %s, rv: %d")` + `throw std::runtime_error("Failed to create VR object")` (`vnetorch.cpp:101-103`)。
- 呼び出し元 `VNetOrch::addOperation()` は `catch(std::runtime_error& _)` で捕捉し `SWSS_LOG_ERROR("VNET add operation error for %s: error %s")` を記録して `return false` (`vnetorch.cpp:550-553`)。
- **挙動**: VNET は m_toSync に残り再試行される。SAI リソース枯渇時は恒久的に失敗する。

### 7. VXLAN tunnel map 作成失敗 → addOperation false

- `VxlanTunnelOrch::createVxlanTunnelMap()` が false を返した場合 `SWSS_LOG_ERROR("VNET '%s', tunnel '%s', map create failed")` + `return false` (`vnetorch.cpp:515-517`)。
- **挙動**: VNI マッピングが取れない場合（VNI 枯渇など）VNET の SAI オブジェクト作成が中断し再試行される。

### 8. VXLAN tunnel が orchagent に未存在 → VNET addOperation リトライ

- `VxlanTunnelOrch::isTunnelExists(tunnel)` が false を返した場合 `SWSS_LOG_WARN("Vxlan tunnel '%s' doesn't exist")` + `return false` (`vnetorch.cpp:501-502`)。
- **挙動**: orchagent 側で VXLAN_TUNNEL が登録される前に VNET が処理されると再キューされる。vxlanmgrd 側の順序依存とは独立した orchagent 内の別チェック。

### 9. VNET 削除時にルートが残存 → delOperation false

- `vrf_obj->getRouteCount()` が 0 より大きい場合 `SWSS_LOG_ERROR("VNET '%s': Routes are still present")` + `return false` (`vnetorch.cpp:584-585`)。
- **挙動**: VNET 配下の VNET_ROUTE / VNET_ROUTE_TUNNEL エントリを先に削除しないと VNET 本体が削除できない（強制順序依存）。

### 10. VNET 削除時の tunnel map 削除失敗 → delOperation false

- `vxlan_orch->removeVxlanTunnelMap()` が false を返した場合 `SWSS_LOG_ERROR("VNET '%s' map delete failed")` + `return false` (`vnetorch.cpp:590-591`)。
- **挙動**: VNI マッピング解除が失敗（SAI エラー）すると VNET 削除がブロックされ、`m_toSync` で再試行される。

### 11. VR オブジェクト更新失敗 → updateObj false

- `sai_virtual_router_api->set_virtual_router_attribute()` が失敗した場合 `SWSS_LOG_ERROR("Failed to update virtual router attribute. VNET name: %s, rv: %d")` + `return false` (`vnetorch.cpp:142-144`)。
- **挙動**: VNET の属性更新（`overlay_dmac` 等）が SAI レベルで失敗しても orchagent はエラーログのみ記録し呼び出し元に `false` を返す。

### 12. VNET_ROUTE SAI 失敗 → route addRoute / delRoute false

- `sai_route_api->create_route_entry()` 失敗時 `SWSS_LOG_ERROR("SAI failed to create route")` + `return false` (`vnetorch.cpp:692-693`)。
- `sai_route_api->remove_route_entry()` 失敗時 `SWSS_LOG_ERROR("SAI Failed to remove route, rv: %d")` + `return false` (`vnetorch.cpp:659-660`)。
- **挙動**: ルートの SAI 操作が失敗した場合、VNetRouteOrch は `return false` を返し再試行キューへ。

### 13. NextHop group 上限超過 → ルート追加失敗

- `SWSS_LOG_ERROR("Reached maximum number of next hop groups. Failed to create new next hop group.")` + `return false` (`vnetorch.cpp:773-774`)。
- **挙動**: ASIC の NextHop group 上限に達した場合、新規 VNET_ROUTE_TUNNEL の ECMP グループ生成が失敗する。既存ルートには影響しない。

---

## 失敗挙動サマリ

| # | 失敗条件 | 記録 | 再試行 | 挙動分類 |
|---|----------|------|--------|---------|
| 1 | VXLAN_TUNNEL 未作成 | DEBUG | ✅ m_toSync 再キュー | 順序依存 suspend |
| 2 | `vxlan_tunnel`/`vni` 欠落 | DEBUG | ❌ 永久 erase | サイレントドロップ |
| 3 | VRF STATE_DB 未 ready | DEBUG | ✅ m_toSync 再キュー | 順序依存 suspend |
| 4 | ルータ MAC 未設定 | DEBUG | ✅ m_toSync 再キュー | 起動シーケンス依存 |
| 5 | netdevice 作成失敗 | ERROR | ✅ m_toSync 再キュー | カーネル操作失敗 |
| 6 | SAI VR 作成失敗 | ERROR | ✅ m_toSync 再キュー | SAI エラー |
| 7 | VXLAN tunnel map 失敗 | ERROR | ✅ m_toSync 再キュー | SAI リソース |
| 8 | orchagent tunnel 未存在 | WARN | ✅ m_toSync 再キュー | 順序依存 suspend |
| 9 | 削除時ルート残存 | ERROR | ✅ m_toSync 再キュー | 削除順序依存 |
| 10 | 削除時 map 解除失敗 | ERROR | ✅ m_toSync 再キュー | SAI エラー |
| 11 | VR 属性更新失敗 | ERROR | ✅（呼び出し元判断） | SAI エラー |
| 12 | VNET_ROUTE SAI 失敗 | ERROR | ✅ m_toSync 再キュー | SAI エラー |
| 13 | NextHop group 上限超過 | ERROR | ✅ m_toSync 再キュー | リソース枯渇 |

---

## ページ反映方針

- `<!-- failure -->` ブロックをページの `<!-- ordering -->` / `<!-- cross-refs -->` ブロックの後に挿入する。
- サイレントドロップ（失敗 #2）を特に強調する。
- 失敗サマリ表 + 主要失敗の散文詳細を含める。
