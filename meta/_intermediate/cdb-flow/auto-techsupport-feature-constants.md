# AUTO_TECHSUPPORT_FEATURE — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-utilities/utilities_common/auto_techsupport_helper.py` (パス・パターン・キー名・終了コード・タイムアウト)
- `sonic-utilities/scripts/coredump_gen_handler.py` (handler ロジック内で参照される定数。実体は helper を `import *`)
- `sonic-utilities/scripts/techsupport_cleanup.py` (cleanup ロジック。helper の `TS_DIR` / `CFG_MAX_TS` のみ参照)
- `sonic-utilities/scripts/memory_threshold_check.py` (メモリしきい値デフォルト)
- `sonic-utilities/sonic_package_manager/service_creator/feature.py` (パッケージ install 時の `AUTO_TECHSUPPORT_FEATURE` 初期値)
- `sonic-utilities/scripts/coredump-compress` (bash; 固定出力パス)

---

## 1. ファイルシステムパス / ファイル名パターン (auto_techsupport_helper.py L33-39)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `CORE_DUMP_DIR` | `/var/core` | core dump の保存ディレクトリ。`coredump-compress` が `/bin/gzip -1 -` の出力先として直接利用、`coredump_gen_handler.py` が `get_stats()` で容量集計 | `auto_techsupport_helper.py:33`; `scripts/coredump-compress:21` |
| `CORE_DUMP_PTRN` | `*.core.gz` | core dump 検出 glob パターン (cleanup 対象) | `auto_techsupport_helper.py:34` |
| `TS_DIR` | `/var/dump` | techsupport tarball の保存ディレクトリ | `auto_techsupport_helper.py:36` |
| `TS_ROOT` | `sonic_dump_*` | techsupport tarball glob 接頭辞 | `auto_techsupport_helper.py:37` |
| `TS_PTRN` | `sonic_dump_.*tar.*` | techsupport tarball 検出正規表現 | `auto_techsupport_helper.py:38` |
| `TS_PTRN_GLOB` | `sonic_dump_*tar*` | techsupport tarball 検出 glob (上記の glob 版) | `auto_techsupport_helper.py:39` |

---

## 2. CONFIG_DB / STATE_DB キー定数 (auto_techsupport_helper.py L42-67)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `CFG_DB` | `"CONFIG_DB"` | `SonicV2Connector.get()` の DB 名引数 | `auto_techsupport_helper.py:42` |
| `STATE_DB` | `"STATE_DB"` | rate-limit 状態 (前回 dump timestamp) を保持する DB 名 | `auto_techsupport_helper.py:43,57` |
| `AUTO_TS` | `"AUTO_TECHSUPPORT\|GLOBAL"` | GLOBAL 設定の Redis key | `auto_techsupport_helper.py:46` |
| `FEATURE` | `"AUTO_TECHSUPPORT_FEATURE\|{}"` | feature 単位 key テンプレ (`format(<feature_name>)`) | `auto_techsupport_helper.py:54` |
| `CFG_STATE` | `"state"` | HGET フィールド名 | `auto_techsupport_helper.py:47` |
| `CFG_MAX_TS` | `"max_techsupport_limit"` | HGET フィールド名 | `auto_techsupport_helper.py:48` |
| `COOLOFF` | `"rate_limit_interval"` | HGET フィールド名。GLOBAL / FEATURE 共通 | `auto_techsupport_helper.py:49` |
| `CFG_CORE_USAGE` | `"max_core_limit"` | HGET フィールド名 (GLOBAL のみ) | `auto_techsupport_helper.py:50` |
| `CFG_SINCE` | `"since"` | HGET フィールド名。`show techsupport --since` に渡す | `auto_techsupport_helper.py:51` |
| `TS_MAP` | `"AUTO_TECHSUPPORT_DUMP_INFO"` | STATE_DB 上の dump 記録テーブル名 | `auto_techsupport_helper.py:60` |
| `CORE_DUMP` | `"core_dump"` | STATE_DB レコードフィールド名 | `auto_techsupport_helper.py:61` |
| `TIMESTAMP` | `"timestamp"` | STATE_DB レコードフィールド名 (rate-limit 計算に使用) | `auto_techsupport_helper.py:62` |
| `CONTAINER` | `"container_name"` | STATE_DB レコードフィールド名 | `auto_techsupport_helper.py:63` |
| `EVENT_TYPE` | `"event_type"` | STATE_DB レコードフィールド名 (`core` / `memory`) | `auto_techsupport_helper.py:64` |
| `EVENT_TYPE_CORE` | `"core"` | event_type 列挙値 | `auto_techsupport_helper.py:66` |
| `EVENT_TYPE_MEMORY` | `"memory"` | event_type 列挙値 (memory_threshold_check 起動時) | `auto_techsupport_helper.py:67` |

