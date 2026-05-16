# BUFFER_QUEUE ハードコード定数調査メモ (Phase E)

ソース: `sonic-swss/cfgmgr/buffermgrdyn.cpp`, `sonic-swss/orchagent/bufferorch.cpp`,
`sonic-swss/cfgmgr/buffermgrdyn.h`, `sonic-swss/orchagent/bufferorch.h`,
`sonic-swss/cfgmgr/buffer_headroom_mellanox.lua`

## 1. queue index 範囲

### 非 VOQ モード
- key 形式: `<port>|<qindex>` — トークン数は厳密に **2**
  (`bufferorch.cpp:943` `tokens.size() != 2` → `task_invalid_entry`)
- `qindex` は `parseIndexRange()` でパース。有効範囲はポートが持つ実 queue 数に依存
- 範囲上限チェック: `port.m_queue_ids.size() <= ind` → `task_invalid_entry`
  (`bufferorch.cpp:1061-1064`)
- YANG regex が許容する最大 qindex: **15** (`(1[0-5]|[0-9])...`)
- デフォルト j2 テンプレート (`buffers_config.j2:307-324`) が設定する 3 レンジ: `0-2`, `3-4`, `5-6`

### VOQ シャーシモード
- key 形式: `<hostname>|<asic_name>|<port>|<qindex>` — トークン数は厳密に **4**
  (`bufferorch.cpp:918` `tokens.size() != 4` → `task_invalid_entry`)
- 範囲上限チェック: `gPortsOrch->getPortVoQIds(port).size() <= ind` → `task_invalid_entry`
  (`bufferorch.cpp:1052-1055`)
- FlexCounter 追加・削除は VOQ モードではスキップ (flexcounterorch が全 system port を一括管理)
  (`bufferorch.cpp:1134-1136`)

## 2. SAI 識別子

| 定数 | 値 (SAI ヘッダ) | 用途 | evidence |
|---|---|---|---|
| `SAI_QUEUE_ATTR_BUFFER_PROFILE_ID` | enum値 (SAI_QUEUE_ATTR_*) | queue に buffer profile を SET する属性 ID | `bufferorch.cpp:1021` |
| `SAI_NULL_OBJECT_ID` | `0` | DEL 時または解決失敗時にセットするヌル OID | `bufferorch.cpp:1005` |
| `SAI_OBJECT_TYPE_QUEUE` | enum値 | `SaiAttrWrapper` への object_type 指定 | `bufferorch.cpp:1082` |

`sai_queue_api->set_queues_attribute()` を bulk で呼び出す (`bufferorch.cpp:1269`)。

## 3. フィールド名文字列定数 (`bufferorch.h`)

| 変数名 | ハードコード値 | 用途 |
|---|---|---|
| `buffer_profile_field_name` | `"profile"` | `BUFFER_QUEUE` の profile フィールド参照キー (`bufferorch.h:30`) |
| `buffer_pool_field_name` | `"pool"` | buffer pool 参照用 (`bufferorch.h:21`) |
| `buffer_pool_mode_dynamic_value` | `"dynamic"` | pool mode 比較用 (`bufferorch.h:22`) |
| `buffer_pool_mode_static_value` | `"static"` | pool mode 比較用 (`bufferorch.h:23`) |
| `buffer_value_ingress` | `"ingress"` | direction 判定用 (`bufferorch.h:31`) |
| `buffer_value_egress` | `"egress"` | direction 判定用 (`bufferorch.h:32`) |
| `buffer_value_both` | `"both"` | direction 判定用 (`bufferorch.h:33`) |
| `buffer_pool_xoff_field_name` | `"xoff"` | pool xoff フィールド (`bufferorch.h:24`) |
| `buffer_xon_field_name` | `"xon"` | profile xon フィールド (`bufferorch.h:25`) |
| `buffer_xon_offset_field_name` | `"xon_offset"` | profile xon_offset フィールド (`bufferorch.h:26`) |
| `buffer_xoff_field_name` | `"xoff"` | profile xoff フィールド (`bufferorch.h:27`) |
| `buffer_dynamic_th_field_name` | `"dynamic_th"` | profile 動的閾値フィールド (`bufferorch.h:28`) |
| `buffer_static_th_field_name` | `"static_th"` | profile 静的閾値フィールド (`bufferorch.h:29`) |

## 4. デーモン設定定数 (`buffermgrdyn.h`)

| 定数 | 値 | 意味 |
|---|---|---|
| `DEFAULT_MTU_STR` | `"9100"` | profile 名生成時に MTU が未指定の場合に使用するデフォルト MTU (bytes). profile key に含まれない (`buffermgrdyn.h:15`) |
| `INGRESS_LOSSLESS_PG_POOL_NAME` | `"ingress_lossless_pool"` | ingress lossless pool 名 (`buffermgrdyn.h:14`) |
| `BUFFERMGR_TIMER_PERIOD` | `10` | buffermgrd 内部タイマー周期（秒）。headroom 再計算・task retry に使用 (`buffermgrdyn.h:17`) |

