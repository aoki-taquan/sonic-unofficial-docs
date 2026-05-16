# MPLS orchagent — Phase E: ハードコード定数 詳細トレース

生成日: 2026-05-16
対象ソース: `sonic-net/sonic-swss orchagent/mplsrouteorch.cpp`
対象ページ: `docs/reference/config-db/appl-mpls-route.md`

> **注**: APPL_DB `LABEL_ROUTE_TABLE` に関する Phase E の詳細証跡は
> `meta/_intermediate/cdb-flow/appl-mpls-route-constants.md` にある。
> このファイルは `mplsrouteorch.cpp` を起点とする定数一覧を再掲・整理したもの。

## 目的

`orchagent/mplsrouteorch.cpp` が APPL_DB `LABEL_ROUTE_TABLE` 経路で使用する
ハードコード定数（MPLS label range、SAI inseg_entry_attr、packet_action enum、
pop/swap モード文字列）をソースコードから抽出し、行番号付き evidence を記録する。

## 訪問ファイル

| ファイル | 内容 |
|---------|------|
| `sonic-swss/orchagent/mplsrouteorch.cpp` | INSEG SAI 属性 / フィールド名リテラル / CRM 連動 |
| `sonic-swss/orchagent/label.h` | MPLS label 値範囲 / `LABEL_DELIMITER` / outseg type リテラル |
| `sonic-swss/orchagent/nexthopkey.h` | `LABELSTACK_DELIMITER` / `NH_DELIMITER` |
| `sonic-swss-common/common/schema.h` | `APP_LABEL_ROUTE_TABLE_NAME` |
| `sonic-swss/orchagent/crmorch.cpp` | CRM MPLS resource ↔ SAI 属性マップ |

---

## 1. MPLS label 値範囲（`label.h`）

RFC 3032 の 20-bit MPLS label フィールドに対応するハードコード上下限。

| マクロ | 値 | 行 | 用途 |
|--------|----|----|------|
| `LABEL_VALUE_MIN` | `0` | `label.h:15` | `to_uint<uint32_t>` 変換時の下限チェック |
| `LABEL_VALUE_MAX` | `0xFFFFF` (1048575) | `label.h:16` | 同上の上限チェック（20-bit 最大値） |
| `LABEL_DELIMITER` | `'/'` | `label.h:14` | label stack 区切り（`<l0>/<l1>/.../<lN>`） |

**参照証跡**:

```cpp
// label.h:47-49
tokenize(str.substr(4), LABEL_DELIMITER)
// 各要素を to_uint<uint32_t>(i, LABEL_VALUE_MIN, LABEL_VALUE_MAX) で変換
// 範囲外の label はパース時に例外スロー
```

---

## 2. SAI inseg_entry_attr（`mplsrouteorch.cpp`）

`addLabelRoute()` / `addLabelRoutePost()` で INSEG entry 作成・更新時に使用される SAI 属性 ID。

| SAI 属性 | 行 | 値の出処 |
|---------|----|---------|
| `SAI_INSEG_ENTRY_ATTR_PACKET_ACTION` | L612, L640, L648 | `SAI_PACKET_ACTION_FORWARD`（デフォルト）/ `SAI_PACKET_ACTION_DROP`（blackhole） |
| `SAI_INSEG_ENTRY_ATTR_NEXT_HOP_ID` | L617, L656 | NHG / 単一 NH の SAI object id（`next_hop_id`） |
| `SAI_INSEG_ENTRY_ATTR_NUM_OF_POP` | L621 | APPL_DB `mpls_pop` field を直接 map（uint32 / デフォルト 0） |
| `SAI_API_MPLS` | L781, L794, L835, L910 | `handleSaiSetStatus` / `handleSaiRemoveStatus` の引数 |

**参照証跡**:

```cpp
// mplsrouteorch.cpp:610-623 (addLabelRoute — create 分岐)
if (blackhole)
{
    inseg_attr.id = SAI_INSEG_ENTRY_ATTR_PACKET_ACTION;
    inseg_attr.value.s32 = SAI_PACKET_ACTION_DROP;
}
else
{
    inseg_attr.id = SAI_INSEG_ENTRY_ATTR_NEXT_HOP_ID;
    inseg_attr.value.oid = next_hop_id;
}
inseg_attrs.push_back(inseg_attr);
inseg_attr.id = SAI_INSEG_ENTRY_ATTR_NUM_OF_POP;
inseg_attr.value.u32 = ctx.pop_count;
inseg_attrs.push_back(inseg_attr);
/* Default SAI_INSEG_ENTRY_ATTR_PACKET_ACTION is SAI_PACKET_ACTION_FORWARD */
```

---

## 3. packet_action enum 値

| SAI enum 値 | 用途 |
|-------------|------|
| `SAI_PACKET_ACTION_FORWARD` | 正常転送（non-blackhole デフォルト）。L625 コメント参照 |
| `SAI_PACKET_ACTION_DROP` | blackhole ルート (`"blackhole"="true"`)、またはデフォルト NULL ルート相当 |

**参照証跡**:

```cpp
// mplsrouteorch.cpp:625
/* Default SAI_INSEG_ENTRY_ATTR_PACKET_ACTION is SAI_PACKET_ACTION_FORWARD */

// mplsrouteorch.cpp:637-652 (set 分岐)
if (it_route->second.nhg_key.getSize() == 0 && !blackhole)
{
    inseg_attr.id = SAI_INSEG_ENTRY_ATTR_PACKET_ACTION;
    inseg_attr.value.s32 = SAI_PACKET_ACTION_FORWARD;
    ...
}
else if (blackhole)
{
    inseg_attr.id = SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION;   // NOTE: typo in source (uses ROUTE not INSEG)
    inseg_attr.value.s32 = SAI_PACKET_ACTION_DROP;
    ...
}
```

> **実装上の注意**: `mplsrouteorch.cpp:648` の set 分岐では `SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION`
> という IP route 用の定数を誤用している（`SAI_INSEG_ENTRY_ATTR_PACKET_ACTION` が正しい）。
> create 分岐（L612）は正しく `SAI_INSEG_ENTRY_ATTR_PACKET_ACTION` を使用している。

---

## 4. pop/swap/push モード文字列（`label.h`）

APPL_DB `mpls_nh` フィールドの値として `fpmsyncd` が書き込み、`mplsrouteorch` が
`LabelStack` コンストラクタでパースするモード識別文字列。

| 文字列プレフィクス | SAI 値 | 行 | パース規則 |
|--------------------|--------|----|-----------|
| `"swap"` | `SAI_OUTSEG_TYPE_SWAP` | `label.h:33-35, 91-93` | `str.find("swap") == 0`、続く部分を label stack としてパース |
| `"push"` | `SAI_OUTSEG_TYPE_PUSH` | `label.h:37-39, 95-97` | `str.find("push") == 0`、同上 |
| `"na"` | 該当なし（IP 転送） | `mplsrouteorch.cpp:244`, `nhgorch.cpp:230` | MPLS label なし扱い。`nhg_str` 構築から除外 |

**デフォルト値**:

```cpp
// label.h:24 — LabelStack() デフォルトコンストラクタ
m_outseg_type(SAI_OUTSEG_TYPE_SWAP)
```

`"swap"` / `"push"` 以外の文字列で始まる `mpls_nh` 要素は `LabelStack::m_outseg_type` が
`SAI_OUTSEG_TYPE_SWAP` のまま（WARN/ERROR ログなし）となるため、書込み元の `fpmsyncd` で
バリデーション済みであることが前提。

**`mpls_pop` 値**: `fpmsyncd` は RTN_UNICAST ルートで常に `"1"` を書く
（`fpmsyncd/routesync.cpp:2728`）。`mplsrouteorch.cpp:149` で `to_uint<uint8_t>(fvValue(i))` に変換し、
`SAI_INSEG_ENTRY_ATTR_NUM_OF_POP` に直接 map。

