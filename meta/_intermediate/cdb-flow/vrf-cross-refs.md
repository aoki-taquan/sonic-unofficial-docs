# VRF テーブル — 暗黙参照 (Phase C) 調査メモ

調査日: 2026-05-15
対象ページ: `docs/reference/config-db/vrf.md`
対象ソース:
- `sonic-swss/cfgmgr/vrfmgr.cpp`
- `sonic-swss/orchagent/vrforch.cpp`
- `sonic-swss/orchagent/vrforch.h`
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vrf.yang`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-interface.yang`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py`

---

## 検出した暗黙参照

### 1. STATE_VRF_TABLE (STATE_DB) — readiness sentinel

- **方向**: `INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` / `LOOPBACK_INTERFACE` → `STATE_VRF_TABLE` (READ)
- **場所**: `intfmgr.cpp` L40, L671-684; `intfsorch.cpp` L826-830
- **内容**: 各 `*_INTERFACE` テーブルで `vrf_name` が指定されたとき、`intfmgrd` は `STATE_DB::STATE_VRF_TABLE` に VRF が登録済みであることを `isIntfStateOk(vrf_name)` で確認する。未登録なら SET をスキップして Consumer キューに残す。YANG leafref `VRF.name` は静的参照だが、この STATE_DB 確認は実行時ガード。orchagent 側も `isVRFexists(vrf_name)` で APP_DB 内の VRF OID 存在を別途確認する。
- **発見種別**: 実行時 readiness ガード（YANG 非表現）

### 2. VRF_OBJECT_TABLE (STATE_DB) — 削除同期 sentinel

- **方向**: VRF 削除時、`vrfmgrd` → `STATE_VRF_OBJECT_TABLE` (READ) + `orchagent/VRFOrch` → `STATE_VRF_OBJECT_TABLE` (WRITE)
- **場所**: `vrfmgr.cpp` (isVrfObjExist チェック); `vrforch.cpp` (SAI VR 作成後 `state=ok` 書き込み)
- **内容**: `vrfmgrd` は VRF 削除前に `STATE_VRF_OBJECT_TABLE` で SAI VRF オブジェクトが残存しないことを確認する。orchagent の VRFOrch が SAI VR 作成成功後に `STATE_VRF_OBJECT_TABLE|<name>` へ `state=ok` を書き込む。この sentinel が VRF 削除の 2 フェーズ同期（vrfmgrd と VRFOrch）を実現する。
- **発見種別**: 非同期削除同期（CONFIG_DB VRF テーブル非表現）

### 3. MGMT_VRF_CONFIG (CONFIG_DB) — mgmt VRF 特例

- **方向**: `vrfmgrd` → `MGMT_VRF_CONFIG` (READ, 起動時)
- **場所**: `vrfmgr.cpp` L257; `vrfmgr.cpp` L180-183
- **内容**: `vrfmgrd` は `MGMT_VRF_CONFIG|vrf_global` の `mgmtVrfEnabled` および `in_band_mgmt_enabled` を参照し、両値のいずれかが `false` のとき `VRF` テーブルへの SET コマンドを `DEL` として処理する。`mgmt` VRF は通常の VRF テーブルプール（1001–5096）を使わず固定 ID `6000` を割り当てる。`VRF` テーブル自体には `mgmtVrfEnabled` フィールドは存在せず、この依存は YANG 上見えない。
- **発見種別**: クロステーブル制御（YANG 非表現）

### 4. VXLAN_TUNNEL_MAP (CONFIG_DB) — vni マッピング副作用

- **方向**: `VRF.vni` 設定時 → `vrfmgrd` が `VXLAN_TUNNEL_MAP` に `evpn_map_<vni>_<vrf>` エントリを作成 (WRITE)
- **場所**: `vrfmgr.cpp` L510
- **内容**: `vni` フィールドに非ゼロ値を設定すると `vrfmgrd` が自動で `VXLAN_TUNNEL_MAP` エントリ (`evpn_map_<vni>_<vrf>`) を生成する。`VRF.vni` フィールド単体を見るだけではこの副作用は見えない。削除時も `VXLAN_TUNNEL_MAP` の対応エントリが消去される。
- **発見種別**: 副作用 WRITE（`VRF.vni` 変更のサイドエフェクト）

### 5. INTERFACE / VLAN_INTERFACE / PORTCHANNEL_INTERFACE / LOOPBACK_INTERFACE / VLAN_SUB_INTERFACE (CONFIG_DB) — leafref 被参照

- **方向**: 上記各テーブルの `vrf_name` フィールド → `VRF.name` への leafref (READ, YANG)
- **場所**: `sonic-interface.yang`, `sonic-vlan-interface.yang`, `sonic-portchannel-interface.yang`, `sonic-loopback-interface.yang`, `sonic-vlan-sub-interface.yang`
- **内容**: 各 `*_INTERFACE` テーブルの `vrf_name` フィールドは YANG `leafref /vrf:sonic-vrf/vrf:VRF/vrf:VRF_LIST/vrf:name` で `VRF` テーブルを参照する。`VRF` エントリが存在しない状態でこれらのテーブルに `vrf_name` を設定すると YANG バリデーションで reject される。
- **発見種別**: YANG leafref 被参照（`VRF` が削除されると orphan）

### 6. BGP_GLOBALS (CONFIG_DB) — VRF 存在前提

- **方向**: `BGP_GLOBALS.<vrf_name>` → `VRF.name` への leafref (YANG union)
- **場所**: `sonic-bgp-globals.yang`
- **内容**: `BGP_GLOBALS|<vrf_name>` の key は `default` または `VRF.name` への leafref union として定義される。`VRF` エントリが削除されると対応 `BGP_GLOBALS` は orphan になり `bgpcfgd` が `"non-default VRF {} was not configured"` でエラーする。
- **発見種別**: YANG leafref 被参照（VRF 削除時の orphan リスク）

### 7. BGP_NEIGHBOR / BGP_NEIGHBOR_AF / BGP_PEER_GROUP / BGP_PEER_GROUP_AF (CONFIG_DB) — 間接依存

- **方向**: `BGP_NEIGHBOR|<vrf_name>|<neighbor>` の key `vrf_name` → `BGP_GLOBALS.vrf_name` への leafref
- **場所**: `sonic-bgp-neighbor.yang`
- **内容**: `BGP_NEIGHBOR` は直接 `VRF` を leafref するのではなく `BGP_GLOBALS.vrf_name` を leafref する。VRF 削除 → BGP_GLOBALS orphan → BGP_NEIGHBOR orphan という連鎖依存がある。
- **発見種別**: 間接 leafref 依存（2 ホップ）

### 8. STATIC_ROUTE (CONFIG_DB) — VRF-aware key

- **方向**: `STATIC_ROUTE|<vrf_name>|<prefix>` の key に VRF 名を直接埋め込む
- **場所**: `sonic-static-route.yang`; `staticroutemgrd`
- **内容**: VRF-aware 形式の `STATIC_ROUTE` は `<vrf_name>` をキーの第 1 要素として持つ。YANG leafref での参照ではなく key 埋め込み形式。`staticroutemgrd` は `vrf_name` が `"default"` / `"mgmt"` / `"Vrf..."` 形式かを判断して FRR へルートを投入する。VRF が未存在でも CONFIG_DB 書き込みは reject されないが FRR への反映で失敗する可能性がある。
- **発見種別**: key 埋め込み参照（leafref 非強制）

### 9. PIM_GLOBALS / PIM_INTERFACE (CONFIG_DB) — VRF key

- **方向**: `PIM_GLOBALS|<vrf>|<af>` および `PIM_INTERFACE|<vrf>|<af>|<interface>` の key に VRF 名を埋め込む
- **場所**: `sonic-pim.yang` (推定)
- **内容**: PIM 設定テーブルは VRF 名を key 要素として持つ。VRF が削除されても PIM テーブルのエントリは自動削除されない。frr-mgmt-framework が VRF の存在を前提にルーターに設定を投入する。
- **発見種別**: key 埋め込み参照

### 10. Linux ルーティングテーブル ID プール（ハードコード外部リソース）

- **方向**: `vrfmgrd` → カーネル ルーティングテーブル ID (1001–5096) 割り当て
- **場所**: `vrfmgr.cpp` L12-15
- **内容**: `VRF` エントリ追加のたびに vrfmgrd が `VRF_TABLE_START=1001` 〜 `VRF_TABLE_END=5097` の範囲でカーネルルーティングテーブル ID を消費する。CONFIG_DB フィールドに現れない外部リソース。4096 VRF 超で `getFreeTable()=0` となり Linux VRF 作成失敗。
- **発見種別**: 隠れたリソース上限（CONFIG_DB 非表現）

---

## 参照タイプ別サマリ

| テーブル / リソース | DB / 媒体 | 方向 | 契機 | 備考 |
|-------------------|-----------|------|------|------|
| `STATE_VRF_TABLE` | STATE_DB | READ | `*_INTERFACE.vrf_name` 設定時 | readiness ガード |
| `VRF_OBJECT_TABLE` | STATE_DB | READ/WRITE | VRF 削除・SAI 作成 | 2 フェーズ削除同期 |
| `MGMT_VRF_CONFIG` | CONFIG_DB | READ | vrfmgrd 起動時 | `mgmt` VRF 特例制御 |
| `VXLAN_TUNNEL_MAP` | CONFIG_DB | WRITE | `VRF.vni` 非ゼロ設定/解除 | 自動 evpn_map エントリ生成 |
| `INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` / `LOOPBACK_INTERFACE` / `VLAN_SUB_INTERFACE` | CONFIG_DB | READ (leafref) | YANG バリデーション | VRF 削除で orphan |
| `BGP_GLOBALS` | CONFIG_DB | READ (leafref) | YANG バリデーション | VRF 削除で orphan |
| `BGP_NEIGHBOR` 等 | CONFIG_DB | READ (間接) | BGP_GLOBALS 経由 2 ホップ | VRF 削除連鎖 orphan |
| `STATIC_ROUTE` | CONFIG_DB | key 埋め込み | staticroutemgrd 処理時 | leafref 強制なし |
| `PIM_GLOBALS` / `PIM_INTERFACE` | CONFIG_DB | key 埋め込み | frr-mgmt-framework | leafref 強制なし |
| Linux ルーティングテーブル ID | カーネル | WRITE | VRF 追加時 | 最大 4096 件 |
