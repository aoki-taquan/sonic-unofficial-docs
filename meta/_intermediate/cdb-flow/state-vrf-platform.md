# state-vrf Phase H — プラットフォーム差分

調査日: 2026-05-19
対象ファイル: docs/reference/config-db/state-vrf.md
ソース: sonic-swss/cfgmgr/vrfmgr.cpp, sonic-swss/orchagent/vrforch.cpp

## 発見された主なプラットフォーム差異

### 1. mgmt VRF — VRF_TABLE のみ、VRF_OBJECT_TABLE は存在しない

`vrfmgr.cpp` は `MGMT_VRF_CONFIG_TABLE_NAME` からのイベントを処理するが、
VRFOrch (`vrforch.cpp`) は mgmt VRF に対して `sai_virtual_router_api->create_virtual_router()` を
呼ばない（APP_VRF_TABLE から mgmt という名前のエントリを受信しても SAI VR を作らない設計）。

このため mgmt VRF が有効な構成では:
- `STATE_DB VRF_TABLE|mgmt` → 存在する（vrfmgrd が書き込む）
- `STATE_DB VRF_OBJECT_TABLE|mgmt` → 存在しない（VRFOrch が書かない）

### 2. mgmt VRF の Linux VRF デバイス削除スキップ

`vrfmgr.cpp` 起動時の `processExistingVrfs()` でカーネルに既存 mgmt VRF デバイスが
見つかった場合、cold boot では `ip link del mgmt` をスキップする（vrfmgr.cpp:73-79）:
```cpp
if (vrfName.compare("mgmt") == 0)
{
    SWSS_LOG_NOTICE("Skipping remove vrf device %s", vrfName.c_str());
    rowType = LINK_ROW;
    break;
}
```
ルーティングテーブル ID の払い出しも mgmt VRF のみ固定値 `MGMT_VRF_TABLE_ID=6000` を使用
（vrfmgr.cpp:180）。他の VRF は `VRF_TABLE_START=1001` から動的に払い出す。

### 3. VNET VRF — VRF_TABLE のみ、VRF_OBJECT_TABLE は存在しない

`CFG_VXLAN_EVPN_NVO_TABLE_NAME` 経由で作成された VNET VRF は vrfmgrd が
`m_appVnetTableProducer` を使って VNETOrch へ通知する。VNETOrch は SAI VR オブジェクトを
管理するが `VRF_OBJECT_TABLE` への書き込みは行わない。VRFOrch は VNET VRF の APP_DB エントリを
処理しないため、`VRF_OBJECT_TABLE|<vnet_vrf>` は存在しない。

### 4. warm-reboot — ルーティングテーブル ID の引き継ぎ

`WarmStart::isWarmStart()` が true の場合、`processExistingVrfs()` でカーネルから読み取った
既存 VRF のルーティングテーブル ID を `m_vrfTableMap` に引き継ぐ（vrfmgr.cpp:65-69）。
Cold boot 時は同じ VRF デバイスを削除して再作成するため、ID が変わる可能性がある。
STATE_DB への書き込み（`m_stateVrfTable.set()`）自体は warm/cold 共通で発生する。

### 5. gMySwitchType / fabric / SmartSwitch との関係

vrforch.cpp, vrfmgr.cpp のいずれにも `gMySwitchType`、`platform` 環境変数チェック、
SmartSwitch/fabric ポート分岐は存在しない。VRF_TABLE / VRF_OBJECT_TABLE の書き込みロジックは
スイッチタイプに依存しない共通パス。

## 結論

STATE_DB の VRF 系テーブルに関するプラットフォーム差は主に「エントリが存在するかどうか」の
非対称性として現れる:
- 通常 VRF: VRF_TABLE + VRF_OBJECT_TABLE の両方が存在
- mgmt VRF: VRF_TABLE のみ（VRF_OBJECT_TABLE は常に不在）
- VNET VRF: VRF_TABLE のみ（VRFOrch 管轄外のため VRF_OBJECT_TABLE は不在）

これらの非対称性は `vrfmgrd` の削除ループ（`isVrfObjExist()` チェック）の挙動にも影響する。
