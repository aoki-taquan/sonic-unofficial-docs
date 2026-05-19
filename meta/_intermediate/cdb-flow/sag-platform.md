# SAG — Phase H platform 調査メモ

## 調査日

2026-05-19

## 調査対象

- HLD: `SONiC/doc/sag/sag-HLD.md` (sha=49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
- sonic-swss master: `cfgmgr/intfmgr.cpp`, `orchagent/intfsorch.cpp`
- sonic-swss-common: `common/schema.h` (sha=158de8d3463ff4b841653f6d57190bb142b80d9c)

## 結論

**SAG はプラットフォーム非依存**。

HLD §SAI API に "There are no changes to SAI headers/implementation to support this feature." と明記されている[^1]。また、sonic-swss master に SAG 専用の実装コードは存在せず（`sagmgr.cpp` / `sagorch.cpp` 不在、`intfmgr.cpp` / `intfsorch.cpp` にも SAG ハンドラは未マージ）、コードレベルでの ASIC ベンダー・`platform` / `sub_platform`・`gMySwitchType` 分岐を確認できない。

SAG の本質は VLAN インターフェースの SAI RIF 属性 `SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS` を仮想 MAC に差し替えるだけである。この属性はすべての主要 ASIC ベンダー（Broadcom / Mellanox(NVIDIA) / Marvell / Barefoot）が SAI v1 時点からサポートしており、ASIC 依存の分岐は不要。

## コード調査結果

| ファイル | SAG 関連コード | 備考 |
|---------|--------------|------|
| `cfgmgr/intfmgrd.cpp` | `cfg_intf_tables` に `CFG_SAG_TABLE_NAME` なし | 未マージ |
| `cfgmgr/intfmgr.cpp` | SAG / anycast / gateway_mac への参照なし | 未マージ |
| `orchagent/intfsorch.cpp` | SAG_TABLE 購読なし | 未マージ |
| `common/schema.h` | `CFG_SAG_TABLE_NAME="SAG"`, `APP_SAG_TABLE_NAME="SAG_TABLE"` 定数のみ | 存在確認済み |

## platform 差異まとめ

| 観点 | 詳細 |
|-----|------|
| SAI 属性変更有無 | なし（既存 `SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS` を使用） |
| ASIC ベンダー分岐 | なし |
| VOQ / chassis 考慮 | なし（HLD に記載なし、master コードにも分岐なし） |
| SmartSwitch DPU | なし（DPU 固有処理なし） |
| `switch_type` 分岐 | なし |
| Warmboot / Fastboot | 影響なし（HLD §Warmboot and Fastboot に明記） |

[^1]: SAG HLD: `SONiC/doc/sag/sag-HLD.md`. https://github.com/sonic-net/SONiC/blob/49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06/doc/sag/sag-HLD.md
