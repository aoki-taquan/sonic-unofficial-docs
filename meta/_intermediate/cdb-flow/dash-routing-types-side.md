# dash-routing-types — Phase F: 副次 DB 書込 (side-effects)

## 調査対象ファイル

- `sonic-swss/orchagent/dash/dashorch.cpp` L441-537 (`addRoutingTypeEntry`, `removeRoutingTypeEntry`, `doTaskRoutingTypeTable`)
- `sonic-swss/orchagent/saihelper.cpp` L1125-1160 (`writeResultToDB`, `removeResultFromDB`)
- `sonic-swss/orchagent/orchdaemon.cpp` L993,1350 (DPU_APPL_STATE_DB 接続, DashOrch 初期化)
- `sonic-swss/orchagent/dash/dashorch.h` L66 (コンストラクタシグネチャ)
- `sonic-swss-common/common/schema.h` L184 (`APP_DASH_ROUTING_TYPE_TABLE_NAME = "DASH_ROUTING_TYPE_TABLE"`)

## 副次 DB 書込の全体像

`DASH_ROUTING_TYPE_TABLE` への SET/DEL が引き起こす副次書込は **DPU_APPL_STATE_DB への結果書込のみ**。

SAI API 呼び出しは一切発生しない。routing_type_entries_ in-memory マップへの格納で処理が完結するため、ASIC_DB・COUNTERS_DB・FLEX_COUNTER_DB への書込もない。

## SET 時の副次書込

### DPU_APPL_STATE_DB / DASH_ROUTING_TYPE_TABLE

- 発生条件: `doTaskRoutingTypeTable()` 内で SET_COMMAND を処理した後（成功・失敗ともに）
- 実装: `writeResultToDB(dash_routing_type_result_table_, routing_type_str, result)` (`dashorch.cpp:517`)
- テーブル接続: `dash_routing_type_result_table_` は `make_unique<Table>(app_state_db, APP_DASH_ROUTING_TYPE_TABLE_NAME)` で初期化。`app_state_db` は `DPU_APPL_STATE_DB` に接続された `DBConnector` (`orchdaemon.cpp:993`)

| キー | フィールド | 値 (成功時) | 値 (失敗時) |
|------|-----------|-----------|-----------|
| `ROUTING_TYPE_<NAME>` | `result` | `"0"` (DASH_RESULT_SUCCESS) | `"1"` (DASH_RESULT_FAILURE) |

- キー変換: 元のキー (`vnet_encap` 等) が `std::transform(::toupper)` + `"ROUTING_TYPE_"` プレフィックス付加後の文字列で書き込まれる (`dashorch.cpp:487-488,517`)
- 書込タイミング: `addRoutingTypeEntry()` の返り値に関わらず必ず書き込まれる（成功・再登録スキップ・失敗のいずれも）

### protobuf デシリアライズ失敗時

`parsePbMessage()` が失敗した場合は `writeResultToDB` が呼ばれず、エントリが consumer キューから erase されるのみ (`dashorch.cpp:500-505`)。DPU_APPL_STATE_DB への書込なし。

## DEL 時の副次書込

### DPU_APPL_STATE_DB エントリ削除

- 発生条件: `removeRoutingTypeEntry()` が成功した場合のみ
- 実装: `removeResultFromDB(dash_routing_type_result_table_, routing_type_str)` (`dashorch.cpp:524`)
- 削除されるキー: `DPU_APPL_STATE_DB / DASH_ROUTING_TYPE_TABLE|ROUTING_TYPE_<NAME>`
- DEL 失敗時（エントリが存在しない場合）: `removeResultFromDB` は呼ばれず、既存の result エントリが残る

## SAI・その他 DB への影響なし

| DB / リソース | 書込発生 | 理由 |
|-------------|---------|------|
| ASIC_DB | なし | routing type は in-memory のみ。SAI DASH API 呼び出しなし |
| COUNTERS_DB | なし | SAI OID を持たないため CRM カウンタ更新なし |
| FLEX_COUNTER_DB | なし | 同上 |
| STATE_DB | なし | DASH 系は STATE_DB でなく DPU_APPL_STATE_DB を使用 |
| CONFIG_DB | なし | orchagent は CONFIG_DB への書戻しを行わない |

## 外部コントローラとの非同期通知

`DPU_APPL_STATE_DB / DASH_ROUTING_TYPE_TABLE` への結果書込は、gNMI 等の外部コントローラが SAI プログラム状態を確認するための非同期通知チャネルとして機能する。外部コントローラは result フィールドをポーリングすることで routing type の登録成否を確認できる。

## スキャン証跡

`dashorch.cpp` L441-537、`saihelper.cpp` L1125-1160、`orchdaemon.cpp` L993,1350、`schema.h` L184 を精読。副次書込は DPU_APPL_STATE_DB のみ。SAI・CRM・FLEX_COUNTER 書込なし確認。
