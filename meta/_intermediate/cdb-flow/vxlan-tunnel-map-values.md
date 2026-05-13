# VXLAN_TUNNEL_MAP — 値依存挙動メモ

## vlan: Vlan<id> (string pattern)
- mandatory true
- pattern 'Vlan([0-9]{1,3}|[1-3][0-9]{3}|[4][0][0-8][0-9]|[4][0][9][0-4])' (sonic-vxlan.yang)
- leafref は libyang バックリンク問題でコメントアウト → VLAN 存在確認は実装側のみ
- 重複 vlan マッピング → "Vlan %s already mapped" でエラー (vxlanmgr.cpp)

## vni: vnid_type (0..16777215)
- mandatory true
- 重複 VNI → "VNI %d already mapped" でエラー (vxlanmgr.cpp)

## mapname (string)
- ユーザ任意のラベル
- 重複キー → "Map already present" でエラー

Sources:
- sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vxlan.yang
- sonic-swss/cfgmgr/vxlanmgr.cpp
