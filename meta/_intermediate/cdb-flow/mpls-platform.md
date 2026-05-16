# MPLS (mplsrouteorch) — Phase H プラットフォーム差調査

対象ページ: `docs/reference/config-db/appl-mpls-route.md`
ソース: `sonic-net/sonic-swss` HEAD (`orchagent/mplsrouteorch.cpp`)
調査日: 2026-05-16

## スコープ

- `orchagent/mplsrouteorch.cpp` — `RouteOrch::doLabelTask()` / `addLabelRoute()` / `addLabelRoutePost()` / `removeLabelRoute()` / `removeLabelRoutePost()`
- `orchagent/saihelper.cpp` — `SAI_API_MPLS` query / log level セット
- `orchagent/routeorch.cpp` — `gMySwitchType` 参照箇所
- `orchagent/nhgorch.cpp` — `isLabeled()` 分岐の MPLS NH 経路
- `orchagent/crmorch.cpp` — `CRM_MPLS_INSEG` / `CRM_MPLS_NEXTHOP` マッピング
- `fpmsyncd/routesync.cpp` — `onLabelRouteMsg()` 書き込み元

## 1. SAI inseg_entry capability — ランタイム問い合わせの有無

### 観察

```cpp
// orchagent/saihelper.cpp:53
sai_mpls_api_t* sai_mpls_api;

// orchagent/saihelper.cpp:220
sai_api_query(SAI_API_MPLS, (void **)&sai_mpls_api);

// orchagent/saihelper.cpp:284
sai_log_set(SAI_API_MPLS, SAI_LOG_LEVEL_NOTICE);
```

`SAI_API_MPLS` は `saihelper.cpp` で orchagent 起動段階に一括 query される。この呼び出しが失敗した場合、個別フォールバックなしに orchagent が異常終了する仕様（`sai_api_query` の戻り値チェック + abort パターン）。

`mplsrouteorch.cpp` および `nhgorch.cpp` の MPLS 経路を全文走査した結果:

- `sai_query_attribute_capability` — **0 件**
- `sai_object_type_query` (INSEG 向け) — **0 件**
- `SAI_SWITCH_ATTR_AVAILABLE_MPLS_INSEG_ENTRY` に類する runtime 問い合わせ — **0 件**

`gLabelRouteBulker.create_entry()` (`mplsrouteorch.cpp:627`) が `SAI_STATUS_NOT_SUPPORTED` を返した場合、`addLabelRoute()` は `SAI_STATUS_ITEM_ALREADY_EXISTS` チェック (`mplsrouteorch.cpp:628`) のみ行い、それ以外の失敗コードは `addLabelRoutePost()` の `*it_status != SAI_STATUS_SUCCESS` 分岐 (`mplsrouteorch.cpp:742`) で `handleSaiSetStatus(SAI_API_MPLS, status)` に委譲される。

### 結論

**orchagent は MPLS inseg_entry のサポート有無を実行時に問い合わせない。**
ベンダー SAI が `SAI_OBJECT_TYPE_INSEG_ENTRY` を未サポートの場合、orchagent は起動段階または create_entry 時に SAI エラーを受け取り、`handleSaiSetStatus` の振る舞い次第で retry ループまたは orchagent 停止となる。MPLS 有効/無効を CONFIG_DB で切り替えるスイッチは実装されていない。

## 2. ASIC ベンダー MPLS 対応差

### CRM による available count の実装差

```cpp
// orchagent/crmorch.cpp:113-114
{ CrmResourceType::CRM_MPLS_INSEG,    SAI_OBJECT_TYPE_INSEG_ENTRY },
{ CrmResourceType::CRM_MPLS_NEXTHOP,  SAI_OBJECT_TYPE_NEXT_HOP    },
```

IPv4/IPv6 route は `SAI_SWITCH_ATTR_AVAILABLE_IPV4_ROUTE_ENTRY` / `SAI_SWITCH_ATTR_AVAILABLE_IPV6_ROUTE_ENTRY` という専用属性で残量を取得する (crmorch.cpp `crmResSaiAvailAttrMap`)。一方 MPLS の `CRM_MPLS_INSEG` / `CRM_MPLS_NEXTHOP` はこのマップに**エントリが存在せず**、`sai_object_type_get_availability(gSwitchId, SAI_OBJECT_TYPE_INSEG_ENTRY, ...)` (`crmorch.cpp:801, 854, 1035`) による汎用パスで取得する。

`sai_object_type_get_availability` の実装品質はベンダー SAI に依存する:
- 未実装ベンダーは `SAI_STATUS_NOT_SUPPORTED` を返す → CRM `available` が 0 または不定
- 実装済みベンダーは正確なハードウェアリソース残量を返す

SONiC コミュニティ master は **この差をガードするコードを持たない**（0 / 不定の場合に閾値超えアラートが誤発する可能性あり）。

### `SAI_STATUS_NOT_SUPPORTED` 到達経路

`addLabelRoutePost()` (`mplsrouteorch.cpp:742-840`) は bulker 経由の create/set/remove 失敗を `handleSaiSetStatus(SAI_API_MPLS, status)` / `handleSaiRemoveStatus(SAI_API_MPLS, status)` に委譲する。これらは `sai_serialize_status()` で文字列化してログ出力し、`SAI_STATUS_CODE(status)` を `task_need_retry` / `task_failed` に変換する共通ハンドラ。`SAI_STATUS_NOT_SUPPORTED` は通常 `task_failed` に振られ、`parseHandleSaiStatusFailure` が `return false` を返し → `m_toSync` 残置 (retry ループ)。ただし inseg を初めから提供しない ASIC ではこの retry は永続する。