## 5. FlexCounter 統計 polling 定数 (`bufferorch.h`)

| 定数 | 値 | 意味 |
|---|---|---|
| `BUFFER_POOL_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS` | `"60000"` | buffer pool watermark 統計の FlexCounter polling 間隔（ms = 60 秒） (`bufferorch.h:16`) |
| `BUFFER_POOL_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"BUFFER_POOL_WATERMARK_STAT_COUNTER"` | FlexCounter グループ名 (`bufferorch.h:15`) |

## 6. `_zero_` プロファイル判定文字列

- 文字列サブストリング: `"_zero_"` (ハードコード)
- 用途: `buffer_profile_name.find("_zero_") == std::string::npos` で zero profile か否かを判定
  - `counter_needs_to_add` / `counter_was_added` の算出に使用
  (`bufferorch.cpp:995, 1017, 1400, 1421`)
- zero profile は egress queue に対して traffic なし（バッファ回収）を意味する
- zero profile 適用時は FlexCounter の queue counter 追加・削除をスキップ

### zero profile 情報の JSON フィールド名 (buffermgrdyn.cpp)

| JSON フィールド名 | 用途 | evidence |
|---|---|---|
| `"queues_to_apply_zero_profile"` | zero profile を適用する queue インデックスリスト | `buffermgrdyn.cpp:283` |
| `"egress_zero_profile"` | queue (egress) 向け zero profile 名 | `buffermgrdyn.cpp:287` |
| `"pgs_to_apply_zero_profile"` | PG 向け（参考・BUFFER_QUEUE スコープ外） | `buffermgrdyn.cpp:275` |
| `"ingress_zero_profile"` | PG 向け（参考・BUFFER_QUEUE スコープ外） | `buffermgrdyn.cpp:279` |

zero profile が未指定の場合、pool の `zero_profile_name` フィールドから自動的に最初の egress zero profile を採用 (`buffermgrdyn.cpp:333-334`)。

## 7. `m_partiallyAppliedQueues` セット

- 型: `std::set<std::string>` (key 文字列のセット)
- 役割: queue lock (`port.m_queue_lock[ind] == true`) で `task_need_retry` を返した key を保持
- 動作:
  - lock 中: `m_partiallyAppliedQueues.insert(key)` → `task_need_retry` (`bufferorch.cpp:1069`)
  - ロック解除後: profile 未変更でも当該 key が `m_partiallyAppliedQueues` に存在すれば SAI 更新を強制し、その後 `erase` (`bufferorch.cpp:979-986`)
  - SET 成功後: `erase` (`bufferorch.cpp:1008`)
- VoQ モードでは lock チェック自体が存在しないため `m_partiallyAppliedQueues` への登録も発生しない

## 8. headroom 計算 Lua スクリプト内定数 (`buffer_headroom_mellanox.lua`)

cell_size・pipeline_latency (IPL)・mac_phy_delay (IPG) はハードコードされず `STATE_DB.ASIC_TABLE` から取得する。以下はスクリプト内にハードコードされる値:

| 定数 | 値 | 意味 |
|---|---|---|
| `speed_of_light` | `198000000` m/s | ケーブル伝播遅延計算用（光速の約 2/3） |
| `minimal_packet_size` | `64` バイト | worst-case cell 占有率算出に使用 |
| IPG (`peer_response_time`) | `pause_quanta * 512 / 8` バイト | IEEE 802.3 pause quanta → IPG 変換式 |
| xoff 切り上げ粒度 | `1024` バイト | `math.ceil(xoff_value / 1024) * 1024` |

pause_quanta_per_speed テーブル (IEEE 802.3 31B.3.7 準拠):

| 速度 (Mb/s) | pause_quanta | peer_response_time (bytes) |
|---|---|---|
| 800000 | 905 | 57,920 |
| 400000 | 905 | 57,920 |
| 200000 | 453 | 28,992 |
| 100000 | 394 | 25,216 |
| 50000 | 147 | 9,408 |
| 40000 | 118 | 7,552 |
| 25000 | 80 | 5,120 |
| 10000 | 67 | 4,288 |
| 1000 | 2 | 128 |
| 100 | 1 | 64 |

## 9. その他のハードコード値

| 定数・リテラル | 値 | 場所 | 意味 |
|---|---|---|---|
| `gMySwitchType` 比較値 | `"voq"` | `bufferorch.cpp:116, 916, 1049` | VOQ モード判定文字列 |
| VOQ key トークン数 | `4` | `bufferorch.cpp:918` | VOQ key の必須トークン数 |
| 非 VOQ key トークン数 | `2` | `bufferorch.cpp:943` | 非 VOQ key の必須トークン数 |
| `BUFFER_QUEUE` enum値 | `1` (BUFFER_PG=0, BUFFER_QUEUE=1 の想定) | `buffermgrdyn.cpp:289` | `m_bufferZeroProfileName[BUFFER_QUEUE]` / `m_bufferObjectIdsToZero[BUFFER_QUEUE]` インデックス |
