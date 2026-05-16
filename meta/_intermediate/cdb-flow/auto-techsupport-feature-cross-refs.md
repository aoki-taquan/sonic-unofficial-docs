# AUTO_TECHSUPPORT_FEATURE テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/auto-techsupport-feature.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-utilities` の `scripts/coredump_gen_handler.py` / `scripts/techsupport_cleanup.py` / `scripts/memory_threshold_check.py` および共通ヘルパ `utilities_common/auto_techsupport_helper.py`。`AUTO_TECHSUPPORT_FEATURE` テーブル変更時に `coredump_gen_handler` パイプラインが**間接的に**読み出す関連 CONFIG_DB / STATE_DB テーブルを列挙する。

> ユーザ指示中の `sonic-host-services/scripts/coredump_gen_handler.py`, `techsupport_cleanup.py` は実体としては `sonic-net/sonic-utilities/scripts/` 配下に存在する (kernel `core_pattern` 経由で host が直接呼び出すため `sonic-utilities` で配布)。本資料は `.cache/sonic-sources/sonic-utilities/` のコードを根拠とする。

## スキャン手順

```
grep -nE "db\.(get|keys|get_all|set)\(|\.get_table\(|\.get_keys\(|format\(" \
    .cache/sonic-sources/sonic-utilities/scripts/coredump_gen_handler.py \
    .cache/sonic-sources/sonic-utilities/scripts/techsupport_cleanup.py \
    .cache/sonic-sources/sonic-utilities/scripts/memory_threshold_check.py \
    .cache/sonic-sources/sonic-utilities/utilities_common/auto_techsupport_helper.py
```

`AUTO_TECHSUPPORT_FEATURE` を主役テーブルとしたとき、ハンドラ実行中に DB 経由で読み合う**周辺**テーブル (`AUTO_TECHSUPPORT|GLOBAL`, `FEATURE`, STATE_DB の `AUTO_TECHSUPPORT_DUMP_INFO`) を抽出する。

## 検出された暗黙参照テーブル

### 1. グローバル共依存: `AUTO_TECHSUPPORT` (key=`GLOBAL`)

`AUTO_TECHSUPPORT_FEATURE|<feat>` の `state` と `rate_limit_interval` を評価する前段で、必ず `AUTO_TECHSUPPORT|GLOBAL` の同名フィールドが先に評価される。`GLOBAL.state != "enabled"` なら FEATURE 側の値に関わらず techsupport は起動しない。

| 参照箇所 | API | フィールド | 用途 | evidence |
|---|---|---|---|---|
| `coredump_gen_handler.handle_coredump_cleanup` | `db.get(CFG_DB, AUTO_TS, CFG_STATE)` | `state` | core dump cleanup 全体の ON/OFF | `coredump_gen_handler.py:17` |
| `coredump_gen_handler.handle_coredump_cleanup` | `db.get(CFG_DB, AUTO_TS, CFG_CORE_USAGE)` | `max_core_limit` | `/var/core` 容量しきい値 | `coredump_gen_handler.py:22` |
| `CriticalProcCoreDumpHandle.handle_core_dump_creation_event` | `db.get(CFG_DB, AUTO_TS, CFG_STATE)` | `state` | FEATURE 評価前のグローバルゲート | `coredump_gen_handler.py:47` |
| `techsupport_cleanup.handle_techsupport_creation_event` | `db.get(CFG_DB, AUTO_TS, CFG_STATE)` | `state` | techsupport cleanup の ON/OFF | `techsupport_cleanup.py:27` |
| `techsupport_cleanup.handle_techsupport_creation_event` | `db.get(CFG_DB, AUTO_TS, CFG_MAX_TS)` | `max_techsupport_limit` | `/var/dump` 容量しきい値 | `techsupport_cleanup.py:32` |
| `auto_techsupport_helper.invoke_ts_command_rate_limited` | `db.get(CFG_DB, AUTO_TS, COOLOFF)` | `rate_limit_interval` | グローバル cool-off (per-feature 値と並列評価) | `auto_techsupport_helper.py:315` |
| `auto_techsupport_helper.get_since_arg` | `db.get(CFG_DB, AUTO_TS, CFG_SINCE)` | `since` | `show techsupport --since` 引数 | `auto_techsupport_helper.py:214` |
| `memory_threshold_check.MemoryChecker` | `cfg_db.get_table(AUTO_TECHSUPPORT)` | `available_mem_threshold` 等 | ホスト全体メモリしきい値の取得 | `memory_threshold_check.py:117` |

