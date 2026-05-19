# dpu-eni Phase H — プラットフォーム差調査

## 調査対象

`DPU` / `REMOTE_DPU` / `VDPU` / `DASH_ENI_FORWARD_TABLE` — DashEniFwdOrch の
プラットフォーム依存性を `orchdaemon.cpp` および `dashenifwdorch.cpp` から調査。

## 主要な分岐条件

### 1. SmartSwitch サブタイプ限定 (orchdaemon.cpp:613)

```cpp
if (gMySwitchSubType == "SmartSwitch")
{
    DashEniFwdOrch *dash_eni_fwd_orch = new DashEniFwdOrch(...);
    ...
}
```

`gMySwitchSubType` は `DEVICE_METADATA|localhost.switch_sub_type` から設定される。
`"SmartSwitch"` 以外ではこのブロックに入らず、`DashEniFwdOrch` は存在しない。
つまり非 SmartSwitch プラットフォームでは `DPU` / `REMOTE_DPU` / `VDPU` テーブルを
CONFIG_DB に書いても一切処理されない。

### 2. DPU ロール (`gMySwitchType == "dpu"`) との分離

`gMySwitchType == "dpu"` の場合は `DpuOrchDaemon` が使われ、DASH ACL / VNet / Route
等の DASH 系オーケストレータが動く。これは SmartSwitch の **DPU カード側** の処理。
NPU 側 SmartSwitch (`gMySwitchSubType == "SmartSwitch"`) で動く `DashEniFwdOrch` とは
完全に異なる Daemon であり、`DPU`/`REMOTE_DPU`/`VDPU` テーブルは NPU 側のみが消費する。

### 3. LOCAL / CLUSTER DPU タイプによる分岐 (dashenifwdorch.cpp)

SAI ベンダー依存は基本なし。ただし ACL ルールへの変換は:
- LOCAL DPU → NeighOrch 経由の Neighbor 解決が必要 (ARP/NDP 依存)
- CLUSTER DPU → VxLAN トンネル OID の存在が必要 (事前にトンネル設定が必要)

いずれも SAI 種別に依存しない。

### 4. ASIC 種別依存

`DashEniFwdOrch` → `AclOrch` 経由で ACL ルールを SAI に反映するため、間接的に
`AclOrch` の platform 分岐 (broadcom / mellanox 等) に依存する。ただし ENI 転送 ACL は
`ACL_TABLE_TYPE_TABLE` に新規タイプを自動定義して使用するため (dashenifwdorch.cpp:403-450)、
standard ACL type の platform 差 (MIRRORV6 可否・L3V4V6 可否等) は ENI 転送には影響しない。

## まとめ

| 観点 | 結果 |
|------|------|
| SmartSwitch 非対応プラットフォーム | DashEniFwdOrch 非存在。DPU/ENI テーブルは無効 |
| DPU ロール (`switch_type=dpu`) | DpuOrchDaemon が動作。DPU/VDPU テーブルは NPU 側消費なし |
| ASIC 種別 (broadcom/mellanox/etc.) | 間接依存 (AclOrch 経由)。ENI 転送専用 ACL タイプを自前定義するため主要な差なし |
| VOQ chassis | SmartSwitch と排他。DashEniFwdOrch は非起動 |
| multi-asic | SmartSwitch 構成では単一 ASIC を想定。multi-asic では DashEniFwdOrch 非起動 |
