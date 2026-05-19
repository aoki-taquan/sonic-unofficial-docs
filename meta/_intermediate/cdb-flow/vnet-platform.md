# VNET / VNET_ROUTE — Phase H: プラットフォーム差・SAI Capability 分岐スキャン

生成日: 2026-05-19
対象ページ: `docs/reference/config-db/vnet.md`
対象ファイル:
- `sonic-swss/orchagent/vnetorch.cpp`
- `sonic-swss/orchagent/vnetorch.h`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/cfgmgr/vxlanmgr.cpp`
- `sonic-swss/orchagent/orch.h`

---

## プラットフォーム分岐スキャン結果

### 1. Ordered ECMP Capability (SAI_NEXT_HOP_GROUP_TYPE_DYNAMIC_ORDERED_ECMP)

`VNetRouteOrch` が VNET_ROUTE_TUNNEL の ECMP Next Hop Group を作成する際、
`gSwitchOrch->checkOrderedEcmpEnable()` の戻り値に基づいて NHG type を切り替える。

```cpp
// vnetorch.cpp:804
nhg_attr.value.s32 = gSwitchOrch->checkOrderedEcmpEnable()
    ? SAI_NEXT_HOP_GROUP_TYPE_DYNAMIC_ORDERED_ECMP
    : SAI_NEXT_HOP_GROUP_TYPE_ECMP;
```

- `checkOrderedEcmpEnable()` が true (SAI capability + CONFIG_DB で有効化) の場合:
  `SAI_NEXT_HOP_GROUP_TYPE_DYNAMIC_ORDERED_ECMP` — ASIC が endpoint の優先順序を保持
- false の場合: `SAI_NEXT_HOP_GROUP_TYPE_ECMP` — 通常 ECMP

`SAI_NEXT_HOP_GROUP_TYPE_DYNAMIC_ORDERED_ECMP` をサポートしない ASIC では、
`create_next_hop_group()` が失敗するか SAI がフォールバックする。
`checkOrderedEcmpEnable()` はスイッチ capability を事前クエリして有効化を判定するため、
capability 非対応 ASIC では自動的に通常 ECMP が使われる。

Evidence: `vnetorch.cpp:804`, `vnetorch.cpp:841`, `vnetorch.cpp:2778`

### 2. VNET_EXEC モード (VRF vs BRIDGE)

`vnetorch.h` では `VNET_EXEC` 列挙型に `VNET_EXEC_VRF` と `VNET_EXEC_BRIDGE` が定義されているが、
`orchdaemon.cpp:276` では常に `VNET_EXEC::VNET_EXEC_VRF` (デフォルト引数) で `VNetOrch` が生成される。
現行 community SONiC では BRIDGE モードは使われない。

Evidence: `vnetorch.h:63-67`, `orchdaemon.cpp:276`

### 3. ベンダー固有コードの有無

`vnetorch.cpp` / `vxlanmgr.cpp` に `platform` 環境変数参照・ベンダー文字列判定コード・ASIC 型分岐は存在しない。
VNET の SAI API (`sai_virtual_router_api->create_virtual_router()` / `sai_route_api->*` / `sai_next_hop_group_api->*`) は
標準 SAI インタフェース経由で呼ばれ、ASIC 固有の最適化は SAI 実装層に委譲される。

### 4. VXLAN SAI 型とポート番号

VXLAN トンネルは `SAI_TUNNEL_TYPE_VXLAN` で作成される (`vxlanorch.cpp:304`)。
UDP 宛先ポート (標準 4789) の変更はコード上構成不可。
`SAI_TUNNEL_ATTR_DECAP_TTL_MODE` や `SAI_TUNNEL_ATTR_ENCAP_TTL_VAL` が
ASIC ごとに異なる挙動を示す可能性があるが、vnetorch.cpp には分岐がなく標準値を使用。

### 5. VoQ / Multi-ASIC 非対応

VNET テーブルの処理に VoQ (Virtualizing Queue) / multi-ASIC 分岐コードは存在しない。
VNET は単一 ASIC 構成を前提とした機能。

---

## 結論

VNET テーブルのコード経路には明示的なベンダー/ASIC 分岐はなく、
唯一の SAI capability 依存点は **Ordered ECMP** の有効化判定のみ。
プラットフォーム差は SAI 実装側に委譲される設計。

---

## `<!-- platform -->` ブロック用テキスト案

```markdown
<!-- platform -->
## プラットフォーム / SAI Capability 差異 (Phase H)

### Ordered ECMP サポート — ASIC Capability 依存

`VNetRouteOrch` が `VNET_ROUTE_TUNNEL` の ECMP Next Hop Group を作成する際、`gSwitchOrch->checkOrderedEcmpEnable()` の SAI capability 問い合わせ結果に基づいて NHG type を決定する (`vnetorch.cpp:804`)。

| ASIC capability | NHG type | 動作 |
|----------------|---------|------|
| Ordered ECMP 対応かつ有効化 | `SAI_NEXT_HOP_GROUP_TYPE_DYNAMIC_ORDERED_ECMP` | endpoint の優先順序を ASIC が保持 |
| 非対応または無効 | `SAI_NEXT_HOP_GROUP_TYPE_ECMP` | 通常 ECMP (ラウンドロビン) |

`checkOrderedEcmpEnable()` は起動時に SAI switch attribute をクエリし、ASIC が非対応の場合は false を返す。このため非対応 ASIC で Ordered ECMP ビットが設定されることはなく、`create_next_hop_group()` 失敗は発生しない。

### ベンダー固有コードなし

`vnetorch.cpp` / `vxlanmgr.cpp` には `platform` 環境変数参照・ベンダー文字列判定 (`mellanox` / `broadcom` 等) が存在しない。VNET の SAI 操作 (`sai_virtual_router_api` / `sai_route_api` / `sai_next_hop_group_api`) は標準 SAI インタフェース経由で呼ばれ、ASIC 固有の最適化は SAI 実装層に委譲される。

### VNET_EXEC モード (VRF 固定)

`vnetorch.h` では `VNET_EXEC_VRF` と `VNET_EXEC_BRIDGE` の 2 モードが定義されているが、`orchdaemon.cpp:276` では常に `VNET_EXEC_VRF` が使用される。コミュニティ SONiC では BRIDGE モードは無効。

### VoQ / Multi-ASIC

VNET テーブル処理に VoQ / multi-ASIC 分岐は存在しない。VNET は単一 ASIC 構成を前提とした機能。

> **スキャン証跡**: `vnetorch.cpp:804,841,2778`（Ordered ECMP NHG type 分岐）、`vnetorch.h:63-67`（VNET_EXEC enum）、`orchdaemon.cpp:276`（VRF モード固定）、`vxlanmgr.cpp` 全体（ベンダー分岐 0 件確認）
<!-- /platform -->
```
