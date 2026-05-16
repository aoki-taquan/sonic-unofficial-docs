# appl-buffer Phase E: ハードコード定数スキャン

`sonic-swss/orchagent/bufferorch.cpp` および `bufferorch.h` / `buffer/bufferschema.h` から抽出した、BUFFER_* テーブル処理に関わるコード内固定値の網羅リスト。

ソース ref:
- `sonic-net/sonic-swss` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
  - `orchagent/bufferorch.h`
  - `orchagent/bufferorch.cpp`
  - `orchagent/buffer/bufferschema.h`

## フィールド名文字列定数 (`bufferorch.h`)

| 定数名 | 値 | 行 |
|---|---|---|
| `buffer_size_field_name` | `"size"` | `bufferorch.h:18` |
| `buffer_pool_type_field_name` | `"type"` | `bufferorch.h:19` |
| `buffer_pool_mode_field_name` | `"mode"` | `bufferorch.h:20` |
| `buffer_pool_field_name` | `"pool"` | `bufferorch.h:21` |
| `buffer_pool_xoff_field_name` | `"xoff"` | `bufferorch.h:24` |
| `buffer_xon_field_name` | `"xon"` | `bufferorch.h:25` |
| `buffer_xon_offset_field_name` | `"xon_offset"` | `bufferorch.h:26` |
| `buffer_xoff_field_name` | `"xoff"` | `bufferorch.h:27` |
| `buffer_dynamic_th_field_name` | `"dynamic_th"` | `bufferorch.h:28` |
| `buffer_static_th_field_name` | `"static_th"` | `bufferorch.h:29` |
| `buffer_profile_field_name` | `"profile"` | `bufferorch.h:30` |
| `buffer_profile_list_field_name` | `"profile_list"` | `bufferorch.h:34` |
| `buffer_headroom_type_field_name` | `"headroom_type"` | `bufferorch.h:35` |

## 列挙値文字列定数 (`bufferorch.h`)

| 定数名 | 値 | 用途 | 行 |
|---|---|---|---|
| `buffer_pool_mode_dynamic_value` | `"dynamic"` | `BUFFER_POOL.mode` | `bufferorch.h:22` |
| `buffer_pool_mode_static_value`  | `"static"`  | `BUFFER_POOL.mode` | `bufferorch.h:23` |
| `buffer_value_ingress` | `"ingress"` | `BUFFER_POOL.type` | `bufferorch.h:31` |
| `buffer_value_egress`  | `"egress"`  | `BUFFER_POOL.type` | `bufferorch.h:32` |
| `buffer_value_both`    | `"both"`    | `BUFFER_POOL.type` | `bufferorch.h:33` |

## `packet_discard_action` 関連 (`buffer/bufferschema.h`)

| 定数名 | 値 | 行 |
|---|---|---|
| `BUFFER_PROFILE_PACKET_DISCARD_ACTION` | `"packet_discard_action"` | `bufferschema.h:8` |
| `BUFFER_PROFILE_PACKET_DISCARD_ACTION_DROP` | `"drop"` | `bufferschema.h:5` |
| `BUFFER_PROFILE_PACKET_DISCARD_ACTION_TRIM` | `"trim"` | `bufferschema.h:6` |

`bufferorch.cpp:730/734` の if-else 分岐でこの 2 値のみが許容され、それ以外は `task_failed` (L743)。

## flex counter group 定数 (`bufferorch.h`)

| 定数名 | 値 | 用途 | 行 |
|---|---|---|---|
| `BUFFER_POOL_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"BUFFER_POOL_WATERMARK_STAT_COUNTER"` | flex counter group 名 | `bufferorch.h:15` |
| `BUFFER_POOL_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS`  | `"60000"` (= 60 秒) | poll 間隔ミリ秒 | `bufferorch.h:16` |

## ゼロプロファイル判定文字列

`bufferorch.cpp` 内で `_zero_` 部分文字列を含むプロファイル名は flex counter 追加をスキップする。

| 行 | 用途 |
|---|---|
| `bufferorch.cpp:378` | `processBufferProfile()` 削除時に参照中ゼロプロファイルを除外 |
| `bufferorch.cpp:995` | `processQueue()` `counter_needs_to_add = !contains("_zero_")` |
| `bufferorch.cpp:1017` | `processQueue()` `counter_was_added` 判定 |
| `bufferorch.cpp:1400` | `processPriorityGroup()` `counter_needs_to_add` |
| `bufferorch.cpp:1421` | `processPriorityGroup()` `counter_was_added` |

`_zero_` というリテラルが 5 箇所にハードコードされており、`*_zero_*` 命名規約が黙示的契約として要求される。

## スイッチタイプ判定文字列

`gMySwitchType` との比較に使われるリテラル値。

| 値 | 行 | 分岐内容 |
|---|---|---|
| `"dpu"` | `bufferorch.cpp:64` | `initBufferConstants()` をスキップ |
| `"voq"` | `bufferorch.cpp:116, 132, 916, 1049, 1136, 1168, 2079` | VoQ 用 key 4 トークン形式・remote port 扱い |

## SAI 属性 / 列挙値 ID 定数

`bufferorch.cpp` から SAI に渡される定数。

