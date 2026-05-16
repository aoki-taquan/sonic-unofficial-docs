# Phase A: STATE_DB MUX_CABLE_TABLE / HW_MUX_CABLE_TABLE コード由来デフォルト調査

## 調査対象ファイル

- `sonic-swss/orchagent/muxorch.cpp` (MuxStateOrch::updateMuxState, MuxOrch::handleMuxCfg)
- `sonic-linkmgrd/src/DbInterface.cpp` (handleGetMuxState, handleSwssNotification)
- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py`
  (put_init_values_for_grpc_states, update_table_mux_status_for_statedb_port_tbl)
- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_table_helper.py`

## STATE_DB MUX_CABLE_TABLE — フィールド解析

### state フィールド

**書き込み元**: `MuxStateOrch::updateMuxState()` (muxorch.cpp:2640)

```cpp
mux_state_table_.hset(portName, "state", muxState);
```

`mux_state_table_` は `STATE_MUX_CABLE_TABLE_NAME` を指す。書き込まれる値は:

| 値 | 書き込みタイミング | コード証跡 |
|----|------------------|-----------|
| `"active"` | MuxCable 状態機械が ACTIVE に遷移したとき | `muxorch.cpp:70`, `updateMuxState` 呼出し `muxorch.cpp:527,562,612` |
| `"standby"` | MuxCable が STANDBY に遷移したとき | `muxorch.cpp:71` |
| `"init"` | warm restart 時の初期値 | `muxorch.cpp:72,441` |
| `"failed"` | `isStateChangeFailed()` が true のとき | `muxorch.cpp:2680` — `MUX_HW_STATE_ERROR` = `"error"` ではなく `"failed"` 扱い |
| `"pending"` | 状態変更待ち | `muxorch.cpp:73` |
| `"unknown"` | hw_state と mux_state が不一致かつ failed でないとき | `muxorch.cpp:2684` (`MUX_HW_STATE_UNKNOWN = "unknown"`) |
| `"error"` | `isStateChangeFailed()` + hw_state/mux_state 不一致のとき | `muxorch.cpp:2680` (`MUX_HW_STATE_ERROR = "error"`) |

**初期化**: 非 warm restart 時 → `stateStandby()` → `state_ = MUX_STATE_STANDBY`
            warm restart 時 → `state_ = MUX_STATE_INIT`

**コード由来デフォルト**:
- cold boot: `"standby"` (muxorch.cpp:445-447)
- warm restart: `"init"` (muxorch.cpp:441)
- hw_state と mux_state が一致: そのまま `hw_state` を STATE_DB に反映
- 不一致 + 非 failed: `"unknown"`
- 不一致 + failed: `"error"`

### neighbor_mode フィールド

**書き込み元**: `MuxOrch::handleMuxCfg()` (muxorch.cpp:2283-2285)

```cpp
std::string neighbor_mode_str = (nbr_handler_type == MuxNbrHandlerType::NBR_HANDLER_PREFIX_BASED)
    ? "prefix-route" : "host-route";
state_mux_cable_table_->hset(port_name, "neighbor_mode", neighbor_mode_str);
```

**値**: `"host-route"` または `"prefix-route"`
**乖離**: YANG default は `host-route`。コードは CONFIG_DB の `neighbor_mode` フィールドに基づき
  `NBR_HANDLER_PREFIX_BASED` か否かを判断して STATE_DB に書き戻す。
  SAI が `SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE` 非対応の場合、CONFIG_DB に `prefix-route` を設定しても
  STATE_DB には `prefix-route` が書かれるが実動作は `host-route` になる。
  初回 MuxPort 設定時のみ書き込まれ、動的変更は拒否される。

## STATE_DB HW_MUX_CABLE_TABLE — フィールド解析

**書き込み元**: ycabled `put_init_values_for_grpc_states()` (y_cable_helper.py:597-631)
              ycabled `update_table_mux_status_for_statedb_port_tbl()` (y_cable_helper.py:839-843)

### state フィールド (HW_MUX_CABLE_TABLE)

```python
fvs_updated = swsscommon.FieldValuePairs([('state', self_state),
                                          ('read_side', str(read_side)),
                                          ('active_side', self_state)])
hw_mux_cable_tbl[asic_index].set(port, fvs_updated)
```

**値**: `"active"`, `"standby"`, `"unknown"`
- gRPC stub が None → `"unknown"` (y_cable_helper.py:604)
- gRPC 応答あり → `parse_grpc_response_forwarding_state()` が返す値 (active/standby/unknown)

