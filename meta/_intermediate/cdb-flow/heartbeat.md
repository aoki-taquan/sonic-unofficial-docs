# CONFIG_DB 例外条件分析: HEARTBEAT

## Consumer

- `eventd` (`sonic-buildimage/src/sonic-eventd/src/eventd.cpp`): 統計ハートビートを発行するデーモン。`HEARTBEAT_INTERVAL_SECS` のデフォルト値を定義し、`GLOBAL_OPTION_HEARTBEAT` (`events_wrap.h` L158) で上書き可能。CONFIG_DB `HEARTBEAT` テーブルとの直接マッピングは `events_wrap.h` の option API 経由。

## 例外条件

### 1. 負の値（-1 以外）は invalid
- ソース: `events_wrap.h` L136
- 「Any negative value other than -1 is treated as invalid.」
- interval に -1 を設定すると heartbeat が無効化される。-2 以下は無効値として拒否される。

### 2. 0 → システムデフォルト（2 秒）を使用
- ソース: `events_wrap.h` L141, `eventd.cpp` L43
- 「A value of 0 implies the system default.」デフォルトは `HEARTBEAT_INTERVAL_SECS = 2`（秒）。
- 0 を設定した場合は常に 2 秒として動作する。

### 3. STATS_HEARTBEAT_MIN (300ms) 単位に丸め
- ソース: `eventd.cpp` L145
- 内部カウンタは `((val * 1000) + STATS_HEARTBEAT_MIN - 1) / STATS_HEARTBEAT_MIN` で切り上げ丸め。300ms 単位に量子化されるため、指定値と実際の周期がずれる場合がある。

### 4. publish 失敗 → エラーログ（サービス継続）
- ソース: `eventd.cpp` L293
- `event_publish()` が失敗した場合 `SWSS_LOG_ERROR("Failed to publish heartbeat rc=%d", rc)` → ハートビート欠落が生じるが eventd は終了しない。
