# vxlan-evpn-nvo — Phase G: 通信メカニズム調査

## 調査対象ソース

- `sonic-swss/cfgmgr/vxlanmgrd.cpp` (main エントリポイント)
- `sonic-swss/cfgmgr/vxlanmgr.cpp` (VxlanMgr クラス)
- `sonic-swss/orchagent/vxlanorch.cpp` (EvpnNvoOrch クラス)
- `sonic-swss/orchagent/vxlanorch.h` (EvpnNvoOrch 定義)
- `sonic-swss/orchagent/orchdaemon.cpp` (orchagent 登録)

## CONFIG_DB Consumer 構造

### vxlanmgrd (cfgmgr コンテナ)

`vxlanmgrd.cpp:46-53` で `CFG_VXLAN_EVPN_NVO_TABLE_NAME` を含む table リストを構築し、`VxlanMgr` コンストラクタに渡す。`VxlanMgr` は `Orch(cfgDb, tables)` を継承し、swsscommon の `ConsumerStateTable` (cfgmgr 系は `Orch` ベースクラス経由) で CONFIG_DB を購読する。

メインループ (`vxlanmgrd.cpp:88-116`):
- `swss::Select s` に `vxlanmgr.getSelectables()` を登録
- `s.select(&sel, 1000ms)` でイベント待機 (SELECT_TIMEOUT=1000ms)
- イベント検出時は `c->execute()` → `VxlanMgr::doTask(Consumer&)` が呼ばれる

`doTask` (`vxlanmgr.cpp:213-285`) では `table_name == CFG_VXLAN_EVPN_NVO_TABLE_NAME` の場合:
- `SET_COMMAND` → `doVxlanEvpnNvoCreateTask(t)`
- `DEL_COMMAND` → `doVxlanEvpnNvoDeleteTask(t)`

### orchagent (EvpnNvoOrch)

`orchdaemon.cpp:358`: `new EvpnNvoOrch(m_applDb, APP_VXLAN_EVPN_NVO_TABLE_NAME)` で **APPL_DB** を購読。`EvpnNvoOrch` は `Orch2` を継承し、内部で `ConsumerStateTable` を使用する。

`EvpnNvoOrch::addOperation` (`vxlanorch.cpp:2775-2788`):
- `request.getAttrString("source_vtep")` で vtep_name を取得
- `VxlanTunnelOrch` から VTEP ポインタを取得してキャッシュ

## SAI tunnel_map_api 呼び出し

`vxlanorch.cpp:28`: `extern sai_tunnel_api_t *sai_tunnel_api;`

tunnel_map_api 主要呼び出し:
- `sai_tunnel_api->create_tunnel_map(...)` (`vxlanorch.cpp:141-145`): MAP_T に応じた SAI_TUNNEL_MAP_TYPE_* でトンネルマップ作成
- `sai_tunnel_api->remove_tunnel_map(tunnel_map_id)` (`vxlanorch.cpp:163`): マップ削除

MAP_T → SAI_TUNNEL_MAP_TYPE 対応 (`vxlanorch.cpp:40-46`):
- VNI_TO_VLAN_ID → SAI_TUNNEL_MAP_TYPE_VNI_TO_VLAN_ID
- VLAN_ID_TO_VNI → SAI_TUNNEL_MAP_TYPE_VLAN_ID_TO_VNI
- VRID_TO_VNI → SAI_TUNNEL_MAP_TYPE_VIRTUAL_ROUTER_ID_TO_VNI
- VNI_TO_VRID → SAI_TUNNEL_MAP_TYPE_VNI_TO_VIRTUAL_ROUTER_ID
- BRIDGE_TO_VNI → SAI_TUNNEL_MAP_TYPE_BRIDGE_IF_TO_VNI
- VNI_TO_BRIDGE → SAI_TUNNEL_MAP_TYPE_VNI_TO_BRIDGE_IF

※ EVPN_NVO エントリ自体は SAI tunnel_map_api を直接呼ばない。VTEP ポインタキャッシュのみ行い、実際の SAI API 呼び出しは VxlanTunnelOrch / VxlanTunnelMapOrch が担当する。

## 購読者まとめ

| 購読者 | DB | テーブル | API 種別 | ハンドラ |
|--------|-----|---------|---------|---------|
| `vxlanmgrd` (VxlanMgr) | CONFIG_DB | `VXLAN_EVPN_NVO` | ConsumerStateTable (Orch継承) | `doVxlanEvpnNvoCreateTask` / `doVxlanEvpnNvoDeleteTask` |
| orchagent (EvpnNvoOrch) | APPL_DB | `APP_VXLAN_EVPN_NVO_TABLE` | ConsumerStateTable (Orch2継承) | `EvpnNvoOrch::addOperation` / `delOperation` |

## イベントフロー

```
CONFIG_DB HSET "VXLAN_EVPN_NVO|nvo1" source_vtep vtep1
  ↓ Redis keyspace → vxlanmgrd の ConsumerStateTable バッファ
Select::select(1000ms) が検出
  ↓ VxlanMgr::doTask() → doVxlanEvpnNvoCreateTask()
  ↓ isTunnelActive(vtep) チェック (失敗時 return false → リトライ)
  ↓ disableLearningForAllVxlanNetdevices() 実行
  ↓ m_appEvpnNvoTable.set() → APPL_DB "APP_VXLAN_EVPN_NVO_TABLE|nvo1" 書込
APPL_DB 書込 → orchagent EvpnNvoOrch が ConsumerStateTable で検出
  ↓ EvpnNvoOrch::addOperation() → VxlanTunnelOrch から VTEP ポインタ取得・キャッシュ
  (SAI 直接呼び出しなし — VTEP オブジェクトはすでに VxlanTunnelOrch が sai_tunnel_api で作成済み)
```

## 参照コード

- `sonic-swss/cfgmgr/vxlanmgrd.cpp:26-123` (vxlanmgrd main)
- `sonic-swss/cfgmgr/vxlanmgr.cpp:183-205` (VxlanMgr コンストラクタ)
- `sonic-swss/cfgmgr/vxlanmgr.cpp:213-285` (doTask ルーター)
- `sonic-swss/cfgmgr/vxlanmgr.cpp:672-735` (doVxlanEvpnNvoCreateTask / DeleteTask)
- `sonic-swss/orchagent/orchdaemon.cpp:358` (EvpnNvoOrch 登録)
- `sonic-swss/orchagent/vxlanorch.h:541-557` (EvpnNvoOrch クラス定義)
- `sonic-swss/orchagent/vxlanorch.cpp:2773-2814` (EvpnNvoOrch::addOperation / delOperation)
- `sonic-swss/orchagent/vxlanorch.cpp:28,124-165` (sai_tunnel_api 宣言・tunnel_map 関数)
