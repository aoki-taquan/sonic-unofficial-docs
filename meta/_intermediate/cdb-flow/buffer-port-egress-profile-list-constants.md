# BUFFER_PORT_EGRESS_PROFILE_LIST — Phase E ハードコード定数

## 対象ソースファイル

- `sonic-swss/cfgmgr/buffermgrdyn.cpp`
- `sonic-swss/orchagent/bufferorch.cpp`
- `sonic-swss-common/common/schema.h`
- `sonic-swss/orchagent/orch.h`

---

## 検出済みハードコード定数

### テーブル名定数 (schema.h)

| 定数名 | 値 | 用途 |
|---|---|---|
| `CFG_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME` | `"BUFFER_PORT_EGRESS_PROFILE_LIST"` | CONFIG_DB テーブル名 |
| `APP_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME` | `"BUFFER_PORT_EGRESS_PROFILE_LIST_TABLE"` | APPL_DB テーブル名 |

evidence: `sonic-swss-common/common/schema.h:164,366`

### フィールド名定数 (bufferorch.cpp)

| 定数名 | 値 | 用途 |
|---|---|---|
| `buffer_profile_list_field_name` | `"profile_list"` | profile_list フィールドキー名 |

evidence: `sonic-swss/orchagent/bufferorch.cpp:34`

### SAI 識別子 (bufferorch.cpp)

| 定数名 | 型 | 用途 |
|---|---|---|
| `SAI_PORT_ATTR_QOS_EGRESS_BUFFER_PROFILE_LIST` | `sai_attr_id_t` | egress バッファプロファイルリストをポートに bind する SAI 属性 ID |
| `SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR` | `sai_bulk_op_error_mode_t` | Bulk SAI 呼び出し時エラーモード（一部失敗が他ポートをブロックしない） |
| `SAI_OBJECT_TYPE_PORT` | `sai_object_type_t` | `SaiAttrWrapper` 生成時に指定するオブジェクト型 |

evidence: `sonic-swss/orchagent/bufferorch.cpp:1865,2014,1958`

### direction 値 (buffermgrdyn.cpp)

| 内部列挙値 | 文字列表現 | 意味 |
|---|---|---|
| `BUFFER_EGRESS` | `"egress"` | egress 方向（固定）。`handleSingleBufferPortEgressProfileListEntry` は常に `BUFFER_EGRESS` を渡す |
| `BUFFER_INGRESS` | `"ingress"` | ingress 方向（参照用：egress 側に ingress profile を指定すると `task_failed`） |

evidence: `sonic-swss/cfgmgr/buffermgrdyn.cpp:36,3459`

### 区切り文字 (orch.h / buffermgrdyn.cpp)

| 定数名 | 値 | 用途 |
|---|---|---|
| `list_item_delimiter` | `','`（カンマ） | port_names のトークン分割（`tokenize(key, list_item_delimiter)`）|
| カンマ区切り | `','` | `checkBufferProfileDirection` 内での profileRefList 分割にも使用 |

evidence: `sonic-swss/orchagent/orch.h:32`, `bufferorch.cpp:1862`, `buffermgrdyn.cpp:3278`

### 空リスト (DEL 操作時の count = 0)

| 挙動 | ハードコード値 | evidence |
|---|---|---|
| DEL 操作時 `attr.value.objlist.count` | `0`（ゼロ固定） | `bufferorch.cpp:1939` |
| DEL 操作時 `attr.value.objlist.list` | `profile_list.data()`（空ベクタのポインタ） | `bufferorch.cpp:1940` |

SAI に count=0 のリストを渡すことで「egress バッファプロファイルなし」を表現する。YANG には記述なし。

### Bulk SAI 呼び出しパラメータ (bufferorch.cpp)

| パラメータ | 値 | 用途 |
|---|---|---|
| error mode | `SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR` | 一部ポートの SAI 失敗が他ポートの処理をブロックしない |
| DEL 処理優先順 | `{DEL_COMMAND, SET_COMMAND}` の順でループ（DEL 優先） | `processEgressBufferProfileListBulk` 内のオペレーション処理順 |

evidence: `bufferorch.cpp:1990,2014`

---

## YANG vs 実装 — 定数レベル乖離

| 項目 | YANG | 実装 |
|---|---|---|
| egress 固定 direction | 記述なし | `BUFFER_EGRESS` 定数で固定、ingress profile を指定すると `task_failed` |
| DEL 時の count=0 | 記述なし | `attr.value.objlist.count = 0` ハードコード |
| SAI Bulk エラーモード | 記述なし | `SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR` ハードコード |
| field 名 `profile_list` | YANG leaf-list 名として定義あり | `buffer_profile_list_field_name = "profile_list"` で一致 |
