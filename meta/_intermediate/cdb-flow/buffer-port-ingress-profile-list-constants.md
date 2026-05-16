# buffer-port-ingress-profile-list — Phase E ハードコード定数

ソース: `sonic-swss/cfgmgr/buffermgrdyn.cpp`, `sonic-swss/orchagent/bufferorch.cpp`

## テーブル名・フィールド名定数

| 定数名 | 値 | ソース |
|---|---|---|
| `CFG_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME` | `"BUFFER_PORT_INGRESS_PROFILE_LIST"` | `sonic-swss-common/common/schema.h:365` |
| `APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME` | `"BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE"` | `sonic-swss-common/common/schema.h:163` |
| `buffer_profile_list_field_name` | `"profile_list"` | `sonic-swss/orchagent/bufferorch.h:34` |

## SAI 識別子

| 定数名 | 用途 | ソース |
|---|---|---|
| `SAI_PORT_ATTR_QOS_INGRESS_BUFFER_PROFILE_LIST` | ingress バッファプロファイルリストをポートに bind する SAI 属性 ID | `bufferorch.cpp:1675` |
| `SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR` | Bulk SAI 呼び出し時エラーモード（一部ポート失敗が他ポートをブロックしない） | `bufferorch.cpp:1824` |
| `SAI_OBJECT_TYPE_PORT` | `SaiAttrWrapper` 生成時に指定するオブジェクト型 | `bufferorch.cpp:1768` |
| `SAI_API_PORT` | `handleSaiSetStatus` でエラー処理時に渡す SAI API 種別 | `bufferorch.cpp:1785` |
| `SAI_STATUS_NOT_EXECUTED` | bulk 配列初期値（未実行状態マーカー） | `bufferorch.cpp:1768,1813` |
| `SAI_STATUS_SUCCESS` | post 処理で成功判定に使う SAI ステータス値 | `bufferorch.cpp:1783` |

## direction 値（ingress 固定）

`handleSingleBufferPortIngressProfileListEntry` は常に `BUFFER_INGRESS`（文字列 `"ingress"`）を `handleSingleBufferPortProfileListEntry` に渡す。egress profile（`BUFFER_EGRESS` 方向）を ingress profile list に指定した場合は `checkBufferProfileDirection` が `task_failed` を返す。

| 内部列挙値 | 整数値 | 文字列表現 | ソース |
|---|---|---|---|
| `BUFFER_INGRESS` | `0` | `"ingress"` | `buffermgrdyn.h:20`, `buffermgrdyn.cpp:36,3454` |
| `BUFFER_EGRESS` | `1` | `"egress"` | `buffermgrdyn.h:22`（参照用） |

## 区切り文字

| 定数名 | 値 | 用途 |
|---|---|---|
| `list_item_delimiter` | `','`（カンマ） | `tokenize(key, list_item_delimiter)` — キー内のポート名分割 | 
| （無名） | `','`（カンマ） | `checkBufferProfileDirection` 内の profile 名リスト分割 |

evidence: `sonic-swss/orchagent/orch.h:32`, `bufferorch.cpp:1672`, `buffermgrdyn.cpp:3278`

## 空リスト（DEL 操作時のハードコード）

DEL 操作時、SAI に count=0 のオブジェクトリストを渡すことで「ingress バッファプロファイルなし」を表現する。YANG には記述なし。

| 属性 | ハードコード値 | ソース |
|---|---|---|
| `attr.value.objlist.count` | `0` | `bufferorch.cpp:1749` |
| `attr.value.objlist.list` | 空ベクタの `.data()` ポインタ | `bufferorch.cpp:1750` |

## trim 禁止判定（ingress 専用ハードコード）

`processIngressBufferProfileList` 内で profile ごとに `profCfg.isTrimmingEligible` を確認し、`true` の場合は `task_failed` を即時返却する。egress profile list には同等チェックがない（SAI 仕様上 ingress 側トリミングは禁止）。

| チェック対象フラグ | 値（禁止条件） | 効果 | ソース |
|---|---|---|---|
| `profCfg.isTrimmingEligible` | `true` | `task_failed` 返却、profile list 適用拒否 | `bufferorch.cpp:1725-1731` |

## Bulk SAI 処理順（DEL 優先）

`processIngressBufferProfileListBulk` 内で `{DEL_COMMAND, SET_COMMAND}` の順にループするため、DEL が SET より先に SAI へ送られる。

evidence: `bufferorch.cpp:1800`
