# kubernetes-master failure analysis

## Source

- `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py`

## Failure paths

### kube_join_master 失敗

`do_join()` は `kube_commands.kube_join_master(ip, port, insecure)` を呼び戻り値 `ret` を検査する。
`ret != 0` の場合:
- `st_server[ST_SER_CONNECTED] = "false"` を設定
- `remote_connected = False` に設定
- `JOIN_RETRY`（デフォルト 10 秒）後に `handle_update()` を再スケジュール (`register_timer`)
- `pending = True` に設定
- 以後タイマー発火ごとに `do_join()` を繰り返す（無限リトライ）

**Evidence**: `ctrmgrd.py:442-455`

### kube_reset_master 失敗

`do_reset()` は `kube_commands.kube_reset_master(True)` を呼ぶが、戻り値は無視する。
失敗してもエラーログは出さず `st_server[ST_SER_CONNECTED] = "false"` を設定する。

**Evidence**: `ctrmgrd.py:418-426`

### set_node_labels 失敗

`set_node_labels()` は `device_info.get_sonic_version_info()` / `device_info.get_hwsku()` / `device_info.get_platform()` を呼び出す。これらが None を返しても処理は継続するが、`version_info['build_version']` への直接キーアクセスは KeyError を発生させる可能性がある（`ctrmgrd.py:301`）。`mod_db_entry()` は Redis 接続失敗時に例外を送出し ctrmgrd プロセスが異常終了する。

**Evidence**: `ctrmgrd.py:292-307`

### select() ERROR

メインループの `selector.select()` が `ERROR` を返した場合、`raise Exception("Received error from select")` を送出してプロセスが終了する（`ctrmgrd.py:272-275`）。UNIT_TESTING=True の場合のみ無視。

**Evidence**: `ctrmgrd.py:271-275`

### STATE_DB 書き込み失敗

`set_db_entry()` / `mod_db_entry()` は Redis 接続失敗時に `swss::DBConnector` 由来の例外を送出し、ctrmgrd プロセスが異常終了する。supervisord によるプロセス再起動後に再試行される。

**Evidence**: `ctrmgrd.py:231-232`