---

## 3. タイミング・しきい値定数 (auto_techsupport_helper.py L69-74)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `TIME_BUF` | `20` 秒 | `verify_recent_file_creation()` の判定窓。core dump イベント発火と実ファイル作成のズレ吸収 | `auto_techsupport_helper.py:69,115` |
| `SINCE_DEFAULT` | `"2 days ago"` | `CFG_SINCE` 値が `date -d` で解釈不能/未指定時の fallback。`show techsupport --since` に渡す | `auto_techsupport_helper.py:70,216,220` |
| `TS_GLOBAL_TIMEOUT` | `"60"` (文字列) | techsupport 全体のグローバルタイムアウト引数 (`show techsupport --global-timeout`) | `auto_techsupport_helper.py:71,235` |

> `TS_GLOBAL_TIMEOUT` は文字列リテラル `"60"` で固定。CONFIG_DB から上書きできない。

---

## 4. プロセス終了コード / リトライ (auto_techsupport_helper.py L81-84)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `EXT_SUCCESS` | `0` | `generate_dump` 正常終了コード | `auto_techsupport_helper.py:83` |
| `EXT_LOCKFAIL` | `2` | techsupport 同時実行ロック取得失敗。再試行せず終了 | `auto_techsupport_helper.py:81,239` |
| `EXT_RETRY` | `4` | techsupport 一時失敗。`MAX_RETRY_LIMIT` 回まで再試行 | `auto_techsupport_helper.py:82,241` |
| `MAX_RETRY_LIMIT` | `2` | `EXT_RETRY` 時の最大再試行回数 | `auto_techsupport_helper.py:84,242` |

---

## 5. メモリしきい値デフォルト (memory_threshold_check.py L10-30)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `EXIT_SUCCESS` | `0` | `memory_threshold_check` 正常終了 | `memory_threshold_check.py:10` |
| `EXIT_FAILURE` | `1` | 一般失敗 (techsupport 起動せず) | `memory_threshold_check.py:11` |
| `EXIT_THRESHOLD_CROSSED` | `2` | メモリしきい値超過。techsupport 起動 | `memory_threshold_check.py:12` |
| `DEFAULT_MEMORY_AVAILABLE_THRESHOLD` | `10` (%) | `AUTO_TECHSUPPORT\|GLOBAL.available_mem_threshold` 欠落時のホスト全体しきい値 fallback | `memory_threshold_check.py:24` |
| `DEFAULT_MEMORY_AVAILABLE_MIN_THRESHOLD` | `200` (MB) | ホスト全体の絶対最小 free memory しきい値 (相対 % しきい値と AND 評価) | `memory_threshold_check.py:26` |
| `DEFAULT_MEMORY_AVAILABLE_FEATURE_THRESHOLD` | `0` (%) | `AUTO_TECHSUPPORT_FEATURE.<feat>.available_mem_threshold` 欠落時 fallback。`0` = メモリチェック無効 | `memory_threshold_check.py:28` |
| `MB_TO_KB_MULTIPLIER` | `1024` | メモリ値 MB → KB 換算定数 | `memory_threshold_check.py:30` |
| `AUTO_TECHSUPPORT` | `"AUTO_TECHSUPPORT"` | CONFIG_DB テーブル名 | `memory_threshold_check.py:17` |
| `AUTO_TECHSUPPORT_FEATURE` | `"AUTO_TECHSUPPORT_FEATURE"` | CONFIG_DB テーブル名 | `memory_threshold_check.py:18` |
| `DOCKER_STATS` | `"DOCKER_STATS"` | STATE_DB テーブル名 (コンテナ毎メモリ %) | `memory_threshold_check.py:21` |

> **GLOBAL fallback (`10`) と FEATURE fallback (`0`) の乖離**: ホスト全体は 10% で発火するが、feature 単位はフィールド欠落だとチェック自体スキップ。`init_cfg.json.j2` / `feature.py` が install 時に `"10.0"` を書き込むため通常運用では発生しないが、CLI で明示的に削除されると無効化される。

---

