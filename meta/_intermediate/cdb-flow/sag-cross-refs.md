# SAG — 暗黙参照テーブル調査 (Phase C)

調査日: 2026-05-18  
根拠: `SONiC/doc/sag/sag-HLD.md` (sha=49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06) + `sonic-swss-common/common/schema.h` (sha=158de8d)  
注: sonic-swss の current master に SAG 固有実装ファイル (sagmgr.cpp / sagorch.cpp) は確認できず、HLD ベースの調査。

## 特定した暗黙参照

### 1. `VLAN_INTERFACE|<name>` (CONFIG_DB)

- **参照方向**: `SAG|GLOBAL` → `VLAN_INTERFACE` への条件付き参照
- `intfmgrd` は `VLAN_INTERFACE|<n>.static_anycast_gateway=true` が検出されると `SAG|GLOBAL.gateway_mac` を参照し、値を `APPL_DB:SAG_TABLE|GLOBAL.gateway_mac` へ書き込む。
- HLD より: "The SAG gateway_mac value will be set as the RIF MAC if static_anycast_gateway=true" (sag-HLD.md §Architecture)

### 2. `SAG_TABLE|GLOBAL` (APPL_DB)

- **参照方向**: `SAG|GLOBAL` → `SAG_TABLE|GLOBAL` への書込み (CONFIG_DB → APPL_DB)
- `intfmgrd` が `SAG|GLOBAL` の変化を検知し、`APPL_DB:SAG_TABLE|GLOBAL.gateway_mac` を SET/DEL する。
- キー変換: `SAG|GLOBAL` → `SAG_TABLE|GLOBAL`（キー構造はシングルトン、完全対応）。
- `schema.h:127`: `#define APP_SAG_TABLE_NAME "SAG_TABLE"`
- `schema.h:393`: `#define CFG_SAG_TABLE_NAME "SAG"`

### 3. VLAN RIF MAC (SAI) — `SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS`

- **参照方向**: `APPL_DB:SAG_TABLE|GLOBAL` → orchagent (IntfsOrch) → SAI RIF
- `IntfsOrch` が `APPL_DB:SAG_TABLE|GLOBAL` を消費し、`static_anycast_gateway=true` のすべての VLAN インターフェースの RIF の `SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS` を `gateway_mac` に差し替える。
- HLD 記載のシーケンス図で確認。

### 4. `VLAN_INTERFACE|<n>` (CONFIG_DB) — `vrf_name` 参照

- SAG 有効化後、VLAN インターフェースが所属する VRF の RIF コンテキストで `gateway_mac` が適用される。
- `vrf_name` が設定されている場合は VRF RIF に適用される（HLD §DB schema: "vrf_name" フィールドが一例として記載）。

## 暗黙参照がない項目

- RouteOrch: MAC 変更時の IPv6 link-local route の del/add は `intfsorch` → `RouteOrch API` 経由で実行されるが、`SAG|GLOBAL` テーブルの direct な参照先ではなく、下流の副次処理。

## SAI 変更なし

HLD §SAI API: "There are no changes to SAI headers/implementation to support this feature."  
SAI 属性 `SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS` は既存属性を流用。
