# VLAN_MEMBER — 値依存挙動メモ

## tagging_mode: tagged / untagged / priority_tagged
- `untagged` → bridge vlan add ... pvid untagged。ポートは PVID として扱われる (vlanmgr.cpp:238-240)
- `priority_tagged` → bridge vlan add ... pvid untagged（untagged と同じ bridge コマンド） (vlanmgr.cpp:238-240)
- `tagged` → bridge vlan add ... （タグあり）
- その他の値 → SWSS_LOG_ERROR("Wrong tagging_mode") で破棄 (vlanmgr.cpp:659-662)
- 省略時デフォルト: `untagged` が補完される (vlanmgr.cpp:873)

## 制約挙動
- 1 ポートに `untagged` で複数 VLAN 割当は先勝ち（後から試みると STATE_DB 内で先勝ち）
- PORTCHANNEL メンバーを直接指定ではなく、PortChannel 親を指定すること

Sources:
- sonic-swss/cfgmgr/vlanmgr.cpp
- sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang
