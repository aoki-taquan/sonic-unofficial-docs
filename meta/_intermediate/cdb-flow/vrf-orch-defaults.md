# APPL_DB VRF_TABLE — VRFOrch フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象テーブル: APPL_DB `VRF_TABLE` (APP_VRF_TABLE_NAME)

## 調査対象ファイル

- `sonic-swss/orchagent/vrforch.cpp` (VRFOrch::addOperation)
- `sonic-swss/orchagent/vrforch.h` (request_description, VRFRequest)
- `sonic-swss/cfgmgr/vrfmgr.cpp` (VrfMgr::doTask, setLink)
- `sonic-swss-common/common/schema.h` (APP_VRF_TABLE_NAME 定義)

---

## テーブル名確認

`schema.h:80`: `#define APP_VRF_TABLE_NAME "VRF_TABLE"`

`orchdaemon.cpp:283`:
```cpp
VRFOrch *vrf_orch = new VRFOrch(m_applDb, APP_VRF_TABLE_NAME,
                                m_stateDb, STATE_VRF_OBJECT_TABLE_NAME);
```

---

## フィールド別 暗黙デフォルト

### `v4` (SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE)

**コード由来デフォルト**: フィールド省略時は SAI 呼び出しに含まれない → SAI / ASIC 側デフォルト依存。

```cpp
// vrforch.cpp:39-42
if (name == "v4")
{
    attr.id = SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE;
    attr.value.booldata = request.getAttrBool("v4");
}
```

vrfmgr.cpp は CONFIG_DB `VRF` の全フィールドを `kfvFieldsValues(t)` でそのまま APP_DB へ pass-through する（`vrfmgr.cpp:303`）。CONFIG_DB `sonic-vrf.yang` に `v4`/`v6` の定義はなく、通常の `config vrf add` では書かれない。VNET テーブル経由の場合のみ到達。**通常運用では dead field 扱い。**

### `v6` (SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE)

`v4` と同様。

```cpp
// vrforch.cpp:44-47
else if (name == "v6")
{
    attr.id = SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE;
    attr.value.booldata = request.getAttrBool("v6");
}
```

### `src_mac` (SAI_VIRTUAL_ROUTER_ATTR_SRC_MAC_ADDRESS)

**コード由来デフォルト**: 省略時は SAI attrs に含まれず SAI 側デフォルト（スイッチ MAC）が適用される。

```cpp
// vrforch.cpp:48-53
else if (name == "src_mac")
{
    const auto& mac = request.getAttrMacAddress("src_mac");
    attr.id = SAI_VIRTUAL_ROUTER_ATTR_SRC_MAC_ADDRESS;
    memcpy(attr.value.mac, mac.getMac(), sizeof(sai_mac_t));
}
```

YANG `sonic-vrf.yang` に `src_mac` フィールド定義なし。CONFIG_DB `VRF` テーブル経由では書かれない。

### `ttl_action` (SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_TTL1_PACKET_ACTION)

**コード由来デフォルト**: 省略時は SAI attrs に含まれず SAI 側デフォルト（通常 `SAI_PACKET_ACTION_TRAP`）が適用される。

```cpp
// vrforch.cpp:54-58
else if (name == "ttl_action")
{
    attr.id = SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_TTL1_PACKET_ACTION;
    attr.value.s32 = request.getAttrPacketAction("ttl_action");
}
```

### `ip_opt_action` (SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_IP_OPTIONS_PACKET_ACTION)

`ttl_action` と同様の構造。省略時は SAI デフォルト。

```cpp
// vrforch.cpp:59-63
else if (name == "ip_opt_action")
{
    attr.id = SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_IP_OPTIONS_PACKET_ACTION;
    attr.value.s32 = request.getAttrPacketAction("ip_opt_action");
}
```

### `l3_mc_action` (SAI_VIRTUAL_ROUTER_ATTR_UNKNOWN_L3_MULTICAST_PACKET_ACTION)

同上。省略時は SAI デフォルト。

```cpp
// vrforch.cpp:64-68
else if (name == "l3_mc_action")
{
    attr.id = SAI_VIRTUAL_ROUTER_ATTR_UNKNOWN_L3_MULTICAST_PACKET_ACTION;
    attr.value.s32 = request.getAttrPacketAction("l3_mc_action");
}
```

### `vni`

**コード由来デフォルト**: `uint32_t vni = 0` (vrforch.cpp:30)。`0` は VNI マッピングなしを意味する。

```cpp
// vrforch.cpp:30
uint32_t vni = 0;
// vrforch.cpp:69-73
else if (name == "vni")
{
    vni = static_cast<uint32_t>(request.getAttrUint(name));
    continue;  // SAI attrs には追加しない
}
```

`vni` は SAI 属性には直接マップされず、`updateVrfVNIMap()` (vrforch.cpp:114) で VXLAN VRF マップ処理に渡す。

### `mgmtVrfEnabled` / `in_band_mgmt_enabled`

**Silent drop**: VRFOrch は明示的にこれらを無視する。

```cpp
// vrforch.cpp:74-78
else if ((name == "mgmtVrfEnabled") || (name == "in_band_mgmt_enabled"))
{
    SWSS_LOG_INFO("MGMT VRF field: %s ignored", name.c_str());
    continue;
}
```

### `fallback` (宣言のみ、ハンドラなし)

**Dead field**: `vrforch.h:34` で `{ "fallback", REQ_T_BOOL }` として宣言されているが、`vrforch.cpp` の `addOperation` に `"fallback"` の分岐が存在しない。`else` ブランチの `SWSS_LOG_ERROR("Logic error: Unknown attribute: %s")` に落ちてフィールドが破棄される。

---

## vrfmgr → orchagent 間のデフォルト補完

`vrfmgr.cpp:303`:
```cpp
m_appVrfTableProducer.set(vrfName, kfvFieldsValues(t));
```

vrfmgrd は CONFIG_DB フィールドを加工せずそのまま APP_DB へ転送する。デフォルト補完は行わない。フィールド省略はそのまま省略として orchagent に届く。

---

## Linux ルーティングテーブル割り当て（CONFIG_DB 非表現のハードコード）

```cpp
// vrfmgr.cpp:12-15
#define VRF_TABLE_START   1001
#define VRF_TABLE_END     5097
#define TABLE_LOCAL_PREF  1001
#define MGMT_VRF_TABLE_ID 6000
```

- 通常 VRF: テーブル ID `1001`〜`5096` をプールから順次割り当て（最大 **4096** 同時 VRF）
- mgmt VRF: 固定 `6000`、`ip link add` は実行しない（hostcfgd 側で作成済み）
- プール枯渇時: `getFreeTable()` が `0` を返し VRF 作成失敗

---

## STATE_DB への書き戻し

VRFOrch は VRF 作成/更新成功時に `STATE_VRF_OBJECT_TABLE` に `"state"="ok"` を書く (vrforch.cpp:120, 150)。削除時は `m_stateVrfObjectTable.del(vrf_name)` (vrforch.cpp:193)。これは vrfmgrd の削除タイミング制御（`isVrfObjExist()` チェック）に使用される。
