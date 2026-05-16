# AUTO_TECHSUPPORT — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-net/sonic-utilities/utilities_common/auto_techsupport_helper.py` (共有定数 + フォールバック既定)
- `sonic-net/sonic-utilities/scripts/coredump_gen_handler.py` (CORE_DUMP_DIR を import 利用)
- `sonic-net/sonic-utilities/scripts/techsupport_cleanup.py` (TS_DIR を import 利用)

> 注: `sonic-host-services` には auto-techsupport 用 daemon は無く、実体は `sonic-utilities` の `scripts/` 配下にある。
> 公式名 `auto-techsupport.service` も `coredump_gen_handler.py` / `techsupport_cleanup.py` を起動する。

---

## 1. ファイルシステムパス (auto_techsupport_helper.py L33-39)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `CORE_DUMP_DIR` | `/var/core` | core dump ファイル収集ディレクトリ。`max_core_limit` 計算時の base path | helper L33 |
| `CORE_DUMP_PTRN` | `*.core.gz` | core dump ファイル名 glob (gzip 圧縮済 core を対象) | helper L34 |
| `TS_DIR` | `/var/dump` | techsupport 出力ディレクトリ。`max_techsupport_limit` 計算時の base path | helper L36 |
| `TS_ROOT` | `sonic_dump_*` | techsupport ファイル名ルート glob | helper L37 |
| `TS_PTRN` | `sonic_dump_.*tar.*` | techsupport ファイル名検出正規表現 | helper L38 |
| `TS_PTRN_GLOB` | `sonic_dump_*tar*` | techsupport ファイル名 glob 形式 (cleanup 用) | helper L39 |

`CORE_DUMP_DIR` は `coredump_gen_handler.py` L15/L33/L72 で、`TS_DIR` は `techsupport_cleanup.py` L22/L25/L43 で import 利用される。ディレクトリパス自体はコード書換以外で変更不可能なハードコード。

---

## 2. CONFIG_DB テーブル / フィールド名定数 (helper L42-54)

| 定数 | 値 | 用途 |
|------|----|------|
| `CFG_DB` | `CONFIG_DB` | DB 名 |
| `STATE_DB` | `STATE_DB` | DB 名 |
| `AUTO_TS` | `AUTO_TECHSUPPORT\|GLOBAL` | GLOBAL key 完全形 |
| `CFG_STATE` | `state` | GLOBAL/FEATURE 共通フィールド名 |
| `CFG_MAX_TS` | `max_techsupport_limit` | GLOBAL フィールド名 |
| `COOLOFF` | `rate_limit_interval` | GLOBAL/FEATURE 共通 |
| `CFG_CORE_USAGE` | `max_core_limit` | GLOBAL フィールド名 |
| `CFG_SINCE` | `since` | GLOBAL フィールド名 |
| `FEATURE` | `AUTO_TECHSUPPORT_FEATURE\|{}` | feature 別 key テンプレ |

---

## 3. 既定値・タイムアウト・バッファ (helper L69-71)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `TIME_BUF` | `20` 秒 | rate-limit 判定時の時間余裕バッファ (連続起動間隔の許容誤差) | helper L69 |
| `SINCE_DEFAULT` | `"2 days ago"` | `AUTO_TECHSUPPORT.since` 未設定 / `date` パース失敗時の二重 fallback | helper L70 |
| `TS_GLOBAL_TIMEOUT` | `"60"` (秒) | `show techsupport` 実行のグローバルタイムアウト | helper L71 |

---

## 4. STATE_DB スキーマ定数 (helper L60-67)

| 定数 | 値 | 用途 |
|------|----|------|
| `TS_MAP` | `AUTO_TECHSUPPORT_DUMP_INFO` | STATE_DB テーブル名 |
| `CORE_DUMP` | `core_dump` | STATE_DB フィールド名 |
| `TIMESTAMP` | `timestamp` | STATE_DB フィールド名 |
| `CONTAINER` | `container_name` | STATE_DB フィールド名 |
| `EVENT_TYPE` | `event_type` | STATE_DB フィールド名 |
| `EVENT_TYPE_CORE` | `core` | event_type 値 |
| `EVENT_TYPE_MEMORY` | `memory` | event_type 値 |

---

## 5. 終了コード / リトライ上限 (helper L81-84)

| 定数 | 値 | 用途 |
|------|----|------|
| `EXT_LOCKFAIL` | `2` | flock 取得失敗 (重複起動防止) |
| `EXT_RETRY` | `4` | リトライ要求 exit code |
| `EXT_SUCCESS` | `0` | 正常終了 |
| `MAX_RETRY_LIMIT` | `2` | techsupport 起動失敗時の最大リトライ回数 |

---

## 6. PATH 環境変数注入 (helper L74-78)

| 定数 / 挙動 | 値 | 用途 |
|------|----|------|
| `ENV_VAR["PATH"]` 前置 | `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:` | クロスビルド (`CROSS_BUILD_ENVIRON=y`) 以外で subprocess 起動前に PATH 先頭へ追加。`show techsupport` が必要とする utilities をネイティブパスから発見させる |

---

## 7. memory_threshold_check.py のコード定数 (参考)

`auto-techsupport.md` の Phase A defaults 表に記載済 (`DEFAULT_AVAILABLE_MEM_THRESHOLD = 10.0`, `DEFAULT_MIN_AVAILABLE_MEM = 200` MB, `DEFAULT_MEMORY_AVAILABLE_FEATURE_THRESHOLD = 0`)。これは fallback 既定値であって、`SINCE_DEFAULT` / パスのような書換不可固定値ではないため本 Phase E では再掲のみ。

---

## 特記事項

1. **`/var/core` / `/var/dump` はビルド固定**: パスは init_cfg.json.j2 にも YANG にも存在せず、helper 内 Python 定数のみ。CONFIG_DB からの変更経路は存在しない。
2. **`SINCE_DEFAULT="2 days ago"` の二重 fallback**: (a) `AUTO_TECHSUPPORT.since` フィールド欠落、(b) 値が `date -d '<since>'` で解釈失敗 — どちらでも同じ `"2 days ago"` に落ちる (`auto_techsupport_helper.py:213,215,219`)。
3. **`TS_GLOBAL_TIMEOUT="60"`**: `show techsupport` の subprocess に渡されるタイムアウト。文字列のまま `--timeout` 等に渡る。CONFIG_DB から変更経路なし。
4. **`TIME_BUF=20` 秒**: rate-limit 連続起動判定で「`rate_limit_interval` 経過後 +20 秒の猶予」を持たせる固定マージン。
5. **`MAX_RETRY_LIMIT=2`**: techsupport が `EXT_RETRY` で抜けた場合の最大再試行回数。3 回目で諦め。
6. **`CORE_DUMP_PTRN="*.core.gz"`**: gzip 圧縮 core dump のみ集計対象。未圧縮 core (`*.core`) は `max_core_limit` 計算から除外される (= `coredump-compress` service による圧縮後にのみ容量カウント)。

---

## 出典

- `sonic-net/sonic-utilities/utilities_common/auto_techsupport_helper.py` L11-84
- `sonic-net/sonic-utilities/scripts/coredump_gen_handler.py` L15, L33, L72 (`CORE_DUMP_DIR` import 利用)
- `sonic-net/sonic-utilities/scripts/techsupport_cleanup.py` L22, L25, L43 (`TS_DIR` import 利用)
