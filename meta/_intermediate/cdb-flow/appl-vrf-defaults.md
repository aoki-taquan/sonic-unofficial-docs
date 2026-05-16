# APPL_DB VRF_TABLE — Phase A フィールドデフォルト調査メモ

調査日: 2026-05-15
対象テーブル: APPL_DB `VRF_TABLE` (APP_VRF_TABLE_NAME)
対象ページ: `docs/reference/config-db/appl-vrf.md`

## 調査対象ソース

- `sonic-swss/orchagent/vrforch.cpp` (rev: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/vrforch.h` (同上)
- `sonic-swss/cfgmgr/vrfmgr.cpp` (同上)
- `sonic-swss-common/common/schema.h` (rev: 158de8d3463ff4b841653f6d57190bb142b80d9c)

---

## テーブル名確認

`schema.h:80`:
```cpp
#define APP_VRF_TABLE_NAME "VRF_TABLE"
```

`orchdaemon.cpp`:
```cpp
VRFOrch *vrf_orch = new VRFOrch(m_applDb, APP_VRF_TABLE_NAME,
                                m_stateDb, STATE_VRF_OBJECT_TABLE_NAME);
```

---

## 書き込み主体

`vrfmgr.cpp:303`:
```cpp
m_appVrfTableProducer.set(vrfName, kfvFieldsValues(t));
```

`vrfmgrd` は CONFIG_DB の全フィールドをそのまま `kfvFieldsValues(t)` で pass-through する。デフォルト補完・フィールド追加はしない。

---

## フィールド別 暗黙デフォルト (VRFOrch::addOperation)

### `v4` (SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE)

- **コード由来デフォルト**: フィールド省略時は SAI attrs に追加されない → SAI/ASIC 側のデフォルト値が使用される
- CONFIG_DB `sonic-vrf.yang` に `v4` フィールド定義なし。通常の `config vrf add` では APP_DB に書き込まれない
- VNET テーブル経由でのみ到達する残存コード

```cpp
// vrforch.cpp:38-42
if (name == "v4")
{
    attr.id = SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE;
    attr.value.booldata = request.getAttrBool("v4");
}
```

### `v6` (SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE)

- `v4` と同様。省略時は SAI デフォルト依存
- YANG 未定義。通常経路では APP_DB に書き込まれない

```cpp
// vrforch.cpp:43-47
else if (name == "v6")
{
    attr.id = SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE;
    attr.value.booldata = request.getAttrBool("v6");
}
```

### `src_mac` (SAI_VIRTUAL_ROUTER_ATTR_SRC_MAC_ADDRESS)

- **コード由来デフォルト**: 省略時は SAI attrs に追加されない → SAI がスイッチ MAC を適用
- YANG 未定義。CONFIG_DB `VRF` テーブル経由では書き込まれない

```cpp
// vrforch.cpp:48-53
else if (name == "src_mac")
{
    const auto& mac = request.getAttrMacAddress("src_mac");
    attr.id = SAI_VIRTUAL_ROUTER_ATTR_SRC_MAC_ADDRESS;
    memcpy(attr.value.mac, mac.getMac(), sizeof(sai_mac_t));
}
```

### `ttl_action` (SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_TTL1_PACKET_ACTION)

- **コード由来デフォルト**: 省略時は SAI attrs に追加されない → SAI デフォルト (通常 `SAI_PACKET_ACTION_TRAP`)
- YANG 未定義

```cpp
// vrforch.cpp:54-58
else if (name == "ttl_action")
{
    attr.id = SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_TTL1_PACKET_ACTION;
    attr.value.s32 = request.getAttrPacketAction("ttl_action");
}
```

### `ip_opt_action` (SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_IP_OPTIONS_PACKET_ACTION)

- `ttl_action` と同様の構造。省略時は SAI デフォルト

```cpp
// vrforch.cpp:59-63
else if (name == "ip_opt_action")
{
    attr.id = SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_IP_OPTIONS_PACKET_ACTION;
    attr.value.s32 = request.getAttrPacketAction("ip_opt_action");
}
```

### `l3_mc_action` (SAI_VIRTUAL_ROUTER_ATTR_UNKNOWN_L3_MULTICAST_PACKET_ACTION)

- `ttl_action` と同様の構造。省略時は SAI デフォルト

```cpp
// vrforch.cpp:64-68
else if (name == "l3_mc_action")
{
    attr.id = SAI_VIRTUAL_ROUTER_ATTR_UNKNOWN_L3_MULTICAST_PACKET_ACTION;
    attr.value.s32 = request.getAttrPacketAction("l3_mc_action");
}
```

### `vni` — コード由来デフォルト `0`

- **コード由来デフォルト**: `uint32_t vni = 0` (`vrforch.cpp:30`)
- `vni == 0` なら VNI マッピング処理 (`updateVrfVNIMap`) はスキップ
- `vni != 0` のとき `continue` で SAI attrs には追加せず、別途 `updateVrfVNIMap()` を呼ぶ

```cpp
// vrforch.cpp:30
uint32_t vni = 0;
// vrforch.cpp:69-73
else if (name == "vni")
{
    vni = static_cast<uint32_t>(request.getAttrUint(name));
    continue;  // SAI attrs には追加しない
}
// vrforch.cpp:111-118
if (vni != 0)
{
    SWSS_LOG_INFO("VRF '%s' vni %d add", vrf_name.c_str(), vni);
    error = updateVrfVNIMap(vrf_name, vni);
    ...
}
```

### `mgmtVrfEnabled` / `in_band_mgmt_enabled` — explicit ignore

- **コード由来デフォルト**: 読み飛ばし (`continue`)。SAI attrs にも追加されない
- `SWSS_LOG_INFO("MGMT VRF field: %s ignored")` が出力されるのみ

```cpp
// vrforch.cpp:74-78
else if ((name == "mgmtVrfEnabled") || (name == "in_band_mgmt_enabled"))
{
    SWSS_LOG_INFO("MGMT VRF field: %s ignored", name.c_str());
    continue;
}
```

### `fallback` — dead field (宣言のみ・ハンドラなし)

- **宣言**: `vrforch.h:34`: `{ "fallback", REQ_T_BOOL }` として `request_description` に登録
- **ハンドラなし**: `vrforch.cpp` `addOperation` のすべての if/else チェーンに `"fallback"` 分岐が存在しない
- **帰結**: `else` ブランチに落ちて `SWSS_LOG_ERROR("Logic error: Unknown attribute: %s")` → フィールド破棄
- vrfmgr は pass-through するため CONFIG_DB に書かれた `fallback=true` が APP_DB に届くが、orchagent で silent drop

---

## STATE_DB への書き戻し

VRFOrch は VRF 作成/更新成功後に `STATE_VRF_OBJECT_TABLE` に `"state"="ok"` を書き込む (`vrforch.cpp:120, 150`)。削除時は `m_stateVrfObjectTable.del(vrf_name)` (`vrforch.cpp:193`)。

---

## 発見まとめ

| フィールド | ハンドラ | SAI 属性 | コード由来デフォルト |
|-----------|---------|---------|------------------|
| `v4` | 実装あり | `ADMIN_V4_STATE` | 省略時 = SAI デフォルト (YANG 未定義) |
| `v6` | 実装あり | `ADMIN_V6_STATE` | 省略時 = SAI デフォルト (YANG 未定義) |
| `src_mac` | 実装あり | `SRC_MAC_ADDRESS` | 省略時 = SAI がスイッチ MAC 適用 (YANG 未定義) |
| `ttl_action` | 実装あり | `VIOLATION_TTL1_PACKET_ACTION` | 省略時 = SAI デフォルト (通常 TRAP) |
| `ip_opt_action` | 実装あり | `VIOLATION_IP_OPTIONS_PACKET_ACTION` | 省略時 = SAI デフォルト |
| `l3_mc_action` | 実装あり | `UNKNOWN_L3_MULTICAST_PACKET_ACTION` | 省略時 = SAI デフォルト |
| `vni` | 実装あり (VNI map) | SAI 非直接 | `uint32_t vni = 0` (マッピングなし) |
| `mgmtVrfEnabled` | explicit ignore | なし | silent skip |
| `in_band_mgmt_enabled` | explicit ignore | なし | silent skip |
| `fallback` | **なし (dead)** | なし | **silent drop at orchagent** |
