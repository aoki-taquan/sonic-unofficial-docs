# route-constants.md — Phase E ハードコード定数

ソース: `sonic-swss/orchagent/routeorch.cpp`  
ref: `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## SAI route_entry 属性定数

| 定数名 | 値 | 用途 |
|--------|-----|------|
| `SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION` | SAI 属性 ID | route の packet action を指定するアトリビュート |
| `SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID` | SAI 属性 ID | route の next hop OID を指定するアトリビュート |
| `SAI_ROUTE_ENTRY_ATTR_PREFIX_AGG_ID` | SAI 属性 ID | route の prefix aggregation ID を指定するアトリビュート |
| `SAI_PACKET_ACTION_DROP` | SAI enum | blackhole / デフォルト route の packet action（破棄） |
| `SAI_PACKET_ACTION_FORWARD` | SAI enum | 通常 route の packet action（転送） |

コード上の使用箇所 (`routeorch.cpp`):
```cpp
// 初期化: IPv4/IPv6 デフォルト経路を DROP でプログラム
attr.id = SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION;
attr.value.s32 = SAI_PACKET_ACTION_DROP;   // routeorch.cpp:138-139

// blackhole 経路のプログラム
route_attr.id = SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION;
route_attr.value.s32 = SAI_PACKET_ACTION_DROP;  // routeorch.cpp:2281-2282

// 通常 unicast 経路のプログラム (デフォルトは FORWARD)
/* Default SAI_ROUTE_ATTR_PACKET_ACTION is SAI_PACKET_ACTION_FORWARD */
route_attr.value.s32 = SAI_PACKET_ACTION_FORWARD;  // routeorch.cpp:2315
```

---

## デフォルト VRF OID

| 変数名 | 型 | 宣言 | 意味 |
|--------|----|------|------|
| `gVirtualRouterId` | `sai_object_id_t` | `extern` (orchdaemon.cpp で定義) | デフォルト VRF（グローバルルーティングインスタンス）の SAI OID |

- orchagent 初期化時に SAI から取得・設定される。
- `ROUTE_TABLE:<prefix>`（VRF prefix なし）のキーは自動的に `gVirtualRouterId` に対してプログラムされる (`routeorch.cpp:721`)。
- デフォルト経路 (`0.0.0.0/0`, `::/0`) も `gVirtualRouterId` に紐付く (`routeorch.cpp:133, 151, 171`)。

---

## Bulk batch size

| 定数名 | 値 | 定義場所 | 意味 |
|--------|----|---------|------|
| `DEFAULT_MAX_BULK_SIZE` | `1000` | `orchdaemon.cpp:81` | `gMaxBulkSize` のデフォルト値 |
| `gMaxBulkSize` | `size_t`、起動時に `DEFAULT_MAX_BULK_SIZE` で初期化 | `orchdaemon.cpp:82` | RouteBulker・NhgMemberBulker 等の共有 batch 上限 |

`gRouteBulker`, `gLabelRouteBulker`, `gNextHopGroupMemberBulker` はすべて `gMaxBulkSize` を上限として構築される (`routeorch.cpp:41-43`):

```cpp
gRouteBulker(sai_route_api, gMaxBulkSize),
gLabelRouteBulker(sai_mpls_api, gMaxBulkSize),
gNextHopGroupMemberBulker(sai_next_hop_group_api, gSwitchId, gMaxBulkSize),
```

`gMaxBulkSize` は orchagent 起動オプション (`--bulk-size`) で上書き可能 (`main.cpp:552`)。

---

## ECMP グループ数デフォルト

| 定数名 | 値 | 意味 |
|--------|----|------|
| `DEFAULT_NUMBER_OF_ECMP_GROUPS` | `128` | SAI クエリ失敗時のフォールバック ECMP グループ数上限 |
| `DEFAULT_MAX_ECMP_GROUP_SIZE` | `32` | Mellanox プラットフォーム補正係数（`m_maxNextHopGroupCount /= 32`） |

コード (`routeorch.cpp:37-38, 68, 86`):
```cpp
#define DEFAULT_NUMBER_OF_ECMP_GROUPS   128
#define DEFAULT_MAX_ECMP_GROUP_SIZE     32

m_maxNextHopGroupCount = DEFAULT_NUMBER_OF_ECMP_GROUPS;  // SAI 失敗時フォールバック
// Mellanox 補正:
m_maxNextHopGroupCount /= DEFAULT_MAX_ECMP_GROUP_SIZE;
```

---

## VRF prefix 文字列

| 定数名 | 値 | 定義場所 | 意味 |
|--------|----|---------|------|
| `VRF_PREFIX` | `"Vrf"` | `orchagent/nexthopkey.h:20` | VRF 名の必須プレフィックス。`Vrf` で始まるキーは VRF ルックアップを実施 |

`routeorch.cpp` での使用:
```cpp
if (!key.compare(0, strlen(VRF_PREFIX), VRF_PREFIX))  // routeorch.cpp:706
```

---

## link-local prefix 定数

| 定数 | 値 | 意味 |
|------|----|------|
| `default_link_local_prefix` | `"fe80::/10"` | 全 link-local パケットを CPU に転送するサブネット route |

orchagent 起動時に `gVirtualRouterId` 配下に `SAI_PACKET_ACTION_FORWARD` + CPU ポート nexthop でプログラムされる (`routeorch.cpp:187-189`)。
