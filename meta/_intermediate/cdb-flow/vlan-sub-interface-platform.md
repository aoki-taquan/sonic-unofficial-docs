# vlan-sub-interface — Phase H Platform Differences

## 調査概要

調査日: 2026-05-19  
対象ソース:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`

## 調査結果

`<!-- platform-diff -->` タグとして既にページに記述されていたプラットフォーム差異セクションを `<!-- platform -->` に正規化した。内容は変更なし。

### 主なプラットフォーム差異

1. **VOQ Chassis**: `switch_type == "voq"` の場合、IPv6 アドレス付与時に `metric 256` を追加（`intfmgr.cpp:103-106`）。system_port 上の VLAN_SUB_INTERFACE は非サポート。
2. **SmartSwitch DPU**: DPU 側は独立管理。`intfmgr.cpp` に DPU 固有分岐なし。
3. **Mellanox (Spectrum)**: `SAI_ROUTER_INTERFACE_TYPE_SUB_PORT` をネイティブサポート。固有分岐なし。
4. **Broadcom**: `SAI_ROUTER_INTERFACE_TYPE_SUB_PORT` をサポート。固有分岐なし。SAI 実装側で VLAN tag 処理。

## 証跡

- `sonic-swss/cfgmgr/intfmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/intfmgr.cpp>
- `sonic-swss/orchagent/intfsorch.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/intfsorch.cpp>
