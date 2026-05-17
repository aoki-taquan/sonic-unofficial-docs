# DASH_ROUTING_TYPE — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-17 (q67-f-dash-rt-types3-next)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-swss/orchagent/dash/dashorch.cpp` (ref: HEAD)

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | result_table ステータス | evidence |
|---|---|---|---|---|
| 無効な routing type 名（`RoutingType_Parse()` 失敗） | `doTaskRoutingTypeTable()` L490 | WARN ログ → `erase(it)` → 恒久スキップ | なし | `dashorch.cpp:490-494` |
| protobuf デシリアライズ失敗（`parsePbMessage()` false） | `doTaskRoutingTypeTable()` L501 | WARN ログ → `erase(it)` → 恒久スキップ | なし | `dashorch.cpp:501-505` |
| 同一 routing type の二重登録（`addRoutingTypeEntry()` 内で重複検出） | `addRoutingTypeEntry()` L445 | WARN ログ → `return true`（冪等・成功扱い、既存エントリ上書きなし） | `DASH_RESULT_SUCCESS` | `dashorch.cpp:445-449` |
| `addRoutingTypeEntry()` が false を返す（現行コードでは発生しないが将来の SAI 連携時の拡張点） | `doTaskRoutingTypeTable()` L508 | `result = DASH_RESULT_FAILURE` → `it++`（再試行） → `writeResultToDB(FAILURE)` | `DASH_RESULT_FAILURE` | `dashorch.cpp:513-517` |
| `action_type=staticencap` かつ `encap_type` 不正（VXLAN/NVGRE 以外）— VNET マッピング参照時 | `addOutboundCaToPa()` L337（`dashvnetorch.cpp`） | ERROR ログ → `return true`（consumer から erase、VNET マッピング未作成） | — | `dashvnetorch.cpp:337-338` |
| `action_type=staticencap` 指定時に `getRouteTypeActions()` で該当 routing type 未登録 | `addOutboundCaToPa()` L315（`dashvnetorch.cpp`） | INFO ログ → `return false`（VNET マッピング作成保留） | — | `dashvnetorch.cpp:315-318` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | result_table ステータス | evidence |
|---|---|---|---|---|
| 存在しない routing type の削除（`removeRoutingTypeEntry()` 内で不在検出） | `removeRoutingTypeEntry()` L461 | WARN ログ → `return true`（冪等・成功扱い） | result エントリ削除 | `dashorch.cpp:461-464` |
| `removeRoutingTypeEntry()` が false を返す（現行コードでは発生しない） | `doTaskRoutingTypeTable()` L521 | `it++`（再試行） | result エントリ残留 | `dashorch.cpp:526-528` |
| 不明な操作コード（SET/DEL 以外） | `doTaskRoutingTypeTable()` L533 | ERROR ログ → `erase(it)` → 恒久スキップ | なし | `dashorch.cpp:533-534` |

### 検出ロジック補足

- **result_table への書き込み先**: `APPL_STATE_DB` の `APP_DASH_ROUTING_TYPE_TABLE_NAME` テーブル（`dashorch.cpp:73` で `app_state_db` に接続）。フィールド `result` に `0`（SUCCESS）または `1`（FAILURE）を書き込む（`DASH_RESULT_SUCCESS` / `DASH_RESULT_FAILURE`、`dashorch.h:35-36`）。
- **二重登録は冪等（サイレント）**: `addRoutingTypeEntry()` は重複を WARN ログで報告するが `return true` を返すため、consumer 側は成功とみなしてエントリを erase する。既存の routing_type_entries_ エントリは変更されない。更新には必ず DEL → SET が必要。
- **SAI 連携なし**: `DASH_ROUTING_TYPE_TABLE` エントリ自体は SAI API を呼ばず orchagent メモリ（`routing_type_entries_`）にのみ格納される。SAI 失敗は発生しない。SAI 失敗経路が生じるのは、この routing type を参照する VNET マッピング・ルートエントリの作成時（`dashvnetorch.cpp`、`dashrouteorch.cpp`）。
- **依存側の失敗伝播**: VNET マッピングが `getRouteTypeActions()` で `false` を返すと、そのマッピングエントリは consumer キューに保留（`return false` → `it++` パターン）。routing type が後から登録されると次の tick で自動再処理される。

### グレップカバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `RoutingType_Parse` | 1 | `dashorch.cpp:490` |
| `parsePbMessage` (routing type) | 1 | `dashorch.cpp:501` |
| `addRoutingTypeEntry` | 2 | `dashorch.cpp:445, 508` |
| `removeRoutingTypeEntry` | 2 | `dashorch.cpp:461, 521` |
| `DASH_RESULT_FAILURE` (routing type) | 1 | `dashorch.cpp:514` |
| `writeResultToDB` (routing type) | 1 | `dashorch.cpp:517` |
| `removeResultFromDB` (routing type) | 1 | `dashorch.cpp:524` |
| `getRouteTypeActions` | 1 | `dashvnetorch.cpp:315` |

<!-- /failure -->