## 6. パッケージ install 時デフォルト (feature.py L22-26)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `DEFAULT_AUTO_TS_FEATURE_CONFIG['state']` | `'disabled'` | `sonic-package-manager install` 時に `AUTO_TECHSUPPORT\|GLOBAL` 不在ならこの値で AUTO_TECHSUPPORT_FEATURE を作成 | `feature.py:23` |
| `DEFAULT_AUTO_TS_FEATURE_CONFIG['rate_limit_interval']` | `'600'` (秒) | install 時 `rate_limit_interval` 初期値 (10 分) | `feature.py:24` |
| `DEFAULT_AUTO_TS_FEATURE_CONFIG['available_mem_threshold']` | `'10.0'` (%) | install 時 `available_mem_threshold` 初期値 | `feature.py:25` |

> install 時 default (`rate_limit_interval=600`) と実行時 fallback (`auto_techsupport_helper.py:328-331` の `except ValueError: container_cooloff = 0.0`) で挙動が異なる。フィールド欠落 = rate-limit 無効。

---

## 7. coredump-compress 出力パス (bash; coredump-compress L21,32)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `/var/core/${PREFIX}core.gz` | 固定出力先 | kernel `core_pattern` から渡された core を gzip 圧縮して書き出す。`PREFIX` は `<comm>.<time>.<pid>.<ppid>.[<ns>.]` で構成 | `scripts/coredump-compress:21` |
| `/usr/local/bin/coredump_gen_handler.py` | 固定 python スクリプトパス | `setsid` でバックグラウンド起動される handler | `scripts/coredump-compress:32` |
| `/tmp/coredump_gen_handler.log` | 固定ログ出力先 | `coredump_gen_handler.py` の stdout/stderr 集約先 (毎回 truncate) | `scripts/coredump-compress:31-32` |

> kernel `core_pattern` 側 (`sonic-buildimage/files/image_config/sysctl/90-sonic.conf:45`) で `|/usr/local/bin/coredump-compress %e %t %p %P` がハードコード。`/var/core` を変更したい場合は coredump-compress と auto_techsupport_helper.py の両方を書き換える必要がある。

---

## 特記事項

1. **`coredump_gen_handler.py` 自身は定数を持たない**: `from utilities_common.auto_techsupport_helper import *` で全定数を取り込み、`CORE_DUMP_DIR` / `CORE_DUMP_PTRN` / `AUTO_TS` / `CFG_STATE` 等を直接参照する。Phase E の調査対象は実質 `auto_techsupport_helper.py`。
2. **`techsupport_cleanup.py` は `TS_DIR` / `CFG_MAX_TS` の 2 定数のみ参照**: `AUTO_TECHSUPPORT_FEATURE` テーブルは見ない (GLOBAL の `state` + `max_techsupport_limit` だけで cleanup 判定)。
3. **`/var/core` / `/var/dump` のディスク容量管理はハードコード**: `max_core_limit` / `max_techsupport_limit` (%) は CONFIG_DB から設定可能だが、対象ディレクトリ自体は変更不可。
4. **`TIME_BUF=20` 秒の意味**: kernel core dump → `coredump-compress` の gzip → `setsid` 起動された `coredump_gen_handler.py` の間にラグがあり、handler 起動時には `find_new_core_files()` で「直近 20 秒以内に作成された `*.core.gz`」のみを対象にする。これより古いものは別イベント由来として扱う。
5. **`TS_GLOBAL_TIMEOUT="60"` は CONFIG_DB から上書き不可**: 単位は `show techsupport --global-timeout` の仕様 (秒) に従う。長時間 techsupport を回したい運用ではここを書き換える必要がある。
6. **STATE_DB `AUTO_TECHSUPPORT_DUMP_INFO_TABLE` の key 名**: helper では `TS_MAP = "AUTO_TECHSUPPORT_DUMP_INFO"` (TABLE サフィックスなし)。実際の Redis key には swsscommon の TABLE 区切り `|` が付き、`AUTO_TECHSUPPORT_DUMP_INFO|<filename>` 形式で書き込まれる。
7. **`/tmp/coredump_gen_handler.log` の取扱い**: 毎回 truncate されるため過去ログは失われる。トラブルシュート時は事象直後にコピーする必要あり。

---

## 出典

- `sonic-net/sonic-utilities/utilities_common/auto_techsupport_helper.py` L1-84
- `sonic-net/sonic-utilities/scripts/coredump_gen_handler.py` L1-82
- `sonic-net/sonic-utilities/scripts/techsupport_cleanup.py` L1-59
- `sonic-net/sonic-utilities/scripts/memory_threshold_check.py` L1-30
- `sonic-net/sonic-utilities/sonic_package_manager/service_creator/feature.py` L19-26
- `sonic-net/sonic-utilities/scripts/coredump-compress` L1-35
- `sonic-net/sonic-buildimage/files/image_config/sysctl/90-sonic.conf` L45 (kernel `core_pattern`)
