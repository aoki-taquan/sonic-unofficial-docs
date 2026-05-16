# l3-mc-table — Phase A: コード由来デフォルト調査メモ

調査日: 2026-05-15  
対象ページ: `docs/reference/config-db/l3-mc-table.md`  
ソース: `sonic-net/sonic-swss` (sha 4305596)

---

## 調査対象フィールド

`VRF` テーブル内の `l3_mc_action` フィールド（および関連する `v4`/`v6`/`src_mac`/`ttl_action`/`ip_opt_action`）。

---

## コード証跡

### vrforch.h:25-40 — request_description_t

```cpp
const request_description_t request_description = {
    { REQ_T_STRING },
    {
        { "v4",            REQ_T_BOOL },
        { "v6",            REQ_T_BOOL },
        { "src_mac",       REQ_T_MAC_ADDRESS },
        { "ttl_action",    REQ_T_PACKET_ACTION },
        { "ip_opt_action", REQ_T_PACKET_ACTION },
        { "l3_mc_action",  REQ_T_PACKET_ACTION },   // 任意フィールド
        { "fallback",      REQ_T_BOOL },
        { "vni",           REQ_T_UINT },
        { "mgmtVrfEnabled",       REQ_T_BOOL },
        { "in_band_mgmt_enabled", REQ_T_BOOL }
    },
    { } // no mandatory attributes — 必須フィールド指定なし
};
```

**結論**: 必須属性リストが `{ }` のため、`l3_mc_action` を含む全フィールドは省略可能。

### vrforch.cpp:64-68 — addOperation 内の分岐

```cpp
else if (name == "l3_mc_action")
{
    attr.id = SAI_VIRTUAL_ROUTER_ATTR_UNKNOWN_L3_MULTICAST_PACKET_ACTION;
    attr.value.s32 = request.getAttrPacketAction("l3_mc_action");
}
```

フィールドが CONFIG_DB に存在しない場合、この分岐は実行されない。  
→ `SAI_VIRTUAL_ROUTER_ATTR_UNKNOWN_L3_MULTICAST_PACKET_ACTION` は送出されない。  
→ ASIC のデフォルト動作が維持される（SAI 仕様では一般的に `SAI_PACKET_ACTION_TRAP`）。

---

## デフォルト値まとめ

| フィールド | YANG定義 | C++定数デフォルト | 実質デフォルト |
|-----------|---------|-----------------|-------------|
| `l3_mc_action` | なし | なし | SAI/ASIC実装依存（一般的にTRAP） |
| `v4` | なし | なし | SAI/ASIC実装依存 |
| `v6` | なし | なし | SAI/ASIC実装依存 |
| `ttl_action` | なし | なし | SAI/ASIC実装依存 |
| `ip_opt_action` | なし | なし | SAI/ASIC実装依存 |

---

## hard = 0 の根拠

- 明示的なハードコード定数（`= SOME_VALUE`）なし
- YANG `default` 文なし
- 実質デフォルトは「何も設定しない」= SAI/ASICベンダー実装依存

---

## docs ページへの反映状況

`docs/reference/config-db/l3-mc-table.md` の `<!-- defaults -->` セクション（行 240-283）にすでに反映済み。  
追加・修正なし（既存内容が正確であることをコード精読で確認）。
