# 値依存挙動分析: MUX_LINKMGR

## Phase 1: YANG フィールド全列挙

### LINK_PROBER
- `interval_v4` (uint32): default 100 [ms]
- `interval_v6` (uint32): default 1000 [ms]
- `positive_signal_count` (uint32): default 1
- `negative_signal_count` (uint32): default 3
- `suspend_timer` (uint32): 未使用 (YANG コメント)
- `use_well_known_mac` (enum): `enabled`/`disabled`
- `src_mac` (enum): `ToRMac`/`VlanMac`
- `interval_pck_loss_count_update` (uint32)

### TIMED_OSCILLATION
- `oscillation_enabled` (boolean): default `true`
- `interval_sec` (uint32): default 300 [秒]

### MUXLOGGER
- `log_verbosity` (enum): `trace`/`debug`/`info`/`error`/`fatal`

### SERVICE_MGMT
- `kill_radv` (enum): `True`/`False`, default `True`

## Phase 2: per-value explicit grep

- `sonic-linkmgrd/src/link_manager/LinkManagerStateMachineActiveStandby.h`: `when there is no icmp heartbeat, start a timer to oscillate between active and standby`
- `sonic-linkmgrd`: `interval_v4=100ms`, `negative_signal_count=3` がデフォルト

## Phase 5: 値依存挙動マトリクス

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `interval_v4` | 100 (default) ms | IPv4 ICMP heartbeat を 100ms 間隔で送信 |
| `interval_v4` | 0 | heartbeat 停止 (range 制約なし。実質 ICMP probe 無効化) |
| `negative_signal_count` | 3 (default) | 3回連続で heartbeat 喪失したら standby 判定 |
| `positive_signal_count` | 1 (default) | 1回受信で active 判定 |
| `oscillation_enabled` | `true` (default) | タイマー駆動で定期的に active/standby 切替を実施 |
| `oscillation_enabled` | `false` | タイマー切替を無効化。ICMP prober 結果のみで切替 |
| `interval_sec` | 300 (default) | 5分ごとにオシレーション実施 |
| `use_well_known_mac` | `enabled` | 既知 MAC を宛先 MAC として ICMP 送信 |
| `use_well_known_mac` | `disabled` (default的) | 動的 MAC を使用 |
| `src_mac` | `ToRMac` | ToR デバイス MAC を送信元 MAC に使用 |
| `src_mac` | `VlanMac` | VLAN インターフェース MAC を送信元 MAC に使用 |
| `log_verbosity` | `info` | 標準ログレベル |
| `log_verbosity` | `debug`/`trace` | 詳細デバッグログ出力 |
| `kill_radv` | `True` (default) | MUX 切替時に radv を graceful でなく kill |
| `kill_radv` | `False` | radv を graceful shutdown |

enum: `use_well_known_mac`=enabled/disabled、`src_mac`=ToRMac/VlanMac、`log_verbosity`=trace/debug/info/error/fatal、`kill_radv`=True/False。
