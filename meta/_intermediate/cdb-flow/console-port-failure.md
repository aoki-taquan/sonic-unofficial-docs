# CONSOLE_PORT / CONSOLE_SWITCH 失敗挙動調査 (Phase D)

生成日: 2026-05-18
対象ページ: `docs/reference/config-db/console-port.md`
調査コミット: sonic-utilities (HEAD)

---

## 1. 失敗経路の分類

### 1-1. CLI 書き込み時の失敗 (config/console.py)

| 失敗条件 | 発生箇所 | 結果 | evidence |
|---|---|---|---|
| `config console add <line>` で linenum が既に存在する | `add_console_setting()` L114 | `ctx.fail("Trying to add console port setting, which is already exists.")` → exit 非 0 | `config/console.py:114-115` |
| `config console add --devicename` で同名 remote_device が既存 | `isExistingSameDevice()` L121 | `ctx.fail("Given device name ... has been used.")` → exit 非 0 | `config/console.py:120-123` |
| `config console add` で YANG バリデーション失敗 (`baud_rate` 型不正等) | `ValidatedConfigDBConnector.set_entry()` L129 | `ctx.fail("Invalid ConfigDB. Error: ...")` → exit 非 0 | `config/console.py:128-131` |
| `config console del <line>` で linenum が存在しない | `remove_console_setting()` L147-148 | `ctx.fail("Trying to delete console port setting, which is not present.")` → exit 非 0 | `config/console.py:147-154` |
| `config console del` で YANG patch conflict | `ValidatedConfigDBConnector.set_entry()` L151 | `ctx.fail("Invalid ConfigDB. Error: ...")` → exit 非 0 | `config/console.py:151-152` |
| `config console remote_device <line>` で linenum が存在しない | `update_console_remote_device_name()` L193 | `ctx.fail("Trying to update console port setting, which is not present.")` → exit 非 0 | `config/console.py:193-194` |
| `config console remote_device <line> <name>` で同名 device が既存 | `isExistingSameDevice()` L185 | `ctx.fail("Given device name ... has been used.")` → exit 非 0 | `config/console.py:185-186` |
| `config console baud <line>` で linenum が存在しない | `update_console_baud()` L224 | `ctx.fail("Trying to update console port setting, which is not present.")` → exit 非 0 | `config/console.py:224-225` |
| `config console flow_control <mode> <line>` で linenum が存在しない | `update_console_flow_control()` L256 | `ctx.fail("Trying to update console port setting, which is not present.")` → exit 非 0 | `config/console.py:256-257` |
| `config console escape <line>` で linenum が存在しない | `update_console_escape_char()` L288 | `ctx.fail("Trying to update console port setting, which is not present.")` → exit 非 0 | `config/console.py:288-289` |

### 1-2. consutil 実行時の失敗 (consutil/main.py, consutil/lib.py)

| 失敗条件 | 発生箇所 | エラーコード | 出力メッセージ | evidence |
|---|---|---|---|---|
| `CONSOLE_SWITCH.enabled` が `"no"` または未設定 | `consutil()` L27-29 | `ERR_DISABLE (1)` | `"Console switch feature is disabled"` | `consutil/main.py:26-29` |
| `consutil connect <target>` で指定ライン / デバイスが CONFIG_DB に存在しない | `LineNotFoundError` L133 | `ERR_DEV (3)` | `"Cannot connect: target [X] does not exist"` | `consutil/main.py:131-134` |
| `consutil connect <target>` で対象ラインが接続中 (busy) | `LineBusyError` L142 | `ERR_BUSY (5)` | `"Cannot connect: line [X] is busy"` | `consutil/main.py:141-143` |
| `consutil connect <target>` で `baud_rate` フィールドが DB に存在しない | `InvalidConfigurationError` L144 | `ERR_CFG (4)` | `"Cannot connect: line [X] has no baud rate"` | `consutil/main.py:144-146`, `lib.py:197-199` |
| `CONSOLE_SWITCH.default_escape_char` が大文字 (`[A-Z]`) | `InvalidConfigurationError` L100 | (例外伝播 → `ConsolePortProvider` 初期化失敗) | `"default console escape character is not valid"` | `consutil/lib.py:99-103` |
| picocom プロセス起動失敗 (デバイスファイル `/dev/ttyUSB<N>` 不在等) | `ConnectionFailedError` L147 | `ERR_DEV (3)` | `"Cannot connect: unable to open picocom process"` | `consutil/main.py:147-149` |
| picocom が `"Resource temporarily unavailable"` を返す (ライン競合) | `LineBusyError` (picocom busy) L221 | `ERR_BUSY (5)` | `"Cannot connect: line [X] is busy"` | `consutil/lib.py:219-221`, `consutil/main.py:141-143` |
| `consutil clear <target>` で root 権限なし | `consutil/main.py:102-104` | `ERR_CMD (2)` | `"Root privileges are required for this operation"` | `consutil/main.py:102-104` |
| `consutil clear <target>` で対象ラインが CONFIG_DB に存在しない | `LineNotFoundError` L110 | `ERR_DEV (3)` | `"Target [X] does not exist"` | `consutil/main.py:110-112` |
| `refresh()` 中にセッション PID が消えて line_num 不一致 | `ConnectionFailedError` L255 | (例外伝播) | なし (呼び出し元で捕捉) | `consutil/lib.py:251-255` |

---

## 2. エラーコード定義 (consutil/lib.py)

| 定数 | 値 | 意味 |
|---|---|---|
| `ERR_DISABLE` | 1 | console switch 機能が無効 |
| `ERR_CMD` | 2 | コマンド実行エラー (権限不足等) |
| `ERR_DEV` | 3 | デバイス / ターゲット不在 |
| `ERR_CFG` | 4 | CONFIG_DB の設定不正 |
| `ERR_BUSY` | 5 | ラインが使用中 |

---

## 3. 静的なガード vs 実行時ガードの区別

- **CLI ガード (静的)**: `config console add/del/baud/flow_control/remote_device/escape` は CONFIG_DB への書き込み前に linenum 存在確認・device 名重複確認・YANG バリデーションを行う。これらは DB の状態に依存したガードであり、直接 `sonic-db-cli` でエントリを書き込んだ場合はスキップされる。
- **consutil 実行時ガード (動的)**: `consutil connect` は `connect()` 内で `baud_rate` 必須チェック・busy チェック・picocom 起動確認を実施。これらは CLI ガードが迂回された場合にも機能する最終防線。
- **YANG バリデーション**: `ValidatedConfigDBConnector` 経由の書き込みのみ YANG スキーマチェックが走る。`sonic-db-cli` での直接書き込みは YANG をバイパスするため、`escape_char` に `[a-z]` 外の文字が格納されても DB 書き込みは成功し、`InvalidConfigurationError` で接続時にのみ発覚する場合がある。

---

## 4. 回復可能性

| エラー | 回復方法 |
|---|---|
| `LineBusyError` | `consutil clear <line>` で既存セッションを終了 → 再接続 |
| `InvalidConfigurationError (baud)` | `config console baud <line> <baud>` でフィールドを補完 |
| `LineNotFoundError` | `config console add <line> --baud <baud>` でエントリ追加 |
| `ConnectionFailedError` | `/dev/ttyUSB<N>` の物理デバイス存在確認 (`ls /dev/ttyUSB*`) |
| `CONSOLE_SWITCH disabled` | `config console enable` で機能を有効化 |