| SAI 定数 | 用途 | 行 |
|---|---|---|
| `SAI_BUFFER_POOL_ATTR_SIZE` | プールサイズ | `bufferorch.cpp:427` |
| `SAI_BUFFER_POOL_ATTR_TYPE` | プール方向 (create-only) | `bufferorch.cpp:460` |
| `SAI_BUFFER_POOL_ATTR_THRESHOLD_MODE` | プール閾値モード (create-only) | `bufferorch.cpp:487` |
| `SAI_BUFFER_POOL_ATTR_XOFF_SIZE` | SHP サイズ | `bufferorch.cpp:493` |
| `SAI_BUFFER_POOL_TYPE_INGRESS` | `type=ingress` の SAI 値 | `bufferorch.cpp:445` |
| `SAI_BUFFER_POOL_TYPE_EGRESS`  | `type=egress` の SAI 値 | `bufferorch.cpp:449` |
| `SAI_BUFFER_POOL_TYPE_BOTH`    | `type=both` の SAI 値 | `bufferorch.cpp:453` |
| `SAI_BUFFER_POOL_THRESHOLD_MODE_DYNAMIC` | `mode=dynamic` | `bufferorch.cpp:476` |
| `SAI_BUFFER_POOL_THRESHOLD_MODE_STATIC`  | `mode=static`  | `bufferorch.cpp:480` |
| `SAI_BUFFER_PROFILE_ATTR_POOL_ID` | profile→pool 参照 (create-only) | `bufferorch.cpp:661` |
| `SAI_BUFFER_PROFILE_ATTR_XON_TH` | XON 閾値 | `bufferorch.cpp:668` |
| `SAI_BUFFER_PROFILE_ATTR_XON_OFFSET_TH` | XON オフセット | `bufferorch.cpp:674` |
| `SAI_BUFFER_PROFILE_ATTR_XOFF_TH` | XOFF 閾値 | `bufferorch.cpp:680` |
| `SAI_BUFFER_PROFILE_ATTR_BUFFER_SIZE` | reserved サイズ | `bufferorch.cpp:686` |
| `SAI_BUFFER_PROFILE_ATTR_THRESHOLD_MODE` | profile threshold モード (create-only) | `bufferorch.cpp:699, 717` |
| `SAI_BUFFER_PROFILE_ATTR_SHARED_DYNAMIC_TH` | dynamic 値 | `bufferorch.cpp:704` |
| `SAI_BUFFER_PROFILE_ATTR_SHARED_STATIC_TH` | static 値 | `bufferorch.cpp:722` |
| `SAI_BUFFER_PROFILE_ATTR_PACKET_ADMISSION_FAIL_ACTION` | `packet_discard_action` | `bufferorch.cpp:728` |
| `SAI_BUFFER_PROFILE_THRESHOLD_MODE_DYNAMIC` | dynamic | `bufferorch.cpp:700` |
| `SAI_BUFFER_PROFILE_THRESHOLD_MODE_STATIC`  | static  | `bufferorch.cpp:718` |
| `SAI_BUFFER_PROFILE_PACKET_ADMISSION_FAIL_ACTION_DROP` | drop | `bufferorch.cpp:732` |
| `SAI_BUFFER_PROFILE_PACKET_ADMISSION_FAIL_ACTION_DROP_AND_TRIM` | trim | `bufferorch.cpp:736` |
| `SAI_BUFFER_POOL_STAT_WATERMARK_BYTES` | flex counter stat | `bufferorch.cpp:31` |
| `SAI_BUFFER_POOL_STAT_XOFF_ROOM_WATERMARK_BYTES` | flex counter stat | `bufferorch.cpp:32` |
| `SAI_NULL_OBJECT_ID` | OID 未割当判定 | 各所 (`processBufferPool` L435 ほか) |
| `SAI_STATUS_ATTR_NOT_IMPLEMENTED_0` | profile/pool SET 時の特例 ignore | `bufferorch.cpp:508, 773` |

## state DB / counters DB 定数

| 定数 | 値 / 出所 | 用途 |
|---|---|---|
| `STATE_BUFFER_MAXIMUM_VALUE_TABLE` | `sonic-swss-common/common/schema.h` | mmu_size 公開先 (`bufferorch.cpp:57`) |
| `COUNTERS_BUFFER_POOL_NAME_MAP` | `sonic-swss-common/common/schema.h` | プール名 → OID マップ (`bufferorch.cpp:55`) |
| `"mmu_size"` | リテラル | `STATE_DB:BUFFER_MAXIMUM_VALUE` のフィールド名 (`bufferorch.cpp:226`) |
| `"global"` | リテラル | 同テーブルの key (`bufferorch.cpp:227`) |
| `"COUNTERS_DB"` | リテラル | DBConnector 引数 (`bufferorch.cpp:55, 56`) |

## まとめ

- 文字列列挙値 (`ingress`/`egress`/`both`/`dynamic`/`static`/`drop`/`trim`) は全て if-else 直接比較で、`else` は `task_invalid_entry` または `task_failed` を返す。
- ゼロプロファイル判定は `_zero_` 部分文字列の `find()` で行われるため、命名規約が暗黙の API。
- flex counter poll 間隔は 60 秒固定 (`"60000"` ms) でランタイム変更不可。
- threshold/type/pool_id 等の SAI 属性は create-only であり、bufferorch は既存 OID 検出時に `LOG_INFO` で skip。
