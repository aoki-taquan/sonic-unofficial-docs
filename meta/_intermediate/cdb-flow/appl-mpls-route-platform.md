# appl-mpls-route — Phase H プラットフォーム差調査

対象ページ: `docs/reference/config-db/appl-mpls-route.md`
ソース: `sonic-swss` (HEAD)
調査日: 2026-05-15

## スコープ

- `orchagent/mplsrouteorch.cpp` (`RouteOrch::doLabelTask()` および inseg_entry 生成)
- `orchagent/routeorch.cpp` (`RouteOrch::doTask` 入口、`APP_LABEL_ROUTE_TABLE_NAME` ディスパッチ)
- `orchagent/nhgorch.cpp` (`isLabeled()` 分岐の MPLS NH 経路)
- `fpmsyncd/routesync.cpp` (`onLabelRouteMsg()` 書き込み元)

## 1. SAI MPLS capability の差

### 観察

`SAI_API_MPLS` は `saihelper.cpp:220` で `sai_api_query()` され、`SAI_LOG_LEVEL_NOTICE` がセットされる。
SAI vendor ライブラリが MPLS API をサポートしていない場合、`sai_api_query()` は失敗するが
orchagent 起動段階で aborted する（個別フォールバックなし）。

```cpp
// orchagent/saihelper.cpp:220
sai_api_query(SAI_API_MPLS,                 (void **)&sai_mpls_api);
```

### 結論

- **orchagent 側に MPLS capability を runtime 問い合わせる分岐はない**。
- `mplsrouteorch.cpp` および `nhgorch.cpp` 全文を走査しても
  `sai_query_attribute_capability` / `sai_object_type_query` / `SAI_SWITCH_ATTR_AVAILABLE_*`
  に基づく分岐は **0 件**。
- すなわち、SAI vendor が `inseg_entry` をサポートしない ASIC では
  - `gLabelRouteBulker.create_entry()` が `SAI_STATUS_NOT_SUPPORTED` を返す
  - `handleSaiSetStatus(SAI_API_MPLS, status)` (`mplsrouteorch.cpp:781,794,835`) に処理が委譲される
  - エラーハンドリング次第で orchagent crash または warn ログのみ
- すなわち **MPLS 有効/無効 は CONFIG_DB スキーマ上で表現されず、SAI 層の暗黙挙動に依存**。

## 2. CRM (Critical Resource Monitor) との差

`crmorch.cpp:113` で `CRM_MPLS_INSEG` は `SAI_OBJECT_TYPE_INSEG_ENTRY` にマップされている
（IPv4/IPv6 ルートのような `SAI_SWITCH_ATTR_AVAILABLE_*` ではなく **object_type 経由**）。

```cpp
// orchagent/crmorch.cpp:113
{ CrmResourceType::CRM_MPLS_INSEG, SAI_OBJECT_TYPE_INSEG_ENTRY },
```

- IPv4/IPv6 route は `SAI_SWITCH_ATTR_AVAILABLE_IPV4_ROUTE_ENTRY` 等で利用可能数を SAI に問い合わせる。
- 一方 MPLS INSEG は `SAI_SWITCH_ATTR_AVAILABLE_MPLS_INSEG_ENTRY` のような attribute が
  `crmorch.cpp` に存在せず、CRM は object_type ベースの汎用パスで残量を取る。
- ベンダー SAI が MPLS available count を実装していない場合、CRM の `used`/`available` は
  ASIC で正確に反映されない可能性がある（コミュニティ master では明示ガードなし）。

## 3. ASIC type / switch type による差

### 観察

- `routeorch.cpp:34` で `extern string gMySwitchType` を参照。
- `routeorch.cpp:106-109` で `gMySwitchType == "voq"` のとき maxEcmpGroupSize が 128 以上で
  特殊扱いされる分岐があるが、**MPLS 経路 (`doLabelTask`) の側にはこの分岐は伝搬しない**。
- `mplsrouteorch.cpp` 全文走査で `gMySwitchType` / `voq` / `chassis` / `fabric` 参照は 0 件。

```bash
grep -nE "voq|chassis|VOQ|fabric|gMySwitchType" orchagent/mplsrouteorch.cpp orchagent/nhgorch.cpp
# → 0 件
```

### 結論

- VoQ/chassis スイッチ向けの MPLS 経路特殊化は **コード上存在しない**。
- ECMP group sizing 最適化 (voq 限定) は IP route のみで、MPLS inseg には適用されない。

## 4. multi-asic / namespace の差

### 観察

`mplsrouteorch.cpp` / `nhgorch.cpp` / `fpmsyncd/routesync.cpp` の `onLabelRouteMsg()` 周辺で
`namespace` / `asic_id` / `multi.asic` 参照は **0 件**。

`fpmsyncd::onLabelRouteMsg()` (`routesync.cpp:2674-2681`) は以下のように VRF master_index を
チェックし、非デフォルト VRF をスキップする:

```cpp
// fpmsyncd/routesync.cpp:2674-2681
uint32_t master_index = rtnl_route_get_table(route_obj);
if (master_index)
{
    SWSS_LOG_INFO("Unsupported Non-default VRF: %d for LabelRoute %s",
                  master_index, destaddr);
    return;
}
```

これは **VRF 制限であり multi-asic 制限ではない**。multi-asic 環境では
各 asic-namespace ごとに独立した fpmsyncd / swss コンテナが動作し、
それぞれの APPL_DB に対して MPLS route を書き込むため、
ASIC-namespace 内の MPLS 経路書き込み挙動はシングル ASIC と同一。

### 結論

- **multi-asic 固有の MPLS 経路特殊化はコード上存在しない**。
- 各 asic-namespace は独立した `LABEL_ROUTE_TABLE` を持つ。
- inter-asic MPLS forwarding (chassis) は SAI 層の責務で、orchagent には可視でない。

## 5. プラットフォーム差まとめ

| 観点 | 差の有無 | 根拠 |
|---|---|---|
| SAI MPLS API capability runtime query | **なし** | `sai_query_attribute_capability` / `sai_object_type_query` for INSEG が `mplsrouteorch.cpp` / `nhgorch.cpp` に 0 件 |
| `SAI_SWITCH_ATTR_AVAILABLE_*` による MPLS 上限取得 | **なし** | `crmorch.cpp` の MPLS は object_type 経由 (CRM `available` は SAI 実装依存) |
| switch type (voq/chassis/fabric) 分岐 | **なし** | `gMySwitchType` 参照は IP route の ECMP sizing のみ |
| multi-asic namespace 特殊化 | **なし** | `mplsrouteorch.cpp` / `nhgorch.cpp` / `onLabelRouteMsg` で namespace 参照 0 件 |
| VRF 制限 | **あり (プラットフォーム非依存)** | `fpmsyncd/routesync.cpp:2674-2681` で非デフォルト VRF はスキップ。これは fpmsyncd 全体の制約で ASIC 依存ではない |

**総括**: APPL_DB `LABEL_ROUTE_TABLE` の挙動はコミュニティ master の orchagent コード上
**プラットフォーム非依存**。差は実質的に SAI ベンダ実装側 (INSEG entry のサポート有無、available count の提供有無) に閉じ、
CONFIG_DB スキーマやキー構造には現れない。
