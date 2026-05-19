# mux-cable-state — Phase D failure 調査ノート

## 調査対象

- `sonic-swss/orchagent/muxorch.cpp`
- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py`

## 主要な失敗パス

### MuxCable::setState() → SAI 操作失敗

`muxorch.cpp:549-561`: 状態遷移ハンドラが `false` を返すと:
1. `st_chg_failed_ = true`
2. `std::runtime_error` throw
3. 呼び出し元 `MuxCableOrch::addOperation()` が catch → `rollbackStateChange()` → `return true` (キューから除去、リトライなし)

`rollbackStateChange()` (`muxorch.cpp:566-614`): 前状態が `MUX_STATE_FAILED` または `MUX_STATE_PENDING` の場合は巻き戻し不可。

### MuxStateOrch::addOperation() — hw/mux 不一致

`muxorch.cpp:2678-2684`:
- `isStateChangeFailed() = true` → `MUX_HW_STATE_ERROR = "error"`
- `isStateChangeFailed() = false` → `MUX_HW_STATE_UNKNOWN = "unknown"`

### return false → キューイング vs return true → エントリ破棄

- `MuxCableOrch::addOperation()`: 例外補足後 `return true` → エントリ除去 (リトライなし)
- `MuxStateOrch::addOperation()`: `isMuxExists()` false → `return false` → キュー残存 (自動リトライ)
- `MuxStateOrch::addOperation()`: `isStateChangeInProgress()` true → `return false` → キュー残存

### ycabled gRPC 失敗

`y_cable_helper.py:600-608`:
- stub が None → `state = "unknown"` を STATE_DB に直接書き込み (例外なし、条件分岐)
- gRPC response が None → `parse_grpc_response_forwarding_state()` が `"unknown"` を返す

## 定数

```cpp
// muxorch.cpp:50-51
#define MUX_HW_STATE_UNKNOWN "unknown"
#define MUX_HW_STATE_ERROR "error"

// muxorch.cpp:73
{ MuxState::MUX_STATE_FAILED, "failed" },
```
