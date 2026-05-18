# tunnel-decap-table — Phase H: プラットフォーム差・SAI capability 分岐

## 調査対象

slug: tunnel-decap-table
phase: platform (プラットフォーム差・SAI capability 分岐)
調査日: 2026-05-18

## ソース

- `orchagent/tunneldecaporch.cpp` (4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/tunneldecaporch.h` (同リポジトリ)

## 調査結果

### 1. SAI create-only 属性によるプラットフォーム間差異

`SAI_TUNNEL_ATTR_DECAP_ECN_MODE` と `SAI_TUNNEL_ATTR_ENCAP_ECN_MODE` は SAI 仕様上 create-only。
tunneldecaporch.cpp:L179 / L195 が更新試行をスキップして WARN/NOTICE ログを出力する:

```cpp
SWSS_LOG_WARN("Skip setting ecn_mode since the SAI attribute SAI_TUNNEL_ATTR_DECAP_ECN_MODE is create only");
SWSS_LOG_NOTICE("Skip setting encap_ecn_mode since the SAI attribute SAI_TUNNEL_ATTR_ENCAP_ECN_MODE is create only");
```

これは SAI 仕様準拠の共通挙動であり、特定ベンダーに依存しない。
一部ベンダー SAI では create-only でない実装もあるが、orchagent は保守的に create-only として扱う。

### 2. OVERLAY_RIF_DEFAULT_MTU = 9100 — ベンダー SAI デフォルト非依存

`#define OVERLAY_RIF_DEFAULT_MTU 9100` (tunneldecaporch.cpp:L14) でオーバーレイ loopback RIF の MTU を
ハードコード。SAI プラットフォームデフォルト (通常 1500 または 9000) より大きい値を明示設定することで
VXLAN/IP-in-IP カプセルパケットの断片化を防ぐ。この値はプラットフォーム問わず固定。

### 3. subnet decap — ハードコードトンネル名による制約

`subnetDecapConfig.tunnel = "IPINIP_SUBNET"` / `subnetDecapConfig.tunnel_v6 = "IPINIP_SUBNET_V6"`
がハードコードされている。subnet decap を有効にするためにはこの名前で TUNNEL を作成しなければならず、
プラットフォーム・構成に関わらず名前変更は不可。

### 4. IPv4 / IPv6 デュアルスタック対応

`src_ip_v6` フィールドのサポートは tunneldecaporch:L604-L619 で実装されているが、
`TUNNEL_DECAP_TABLE` APPL_DB テーブルとして実際に投入できるかどうかは tunnelmgrd の
実装と YANG スキーマに依存する（YANG 未定義のため事実上 APPL_DB 直書きのみ）。

### 5. SAI capability query なし

tunneldecaporch は orchagent 起動時に `sai_query_attribute_enum_values_capability()` を
呼ばない。プラットフォーム capability に応じた動作分岐は存在せず、全プラットフォームで
同一の SAI 属性セットを使用する。SAI が特定の属性を非サポートの場合はエラーログのみ。

## 結論

tunneldecaporch のプラットフォーム差は SAI capability query による動的分岐ではなく、
「SAI create-only 属性の更新スキップ」と「OVERLAY_RIF_DEFAULT_MTU のハードコード」が
主要な関心点。subnet decap の名前制約もプラットフォーム独立のコード側制約。
