# ERROR_DB ハードコード定数調査メモ (Phase E)

調査日: 2026-05-19
対象: ERROR_DB (ERROR_ROUTE_TABLE / ERROR_NEIGH_TABLE)

## 調査対象ファイル

- `sonic-swss-common/common/status_code_util.h` — `StatusCode` enum + `statusCodeMapping` (実装済み)
- `SONiC/doc/error-handling/error_handling_design_spec.md` (HLD Rev 0.1, 2019-05-06) — Section 3.3.2 で ERR_NOTIFY_FAIL / ERR_NOTIFY_POSITIVE_ACK フラグを使用
- `sonic-swss/orchagent/lagid.h` — `LAG_ID_ALLOCATOR_ERROR_DB_ERROR = -4` (本 DB とは別の定数)

## 重要事項

ERROR_DB / ErrorReporter / ErrorListener は 2026-05 時点で master 未マージ。
実装済みコンポーネントは `sonic-swss-common/common/status_code_util.h` の `StatusCode` enum のみ。

## 実装済み定数

### StatusCode enum (status_code_util.h)

15 コード定義。HLD 設計時の 8 コードから拡張済み。

```cpp
// sonic-swss-common/common/status_code_util.h:9-26
enum class StatusCode {
    SWSS_RC_SUCCESS,           // SAI_STATUS_SUCCESS
    SWSS_RC_INVALID_PARAM,     // SAI_STATUS_INVALID_PARAMETER
    SWSS_RC_DEADLINE_EXCEEDED, // HLD 後追加
    SWSS_RC_UNAVAIL,           // SAI_STATUS_NOT_SUPPORTED
    SWSS_RC_NOT_FOUND,         // SAI_STATUS_ITEM_NOT_FOUND
    SWSS_RC_NO_MEMORY,         // SAI_STATUS_NO_MEMORY
    SWSS_RC_EXISTS,            // SAI_STATUS_ITEM_ALREADY_EXISTS
    SWSS_RC_PERMISSION_DENIED, // HLD 後追加
    SWSS_RC_FULL,              // SAI_STATUS_TABLE_FULL
    SWSS_RC_IN_USE,            // SAI_STATUS_OBJECT_IN_USE
    SWSS_RC_INTERNAL,          // HLD 後追加
    SWSS_RC_UNIMPLEMENTED,     // HLD 後追加
    SWSS_RC_NOT_EXECUTED,      // HLD 後追加
    SWSS_RC_FAILED_PRECONDITION, // HLD 後追加
    SWSS_RC_UNKNOWN,           // フォールバック
};
```

`strToStatusCode()` は未知文字列を受けると `SWSS_RC_UNKNOWN` を返す (status_code_util.h:74-80)。

### HLD 定義の ERR_NOTIFY フラグ (未実装)

HLD Section 3.3.2 の ErrorListener 登録例 (コード未マージ):

```cpp
ErrorListener fpmErrorListener(APP_ROUTE_TABLE_NAME,
    (ERR_NOTIFY_FAIL | ERR_NOTIFY_POSITIVE_ACK));
```

- `ERR_NOTIFY_FAIL` — 失敗通知を受け取るフラグ (デフォルト動作)
- `ERR_NOTIFY_POSITIVE_ACK` — 成功時も通知を受け取るフラグ (オプション)

正式なビット値は HLD 未定義。実装ヘッダーが存在しないため数値不明。

## 未実装のため存在しないハードコード定数

以下のコードパスは master 未マージのため、orchagent 内にハードコード定数は存在しない:
- ERROR_DB の Redis DB ID (database_config.json 未登録)
- ErrorReporter / ErrorListener クラスの定数
- ASIC_DB → ERROR_DB 変換テーブル定数
