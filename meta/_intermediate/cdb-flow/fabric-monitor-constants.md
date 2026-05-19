# FABRIC_MONITOR — ハードコード定数調査 (Phase E)

Task F Phase E: `fabricportsorch.cpp` / `fabricmgr.cpp` に存在する、CONFIG_DB / YANG で管理されないハードコード定数を精読した結果。

## 調査ファイル

- `sonic-swss/orchagent/fabricportsorch.cpp` L21-48 (`#define` 群)
- `sonic-swss/orchagent/fabricportsorch.cpp` L80-133 (コンストラクタ)
- `sonic-swss/orchagent/fabricportsorch.cpp` L434-483 (updateFabricDebugCounters — フォールバック値として参照)
- `sonic-swss/orchagent/fabricportsorch.cpp` L766-820 (MAX_SKIP 参照)
- `sonic-swss/orchagent/fabricportsorch.cpp` L1133,1137 (FABRIC_LINK_RATE 参照)
- `sonic-swss/orchagent/fabricportsorch.cpp` L1350 (FABRIC_DEBUG_POLLING_INTERVAL_DEFAULT 参照)
- `sonic-swss/orchagent/fabricportsorch.cpp` L1647,1697 (CHECK_TIME 参照)
- `sonic-swss/cfgmgr/fabricmgr.cpp` — 定数定義なし (CONFIG_DB フィールド値をそのまま APPL_DB へ転送するのみ)

## 定数一覧

### ポーリングタイマー

| 定数名 | 値 | 用途 |
|--------|----|------|
| `FABRIC_POLLING_INTERVAL_DEFAULT` | `30` 秒 | `m_timer` (FABRIC_POLL) タイマー周期。ポート状態・統計の定期ポーリング間隔 |
| `FABRIC_DEBUG_POLLING_INTERVAL_DEFAULT` | `12` 秒 | `m_debugTimer` (FABRIC_DEBUG_POLL) タイマー周期。監視有効時の CRC/FEC エラー集計間隔 |
| `FABRIC_PORT_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` ms (10 秒) | COUNTERS_DB ファブリックポート統計収集の FlexCounter 周期 |
| `FABRIC_QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `100000` ms (100 秒) | COUNTERS_DB ファブリックキュー統計収集の FlexCounter 周期 |
| `SWITCH_DEBUG_COUNTER_POLLING_INTERVAL_MS` | `500` ms | VOQ switch 用 switch drop counter FlexCounter 周期 |
| `FABRIC_SWITCH_DEBUG_COUNTER_POLLING_INTERVAL_MS` | `60000` ms (60 秒) | fabric switch 用 switch drop counter FlexCounter 周期 |

### CRC/FEC エラー閾値フォールバック (APPL_DB 未設定時)

| 定数名 | 値 | 対応 CONFIG_DB フィールド | 用途 |
|--------|----|--------------------------|------|
| `ISOLATION_POLLS_CFG` | `1` | `monPollThreshIsolation` | isolate 判定に必要な連続超過ポーリング数 (CRC) |
| `RECOVERY_POLLS_CFG` | `8` | `monPollThreshRecovery` | unisolate 判定に必要な連続回復ポーリング数 (CRC) |
| `ERROR_RATE_CRC_CELLS_CFG` | `1` | `monErrThreshCrcCells` | CRC エラーセル閾値 |
| `ERROR_RATE_RX_CELLS_CFG` | `61035156` | `monErrThreshRxCells` | 受信セル総数閾値 |

### FEC エラー専用フォールバック (CONFIG_DB 非管理)

| 定数名 | 値 | 用途 |
|--------|----|------|
| `FEC_ISOLATE_POLLS` | `2` | FEC uncorrectable エラー連続超過でファブリックリンクを isolate するポーリング数 (CONFIG_DB フィールドなし) |
| `FEC_UNISOLATE_POLLS` | `8` | FEC 回復連続ポーリング数 (CONFIG_DB フィールドなし) |

### リンクアップ直後のスキップカウント

| 定数名 | 値 | 用途 |
|--------|----|------|
| `MAX_SKIP_CRCERR_ON_LNKUP_POLLS` | `20` | リンクアップ直後に CRC エラーカウントを無視するポーリング回数上限 (ブート時誤検知防止) |
| `MAX_SKIP_FECERR_ON_LNKUP_POLLS` | `20` | リンクアップ直後に FEC エラーカウントを無視するポーリング回数上限 |

### リンクフラッピング検知

| 定数名 | 値 | 用途 |
|--------|----|------|
| `CHECK_TIME` | `120` 分 | ファブリックリンクの permanent isolation 判定に使う時間窓。120 分以内に 3 回以上 auto-isolate が発生すると permanent isolation 対象 |

### キャパシティ計算

| 定数名 | 値 | 用途 |
|--------|----|------|
| `FABRIC_LINK_RATE` | `44316` (単位不明、Mbps 相当) | ファブリックリンク 1 本あたりの帯域レート。`updateFabricCapacity()` 内で総キャパシティおよびダウンキャパシティ計算に使用 |

## fabricmgr.cpp の定数状況

`fabricmgr.cpp` には `#define` / `const` による数値定数は存在しない。`doTask()` は CONFIG_DB から受け取ったフィールド値をそのまま `writeConfigToAppDb()` で APPL_DB に転送するパイプに徹しており、デフォルト値や閾値は一切コード上で管理しない。すべてのフォールバックは `fabricportsorch.cpp` 側の `updateFabricDebugCounters()` で吸収される。

## YANG デフォルトとの対応

YANG (`sonic-fabric-monitor.yang`) の `default` 値は `ISOLATION_POLLS_CFG`・`RECOVERY_POLLS_CFG`・`ERROR_RATE_CRC_CELLS_CFG`・`ERROR_RATE_RX_CELLS_CFG` と一致。`monCapacityThreshWarn` のみ YANG default=`10` に対して orchagent フォールバック=`100` という乖離がある（cdb-exceptions ブロック参照）。

ポーリングタイマー定数（`FABRIC_POLLING_INTERVAL_DEFAULT` 等）は YANG / CONFIG_DB での管理外であり、コードを変更するか orchagent 再コンパイルでのみ変更可能。
