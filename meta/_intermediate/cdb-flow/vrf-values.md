# VRF — 値依存挙動メモ

## fallback: true / false
- YANG default: false
- true → 指定 VRF からデフォルト経路へフォールバック (ip rule add ... lookup main)
- false → 当該 VRF の経路テーブルのみ参照

## vni: 0..16777215
- YANG default: 0
- 0 → L3 VNI マッピングなし
- 0 以外 → EVPN L3 VNI マッピングを設定 (vrfmgr.cpp doVrfVxlanTableUpdate)
- 重複 VNI は vrfmgr.cpp が "vni %d is already mapped to vrf %s" でエラー
- VRF の VNI 再マップも "vrf %s is already mapped to vni %d" でエラー

## name: Vrf[a-zA-Z0-9_-]+
- "Vrf" プレフィクス必須
- sonic-cfggen / orchagent が "Vrf" で始まる名前を VRF として認識

Sources:
- sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vrf.yang
- sonic-swss/cfgmgr/vrfmgr.cpp
