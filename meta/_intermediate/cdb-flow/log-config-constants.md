# LOGGER ハードコード定数 (Phase E)

ソース:
- `sonic-net/sonic-swss-common` `common/loglevel.h` @ 158de8d3463ff4b841653f6d57190bb142b80d9c
- `sonic-net/sonic-swss-common` `common/logger.h` @ 158de8d3463ff4b841653f6d57190bb142b80d9c
- `sonic-net/sonic-swss-common` `common/logger.cpp` @ 158de8d3463ff4b841653f6d57190bb142b80d9c

## デフォルト loglevel 定数 (loglevel.h:4-5)

| 定数名 | 値 | 用途 |
|--------|----|------|
| `DEFAULT_LOGLEVEL` | `"NOTICE"` | swss コンポーネントの `LOGLEVEL` 初期値。`linkToDbNative()` のデフォルト引数として使用 |
| `SAI_DEFAULT_LOGLEVEL` | `"SAI_LOG_LEVEL_NOTICE"` | SAI コンポーネント (`SAI_API_*`) の `LOGLEVEL` 初期値。`swssloglevel -d` での全リセット値 |

## settingThread タイムアウト定数 (logger.cpp:208)

| 値 | 用途 |
|----|------|
| `1000` ms | `select.select(&selectable, 1000)` のタイムアウト。loglevel 変更通知の最大遅延時間を決定する。1 秒ごとにポーリングループが回る |

## ログバッファサイズ定数 (logger.cpp:302, 378)

| 値 | 用途 |
|----|------|
| `0x1000` (4096 bytes) | ログメッセージの最大バッファサイズ。`write()` / `wthrow()` 内の `vsnprintf(buffer, 0x1000, ...)` で使用。4096 バイトを超えるメッセージは切り捨てられる |

## Priority enum 値 (logger.h:54-64)

| 内部値 | 対応する CONFIG_DB 文字列 | syslog priority |
|-------|------------------------|----------------|
| `SWSS_EMERG` | `"EMERG"` | LOG_EMERG |
| `SWSS_ALERT` | `"ALERT"` | LOG_ALERT |
| `SWSS_CRIT` | `"CRIT"` | LOG_CRIT |
| `SWSS_ERROR` | `"ERROR"` | LOG_ERR |
| `SWSS_WARN` | `"WARN"` | LOG_WARNING |
| `SWSS_NOTICE` | `"NOTICE"` (デフォルト) | LOG_NOTICE |
| `SWSS_INFO` | `"INFO"` | LOG_INFO |
| `SWSS_DEBUG` | `"DEBUG"` | LOG_DEBUG |

## Output enum 値 (logger.h:70-75)

| 内部値 | 対応する CONFIG_DB 文字列 | 出力先 |
|-------|------------------------|--------|
| `SWSS_SYSLOG` | `"SYSLOG"` (デフォルト) | syslog デーモン (`vsyslog()`) |
| `SWSS_STDOUT` | `"STDOUT"` | 標準出力 (`printf`) |
| `SWSS_STDERR` | `"STDERR"` | 標準エラー出力 (`fprintf(stderr, ...)`) |

## 内部初期値 (logger.h:160, 162)

| メンバー変数 | 初期値 | 意味 |
|------------|--------|------|
| `m_minPrio` | `SWSS_NOTICE` | プロセス内部の最小ログ優先度。CONFIG_DB から読み取った値で上書き |
| `m_output` | `SWSS_SYSLOG` | プロセス内部のログ出力先。CONFIG_DB から読み取った値で上書き |
