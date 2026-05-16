# BUFFER_POOL — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/cfgmgr/buffermgrdyn.cpp` (dynamic buffer model manager)
- `sonic-swss/cfgmgr/buffermgr.cpp` (static buffer model manager)
- `sonic-swss/orchagent/bufferorch.cpp` (SAI orch)
- `sonic-swss/orchagent/bufferorch.h` (定数ヘッダ)
- `sonic-swss/cfgmgr/buffermgrdyn.h` (dynamic buffer manager ヘッダ)
- `sonic-swss/cfgmgr/buffermgr.h` (static buffer manager ヘッダ)

---

## 1. pool 名 (ハードコード文字列リテラル)

| 定数名 / 定義 | 値 | 用途 | ソース |
|---|---|---|---|
| `INGRESS_LOSSLESS_PG_POOL_NAME` | `"ingress_lossless_pool"` | lossless PG headroom / SHP 計算の基準プール名。xoff フィールド有効チェック・mode 取得・SHP 判定に使用 | `buffermgrdyn.h:14`, `buffermgr.h:13` |
| (リテラル) | `"ingress_lossless_pool"` | buffermgr.cpp で static model の lossless PG プール pool フィールドデフォルト値 | `buffermgr.cpp:132, 264` |
| (リテラル) | `"egress_lossless_pool"` | Lua plugin コメント内でのサンプル名称 (コード処理なし) | `buffermgrdyn.cpp:703` |

> **注**: `egress_lossless_pool`・`egress_lossy_pool`・`ingress_lossy_pool` はコード内でハードコードされていない。Lua plugin / j2 テンプレートが APPL_DB に書き込む際の名称は CONFIG_DB の key から取得される。`ingress_lossless_pool` のみ特別扱い (SHP / xoff 計算) で `INGRESS_LOSSLESS_PG_POOL_NAME` としてマクロ定義されている。

---

## 2. フィールド名定数 (bufferorch.h)

| 定数名 | 値 | 用途 | ソース |
|---|---|---|---|
| `buffer_size_field_name` | `"size"` | pool / profile の `size` フィールド識別 | `bufferorch.h:17` |
| `buffer_pool_type_field_name` | `"type"` | pool の `type` フィールド識別 | `bufferorch.h:18` |
| `buffer_pool_mode_field_name` | `"mode"` | pool の `mode` フィールド識別 | `bufferorch.h:19` |
| `buffer_pool_field_name` | `"pool"` | profile の `pool` フィールド識別 | `bufferorch.h:20` |
| `buffer_pool_xoff_field_name` | `"xoff"` | pool の `xoff` フィールド識別 | `bufferorch.h:23` |
| `buffer_xon_field_name` | `"xon"` | profile の `xon` フィールド識別 | `bufferorch.h:24` |
| `buffer_xon_offset_field_name` | `"xon_offset"` | profile の `xon_offset` フィールド識別 | `bufferorch.h:25` |
| `buffer_xoff_field_name` | `"xoff"` | profile の `xoff` フィールド識別 (`buffer_pool_xoff_field_name` と同値) | `bufferorch.h:26` |
| `buffer_dynamic_th_field_name` | `"dynamic_th"` | profile の `dynamic_th` フィールド識別 | `bufferorch.h:27` |
| `buffer_static_th_field_name` | `"static_th"` | profile の `static_th` フィールド識別 | `bufferorch.h:28` |
| `buffer_profile_field_name` | `"profile"` | PG / Queue の `profile` フィールド識別 | `bufferorch.h:29` |
| `buffer_profile_list_field_name` | `"profile_list"` | port ingress/egress profile list フィールド識別 | `bufferorch.h:33` |
| `buffer_headroom_type_field_name` | `"headroom_type"` | profile の headroom_type フィールド識別 | `bufferorch.h:34` |

---

## 3. `type` フィールド値定数

| 定数名 | 値 | SAI 対応 | ソース |
|---|---|---|---|
| `buffer_value_ingress` | `"ingress"` | `SAI_BUFFER_POOL_TYPE_INGRESS` | `bufferorch.h:31`, `bufferorch.cpp:443,445` |
| `buffer_value_egress` | `"egress"` | `SAI_BUFFER_POOL_TYPE_EGRESS` | `bufferorch.h:32`, `bufferorch.cpp:447,449` |
| `buffer_value_both` | `"both"` | `SAI_BUFFER_POOL_TYPE_BOTH` | `bufferorch.h:33` (暗示), `bufferorch.cpp:451,453` |

> **乖離**: `buffermgrdyn.cpp` L2544-2549 では `buffer_value_ingress` ("ingress") 以外はすべて `BUFFER_EGRESS` に分類する。`"both"` を指定すると内部キャッシュ上は `BUFFER_EGRESS` 扱いになる。

---

## 4. `mode` フィールド値定数

| 定数名 | 値 | SAI 対応 | ソース |
|---|---|---|---|
| `buffer_pool_mode_dynamic_value` | `"dynamic"` | `SAI_BUFFER_POOL_THRESHOLD_MODE_DYNAMIC` | `bufferorch.h:21`, `bufferorch.cpp:476` |
| `buffer_pool_mode_static_value` | `"static"` | `SAI_BUFFER_POOL_THRESHOLD_MODE_STATIC` | `bufferorch.h:22`, `bufferorch.cpp:480` |

---

## 5. 方向 enum (buffermgrdyn.h)

| 値 | 数値 | 別名 | 用途 | ソース |
|---|---|---|---|---|
| `BUFFER_INGRESS` | `0` | `BUFFER_PG` | ingress 方向 PG headroom 管理 | `buffermgrdyn.h:20-21` |
| `BUFFER_EGRESS` | `1` | `BUFFER_QUEUE` | egress 方向 queue 管理 | `buffermgrdyn.h:22-23` |