定数定義: `AUTO_TS = "AUTO_TECHSUPPORT|GLOBAL"` (`auto_techsupport_helper.py:46`)。

### 2. 隣接共依存: `FEATURE` (docker)

`AUTO_TECHSUPPORT_FEATURE` の key は `FEATURE` テーブルの `name` (docker 名) と同一の文字列空間を共有する。YANG コメントに `TODO: Leafref once the FEATURE YANG is added` とあり、現状は型レベルの強制はないが、`coredump_gen_handler` は `args.container` (コンテナ名) を `AUTO_TECHSUPPORT_FEATURE|{}` のキーとして直接使う暗黙の対応関係を持つ。

| 参照箇所 | 形式 | 用途 | evidence |
|---|---|---|---|
| `CriticalProcCoreDumpHandle.handle_core_dump_creation_event` | `FEATURE_KEY = FEATURE.format(self.container)` | `args.container` (kernel 由来) を `AUTO_TECHSUPPORT_FEATURE\|<container>` キーに変換 | `coredump_gen_handler.py:54-55` |
| `auto_techsupport_helper.invoke_ts_command_rate_limited` | `db.get(CFG_DB, FEATURE.format(container), COOLOFF)` | per-feature rate-limit 値の取得 | `auto_techsupport_helper.py:317-319` |
| `memory_threshold_check.MemoryChecker` | `cfg_db.get_table(AUTO_TECHSUPPORT_FEATURE)` | 全 feature の `available_mem_threshold` を一括取得し、`args.container` を `startswith` で前方一致 | `memory_threshold_check.py:118,144` |

`FEATURE.format(container)` テンプレ定数: `FEATURE = "AUTO_TECHSUPPORT_FEATURE|{}"` (`auto_techsupport_helper.py:54`)。`container` 文字列は kernel `core_pattern` → `coredump-compress %e %t %p %P` から渡され `coredump_gen_handler.py:66-67` で `args.container` として受け取られる。`trim_masic_suffix()` で `swss0` → `swss` 等の masic suffix を剥がしてから FEATURE key を構築するため、`AUTO_TECHSUPPORT_FEATURE` のキーは masic suffix なしの形式 (`FEATURE` テーブルと同形) で書く必要がある (`coredump_gen_handler.py:52`)。

> ユーザ指示中の **`CORE_DUMP_NAME_TO_CONTAINER_MAP`** は現行 sonic-utilities master のコード上には存在しない名称。kernel `core_pattern` の `%e` (実行ファイル名) → コンテナ名のマッピングは `coredump-compress` シェルスクリプト側が `args.container` を組み立てて handler に渡す形で実装されており、CONFIG_DB / STATE_DB 上のテーブルとしては具現化されていない。よって本ページ Phase C では「`FEATURE` テーブル名 = container 名」という暗黙 leafref のみ記録する。

### 3. STATE_DB 連動: `AUTO_TECHSUPPORT_DUMP_INFO` (STATE_DB)

per-feature rate-limit 判定は CONFIG_DB の `rate_limit_interval` 値だけでは決定せず、STATE_DB に記録された**前回 dump の timestamp** と現在時刻の差で判定する。