---

## 5. フィールド名リテラル（`mplsrouteorch.cpp`）

`doLabelTask()` の fv ループ（L143-160）でフィールド名として比較されるハードコード文字列。

| 文字列 | 行 | 用途 |
|--------|----|------|
| `"mpls_nh"` | L145 | outgoing MPLS ラベル操作リスト（`LabelStack` リスト） |
| `"mpls_pop"` | L148 | pop 段数（uint8_t、SAI `NUM_OF_POP` に直接 map） |
| `"blackhole"` | L151 | `"true"` でブラックホール扱い |
| `"weight"` | L154 | ECMP ネクストホップ重み（カンマ区切り） |
| `"nexthop_group"` | L157 | NhgOrch NHG インデックス（`nexthop`/`ifname` と排他） |
| `"true"` | L152 | `blackhole` フィールドの boolean string 値 |

---

## 6. key 区切り・プレフィクス（`nexthopkey.h`）

| マクロ | 値 | 行 | 用途 |
|--------|----|----|------|
| `LABELSTACK_DELIMITER` | `'+'` | `nexthopkey.h:17` | `<labelstack>+<ip>@<intf>` の MPLS / 非 MPLS 区切り |
| `NH_DELIMITER` | `'@'` | `nexthopkey.h:18` | nexthop IP と intf alias の区切り |
| `NHG_DELIMITER` | `','` | `nexthopkey.h:19` | ECMP NH カンマ区切り |
| `VRF_PREFIX` | `"Vrf"` | `nexthopkey.h:20` | non-default VRF key 判定（`mplsrouteorch.cpp:107-118`） |

---

## 7. CRM resource ↔ SAI マップ（`crmorch.cpp`）

| 観点 | CRM_MPLS_INSEG | CRM_MPLS_NEXTHOP |
|------|---------------|-----------------|
| `crmResTypeNameMap` 文字列 | `"MPLS_INSEG"` (L46) | `"MPLS_NEXTHOP"` (L47) |
| `crmResSaiObjAttrMap` SAI 型 | `SAI_OBJECT_TYPE_INSEG_ENTRY` (L113) | `SAI_OBJECT_TYPE_NEXT_HOP` (L114) |
| `crmResSaiAvailAttrMap` | なし（`sai_object_type_get_availability` 経由） | なし（同上） |
| inc 箇所 | `mplsrouteorch.cpp:754` (`addLabelRoutePost` 成功時) | `nhgorch.cpp` MPLS NH create 時 |
| dec 箇所 | `mplsrouteorch.cpp:917` (`removeLabelRoutePost` 成功時) | `nhgorch.cpp` MPLS NH remove 時 |

---

## まとめ

| 定数カテゴリ | 主要値 | ソース |
|-------------|--------|--------|
| MPLS label range | `LABEL_VALUE_MIN=0`, `LABEL_VALUE_MAX=0xFFFFF` (1048575, 20-bit) | `label.h:15-16` |
| SAI inseg_entry_attr | `PACKET_ACTION`, `NEXT_HOP_ID`, `NUM_OF_POP` | `mplsrouteorch.cpp:612-661` |
| packet_action enum | `FORWARD` (正常転送), `DROP` (blackhole) | `mplsrouteorch.cpp:613, 641, 649` |
| pop モード | `mpls_pop` → `SAI_INSEG_ENTRY_ATTR_NUM_OF_POP` へ直接 map、fpmsyncd は常に `"1"` | `mplsrouteorch.cpp:149`, `routesync.cpp:2728` |
| swap モード | `"swap"` プレフィクス → `SAI_OUTSEG_TYPE_SWAP` | `label.h:33-35` |
| push モード | `"push"` プレフィクス → `SAI_OUTSEG_TYPE_PUSH` | `label.h:37-39` |
| IP 転送（label なし） | `"na"` → nhg_str 構築から除外 | `mplsrouteorch.cpp:244` |
