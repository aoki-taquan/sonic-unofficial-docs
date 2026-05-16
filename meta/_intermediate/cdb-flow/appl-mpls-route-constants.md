# APPL_DB LABEL_ROUTE_TABLE — Phase E: ハードコード定数 詳細トレース

生成日: 2026-05-15
対象ページ: `docs/reference/config-db/appl-mpls-route.md`

## 目的

`fpmsyncd::onLabelRouteMsg()` / `routeorch::doLabelTask()` / `mplsrouteorch` / `nhgorch` MPLS 経路 / `CrmOrch` MPLS resource が APPL_DB `LABEL_ROUTE_TABLE` 経路で使用するハードコード定数（MPLS ラベル値範囲、outseg type リテラル、key プレフィクス、SAI INSEG 属性、CRM resource ↔ SAI 紐付け、CRM threshold/counter 文字列）をソースコードから抽出し、evidence 行付きで一覧化する。

## 訪問ファイル

| ファイル | 内容 |
|---------|------|
| `sonic-swss-common/common/schema.h` | `APP_LABEL_ROUTE_TABLE_NAME` |
| `sonic-swss/orchagent/label.h` | MPLS label 値範囲 / `LABEL_DELIMITER` / outseg type リテラル |
| `sonic-swss/orchagent/nexthopkey.h` | `LABELSTACK_DELIMITER` / `NH_DELIMITER` / `NHG_DELIMITER` / `VRF_PREFIX` |
| `sonic-swss/orchagent/mplsrouteorch.cpp` | INSEG SAI 属性 / フィールド名リテラル / SAI_API_MPLS / CRM_MPLS_INSEG 連動 |
| `sonic-swss/orchagent/nhgorch.cpp` | MPLS NH 分岐 `"na"` リテラル |
| `sonic-swss/orchagent/crmorch.cpp` | CRM MPLS resource ↔ SAI 属性 / threshold/counter 文字列マップ |

## 1. APPL_DB テーブル名（`schema.h`）

| マクロ | 値 | 行 |
|--------|----|----|
| `APP_LABEL_ROUTE_TABLE_NAME` | `"LABEL_ROUTE_TABLE"` | `sonic-swss-common/common/schema.h:48` |

`routeorch.cpp` の `doTask` で `getTableName() == APP_LABEL_ROUTE_TABLE_NAME` のとき `doLabelTask` を呼び出し、その後 `return;` する（IPv4/IPv6 経路と排他）。

## 2. MPLS label 値範囲（`label.h`）

| マクロ | 値 | 行 | 用途 |
|--------|----|----|------|
| `LABEL_VALUE_MIN` | `0` | `label.h:15` | `to_uint<uint32_t>` で MPLS label を変換する際の下限チェック |
| `LABEL_VALUE_MAX` | `0xFFFFF` (1048575) | `label.h:16` | 同上の上限チェック。20-bit MPLS label space (RFC 3032) |
| `LABEL_DELIMITER` | `'/'` | `label.h:14` | label stack 区切り（`<label0>/<label1>/.../<labelN>`） |

参照箇所:

- `label.h:47-49`: `LabelStack(const std::string &str)` 内で `tokenize(str.substr(4), LABEL_DELIMITER)` 後、各要素を `to_uint<uint32_t>(i, LABEL_VALUE_MIN, LABEL_VALUE_MAX)` で変換。範囲外の label はパース時に例外。

## 3. MPLS outseg type 文字列リテラル（`label.h`）

`LabelStack(const std::string&)` コンストラクタ（`label.h:23-50`）と `to_string()`（L84-108）でハードコード:

| 文字列 | SAI 値 | 行 |
|--------|--------|----|
| `"swap"` | `SAI_OUTSEG_TYPE_SWAP` | `label.h:33-35, 91-93` |
| `"push"` | `SAI_OUTSEG_TYPE_PUSH` | `label.h:37-39, 95-97` |

デフォルトコンストラクタ `LabelStack()` は `m_outseg_type(SAI_OUTSEG_TYPE_SWAP)` 初期化（L24）。`str.find("swap") == 0` / `str.find("push") == 0` で prefix 判定し、続く 4 文字以降を label stack としてパースする（`str.substr(4)`、L47）。

## 4. key 区切り・プレフィクスマクロ（`nexthopkey.h`）

