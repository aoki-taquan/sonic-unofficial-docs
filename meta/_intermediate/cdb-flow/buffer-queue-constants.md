# BUFFER_QUEUE ハードコード定数調査メモ (Phase E)

ソース: `sonic-swss/cfgmgr/buffermgrdyn.cpp`, `sonic-swss/orchagent/bufferorch.cpp`

## 1. queue index 範囲

### 非 VOQ モード
- key 形式: `<port>|<qindex>` — トークン数は厳密に **2**
  (`bufferorch.cpp:943` `tokens.size() != 2` → `task_invalid_entry`)
- `qindex` は `parseIndexRange()` でパース。有効範囲はポートが持つ実 queue 数に依存
- 範囲上限チェック: `port.m_queue_ids.size() <= ind` → `task_invalid_entry`
  (`bufferorch.cpp:1061-1064`)
- 実装上の上限は SAI / プラットフォームから取得した `m_queue_ids` サイズ次第
  (YANG regex `(1[0-5]|[0-9])((-)(1[0-5]|[0-9]))?` は **0〜15** を許容)

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

## 3. フィールド名文字列定数 (bufferorch.cpp)

| 変数名 | ハードコード値 | 用途 |
|---|---|---|
| `buffer_profile_field_name` | `"profile"` | `BUFFER_QUEUE` の profile フィールド参照キー (`bufferorch.cpp:30`) |
| `buffer_pool_field_name` | `"pool"` | buffer pool 参照用 (`bufferorch.cpp:21`) |
| `buffer_pool_mode_dynamic_value` | `"dynamic"` | pool mode 比較用 (`bufferorch.cpp:22`) |
| `buffer_pool_mode_static_value` | `"static"` | pool mode 比較用 (`bufferorch.cpp:23`) |

## 4. `_zero_` プロファイル判定文字列

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

## 5. `m_partiallyAppliedQueues` セット

- 型: `std::set<std::string>` (key 文字列のセット)
- 役割: queue lock (`port.m_queue_lock[ind] == true`) で `task_need_retry` を返した key を保持
- 動作:
  - lock 中: `m_partiallyAppliedQueues.insert(key)` → `task_need_retry` (`bufferorch.cpp:1069`)
  - ロック解除後: profile 未変更でも当該 key が `m_partiallyAppliedQueues` に存在すれば SAI 更新を強制し、その後 `erase` (`bufferorch.cpp:979-986`)
  - SET 成功後: `erase` (`bufferorch.cpp:1008`)
- VoQ モードでは lock チェック自体が存在しないため `m_partiallyAppliedQueues` への登録も発生しない

## 6. その他のハードコード値

| 定数・リテラル | 値 | 場所 | 意味 |
|---|---|---|---|
| `gMySwitchType` 比較値 | `"voq"` | `bufferorch.cpp:116, 916, 1049` | VOQ モード判定文字列 |
| VOQ key トークン数 | `4` | `bufferorch.cpp:918` | VOQ key の必須トークン数 |
| 非 VOQ key トークン数 | `2` | `bufferorch.cpp:943` | 非 VOQ key の必須トークン数 |
| `BUFFER_QUEUE` enum値 | `1` (BUFFER_PG=0, BUFFER_QUEUE=1 の想定) | `buffermgrdyn.cpp:289` | `m_bufferZeroProfileName[BUFFER_QUEUE]` / `m_bufferObjectIdsToZero[BUFFER_QUEUE]` インデックス |
