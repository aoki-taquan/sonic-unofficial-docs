# pim-constants — Phase E スキャンノート

## 対象テーブル

- `PIM_GLOBALS` / `PIM_INTERFACE`
- ハンドラ: `frrcfgd.py` `pim_global_key_map` / `pim_interface_key_map`
- FRR 実装: `sonic-frr/pimd/pim_pim.h`, `pim_upstream.h`, `pim_cmd.c`

---

## FRR ハードコード定数 (pim_pim.h L27-36)

| 定数名 | 値 | RFC / 用途 |
|--------|----|----------|
| `PIM_PIM_BUFSIZE_READ` | `20000` (bytes) | PIM ソケット受信バッファサイズ |
| `PIM_PIM_BUFSIZE_WRITE` | `20000` (bytes) | PIM ソケット送信バッファサイズ |
| `PIM_DEFAULT_HELLO_PERIOD` | `30` (秒) | RFC 4601 §4.11 Hello Period |
| `PIM_DEFAULT_TRIGGERED_HELLO_DELAY` | `5` (秒) | RFC 4601 §4.11 Triggered_Hello_Delay |
| `PIM_DEFAULT_DR_PRIORITY` | `1` | RFC 4601 §4.3.1 DR Priority |
| `PIM_DEFAULT_PROPAGATION_DELAY_MSEC` | `500` (ms) | RFC 4601 §4.11 Propagation_Delay |
| `PIM_DEFAULT_OVERRIDE_INTERVAL_MSEC` | `2500` (ms) | RFC 4601 §4.11 Override_Interval |
| `PIM_DEFAULT_CAN_DISABLE_JOIN_SUPPRESSION` | `0` (false) | Join Suppression 無効化フラグ |
| `PIM_DEFAULT_T_PERIODIC` | `60` (秒) | RFC 4601 §4.11 t_periodic (Join/Prune 周期) |

## FRR ハードコード定数 (pim_upstream.h L206-221)

| 定数名 | 値 | 用途 |
|--------|----|------|
| `PIM_REGISTER_SUPPRESSION_PERIOD` | `60` (秒) | Register 抑制タイマー (RST) デフォルト。FRR `pim_cmd.c` L5443 コマンド `ip pim keep-alive-timer (31-60000)` とは別物 |
| `PIM_REGISTER_PROBE_PERIOD` | `5` (秒) | Register Probe タイマー (送信前試行期間) |
| `PIM_KEEPALIVE_PERIOD` | `210` (秒) | KAT(S,G) デフォルト。`keep-alive-timer` フィールドのデフォルト値 (CONFIG_DB 未設定時) |
| `PIM_RP_KEEPALIVE_PERIOD` | `3 * register_suppress_time + register_probe_time` | RP 側の KAT(S,G)。動的計算 (185 秒 = 3×60 + 5) |

## FRR CLI コマンドの値域制約 (pim_cmd.c)

CONFIG_DB フィールドに書ける値の範囲は FRR vtysh が受け付ける範囲に一致する。frrcfgd は値域チェックを行わずコマンドをそのまま発行するため、FRR 側のコマンドがエラーを返した場合は LOG_ERR が出力される。

| CONFIG_DB フィールド | vtysh コマンド | FRR 値域 | ソース |
|----------------------|---------------|---------|-------|
| `join-prune-interval` | `ip pim join-prune-interval <N>` | `60`〜`600` 秒 | `pim_cmd.c` L5360 |
| `keep-alive-timer` | `ip pim keep-alive-timer <N>` | `31`〜`60000` 秒 | `pim_cmd.c` L5443 |
| `hello-interval` (interval 部) | `ip pim hello <N> [<hold>]` | `1`〜`180` 秒 | `pim_cmd.c` L6997 |
| `hello-interval` (hold-time 部) | `ip pim hello <interval> <hold>` | `1`〜`180` 秒 | `pim_cmd.c` L6997 |
| `dr-priority` | `ip pim drpriority <N>` | `1`〜`4294967295` | `pim_cmd.c` L6458 |

## frrcfgd 側の追加制約

- `frrcfgd.py` L941-942: `hello-interval` の値が `"30,5"` 形式の場合、カンマをスペースに置換して `ip pim hello 30 5` として発行する。カンマ区切りの第 2 トークンが hold-time に相当する。
- frrcfgd は値の範囲チェックを **行わない**。FRR vtysh が `CMD_WARNING_CONFIG_FAILED` を返した場合、`syslog(LOG_ERR, 'failed running PIM config command')` を出力して継続する (`frrcfgd.py` L3817-3818)。

## CONFIG_DB で管理されない定数 (frrcfgd / FRR 内部固定値)

以下の定数は CONFIG_DB に対応するフィールドがなく、コードで直書きされている:

| 定数 | 値 | 説明 |
|------|----|------|
| `PIM_DEFAULT_TRIGGERED_HELLO_DELAY` | `5` 秒 | 隣接変化時のトリガ Hello 送出遅延。CONFIG_DB で変更不可 |
| `PIM_DEFAULT_PROPAGATION_DELAY_MSEC` | `500` ms | LAN prune delay の propagation_delay。CONFIG_DB で変更不可 |
| `PIM_DEFAULT_OVERRIDE_INTERVAL_MSEC` | `2500` ms | LAN prune delay の override_interval。CONFIG_DB で変更不可 |
| `PIM_PIM_BUFSIZE_READ` | `20000` bytes | PIM ソケット受信バッファ。CONFIG_DB で変更不可 |
| `PIM_PIM_BUFSIZE_WRITE` | `20000` bytes | PIM ソケット送信バッファ。CONFIG_DB で変更不可 |
| `PIM_REGISTER_SUPPRESSION_PERIOD` | `60` 秒 | Register 抑制タイマーデフォルト。CONFIG_DB で変更不可 |
| `PIM_REGISTER_PROBE_PERIOD` | `5` 秒 | Register Probe タイマーデフォルト。CONFIG_DB で変更不可 |

---

*スキャン日: 2026-05-17 / ソース: sonic-frr @ HEAD*