| マクロ | 値 | 行 | 用途 |
|--------|----|----|------|
| `LABELSTACK_DELIMITER` | `'+'` | `nexthopkey.h:17` | `<labelstack>+<ip>@<intf>` の MPLS / 非 MPLS 部分区切り |
| `NH_DELIMITER` | `'@'` | `nexthopkey.h:18` | nexthop IP と intf alias の区切り |
| `NHG_DELIMITER` | `','` | `nexthopkey.h:19` | ECMP NH カンマ区切り |
| `VRF_PREFIX` | `"Vrf"` | `nexthopkey.h:20` | non-default VRF key 判定 |

参照箇所:

- `mplsrouteorch.cpp:244-248`: `nhg_str` 構築時、`mpls_nhv[i] != "na"` のとき `mpls_nhv[i] + LABELSTACK_DELIMITER + ipv[i] + NH_DELIMITER + alsv[i]` を組み立てる
- `nexthopkey.h:186`: `parseMplsNextHop()` で `tokenize(str, LABELSTACK_DELIMITER)` により MPLS / non-MPLS 分割
- `nexthopkey.h:216`: `formatMplsNextHop()` で `label_stack.to_string() + LABELSTACK_DELIMITER`

## 5. APPL_DB フィールド名・値リテラル（`mplsrouteorch.cpp`）

`doLabelTask()` の fv ループ（L143-160）でハードコード文字列をフィールド名として比較:

| 文字列 | 行 | 用途 |
|--------|----|------|
| `"mpls_nh"` | `mplsrouteorch.cpp:145` | outgoing MPLS ラベル操作リスト |
| `"mpls_pop"` | `mplsrouteorch.cpp:148` | pop 段数 |
| `"blackhole"` | `mplsrouteorch.cpp:151` | `"true"` でブラックホール扱い（`fvValue(i) == "true"` 比較） |
| `"weight"` | `mplsrouteorch.cpp:154` | ECMP ネクストホップ重み |
| `"nexthop_group"` | `mplsrouteorch.cpp:157` | NhgOrch NHG インデックス |

`"true"` リテラルは `mplsrouteorch.cpp:152` で `blackhole = fvValue(i) == "true"` の値判定（boolean string）。

`mpls_nhv` 要素値リテラル:

| 文字列 | 行 | 用途 |
|--------|----|------|
| `"na"` | `mplsrouteorch.cpp:244`, `nhgorch.cpp:230` | MPLS NH カンマ区切り要素が `"na"` のとき IP 転送（ラベルなし）扱いで `nhg_str` 構築から除外 |

## 6. SAI INSEG ENTRY 属性（`mplsrouteorch.cpp`）

`addLabelRoutePost()` 内で INSEG entry 作成時に使用される SAI 属性 ID:

| SAI 属性 | 行 | 値の出処 |
|---------|----|---------|
| `SAI_INSEG_ENTRY_ATTR_PACKET_ACTION` | L612, L640 | `SAI_PACKET_ACTION_FORWARD`（デフォルト、L625 コメント）/ `SAI_PACKET_ACTION_DROP`（blackhole 時） |
| `SAI_INSEG_ENTRY_ATTR_NEXT_HOP_ID` | L617, L656 | NHG / 単一 NH SAI object id |
| `SAI_INSEG_ENTRY_ATTR_NUM_OF_POP` | L621 | APPL_DB `mpls_pop` field をそのまま map（デフォルト 0 = pop なし） |

`SAI_API_MPLS` は SAI status ハンドラの引数として L781, L794, L835, L910 で参照（`handleSaiSetStatus` / `handleSaiRemoveStatus`）。

## 7. CRM resource ↔ SAI / 文字列マップ（`crmorch.cpp`）

`CRM_MPLS_INSEG` および `CRM_MPLS_NEXTHOP` は MPLS 経路の CRM カウンタ。`routeorch::addLabelRoutePost` 成功時 `gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_MPLS_INSEG)`（`mplsrouteorch.cpp:754`）、`removeLabelRoutePost` 成功時 `decCrmResUsedCounter`（L917）。

`crmResTypeNameMap`（`crmorch.cpp:46-47`）:

| enum | 文字列 |
|------|--------|
| `CRM_MPLS_INSEG` | `"MPLS_INSEG"` |
| `CRM_MPLS_NEXTHOP` | `"MPLS_NEXTHOP"` |

`crmResSaiObjAttrMap`（`crmorch.cpp:113-114`）:

| CRM resource | SAI オブジェクト型 |
|--------------|------------------|
| `CRM_MPLS_INSEG` | `SAI_OBJECT_TYPE_INSEG_ENTRY` |
| `CRM_MPLS_NEXTHOP` | `SAI_OBJECT_TYPE_NEXT_HOP` |

