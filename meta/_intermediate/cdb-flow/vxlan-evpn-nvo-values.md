# VXLAN_EVPN_NVO — 値依存挙動メモ

## source_vtep (leafref)
- mandatory true
- 参照先 VXLAN_TUNNEL が active でない場合 "NVO %s creation failed. VTEP not present" でリトライ

## NVO 作成後の副作用
- disableLearningForAllVxlanNetdevices() を呼び出してすべての VXLAN netdev の MAC learning を無効化
- EVPN コントロールプレーン前提の動作 (vxlanmgr.cpp)

## max-elements 1
- YANG による制約
- vxlanmgr.cpp でもキャッシュで重複チェック ("Only Single NVO object allowed")

## enum 無しページ
- フィールドは source_vtep (leafref) と name (string) のみ
- 実質的な enum 値なし

Sources:
- sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vxlan.yang
- sonic-swss/cfgmgr/vxlanmgr.cpp
