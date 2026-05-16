# TC_TO_DSCP_MAP — Phase A: 暗黙デフォルト調査結果

## 調査対象ファイル

- `sonic-swss/orchagent/qosorch.cpp` (TcToDscpMapHandler)
- `sonic-swss/orchagent/qosorch.h`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-tc-dscp-map.yang`
- `sonic-buildimage/files/build_templates/qos_config.j2`

## フィールド一覧と暗黙デフォルト

### `dscp` フィールド

- **YANG デフォルト**: なし（`default` 文なし）。
- **YANG パターン**: `"6[0-3]|[1-5][0-9]?|[0-9]?"` — 0〜63 の文字列。
- **コード挙動**: `TcToDscpMapHandler::convertFieldValuesToAttributes()` (qosorch.cpp:1231) は `stoi(fvValue(*i))` で変換し、負値または `DSCP_MAX_VAL(=63)` 超過の場合は明示的に `SWSS_LOG_ERROR` を出力して `false` を返す → `task_invalid_entry`。
- **例外処理あり**: `try { stoi(...) } catch(invalid_argument)` で囲まれており、非数値文字列でも `task_invalid_entry` 止まり（silent drop ではない）。
- **上限定数**: `#define DSCP_MAX_VAL 63` (qosorch.cpp:119)。

### `tc` フィールド（key）

- **YANG 型**: `stypes:tc_type`（uint8, range 0..15, sonic-types.yang.j2:338）。
- **コード**: `static_cast<sai_uint8_t>(stoi(fvField(*i)))` (qosorch.cpp:1244)。try-catch 内で変換。
- **YANG-実装 discrepancy**: YANG は 0..15 を許可するが、多数の ASIC は TC 0..7 のみサポート。TC 8..15 を設定すると SAI エラー → `task_failed`（実装はコードではなく ASIC が拒否）。

## ビルド時デフォルト（プラットフォーム依存）

`qos_config.j2` の TC_TO_DSCP_MAP セクション（L334-337）:

```jinja
{% if (generate_tc_to_dscp_map is defined) and tunnel_qos_remap_enable %}
    {{- generate_tc_to_dscp_map() }}
{% elif (generate_tc_to_dscp_map_per_sku is defined) %}
    {{ generate_tc_to_dscp_map_per_sku() }}
{% endif %}
```

**重要**: TC_TO_QUEUE_MAP とは異なり、フォールバック（else 節）が存在しない。`generate_tc_to_dscp_map` も `generate_tc_to_dscp_map_per_sku` も定義されていないプラットフォームでは `TC_TO_DSCP_MAP` はデフォルト生成されない。

### プラットフォーム別サンプル値

common/profiles（th2/7260 系, BALANCED/RDMA-CENTRIC プロファイル）に定義される `AZURE_TUNNEL` マップ:

| TC (key) | DSCP value | 備考 |
|----------|------------|------|
| `0` | `8` | CS1 |
| `1` | `0` | BE |
| `2` | `0` | BE |
| `3` | `2` | — |
| `4` | `6` | — |
| `5` | `46` | EF (expedited forwarding) |
| `6` | `0` | — |
| `7` | `48` | CS6 (network control) |
| `8` | `33` | — |

- ソース: `device/common/profiles/th2/7260/BALANCED/qos.json.j2`

### encap_tc_to_dscp_map (TUNNEL_MAP 参照)

`TC_TO_DSCP_MAP` は PORT_QOS_MAP の `tc_to_dscp_map` フィールド経由でポートに適用されるほか、TUNNEL テーブルの `encap_tc_to_dscp_map` フィールド経由でトンネルの egress DSCP 上書きにも使用される（qosorch.h:37, qosorch.cpp:115）。

## SAI MAP TYPE ハードコード

`TcToDscpMapHandler::addQosItem()` にて SAI map type がハードコード:

```cpp
qos_map_attr.value.u32 = SAI_QOS_MAP_TYPE_TC_AND_COLOR_TO_DSCP;  // qosorch.cpp:1271
```

CONFIG_DB のテーブル名から動的決定ではなく、ハンドラクラスに静的に埋め込まれている。
なお SAI map type は `SAI_QOS_MAP_TYPE_TC_AND_COLOR_TO_DSCP`（TC かつ color の組み合わせ → DSCP）であり、
ポート attribute は `SAI_PORT_ATTR_QOS_TC_AND_COLOR_TO_DSCP_MAP`（qosorch.h:37, qosorch.cpp:66）。

## dead consumer / 書込み順依存

- QosOrch は常時 `TC_TO_DSCP_MAP` を購読。dead consumer なし。
- **書込み順依存**: `TC_TO_DSCP_MAP` を作成する前に `PORT_QOS_MAP` または TUNNEL で参照した場合は `task_need_retry` でキューイング。
- **DEL 保留**: 参照中は DEL が `m_pendingRemove=true` でキューイングされ、参照解放まで SAI remove は呼ばれない（qosorch.cpp:181-186）。

## 発見サマリ

| 分類 | 詳細 |
|------|------|
| YANG デフォルトなし | `dscp` フィールドに YANG `default` 文なし |
| 例外処理あり | `dscp` が非数値でも try-catch で `task_invalid_entry`（silent drop ではない） |
| 範囲チェックあり | `DSCP_MAX_VAL=63` 超過は明示エラー（qosorch.cpp:1238-1243） |
| YANG-実装乖離 | TC は YANG で 0..15 を許可するが ASIC は 0..7 のみ（8..15 は SAI エラー） |
| ハードコード | SAI map type `SAI_QOS_MAP_TYPE_TC_AND_COLOR_TO_DSCP` がクラス内にハードコード |
| ビルド時デフォルトなし | フォールバック else 節なし。プラットフォーム関数未定義時は TABLE 非生成 |
| 主な用途 | egress DSCP remarking（ポートまたはトンネル encap の両方から参照可） |
| 書込み順依存 | PORT_QOS_MAP / TUNNEL 参照前に TC_TO_DSCP_MAP が必要。逆順は retry |