| 参照箇所 | API | キー | 用途 | evidence |
|---|---|---|---|---|
| `auto_techsupport_helper.get_ts_map` | `db.keys(STATE_DB, TS_MAP+"*")` + `db.get_all` | `AUTO_TECHSUPPORT_DUMP_INFO\|<dump_name>` | container 別の前回 dump 時刻一覧を再構成 | `auto_techsupport_helper.py:260-279` |
| `auto_techsupport_helper.verify_rate_limit_intervals` | (`get_ts_map` の戻りを使用) | 同上 | per-feature cool-off の経過判定 | `auto_techsupport_helper.py:292-298` |
| `auto_techsupport_helper.write_to_state_db` | `db.set(STATE_DB, key, ...)` | 同上 | techsupport 完了時に timestamp / event_type / container を書き込み | `auto_techsupport_helper.py:302-310` |
| `techsupport_cleanup.clean_state_db_entries` | `db.delete(STATE_DB, TS_MAP + "\|" + name)` | 同上 | tarball cleanup と同期して entry を削除 | `techsupport_cleanup.py:13-18` |

定数: `TS_MAP = "AUTO_TECHSUPPORT_DUMP_INFO"` (`auto_techsupport_helper.py:60`)。

### 4. 範囲外 (誤解されやすい隣接)

- **`hostcfgd` / `featured` daemon**: 本ページの `<!-- pubsub -->` セクション (`auto-techsupport-feature-pubsub.md` 解析) で確認済みの通り、`AUTO_TECHSUPPORT_FEATURE` を `subscribe()` する常駐プロセスは存在しない。`hostcfgd:2468-2528` の register_callbacks に AUTO_TECHSUPPORT 系の購読呼び出しはなく、`featured` は `FEATURE` テーブルのみ購読し AUTO_TECHSUPPORT_FEATURE には触らない。よって Phase C 暗黙参照には含めない。
- **`DEVICE_METADATA`**: `coredump_gen_handler` / `techsupport_cleanup` / `memory_threshold_check` / `auto_techsupport_helper` の 4 ファイルを `DEVICE_METADATA` で grep して 0 ヒット。multi-asic 判定は `SonicV2Connector(use_unix_socket_path=True)` のローカル接続で完結し、`localhost.hostname` 等も参照しない。
- **`CORE_DUMP_NAME_TO_CONTAINER_MAP`**: 上述の通り現行 master コード上に該当 CONFIG_DB / STATE_DB テーブルは存在しない (`grep -rn "CORE_DUMP_NAME_TO_CONTAINER" .cache/sonic-sources/` で 0 ヒット)。本ページ Phase C 範囲外。

## まとめ — `auto-techsupport-feature.md` Phase C 記載対象

| カテゴリ | テーブル | DB |
|---|---|---|
| グローバル共依存 (必ず先に評価) | `AUTO_TECHSUPPORT` (key `GLOBAL`) | CONFIG_DB |
| 暗黙 leafref (key 空間共有) | `FEATURE` | CONFIG_DB |
| ランタイム連動 (rate-limit 判定) | `AUTO_TECHSUPPORT_DUMP_INFO` | STATE_DB |

## 検証コマンド

```bash
grep -nE 'db\.(get|keys|get_all|set|delete)\(|format\(' \
    .cache/sonic-sources/sonic-utilities/scripts/coredump_gen_handler.py \
    .cache/sonic-sources/sonic-utilities/scripts/techsupport_cleanup.py \
    .cache/sonic-sources/sonic-utilities/utilities_common/auto_techsupport_helper.py

grep -rn "CORE_DUMP_NAME_TO_CONTAINER" .cache/sonic-sources/  # 0 hit
grep -n "DEVICE_METADATA" \
    .cache/sonic-sources/sonic-utilities/scripts/coredump_gen_handler.py \
    .cache/sonic-sources/sonic-utilities/scripts/techsupport_cleanup.py \
    .cache/sonic-sources/sonic-utilities/scripts/memory_threshold_check.py \
    .cache/sonic-sources/sonic-utilities/utilities_common/auto_techsupport_helper.py  # 0 hit
```

このスキャン結果から派生して `docs/reference/config-db/auto-techsupport-feature.md` の `<!-- cross-refs -->` ブロックを生成する。
