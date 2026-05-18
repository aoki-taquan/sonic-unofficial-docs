# SAG ハードコード定数 調査証跡 (Phase E)

**調査日**: 2026-05-18  
**対象テーブル**: `SAG|GLOBAL`  
**調査者**: Agent (batch256)

## 調査ソース

| ソース | 確認内容 |
|--------|---------|
| `sonic-swss-common/common/schema.h:127` | `APP_SAG_TABLE_NAME = "SAG_TABLE"` |
| `sonic-swss-common/common/schema.h:393` | `CFG_SAG_TABLE_NAME = "SAG"` |
| `SONiC/doc/sag/sag-HLD.md` §DB | キー `SAG\|GLOBAL` シングルトン構造、`gateway_mac` フィールド定義 |
| `SONiC/doc/sag/sag-HLD.md` §YANG | `sonic-static-anycast-gateway.yang`: `gateway_mac` の YANG 型 `yang:mac-address` |
| `SONiC/doc/sag/sag-HLD.md` §sonic-swss | `static_anycast_gateway` デフォルト `false`、SAI 属性 `SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS` の再利用 |

## 検出した定数

### スキーマキー定数 (schema.h)

| 定数名 | 値 | 定義箇所 |
|-------|----|---------|
| `CFG_SAG_TABLE_NAME` | `"SAG"` | `sonic-swss-common/common/schema.h:393` |
| `APP_SAG_TABLE_NAME` | `"SAG_TABLE"` | `sonic-swss-common/common/schema.h:127` |

### シングルトンキー

| 項目 | 値 | 備考 |
|-----|-----|------|
| テーブルキー | `"GLOBAL"` | HLD §DB に直接文字列リテラルとして記載。YANG `GLOBAL` コンテナ名と一致。コード実装不確認（swss master に SAG 実装なし） |
| フルキー | `"SAG\|GLOBAL"` | `CFG_SAG_TABLE_NAME + "|GLOBAL"` の組み合わせ |
| APPL_DB キー | `"SAG_TABLE\|GLOBAL"` | `APP_SAG_TABLE_NAME + "|GLOBAL"` |

### YANG デフォルト値

| フィールド | テーブル | YANG デフォルト | ソース |
|-----------|---------|---------------|--------|
| `static_anycast_gateway` | `VLAN_INTERFACE` | `false` | HLD §YANG: `default false;` in `sonic-vlan.yang` VLAN_INTERFACE_LIST |
| `gateway_mac` | `SAG` | なし (必須) | HLD §YANG: `type yang:mac-address;` (default 節なし) |

### SAI 属性（既存流用・新規追加なし）

| 属性名 | 備考 |
|-------|------|
| `SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS` | 既存 SAI RIF 属性を流用。HLD §SAI API: "There are no changes to SAI headers/implementation to support this feature." |

## コード確認状況

sonic-swss master ブランチに `sagmgr.cpp` / `sagorch.cpp` 等の独立した SAG 実装が存在しない（`schema.h` の定数定義のみ確認済み）。  
HLD §High-Level Design では `intfmgrd` / `IntfsOrch` を拡張する設計が記載されているが、現行コードでは当該拡張が未マージまたは別実装手段で統合済みの可能性がある。

定数値はすべて HLD の記述と `schema.h` の定数定義を根拠とする。
