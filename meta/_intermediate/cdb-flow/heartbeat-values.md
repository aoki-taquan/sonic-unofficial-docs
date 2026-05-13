# HEARTBEAT 値依存挙動分析

## 数値フィールド

### interval (eventd.cpp L139-157, events_wrap.h L131-136)
- `-1`: heartbeat を無効化（"A value of -1 implies no heartbeat"）
- `< -1`（-2 以下）: invalid 扱い。syslog 記録後処理中断
- `0`: システムデフォルト 2 秒として動作（HEARTBEAT_INTERVAL_SECS = 2）
- 正値: 内部 300ms 単位（STATS_HEARTBEAT_MIN）に切り上げ量子化。指定値と実周期がずれる場合あり

## 結論
厳密な enum なし。interval の特殊値（-1, 0, 負値）で挙動が分岐する数値フィールド。
HEARTBEAT|config の heartbeat_interval / alert_interval は uint32 (ms 単位、eventd.cpp とは別スキーマに注意)。
