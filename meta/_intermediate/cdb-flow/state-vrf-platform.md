# state-vrf Phase H — プラットフォーム差調査

調査日: 2026-05-19
対象ソース:
- `sonic-swss/cfgmgr/vrfmgr.cpp`
- `sonic-swss/orchagent/vrforch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/cfgmgr/vxlanmgr.cpp`

## 調査結果

### switch_type / ASIC 種別依存

`vrfmgr.cpp` および `vrforch.cpp` には `gMySwitchType`、`platform`、`ASIC_TYPE` 参照が一切存在しない。
VRFOrch の生成は `orchdaemon.cpp:283` で無条件に実行され、switch_type の分岐がない。
`FabricOrchDaemon`（switch_type="fabric"）では VRFOrch が起動しないため、fabric ノードは STATE_DB に
VRF_OBJECT_TABLE を書かない（VRFOrch 自体が存在しない）。

### VRF_TABLE（vrfmgrd 書込み）

`vrfmgrd` は Linux VRF デバイスとルーティングテーブル ID を管理するプロセス。
ASIC 種別・switch_type に依存しない。
- `VRF_TABLE_START=1001`, `VRF_TABLE_END=5097`, `MGMT_VRF_TABLE_ID=6000` はコード定数であり
  プラットフォームによって変わらない（vrfmgr.cpp:12-15）。
- `mgmtVrfEnabled` の処理は `CFG_MGMT_VRF_CONFIG_TABLE_NAME` 経由で全プラットフォーム共通。
- 例外: `FabricOrchDaemon` 環境では orchagent が VRF_OBJECT_TABLE を書かないため、vrfmgrd の
  削除待機ループ（`isVrfObjExist()` が常に false）が即座に完了する。
  ただし fabric ノードでは通常 VRF 設定自体が投入されない。

### VRF_OBJECT_TABLE（VRFOrch 書込み）

`vrforch.cpp` に platform 分岐なし。SAI `create_virtual_router()` / `remove_virtual_router()` の
成否のみに基づいて書き込む。
ベンダー SAI が `SAI_API_VIRTUAL_ROUTER` をサポートしない場合、orchagent 起動時に SAI 初期化エラー
が発生するため VRFOrch 自体が機能しない（VRF_OBJECT_TABLE に書き込まれない）。

### multi-asic / VOQ chassis

multi-asic 構成では各 asic namespace に独立した `vrfmgrd` と `VRFOrch` プロセスが存在し、
それぞれの namespace 内 STATE_DB に書き込む。VOQ chassis の linecard asic も同様。
フィールド・値・書込みロジックに namespace 間の差異はなく、書込みスコープが namespace に
閉じているだけである。

### 結論

VRF_TABLE / VRF_OBJECT_TABLE ともにプラットフォーム（ASIC 種別 / switch_type）による
フィールド差・挙動差は存在しない。
差異があるとすれば「fabric ノードでは VRFOrch が起動しない」点のみで、これは機能の
有無であり挙動差ではない。