`CRM_MPLS_INSEG` / `CRM_MPLS_NEXTHOP` には `crmResSaiAvailAttrMap`（`SAI_SWITCH_ATTR_AVAILABLE_*`）エントリが**存在しない** — IPv4/IPv6 route と異なり `available` 値は `sai_object_type_get_availability(SAI_OBJECT_TYPE_INSEG_ENTRY / NEXT_HOP)` 経由で取得（`crmorch.cpp:904-908`）。精度はベンダ SAI 実装依存。

## 8. CRM threshold / counter 文字列キー（`crmorch.cpp`）

CONFIG_DB `CRM` フィールド名・COUNTERS_DB `CRM:STATS` フィールド名:

| 文字列 | マップ | 行 | 用途 |
|--------|--------|----|------|
| `"mpls_inseg_threshold_type"` | `crmThreshTypeResMap` | 179 | CONFIG_DB threshold 種別 (INSEG) |
| `"mpls_nexthop_threshold_type"` | `crmThreshTypeResMap` | 180 | CONFIG_DB threshold 種別 (MPLS NH) |
| `"mpls_inseg_low_threshold"` | `crmThreshLowResMap` | 225 | CONFIG_DB low 閾値 (INSEG) |
| `"mpls_nexthop_low_threshold"` | `crmThreshLowResMap` | 226 | CONFIG_DB low 閾値 (MPLS NH) |
| `"mpls_inseg_high_threshold"` | `crmThreshHighResMap` | 271 | CONFIG_DB high 閾値 (INSEG) |
| `"mpls_nexthop_high_threshold"` | `crmThreshHighResMap` | 272 | CONFIG_DB high 閾値 (MPLS NH) |
| `"crm_stats_mpls_inseg_available"` | `crmAvailCntsTableMap` | 324 | COUNTERS_DB available 値 (INSEG) |
| `"crm_stats_mpls_nexthop_available"` | `crmAvailCntsTableMap` | 325 | COUNTERS_DB available 値 (MPLS NH) |
| `"crm_stats_mpls_inseg_used"` | `crmUsedCntsTableMap` | 370 | COUNTERS_DB used 値 (mplsrouteorch L754 で inc / L917 で dec) |
| `"crm_stats_mpls_nexthop_used"` | `crmUsedCntsTableMap` | 371 | COUNTERS_DB used 値 (NeighOrch MPLS NH 経由) |

## 9. その他関連定数（参考、本文には含めない）

| 名前 | 場所 | 備考 |
|------|------|------|
| `gMaxBulkSize` | `mplsrouteorch.cpp` constructor 経由 | SAI bulker バッチサイズ（switchorch 由来、マジック数なし） |
| `m_maxNextHopGroupCount` | `routeorch.cpp:66-90` | IP route 由来の NHG 上限。MPLS NHG も同上限を共有するが、`doLabelTask` パス内で直接の上限チェックは存在しない（NhgOrch 全体で集計） |
| ECMP NHG `addTempLabelRoute()` | `mplsrouteorch.cpp:550-583` | 上限値ではなく一時 NH 経路のフォールバック（Phase D で扱い済み） |

これらは本文 `<!-- constants -->` ブロックには含めない。

## まとめ

ページ `appl-mpls-route.md` 本文の `<!-- constants -->` ブロックでは以下を網羅する:

1. APPL_DB テーブル名マクロ `APP_LABEL_ROUTE_TABLE_NAME="LABEL_ROUTE_TABLE"`
2. MPLS label 値範囲マクロ `LABEL_VALUE_MIN=0` / `LABEL_VALUE_MAX=0xFFFFF` / `LABEL_DELIMITER='/'`
3. MPLS outseg type 文字列リテラル `"swap"` / `"push"` ↔ `SAI_OUTSEG_TYPE_*`
4. key 区切り・プレフィクス `LABELSTACK_DELIMITER='+'` / `NH_DELIMITER='@'` / `NHG_DELIMITER=','` / `VRF_PREFIX="Vrf"`
5. APPL_DB フィールド名リテラル 5 種（`"mpls_nh"`, `"mpls_pop"`, `"blackhole"`, `"weight"`, `"nexthop_group"`）と値リテラル `"true"` / `"na"`
6. SAI INSEG ENTRY 属性 3 種（`PACKET_ACTION` / `NEXT_HOP_ID` / `NUM_OF_POP`）+ `SAI_API_MPLS`
7. CRM resource enum ↔ name / SAI object type マップ（`CRM_MPLS_INSEG`, `CRM_MPLS_NEXTHOP`）
8. CRM threshold/counter 文字列キー 10 種（CONFIG_DB `CRM` + COUNTERS_DB `CRM:STATS`）