**コード由来デフォルト**:
- gRPC stub 未セットアップ（`soc_ipv4` 欠落など） → `"unknown"` が書き込まれる

### read_side フィールド (HW_MUX_CABLE_TABLE)

**値**: `"0"` または `"1"` (整数文字列)
- Loopback3 の IPアドレスから判定 (`process_loopback_interface_and_get_read_side()`)
- LOOPBACK_INTERFACE_LT0 → `0`、LOOPBACK_INTERFACE_T0 → `1`
- 判定不能時 → `-1` (エラー扱い、書き込みスキップ)

**コード由来デフォルト**: なし。Loopback3 インターフェースが設定されていることが前提。

### active_side フィールド (HW_MUX_CABLE_TABLE)

**値**: `state` と同じ値 (`"active"`, `"standby"`, `"unknown"`)
- `put_init_values_for_grpc_states()` では `active_side = self_state` として state と同値で書き込まれる
- `update_table_mux_status_for_statedb_port_tbl()` では `active_side` を引数で受け取る

**コード由来デフォルト**: `state` と同値（初期化時）。gRPC stub None → `"unknown"`

## HW_MUX_CABLE_TABLE_PEER (STATE_DB)

**書き込み元**: ycabled `put_init_values_for_grpc_states()` (y_cable_helper.py:628-631)

ピア側 ToR の forwarding state を保存。フィールドは `HW_MUX_CABLE_TABLE` と同じ構造:
`state`, `read_side`, `active_side`。値は `peer_state` (peer ToR の gRPC 応答から取得)。

## linkmgrd の STATE_MUX_CABLE_TABLE 読み取り

linkmgrd は STATE_DB `MUX_CABLE_TABLE` を書き込まない（orchagent が書き込む）が、
`handleGetMuxState()` (DbInterface.cpp:393-401) で `state` フィールドを読み取り、
`processGetMuxState()` を通じて内部ステートマシンを更新する。

## 乖離サマリ

| テーブル | フィールド | YANG定義 | コード由来デフォルト | 乖離種別 |
|---------|-----------|---------|------------------|---------|
| MUX_CABLE_TABLE (STATE_DB) | `state` | — (state-db) | cold boot: `"standby"` (muxorch.cpp:445-447) | cold boot 初期値 hardcode |
| MUX_CABLE_TABLE (STATE_DB) | `state` | — | warm restart: `"init"` (muxorch.cpp:441) | warm restart 時 `"init"` を経由 |
| MUX_CABLE_TABLE (STATE_DB) | `state` | — | hw/mux 不一致 → `"unknown"`/`"error"` (muxorch.cpp:2680-2684) | mismatch 検出値 |
| MUX_CABLE_TABLE (STATE_DB) | `neighbor_mode` | — | `"host-route"` (CONFIG_DB由来、動的変更不可) | 初回設定時のみ書き込み |
| HW_MUX_CABLE_TABLE (STATE_DB) | `state` | — | gRPC stub None → `"unknown"` (y_cable_helper.py:604) | gRPC 未確立時 fallback |
| HW_MUX_CABLE_TABLE (STATE_DB) | `read_side` | — | Loopback3 未設定 → 書き込みスキップ | 設定必須 |
| HW_MUX_CABLE_TABLE (STATE_DB) | `active_side` | — | state と同値で初期化 | 乖離なし |

## Evidence コード行

- `muxorch.cpp:50-51`: `MUX_HW_STATE_UNKNOWN = "unknown"`, `MUX_HW_STATE_ERROR = "error"`
- `muxorch.cpp:68-74`: `muxStateValToString` マップ — state string 一覧
- `muxorch.cpp:441,447`: warm/cold boot 時の初期 state_ 設定
- `muxorch.cpp:2283-2285`: `neighbor_mode` を STATE_DB MUX_CABLE_TABLE に書き込み
- `muxorch.cpp:2640`: `MuxStateOrch::updateMuxState` — `state` hset
- `muxorch.cpp:2676-2691`: hw_state vs mux_state 比較 → unknown/error 書き込み
- `y_cable_helper.py:597-631`: `put_init_values_for_grpc_states` — HW_MUX_CABLE_TABLE 初期化
- `y_cable_helper.py:839-843`: `update_table_mux_status_for_statedb_port_tbl` — HW_MUX_CABLE_TABLE 更新
- `DbInterface.cpp:393-401`: `handleGetMuxState` — STATE_DB `state` 読み取り
