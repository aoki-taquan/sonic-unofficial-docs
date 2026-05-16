# BMP — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-bmp)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-buildimage/src/sonic-bmpcfgd/bmpcfgd/bmpcfgd.py`

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `supervisorctl stop openbmpd` が非ゼロ終了 / openbmpd が存在しない | `stop_bmp()` L56-58 | `subprocess.call()` は例外を raise しない（returncode は無視）。ただし openbmpd が実際に停止していない場合、後続の `reset_bmp_table()` と BMP_STATE_DB 削除が動作中プロセスと競合する | syslog LOG_NOTICE のみ (`bmpcfgd: stop bmp daemon`) | `bmpcfgd.py:56-58` |
| `BMP_STATE_DB` への接続失敗（Redis 未起動 / ポート閉塞） | `BMPCfgDaemon.__init__()` L75-76 (`SonicV2Connector` + `connect`) | `swsscommon` が例外を raise → デーモン起動失敗・supervisord がプロセス終了を検知して再起動を試みる | スタックトレースが syslog へ（未捕捉） | `bmpcfgd.py:75-76` |
| `reset_bmp_table()` の `delete_all_by_pattern()` 呼び出し失敗（Redis 接続断） | `reset_bmp_table()` L61-65 | 例外が `load()` → `cfg_handler()` まで伝播（catch なし）。bmpcfgd がクラッシュし supervisord が再起動する。BMP_STATE_DB の一部パターンだけ削除された中途状態が残る | スタックトレースが syslog へ（未捕捉） | `bmpcfgd.py:61-65` |
| `supervisorctl start openbmpd` が非ゼロ終了（openbmpd バイナリ欠如 / supervisord 未起動） | `start_bmp()` L68-70 | `subprocess.call()` は returncode を無視。openbmpd が起動しないまま処理続行。BMP_STATE_DB は空のまま・BMP データが collector に届かない | syslog LOG_NOTICE のみ (`bmpcfgd: start bmp daemon`) | `bmpcfgd.py:68-70` |
| `CONFIG_DB` 接続失敗（起動直後 Redis 未準備） | `BMPCfgDaemon.__init__()` L77-78 (`ConfigDBConnector.connect(retry_on=True)`) | `retry_on=True` により無限リトライ。Redis が起動するまでブロック。デーモンは起動完了しない（停止はしない） | swsscommon 内部ログ（接続試行ごと） | `bmpcfgd.py:77-78` |
| `"True"` / `"TRUE"` / `"1"` などの非小文字 `true` 値が CONFIG_DB に書き込まれた場合 | `is_true()` L27-28 | `str(val).lower() == 'true'` は `"true"` 小文字のみ受理。`"True"` 等はすべて `False` 扱い → フィールドが無効化されたように見える | なし（silent）。ログ出力なし | `bmpcfgd.py:27-28, 41-43` |
| `BMP|table` エントリが CONFIG_DB に存在しない状態で `load()` が呼ばれる | `load()` L39-43 | `data.get('table', {})` → 空 dict → 全フィールドが `'false'` fallback → openbmpd を stop → reset → start（全テーブルダンプ無効で再起動）。YANG default の `bgp_neighbor_table=true` は反映されない | syslog LOG_NOTICE（設定値 `False, False, False` で config update） | `bmpcfgd.py:39-44` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `BMP` テーブルの DEL イベント（`data == {}` で `bmp_handler` が呼ばれる） | `bmp_handler()` L81-83 | `config_db.get_table(BMP_TABLE)` を再取得するため、DEL 後は空 dict → `load({})` → 全フィールド `False` で openbmpd 再起動（テーブルダンプ全停止）。BMP_STATE_DB はクリアされる | syslog LOG_NOTICE | `bmpcfgd.py:81-83, 39-49` |

### retry / 復旧挙動補足

- **`CONFIG_DB` 無限リトライ**: `retry_on=True` により `ConfigDBConnector.connect()` は Redis が応答するまでブロックし続ける。デーモン停止のトリガーにはならない。
- **`BMP_STATE_DB` 接続は 1 回のみ**: `SonicV2Connector.connect(BMP_STATE_DB)` は `__init__` で 1 度だけ呼ばれ、失敗時は例外でデーモン終了。接続断後の自動復旧機構はない。
- **`supervisorctl` 呼び出しの failure-silencing**: `stop_bmp()` / `start_bmp()` は `subprocess.call()` で returncode を確認しない。openbmpd の起動失敗が bmpcfgd に伝わらず、BMP 機能が静かに停止したままになるリスクがある。
- **vtysh 非使用**: `bmpcfgd.py` は vtysh / FRR CLI を直接呼び出さない。BMP の FRR 側設定は `bgpd.main.conf.j2` によりコンテナ起動時に静的注入される。frrcfgd.py の vtysh 失敗経路（`g_run_command` / `run_vtysh_command`）は BMP テーブル処理に関与しない。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `subprocess.call` (returncode 無視) | 2 | `bmpcfgd.py:58, 70` |
| `delete_all_by_pattern` (例外 catch なし) | 3 | `bmpcfgd.py:63, 64, 65` |
| `retry_on=True` | 1 | `bmpcfgd.py:78` |
| `SonicV2Connector.connect` (単発) | 1 | `bmpcfgd.py:76` |
| `is_true()` (silent false fallback) | 3 | `bmpcfgd.py:41, 42, 43` |

<!-- /failure -->
