# AUTO_TECHSUPPORT — Phase E ハードコード定数 中間ファイル

生成日: 2026-05-16 (task q67-f-phaseE-coredump)
ソース: `sonic-utilities/scripts/coredump_gen_handler.py`, `utilities_common/auto_techsupport_helper.py`, `scripts/coredump-compress`

<!-- constants -->
## 抽出定数一覧

### ファイルパス・ディレクトリ定数

| 定数名 | 値 | ファイル:行 |
|--------|-----|-----------|
| `CORE_DUMP_DIR` | `"/var/core"` | `auto_techsupport_helper.py:33` |
| `CORE_DUMP_PTRN` | `"*.core.gz"` | `auto_techsupport_helper.py:34` |
| `TS_DIR` | `"/var/dump"` | `auto_techsupport_helper.py:36` |
| `TS_PTRN` | `"sonic_dump_.*tar.*"` | `auto_techsupport_helper.py:38` |
| `TS_PTRN_GLOB` | `"sonic_dump_*tar*"` | `auto_techsupport_helper.py:39` |

### CONFIG_DB キー・フィールド定数

| 定数名 | 値 | ファイル:行 |
|--------|-----|-----------|
| `CFG_DB` | `"CONFIG_DB"` | `auto_techsupport_helper.py:42` |
| `STATE_DB` | `"STATE_DB"` | `auto_techsupport_helper.py:43` |
| `AUTO_TS` | `"AUTO_TECHSUPPORT\|GLOBAL"` | `auto_techsupport_helper.py:46` |
| `CFG_STATE` | `"state"` | `auto_techsupport_helper.py:47` |
| `CFG_MAX_TS` | `"max_techsupport_limit"` | `auto_techsupport_helper.py:48` |
| `COOLOFF` | `"rate_limit_interval"` | `auto_techsupport_helper.py:49` |
| `CFG_CORE_USAGE` | `"max_core_limit"` | `auto_techsupport_helper.py:50` |
| `CFG_SINCE` | `"since"` | `auto_techsupport_helper.py:51` |
| `FEATURE` | `"AUTO_TECHSUPPORT_FEATURE\|{}"` | `auto_techsupport_helper.py:54` |

### タイミング・動作制御定数

| 定数名 | 値 | 用途 |
|--------|-----|------|
| `TIME_BUF` | `20` (秒) | coredump ファイル生成からの有効期間 (`verify_recent_file_creation`) |
| `SINCE_DEFAULT` | `"2 days ago"` | `since` 未設定時のデフォルト収集期間 |
| `TS_GLOBAL_TIMEOUT` | `"60"` (秒) | `show techsupport --global-timeout` の値 |

ソース: `auto_techsupport_helper.py:69-71`

### techsupport 終了コード定数

| 定数名 | 値 | 意味 |
|--------|-----|------|
| `EXT_SUCCESS` | `0` | 正常終了 |
| `EXT_LOCKFAIL` | `2` | 別インスタンス実行中、リトライしない |
| `EXT_RETRY` | `4` | リトライ要求 |
| `MAX_RETRY_LIMIT` | `2` | 最大リトライ回数 |

ソース: `auto_techsupport_helper.py:81-84`

### state フィールド有効 enum 値

`AUTO_TECHSUPPORT|GLOBAL` および `AUTO_TECHSUPPORT_FEATURE|<feature>` の `state`:

- `"enabled"`: techsupport 収集を有効化
- `"disabled"`: 収集をスキップ

チェック箇所: `coredump_gen_handler.py:17` (`!= "enabled"`)、`coredump_gen_handler.py:47`、`coredump_gen_handler.py:55`

### systemd-coredump / coredump-compress 統合定数

`scripts/coredump-compress` (bash) のハードコード値:

| 項目 | 値 | 説明 |
|------|-----|------|
| 保存先パス | `/var/core/${PREFIX}core.gz` | gzip 圧縮コアの書き込み先 |
| gzip 圧縮レベル | `-1` (最速) | `gzip -1` で圧縮 |
| ハンドラログ | `/tmp/coredump_gen_handler.log` | `coredump_gen_handler.py` の標準出力/エラー |
| 起動方式 | `setsid ... &` (非同期) | コアダンプ圧縮をブロックしない非同期起動 |

ソース: `scripts/coredump-compress:19-31`

<!-- /constants -->
