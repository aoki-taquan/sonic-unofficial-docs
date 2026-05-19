# state-vrf Phase H — プラットフォーム差異調査メモ

調査対象:
- sonic-swss/cfgmgr/vrfmgr.cpp
- sonic-swss/orchagent/vrforch.cpp
- sonic-swss/cfgmgr/intfmgr.cpp
- sonic-swss/cfgmgr/vxlanmgr.cpp

調査日: 2026-05-19

## VRF_TABLE / VRF_OBJECT_TABLE の書き込みロジック

vrfmgr.cpp および vrforch.cpp のいずれにも以下の参照は存在しない:
- switch_type
- voq / VOQ
- chassis / is_chassis
- multi_asic
- platform
- DEVICE_METADATA

→ 書き込みロジック自体はプラットフォーム非依存。

## mgmt VRF の非対称性 (全プラットフォーム共通の特殊ケース)

MGMT_VRF ("mgmt") は通常の VRF とは異なる処理パスを持つ:
1. setLink() では MGMT_VRF_TABLE_ID = 6000 を固定使用し、
   "ip link add mgmt type vrf table 6000" を実行しない (vrfmgr.cpp:176-182)
2. VRFOrch は mgmt VRF の SAI VR を作成しないため、
   VRF_OBJECT_TABLE|mgmt は書き込まれない (vrforch.cpp — mgmt VRF 向け分岐なし)
3. VRF_TABLE|mgmt は vrfmgrd が書き込む (vrfmgr.cpp:289, CFG_MGMT_VRF_CONFIG_TABLE_NAME)

この非対称性は mgmt VRF の設定有無 (MGMT_VRF_CONFIG.mgmtVrfEnabled) に依存し、
特定 ASIC や switch_type には非依存。

## intfmgrd における switch_type 参照

intfmgr.cpp:70-75: switch_type を DEVICE_METADATA から読み込み、mySwitchType に保存
intfmgr.cpp:103: mySwitchType == "voq" の場合のみ IPv6 アドレス追加に metric 256 を付加

これは VRF_TABLE の読み取り (intfmgr.cpp:671, 680) とは別ロジック。
VRF_TABLE の get() は switch_type に関わらず同一コードパスで実行される。

## vxlanmgr.cpp

switch_type / voq / chassis 参照なし。
VRF_TABLE への get() polling は全プラットフォームで同一。

## 結論

VRF_TABLE / VRF_OBJECT_TABLE の書き込み動作にプラットフォーム差異なし。
唯一の特殊ケースは mgmt VRF の非対称性だが、これはハードウェア種別ではなく
mgmtVrfEnabled 設定フラグに依存する。
