# TUNNEL_DECAP_TERM_TABLE — Phase E ハードコード定数調査

調査日: 2026-05-17
対象ファイル:
- `sonic-swss/orchagent/tunneldecaporch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/tunnelmgr.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## CONFIG_DB 非連動のハードコード定数

以下は TUNNEL_DECAP_TERM_TABLE のフィールドで上書き不可、
またはコードに直書きされていて APPL_DB 値から独立している定数。

### SAI 固定属性

| 定数 / グローバル変数 | 値 / 型 | 定義場所 | 用途 |
|---|---|---|---|
| `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_VR_ID` → `gVirtualRouterId` | デフォルト VRF OID (起動時に switch から取得) | `tunneldecaporch.cpp` L921-923 | 全 term entry に強制付与。VRF 選択はフィールドで変更不可 |
| `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_TUNNEL_TYPE` → `SAI_TUNNEL_TYPE_IPINIP` | 固定 enum 値 | `tunneldecaporch.cpp` L940-942 | トンネルタイプは常に IPINIP。VXLAN 等は別 Orch が担当 |
| `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_ACTION_TUNNEL_ID` → 親トンネル OID | 実行時 OID | `tunneldecaporch.cpp` L944-946 | `tunnelTable[tunnel_name].tunnel_id` から取得。直接指定不可 |

### term_type → SAI マッピング (静的テーブル)

`doDecapTunnelTermTask()` (L342-345) が `DecapTermTypes` 静的マップでキー→列挙変換する。
`addDecapTunnelTermEntry()` (L925-938) は以下の固定マッピングで SAI enum を設定する。

| APPL_DB `term_type` 文字列 | SAI 属性値 | 定義場所 |
|---|---|---|
| `"P2P"` | `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2P` | `tunneldecaporch.cpp` L928 |
| `"P2MP"` | `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2MP` | `tunneldecaporch.cpp` L932 |
| `"MP2MP"` | `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_MP2MP` | `tunneldecaporch.cpp` L936 |

これら以外の文字列は `DecapTermTypes.find()` で miss → `LOG_ERROR("invalid tunnel decap term type")` → エントリ消費スキップ。

### フィールドが存在しても SAI に渡らない属性

| フィールド | SAI に渡る条件 |
|---|---|
| `src_ip` | `term_type == P2P` または `term_type == MP2MP` の場合のみ `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_SRC_IP` に設定 (L948-959)。`P2MP` では SAI に渡さない |
| `src_ip` マスク部 | `term_type == MP2MP` のみ `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_SRC_IP_MASK` (L968-970) |
| `dst_ip` マスク部 | `term_type == MP2MP` のみ `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_DST_IP_MASK` (L972-974) |
| `subnet_type` | SAI には一切渡さない。orchagent 内部ステートと STATE_DB のみ |

### 有効 subnet_type 値 (静的コード定数)

`doDecapTunnelTermTask()` L426-434 が `subnet_type` を検証する。
許可値は `"vlan"` と `"vip"` のみ。コードにハードコードされており、YANG では定義されない。

## ソース参照

- `tunneldecaporch.cpp` L342-345: DecapTermTypes 静的マップ
- `tunneldecaporch.cpp` L361: term_type デフォルト初期値 `TUNNEL_TERM_TYPE_P2MP`
- `tunneldecaporch.cpp` L426-434: subnet_type 有効値チェック
- `tunneldecaporch.cpp` L921-946: SAI 固定属性付与
- `tunneldecaporch.cpp` L948-974: IP アドレス属性の条件付き設定
