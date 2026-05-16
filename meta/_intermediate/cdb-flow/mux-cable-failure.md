# mux-cable — Phase D 失敗挙動メモ

ソース: `sonic-swss/orchagent/muxorch.cpp`

## 1. state 遷移失敗 (MuxCable::setState / stateActive / stateStandby)

### 遷移テーブルに存在しない遷移
- `muxStateTransition` マップに `(prev_state, new_state)` ペアが存在しない場合、
  HW mux state は更新するが SAI プログラミングはスキップ。
- 同一 state への遷移 (no-op) は `SWSS_LOG_NOTICE` のみ。
- 異なる state への未定義遷移は `SWSS_LOG_ERROR("State transition from %s to %s is not-handled")` を出力して処理を中断。
- ソース: `muxorch.cpp:523-538`

### ハンドラ関数失敗 → rollback
- `state_machine_handlers_` のハンドラ関数が false を返すと:
  - `state_` を `prev_state_` に戻す
  - `st_chg_failed_ = true` をセット
  - `std::runtime_error("Failed to handle state transition")` をスロー
- ソース: `muxorch.cpp:547-553`

### stateActive 失敗
- `gPortsOrch->getPort()` がポートを見つけられない → `SWSS_LOG_NOTICE("Port %s not found")` → false 返却。
- ACL drop rule 削除失敗 → `SWSS_LOG_INFO("Remove ACL drop rule failed")` → false 返却。
- `nbrHandler(true)` 失敗 → false 返却。
- ソース: `muxorch.cpp:463-486`

### stateStandby 失敗
- `gPortsOrch->getPort()` がポートを見つけられない → `SWSS_LOG_NOTICE("Port %s not found")` → false 返却。
- `nbrHandler(false)` 失敗 → false 返却 (Tunnel NH が未解決の場合も含む)。
- ACL drop rule 追加失敗 → `SWSS_LOG_INFO("Add ACL drop rule failed")` → false 返却。
- ソース: `muxorch.cpp:488-511`

### rollbackStateChange 失敗
- `prev_state_` が `FAILED` または `PENDING` の場合はロールバック不可 (`SWSS_LOG_ERROR`) → 処理中断。
- ロールバック自体が失敗した場合: `st_chg_failed_ = true`、`SWSS_LOG_ERROR("[%s] Rollback to %s failed")` を出力。
- ソース: `muxorch.cpp:566-613`

## 2. Tunnel NH 未解決 → retry

### nbrHandler(disable) での Tunnel NH 未解決
- standby 方向への切替時に `mux_orch_->createNextHopTunnel(MUX_TUNNEL, peer_ip4_)` が
  `SAI_NULL_OBJECT_ID` を返した場合:
  - `SWSS_LOG_INFO("Null NH object id, retry for %s", peer_ip4_)` を出力
  - `nbrHandler` が false を返す → 上位の state 遷移ハンドラが失敗扱いに
- 明示的な retry ループはコード上なし。orchagent の Consumer タスクキューが
  次の処理サイクルで再試行する仕組みに依存。
- ソース: `muxorch.cpp:667-671`

### Tunnel NH 作成失敗 (create_nh_tunnel)
- `sai_next_hop_api->create_next_hop()` 失敗時: `SWSS_LOG_ERROR("Tunnel NH create failed for ip %s")`
  を出力し `SAI_NULL_OBJECT_ID` を返す。
- ソース: `muxorch.cpp:358-361`

### Tunnel route 作成失敗 (create_route)
- `sai_route_api->create_route_entry()` 失敗かつ `SAI_STATUS_ITEM_ALREADY_EXISTS` でもない場合:
  `SWSS_LOG_ERROR("Failed to create tunnel route %s")` → エラー status 返却。
- ソース: `muxorch.cpp:118-127`

## 3. NEIGHBOR 未解決時の挙動

### enable (active 方向) での NEIGHBOR 失敗
- `gNeighOrch->enableNeighbors()` 失敗 → false 返却、状態遷移中断。
- `gRouteOrch->updateNextHopRoutes()` 失敗 → `SWSS_LOG_INFO("Update route failed for NH %s")` → false 返却。
- `gRouteOrch->invalidnexthopinNextHopGroup()` 失敗 → `SWSS_LOG_ERROR("Removing existing NH failed for %s")` → false 返却。
- `gRouteOrch->validnexthopinNextHopGroup()` 失敗 → `SWSS_LOG_ERROR("Adding NH failed for %s")` → false 返却。
- ソース: `muxorch.cpp:813-869`

### disable (standby 方向) での NEIGHBOR 失敗
- `gRouteOrch->updateNextHopRoutes()` 失敗 → `SWSS_LOG_INFO("Update route failed for NH %s")` → false 返却。
- `gRouteOrch->invalidnexthopinNextHopGroup()` 失敗 → `SWSS_LOG_ERROR("Removing existing NH failed for %s")` → false 返却。
- `gRouteOrch->validnexthopinNextHopGroup()` 失敗 → `SWSS_LOG_ERROR("Adding NH failed for %s")` → false 返却。
- `addRoutes()` 失敗 → false 返却。
- `gNeighOrch->disableNeighbors()` 失敗 → false 返却。
- ソース: `muxorch.cpp:875-940`

### 未知 state での neighbor update
- `MuxNbrHandler::update()` で `state` が `INIT`/`ACTIVE`/`STANDBY` 以外の場合:
  `SWSS_LOG_NOTICE("State '%s' not handled for nbr %s update")` を出力してスキップ (no-op)。
- ソース: `muxorch.cpp:778-782`
