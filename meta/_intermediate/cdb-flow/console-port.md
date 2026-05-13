# CONFIG_DB 例外条件分析: CONSOLE_PORT

## Consumer

- `sonic-utilities` の `config console` コマンド群 (`config/console.py`): CONSOLE_PORT テーブルを直接 read/write。consutil がポート接続時に参照。
- `consmgr` は存在せず、ConfigDB への書き込みは CLI が直接行う。

## 例外条件

### 1. 既存エントリへの add → 即時失敗
- ソース: `config/console.py` L114-115
- `config console add` 時に指定 linenum のエントリが既に存在する場合 `ctx.fail("Trying to add console port setting, which is already exists.")` で終了。上書き不可。

### 2. remote_device 重複 → 失敗
- ソース: `config/console.py` L120-121, `isExistingSameDevice()`
- 同じ `remote_device` 名がすでに他の linenum で使われている場合 `ctx.fail("Given device name {} has been used. Please enter a valid device name ...")` で終了。device 名はシステム内一意制約。

### 3. ConfigDB 書き込みエラー (ValueError / JsonPatchConflict) → ctx.fail
- ソース: `config/console.py` L130-131, L151-152
- `ValidatedConfigDBConnector` への書き込み時に YANG スキーマ検証失敗 (baud_rate の型不正等) で `ValueError` / `JsonPatchConflict` が発生した場合 `ctx.fail("Invalid ConfigDB. Error: ...")` で終了。

### 4. 存在しないエントリへの del / update → 失敗
- ソース: `config/console.py` L145-148, L172-173
- `config console del` / `config console remote_device` で指定 linenum が未存在の場合 `ctx.fail("Trying to delete/update console port setting, which is not present.")` で終了。

### 5. baud_rate が既存値と同一 → no-op
- ソース: `config/console.py` L215-216
- `config console baud` で指定した baud が現在値と同じ場合、DB 更新をスキップして正常終了。
