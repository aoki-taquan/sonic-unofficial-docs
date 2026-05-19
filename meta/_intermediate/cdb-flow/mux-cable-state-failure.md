# mux-cable-state — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-19 (chore/q67-f-batch1071)

ソース:
- `sonic-net/sonic-swss/orchagent/muxorch.cpp` (ref: master)
- `sonic-net/sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py` (ref: master)

対象ページ: `docs/reference/config-db/mux-cable-state.md`
対象 STATE_DB テーブル: `MUX_CABLE_TABLE` / `HW_MUX_CABLE_TABLE`

<!-- failure -->
## Phase D: 失敗挙動マトリクス

`MUX_CABLE_TABLE` (STATE_DB) への書き込みは `MuxStateOrch::updateMuxState()` → `mux_state_table_.hset()` を
経由する。`HW_MUX_CABLE_TABLE` は ycabled が直接 `swsscommon` Table API で書き込む。いずれも
`swss::Table::hset/set` は戻り値なし (void) で Redis 側の I/O エラーは例外で伝播する。

### A. 状態遷移失敗 → rollback → STATE_DB 反映

| 失敗条件 | 検出箇所 | 結果 | STATE_DB 反映 | evidence |
|---|---|---|---|---|
| `state_machine_handlers_` のハンドラ (stateActive / stateStandby) が false を返す | `MuxCable::setState()` L547-553 | `state_` を `prev_state_` に戻し、`st_chg_failed_ = true` セット、`std::runtime_error` スロー | STATE_DB 更新前に中断 → STATE_DB は前値のまま。catch 後に `rollbackStateChange()` が呼ばれて `updateMuxState(prev_state)` を実行 | `muxorch.cpp:547-553, 2597` |
| `stateActive()` 失敗 (`getPort()` 不明 / ACL drop rule 削除失敗 / `nbrHandler` 失敗) | `muxorch.cpp:463-486` | false 返却 → 上記の rollback フロー | STATE_DB は rollback 先 state に書き換え (prev_state が `FAILED`/`PENDING` でない場合) | `muxorch.cpp:463-486, 566-611` |
| `stateStandby()` 失敗 (`getPort()` 不明 / nbrHandler 失敗 / ACL drop rule 追加失敗) | `muxorch.cpp:488-511` | false 返却 → rollback フロー | 同上 | `muxorch.cpp:488-511, 566-611` |
| rollback 先が `MUX_STATE_FAILED` または `MUX_STATE_PENDING` | `rollbackStateChange()` L568-572 | `SWSS_LOG_ERROR` → rollback スキップ (return のみ) | STATE_DB 更新なし、`st_chg_failed_` は true のまま | `muxorch.cpp:568-572` |
| rollback 自体も失敗 (`stateActive()`/`stateStandby()` が false を返す) | `rollbackStateChange()` L607-608 | `st_chg_failed_ = true`、`SWSS_LOG_ERROR("[%s] Rollback to %s failed")` | `updateMuxState()` が呼ばれ、rollback 試行後の state を STATE_DB に書込 (rollback 先への書き込みだが SAI は失敗) | `muxorch.cpp:603-611` |

### B. MuxCableOrch::addOperation 例外キャッチ後の STATE_DB 挙動

| 失敗条件 | 検出箇所 | 結果 | STATE_DB 反映 | evidence |
|---|---|---|---|---|
| `mux_obj->setState()` が `std::runtime_error` をスロー (ハンドラ失敗) | `MuxCableOrch::addOperation()` L2593-2598 | `SWSS_LOG_ERROR` → `rollbackStateChange()` → `return true` (消費完了扱い) | rollback 結果の state が STATE_DB に書込まれる。retry なし | `muxorch.cpp:2593-2598` |
| `std::logic_error` がスロー | L2599-2604 | 同上 | 同上 | `muxorch.cpp:2599-2604` |
| その他 `std::exception` がスロー | L2605-2611 | 同上 | 同上 | `muxorch.cpp:2605-2611` |

!!! note "retry なし・消費完了扱い"
    `MuxCableOrch::addOperation()` の catch ブロックはすべて `return true` を返す。
    SONiC の `Orch2` フレームワークでは `true` は「消費完了」を意味するため、
    状態遷移の失敗があっても当該エントリを再キューしない。
    orchagent が再起動するか、次に別の HW 状態更新が来るまで STATE_DB は rollback 値のまま固定される。