## 3. VOQ Chassis MPLS

### routeorch.cpp での gMySwitchType 参照

```cpp
// orchagent/routeorch.cpp:34
extern string gMySwitchType;

// orchagent/routeorch.cpp:95-109 (RouteOrch コンストラクタ)
/* If the switch type is voq, and max Ecmp group size supported is >= 128, set to 128 */
if (gMySwitchType == "voq" && maxEcmpGroupSize >= 128)
{
    maxEcmpGroupSize = 128;
}
```

この voq 分岐は **`doLabelTask` には直接伝搬しない**。`doLabelTask` は `m_maxNextHopGroupCount` を参照する NHG 上限チェック (`mplsrouteorch.cpp:310-316`) で間接的に影響を受ける。voq 環境では `maxEcmpGroupSize` が 128 にクランプされるため、MPLS ECMP の NHG 最大メンバー数も 128 に制限される副次的な差が生じる。

```bash
# mplsrouteorch.cpp / nhgorch.cpp での直接参照を確認
grep -nE "voq|chassis|VOQ|fabric|gMySwitchType" \
    orchagent/mplsrouteorch.cpp orchagent/nhgorch.cpp
# → 0 件
```

`nhgorch.cpp` の MPLS NH (`isLabeled()`) 経路にも `gMySwitchType` 参照は**0 件**。

### VOQ Chassis での inter-ASIC MPLS 転送

VOQ chassis アーキテクチャでは、各ラインカードが独立した `swss` コンテナを持ち、それぞれ `doLabelTask` を独立実行する。inter-ASIC MPLS forwarding（ラベルスタックのクロス ASIC 転送）は **SAI / ASIC ファブリック層の責務**であり、orchagent/`mplsrouteorch.cpp` には可視でない。`mplsrouteorch.cpp` が扱う `inseg_entry` は各 ASIC ローカルの受信ラベル処理のみを制御する。

`orchdaemon.cpp` で multi-asic 用の namespace 分離は IP route (`RouteOrch` 共通) と同一パターンで行われ、MPLS 固有の namespace 処理は存在しない。

## 4. multi-asic namespace の差

`fpmsyncd/routesync.cpp::onLabelRouteMsg()` の `master_index` チェック:

```cpp
// fpmsyncd/routesync.cpp:2674-2681
uint32_t master_index = rtnl_route_get_table(route_obj);
if (master_index)
{
    SWSS_LOG_INFO("Unsupported Non-default VRF: %d for LabelRoute %s", master_index, destaddr);
    return;
}
```

これは **multi-asic 制限ではなく VRF 制限**。multi-asic 環境では各 asic-namespace ごとに独立した fpmsyncd / swss コンテナが起動し、各自の `APPL_DB` に書き込む。namespace 固有の MPLS 経路制御は実装されていない。

`mplsrouteorch.cpp` 全文:
- `namespace` / `asic_id` 参照 — **0 件**
- `SONIC_DB_GLOBAL_PATH` / `SONIC_DB_PATH` 参照 — **0 件**

## 5. プラットフォーム差まとめ

| 観点 | 差の有無 | 根拠 | ファイル:行 |
|---|---|---|---|
| SAI MPLS API capability runtime query | **なし** | `sai_query_attribute_capability` / `sai_object_type_query` for INSEG が 0 件。起動時 `sai_api_query(SAI_API_MPLS)` のみ | `saihelper.cpp:220` |
| inseg_entry 非サポート ASIC での挙動 | **差あり (SAI 層)** | `SAI_STATUS_NOT_SUPPORTED` → `handleSaiSetStatus` → retry 永続。CONFIG_DB ガードなし | `mplsrouteorch.cpp:742,781,794,835` |
| `SAI_SWITCH_ATTR_AVAILABLE_*` による MPLS 上限取得 | **なし** | `crmResSaiAvailAttrMap` に MPLS エントリなし。`sai_object_type_get_availability` 経由（ベンダー実装依存） | `crmorch.cpp:801,854` |
| switch type voq/chassis/fabric 分岐 (MPLS inseg 直接) | **なし** | `mplsrouteorch.cpp` / `nhgorch.cpp` で `gMySwitchType` / `voq` / `chassis` 参照 0 件 | — |
| voq による NHG 上限クランプの副次的影響 | **差あり (間接)** | voq 環境で `maxEcmpGroupSize` が 128 にクランプ → MPLS ECMP NHG 上限に波及 | `routeorch.cpp:109`, `mplsrouteorch.cpp:310-316` |
| multi-asic namespace 特殊化 | **なし** | `namespace` / `asic_id` 参照 0 件。各 namespace は独立コンテナで同一ロジックを実行 | — |
| VRF 制限 (プラットフォーム非依存) | **あり** | 非デフォルト VRF の MPLS ルートは fpmsyncd がスキップ。ASIC 依存ではない | `routesync.cpp:2674-2681` |

**総括**: APPL_DB `LABEL_ROUTE_TABLE` の orchagent 処理は **コード上プラットフォーム非依存**。実質的な差は SAI ベンダー実装側（`inseg_entry` サポートの有無、`sai_object_type_get_availability` の精度）に閉じる。VOQ chassis 向けには `m_maxNextHopGroupCount` クランプ (128) が MPLS ECMP の間接的な上限として機能するが、inseg スキーマ・キー構造・フィールド定義には現れない。
