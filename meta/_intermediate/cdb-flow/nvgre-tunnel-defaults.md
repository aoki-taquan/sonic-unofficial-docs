# NVGRE_TUNNEL / NVGRE_TUNNEL_MAP フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象テーブル: CONFIG_DB `NVGRE_TUNNEL` / `NVGRE_TUNNEL_MAP`

## 調査対象ファイル

- `sonic-swss/orchagent/nvgreorch.cpp`
- `sonic-swss/orchagent/nvgreorch.h`

---

## 結論 (要約)

NVGRE 関連 2 テーブルには **コード由来のフィールドデフォルトは存在しない**。
すべてのフィールドが `request_description_t` の必須リストに列挙されており、未指定の場合は `request_parser` 段階で reject される。
ただし SAI 層に渡される構造的な「ハードコード値」「外部依存値」「ハードコード上限」が複数存在するため、本書ではそれらを列挙する。

---

## フィールド別 暗黙デフォルト調査

### `NVGRE_TUNNEL.tunnel_name` (key)

**コード由来デフォルト**: なし (key は必須、`REQ_T_STRING`)

```cpp
// nvgreorch.h:31-37
const request_description_t nvgre_tunnel_request_description = {
            { REQ_T_STRING },
            {
                { "src_ip", REQ_T_IP },
            },
            { "src_ip" }
};
```

- key の自動採番・デフォルト名は無い。CLI / RESTCONF 利用者が任意の文字列を指定する。
- 名前長制約は YANG 側 `string (1..255)` のみで、orchagent には範囲チェックなし。

### `NVGRE_TUNNEL.src_ip`

**コード由来デフォルト**: なし (mandatory フィールド)

```cpp
// nvgreorch.h:36
{ "src_ip" }   // 必須フィールドリストに含まれる
```

```cpp
// nvgreorch.cpp:354
auto src_ip = request.getAttrIP("src_ip");
```

- `request_description_t` の第 3 要素 (mandatory_attr_fields) に `"src_ip"` が登録されているため、未指定または不正なフォーマット時は `request_parser` が例外を投げて orchagent が WARN を出す。
- ローカル loopback IP との一致チェックは orchagent には**なく**、任意の IP アドレスを受け入れる (運用ヒント側でのみ「ローカル loopback を指定」を推奨)。

### `NVGRE_TUNNEL_MAP.tunnel_map_name` (key)

**コード由来デフォルト**: なし

- 第二 key として CLI 側で任意指定。orchagent は文字列としてそのまま map table のキーに採用 (`NvgreTunnelMapTable` は `std::map<std::string, ...>`)。

### `NVGRE_TUNNEL_MAP.vlan_id`

**コード由来デフォルト**: なし (`REQ_T_VLAN`、mandatory)

```cpp
// nvgreorch.h:140-147
const request_description_t nvgre_tunnel_map_request_description = {
            { REQ_T_STRING, REQ_T_STRING },
            {
                { "vsid",  REQ_T_UINT },
                { "vlan_id", REQ_T_VLAN },
            },
            { "vsid", "vlan_id" }
};
```

- `vsid` と `vlan_id` の双方が必須フィールドリスト (第 3 要素) に含まれており、両者とも未指定は不可。

### `NVGRE_TUNNEL_MAP.vsid`

**コード由来デフォルト**: なし (`REQ_T_UINT`、mandatory)

- 上記同上。`vsid` は範囲チェック `NVGRE_VSID_MAX_VALUE = 16777214` がコード内で定義されているが、これは「上限定数」であり「デフォルト」ではない。

```cpp
// nvgreorch.cpp:7
#define NVGRE_VSID_MAX_VALUE 16777214
```

---

## SAI 層に渡されるハードコード値 (デフォルトではないが固定)

| 項目 | 値 | 由来 | 備考 |
|---|---|---|---|
| `SAI_TUNNEL_ATTR_TYPE` | `SAI_TUNNEL_TYPE_NVGRE` | `nvgreorch.cpp:142` | テーブル名から確定 |
| `SAI_TUNNEL_ATTR_UNDERLAY_INTERFACE` | `gUnderlayIfId` | `nvgreorch.cpp:146` | 起動時の grobal RIF (`switch.cpp` 由来) |
| `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_TYPE` | `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2MP` | `nvgreorch.cpp:225` | NVGRE は P2MP 固定 |
| `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_VR_ID` | `gVirtualRouterId` | `nvgreorch.cpp:229` | デフォルト VRF |
| `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_DST_IP` | `src_ip` (= encap 側と同一) | `nvgreorch.cpp:233` | dst termination で src と同じ IP を渡す (P2MP のため) |
| Mapper types | `MAP_T_VLAN`, `MAP_T_BRIDGE` の両方を常時生成 | `nvgreorch.cpp:16-19` | `nvgreMapTypes` static vector |
| Encap mapper | `SAI_TUNNEL_MAP_TYPE_VLAN_ID_TO_VSID` / `BRIDGE_IF_TO_VSID` | `nvgreorch.cpp:21-24` | テーブル無関係に常に両方作成 |
| Decap mapper | `SAI_TUNNEL_MAP_TYPE_VSID_TO_VLAN_ID` / `VSID_TO_BRIDGE_IF` | `nvgreorch.cpp:31-34` | 同上 |

---

## 範囲・上限定数 (デフォルトではないが固定)

| 項目 | 値 | 由来 |
|---|---|---|
| `NVGRE_VSID_MAX_VALUE` | `16777214` (= 2^24 - 2) | `nvgreorch.cpp:7` |
| VLAN ID 上限 | `4094` (`REQ_T_VLAN`) | request_parser 側 |

---

## 要約表

| フィールド | テーブル | コード由来デフォルト | 未指定時の挙動 | 証拠 |
|-----------|---------|-------------------|---------------|------|
| `tunnel_name` | NVGRE_TUNNEL | なし (key、必須) | request_parser reject | `nvgreorch.h:32` |
| `src_ip` | NVGRE_TUNNEL | なし (mandatory) | request_parser reject | `nvgreorch.h:36`, `nvgreorch.cpp:354` |
| `tunnel_map_name` | NVGRE_TUNNEL_MAP | なし (key、必須) | request_parser reject | `nvgreorch.h:141` |
| `vlan_id` | NVGRE_TUNNEL_MAP | なし (mandatory) | request_parser reject | `nvgreorch.h:144,146` |
| `vsid` | NVGRE_TUNNEL_MAP | なし (mandatory) | request_parser reject | `nvgreorch.h:143,146` |

---

## ソース引用

- `sonic-swss/orchagent/nvgreorch.h:31-37` — `nvgre_tunnel_request_description` (src_ip mandatory)
- `sonic-swss/orchagent/nvgreorch.h:140-147` — `nvgre_tunnel_map_request_description` (vsid/vlan_id mandatory)
- `sonic-swss/orchagent/nvgreorch.cpp:7` — `NVGRE_VSID_MAX_VALUE` 定数
- `sonic-swss/orchagent/nvgreorch.cpp:136-194` — `sai_create_tunnel` (SAI 固定属性)
- `sonic-swss/orchagent/nvgreorch.cpp:219-257` — `sai_create_tunnel_termination` (P2MP / default VR)
- `sonic-swss/orchagent/nvgreorch.cpp:336-342` — `NvgreTunnel` ctor (`createNvgreMappers()` + `createNvgreTunnel()` を常に両方実行)