### C. MuxStateOrch::addOperation の失敗経路 (HW → SW 状態同期)

| 失敗条件 | 検出箇所 | 結果 | STATE_DB 反映 | evidence |
|---|---|---|---|---|
| `isMuxExists(port_name)` false (MuxCable 未生成) | `MuxStateOrch::addOperation()` L2651-2653 | `SWSS_LOG_WARN` → `return false` (再キュー) | STATE_DB 更新なし。`MuxCable` 生成まで再試行 | `muxorch.cpp:2651-2653` |
| `mux_obj->getState()` が `std::runtime_error` をスロー | L2664-2667 | `SWSS_LOG_ERROR` → `return false` (再キュー) | STATE_DB 更新なし | `muxorch.cpp:2664-2667` |
| `isStateChangeInProgress()` true (遷移中) | L2671-2673 | `SWSS_LOG_INFO` → `return false` (再キュー、次サイクルで再試行) | STATE_DB 更新なし。遷移完了後に再処理 | `muxorch.cpp:2671-2673` |
| HW state と mux state が不一致 かつ `isStateChangeFailed()` true | L2678-2680 | `mux_state = MUX_HW_STATE_ERROR = "error"` を書込 | `MUX_CABLE_TABLE.state = "error"` | `muxorch.cpp:2678-2680` |
| HW state と mux state が不一致 かつ `isStateChangeFailed()` false | L2681-2683 | `mux_state = MUX_HW_STATE_UNKNOWN = "unknown"` を書込 | `MUX_CABLE_TABLE.state = "unknown"` | `muxorch.cpp:2681-2683` |

### D. ycabled / HW_MUX_CABLE_TABLE 書き込み失敗

| 失敗条件 | 検出箇所 | 結果 | STATE_DB 反映 | evidence |
|---|---|---|---|---|
| gRPC stub が None (gRPC チャネル未確立) | `put_init_values_for_grpc_states()` L603 | `log_notice` → `state='unknown'`, `active_side='unknown'` を書込んで return | `HW_MUX_CABLE_TABLE.state = "unknown"` | `y_cable_helper.py:603-612` |
| gRPC `QueryAdminForwardingPortState` response が None | L621 | `log_warning` → `parse_grpc_response_forwarding_state()` で `"unknown"` が返される | `HW_MUX_CABLE_TABLE.state = "unknown"` | `y_cable_helper.py:621-622` |
| gRPC `RpcError` | `try_grpc()` L799 | gRPC エラーコードをログ出力 → `ret=False` → `parse_grpc_response_forwarding_state(False, ...)` → `"unknown"` | `HW_MUX_CABLE_TABLE.state = "unknown"` | `y_cable_helper.py:799-810` |
| Loopback3 IPv4 未設定 → `read_side` が確定できない | `process_loopback_interface_and_get_read_side()` | `None` を返す → 呼び出し元が書き込みスキップ | `HW_MUX_CABLE_TABLE` に `read_side` が書き込まれない | `y_cable_helper.py:633-651` |

### E. STATE_DB 書き込み API 自体の失敗

`MuxStateOrch::updateMuxState()` は `mux_state_table_.hset()` を呼ぶ。`swss::Table::hset()` は
Redis 接続断や AUTH エラーを `swss::RedisCommandException` または `system_error` として送出するが、
`MuxStateOrch` 内に catch ブロックはない。例外はスタックを伝播して orchagent プロセスを abort させ、
systemd により再起動される。再起動後に `orchagent` は CONFIG_DB を再読み込みし STATE_DB を再構築するため、
書き込み失敗が永続的な不整合を残すことはない（自己回復系）。

### グレップカバレッジ

| 項目 | 証跡箇所 |
|---|---|
| `rollbackStateChange()` 呼び出し | `muxorch.cpp:2597, 2604, 2611` |
| `st_chg_failed_ = true` セット | `muxorch.cpp:552, 607` |
| `MUX_HW_STATE_ERROR` 書込み | `muxorch.cpp:2680` |
| `MUX_HW_STATE_UNKNOWN` 書込み | `muxorch.cpp:2683` |
| `return false` (再キュー) in MuxStateOrch | `muxorch.cpp:2653, 2667, 2673` |
| gRPC stub None → `"unknown"` 書込み | `y_cable_helper.py:603-612` |
| gRPC response None → `"unknown"` | `y_cable_helper.py:621-622` |

<!-- /failure -->