---

## 6. SAI 識別子 (bufferorch.cpp)

### pool 属性

| SAI 識別子 | 用途 | ソース |
|---|---|---|
| `SAI_BUFFER_POOL_ATTR_SIZE` | pool の `size` フィールドを SAI に渡す | `bufferorch.cpp:427` |
| `SAI_BUFFER_POOL_ATTR_TYPE` | pool の `type` フィールドを SAI に渡す (create-only) | `bufferorch.cpp:460` |
| `SAI_BUFFER_POOL_ATTR_THRESHOLD_MODE` | pool の `mode` フィールドを SAI に渡す (create-only) | `bufferorch.cpp:487` |
| `SAI_BUFFER_POOL_ATTR_XOFF_SIZE` | pool の `xoff` フィールドを SAI に渡す | `bufferorch.cpp:493` |
| `SAI_BUFFER_POOL_TYPE_INGRESS` | type=ingress の SAI 値 | `bufferorch.cpp:445` |
| `SAI_BUFFER_POOL_TYPE_EGRESS` | type=egress の SAI 値 | `bufferorch.cpp:449` |
| `SAI_BUFFER_POOL_TYPE_BOTH` | type=both の SAI 値 | `bufferorch.cpp:453` |
| `SAI_BUFFER_POOL_THRESHOLD_MODE_DYNAMIC` | mode=dynamic の SAI 値 | `bufferorch.cpp:476` |
| `SAI_BUFFER_POOL_THRESHOLD_MODE_STATIC` | mode=static の SAI 値 | `bufferorch.cpp:480` |

### watermark 統計 ID

| SAI 識別子 | 用途 | ソース |
|---|---|---|
| `SAI_BUFFER_POOL_STAT_WATERMARK_BYTES` | pool 使用量 watermark (bytes) | `bufferorch.cpp:31` |
| `SAI_BUFFER_POOL_STAT_XOFF_ROOM_WATERMARK_BYTES` | SHP (xoff room) watermark (bytes) | `bufferorch.cpp:32` |

---

## 7. Flex Counter / Counter DB 定数 (bufferorch.h / bufferorch.cpp)

| 定数名 | 値 | 用途 | ソース |
|---|---|---|---|
| `BUFFER_POOL_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"BUFFER_POOL_WATERMARK_STAT_COUNTER"` | FLEX_COUNTER_DB の group name。`FLEX_COUNTER_GROUP_TABLE` キーに使用 | `bufferorch.h:15`, `bufferorch.cpp:247,281,333,344` |
| `BUFFER_POOL_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS` | `"60000"` (= 60 秒) | watermark ポーリング間隔 (ミリ秒) | `bufferorch.h:16`, `bufferorch.cpp:248` |
| `COUNTERS_BUFFER_POOL_NAME_MAP` | `"COUNTERS_BUFFER_POOL_NAME_MAP"` | COUNTERS_DB の pool 名 → SAI OID マッピング hash 名 | `sonic-swss-common/common/schema.h:238`, `bufferorch.cpp:55` |

---

## 8. Lua plugin / Watermark 関連定数

| 定数 / 識別子 | 値 | 用途 | ソース |
|---|---|---|---|
| `bufferPoolWatermarkStatIds` | `{SAI_BUFFER_POOL_STAT_WATERMARK_BYTES, SAI_BUFFER_POOL_STAT_XOFF_ROOM_WATERMARK_BYTES}` | FLEX_COUNTER_DB に書き込む watermark stat ID リスト | `bufferorch.cpp:29-33` |
| `BUFFER_POOL_COUNTER_ID_LIST` フィールド名 | `"BUFFER_POOL_COUNTER_ID_LIST"` | FLEX_COUNTER_TABLE の stat ID リストフィールド名 | `bufferorch.cpp:358` |

---

## 特記事項

1. **`ingress_lossless_pool` のみ特別扱い**: xoff フィールドの書き込みチェック (`buffermgrdyn.cpp:2625`)、SHP (Shared Headroom Pool) 計算 (`buffermgrdyn.cpp:740`)、mode 取得 (`buffermgrdyn.cpp:546`) はすべてこのプール名にハードコードされている。他の pool 名 (egress 系) は CONFIG_DB の key をそのまま使用する。
2. **`type` / `mode` は SAI create-only 属性**: `bufferorch.cpp:437-441` / `467-471` で確認。既存 pool への SET 時に type/mode フィールドが来ても LOG_INFO のみでスキップ。YANG にこの制約の記述なし。
3. **poll 間隔は非 YANG**: `BUFFER_POOL_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS = "60000"` はコードハードコード。CONFIG_DB からは変更不可。
4. **`COUNTERS_BUFFER_POOL_NAME_MAP` は sonic-swss-common で定義**: orchagent はヘッダ経由で参照するが、文字列値はスキーマファイル (`schema.h`) で一元管理。

---

## 出典

- `sonic-net/sonic-swss/cfgmgr/buffermgrdyn.h` L14, L20-23
- `sonic-net/sonic-swss/cfgmgr/buffermgr.h` L13
- `sonic-net/sonic-swss/orchagent/bufferorch.h` L15-34
- `sonic-net/sonic-swss/cfgmgr/buffermgr.cpp` L118, L132, L264
- `sonic-net/sonic-swss/cfgmgr/buffermgrdyn.cpp` L546, L703-706, L740, L747, L987, L1263, L2546-2549, L2556, L2625, L2640
- `sonic-net/sonic-swss/orchagent/bufferorch.cpp` L29-33, L55, L247-252, L281-282, L333-344, L358, L427-487, L493, L540-547
- `sonic-net/sonic-swss-common/common/schema.h` L238
