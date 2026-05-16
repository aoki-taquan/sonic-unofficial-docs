# FABRIC_MONITOR — Phase A: field defaults

## 調査対象

`FABRIC_MONITOR|FABRIC_MONITOR_DATA` の全フィールドについて、コード由来デフォルトを特定する。

## ソースと Evidence

### YANG モデル (primary source)

`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-fabric-monitor.yang`

YANG `default` ステートメントが CONFIG_DB の規範的デフォルト値を定義する。

| フィールド | YANG default | 型/range |
|---|---|---|
| `monErrThreshCrcCells` | `1` | uint32 |
| `monErrThreshRxCells` | `61035156` | uint32 |
| `monPollThreshIsolation` | `1` | uint8, 1..10 |
| `monPollThreshRecovery` | `8` | uint8, 1..10 |
| `monCapacityThreshWarn` | `10` | uint8, 5..100 |
| `monState` | `disable` | mode-status (enable/disable) |

### orchagent ハードコード定数 (fallback)

`sonic-swss/orchagent/fabricportsorch.cpp:46-47` および `fabricportsorch.h:42-45`

APPL_DB にエントリが存在しない場合のフォールバック定数:

```cpp
#define ERROR_RATE_CRC_CELLS_CFG 1      // monErrThreshCrcCells
#define ERROR_RATE_RX_CELLS_CFG  61035156 // monErrThreshRxCells
#define ISOLATION_POLLS_CFG      1      // monPollThreshIsolation
#define RECOVERY_POLLS_CFG       8      // monPollThreshRecovery
// FEC 系 (fabric link FEC, 別経路)
#define FEC_ISOLATE_POLLS        2
#define FEC_UNISOLATE_POLLS      8
```

`monCapacityThreshWarn` のフォールバック: `updateFabricCapacity()` 内 `int threshold = 100` (fabricportsorch.cpp:1052)

> **注意**: YANG default=10 に対し orchagent フォールバックは 100。APPL_DB 経由で受け取った場合は 10 が使われるが、APPL_DB が未設定の場合は 100 が使われる (fabricportsorch.cpp:1057 コメント参照)。これは discrepancy。

### fabricmgrd (CONFIG_DB → APPL_DB ブリッジ)

`sonic-swss/cfgmgr/fabricmgr.cpp:70-74`

`monState` フィールドのみ CONFIG_DB から APPL_DB へ転記。他フィールドはすべて `fabricmgr.cpp` を経由して APPL_DB に書き込まれる。

## デフォルト由来まとめ

| フィールド | デフォルト値 | 由来 |
|---|---|---|
| `monErrThreshCrcCells` | `1` | YANG default; orchagent `ERROR_RATE_CRC_CELLS_CFG=1` (一致) |
| `monErrThreshRxCells` | `61035156` | YANG default; orchagent `ERROR_RATE_RX_CELLS_CFG=61035156` (一致) |
| `monPollThreshIsolation` | `1` | YANG default; orchagent `ISOLATION_POLLS_CFG=1` (一致) |
| `monPollThreshRecovery` | `8` | YANG default; orchagent `RECOVERY_POLLS_CFG=8` (一致) |
| `monCapacityThreshWarn` | `10` (YANG) / `100` (orchagent fallback) | YANG=10; orchagent フォールバック=100 → discrepancy |
| `monState` | `disable` | YANG default |

## discrepancy メモ

`monCapacityThreshWarn` について:
- YANG: `default 10` (%)
- orchagent フォールバック (`updateFabricCapacity()` 内): `int threshold = 100`
- APPL_DB が設定されている場合は YANG 由来の値 (10) が使われる
- APPL_DB 未設定時 (fabric monitor 無効構成) は orchagent が 100 を使う

既存ドキュメントのデフォルト記載 (10) は YANG 準拠で正しい。orchagent フォールバック差異は `cdb-exceptions` ブロックに追記する価値あり。
