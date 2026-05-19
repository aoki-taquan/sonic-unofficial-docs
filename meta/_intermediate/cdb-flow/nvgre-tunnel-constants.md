# NVGRE_TUNNEL / NVGRE_TUNNEL_MAP — Phase E ハードコード定数スキャンノート

対象テーブル: `NVGRE_TUNNEL`, `NVGRE_TUNNEL_MAP`
Consumer: `NvgreTunnelOrch`, `NvgreTunnelMapOrch` (`sonic-swss/orchagent/nvgreorch.cpp`)
スキャン範囲: `nvgreorch.cpp` + `nvgreorch.h` 全行精読

---

## 検出したハードコード定数

### VSID 上限値

```cpp
// nvgreorch.cpp:7
#define NVGRE_VSID_MAX_VALUE 16777214
```

- `NvgreTunnelMapOrch::addOperation()` L496 で `vsid > NVGRE_VSID_MAX_VALUE` チェックに使用。
- 24bit 最大値 (2^24 - 2 = 16777214)。RFC 7637 の VSID 範囲上限。
- CONFIG_DB / YANG の `vsid` フィールドの range (0..16777214) と一致。

### MAP タイプ固定セット

```cpp
// nvgreorch.cpp:16-19
static const std::vector<map_type_t> nvgreMapTypes = {
    MAP_T_VLAN,
    MAP_T_BRIDGE
};
```

- `NvgreTunnel` 構築時に常時 MAP_T_VLAN と MAP_T_BRIDGE の 2 種類のマッパーオブジェクト (Encap + Decap 計 4 個) を作成する。ユーザー設定で変更不可。

### SAI トンネルタイプ固定

- `SAI_TUNNEL_TYPE_NVGRE` — nvgreorch.cpp:177 で `sai_create_tunnel()` に渡す固定値。
- `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2MP` — nvgreorch.cpp:241 で termination entry に固定。

### SAI マップタイプ定数

```cpp
// nvgreorch.cpp:21-24 (Encap)
MAP_T_VLAN   → SAI_TUNNEL_MAP_TYPE_VLAN_ID_TO_VSID
MAP_T_BRIDGE → SAI_TUNNEL_MAP_TYPE_BRIDGE_IF_TO_VSID

// nvgreorch.cpp:31-34 (Decap)
MAP_T_VLAN   → SAI_TUNNEL_MAP_TYPE_VSID_TO_VLAN_ID
MAP_T_BRIDGE → SAI_TUNNEL_MAP_TYPE_BRIDGE_IF_TO_VSID
```

### グローバル SAI オブジェクト参照

| 定数 | 型 | 値の出所 | 用途 | ソース |
|------|----|---------|------|--------|
| `gUnderlayIfId` | `sai_object_id_t` | orchagent 起動時に main.cpp が初期化 | `sai_create_tunnel()` の underlay RIF 引数として渡す | `nvgreorch.cpp:312` |
| `gVirtualRouterId` | `sai_object_id_t` | orchagent 起動時に main.cpp が初期化 | `sai_create_tunnel_termination()` の VR OID として渡す | `nvgreorch.cpp:313` |
| `gSwitchId` | `sai_object_id_t` | orchagent 起動時に main.cpp が初期化 | SAI オブジェクト作成時に switch_id として渡す | `nvgreorch.cpp` 各所 |

---

## 定数サマリ

| 定数 | 値 | 変更可否 | ソース |
|------|----|---------|--------|
| `NVGRE_VSID_MAX_VALUE` | `16777214` | 不可 (コード固定) | `nvgreorch.cpp:7` |
| MAP タイプセット | `{MAP_T_VLAN, MAP_T_BRIDGE}` | 不可 | `nvgreorch.cpp:16-19` |
| SAI トンネルタイプ | `SAI_TUNNEL_TYPE_NVGRE` | 不可 | `nvgreorch.cpp:177` |
| SAI termination タイプ | `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2MP` | 不可 | `nvgreorch.cpp:241` |
| `gUnderlayIfId` | 起動時 SAI 初期化値 | 不可 (実行時) | `nvgreorch.cpp:312` |
| `gVirtualRouterId` | 起動時 SAI 初期化値 | 不可 (実行時) | `nvgreorch.cpp:313` |
