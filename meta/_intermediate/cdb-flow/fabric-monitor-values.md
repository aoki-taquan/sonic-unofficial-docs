# FABRIC_MONITOR フィールド値分析

## mode-status フィールド

### `monState` (mode-status: enable/disable)
- `enable` → fabricmgr が APPL_DB の APP_FABRIC_MONITOR_DATA_TABLE に monState を書き込み、fabric 監視が開始（fabricmgr.cpp:70-74）
- `disable` (デフォルト) → 監視停止。不良ファブリックリンクが自動 isolate されない

## uint フィールド

### `monErrThreshCrcCells` (uint32, デフォルト 1)
- fabricmgr.cpp:50-53 で APPL_DB に転写し、syncd 経由で SAI へ
- 値が小さいほど敏感: 1 CRC エラーセルで isolate 判定を開始

### `monErrThreshRxCells` (uint32, デフォルト 61035156)
- 受信総セル数の窓サイズ。この窓内で `monErrThreshCrcCells` を超えると隔離判定

### `monPollThreshIsolation` (uint8, 1..10, デフォルト 1)
- 閾値超過が N 回連続したとき FABRIC_PORT を isolate
- 1 → 即時 isolate（CRC スパイクで誤 isolate のリスク）
- 10 → 安定性重視

### `monPollThreshRecovery` (uint8, 1..10, デフォルト 8)
- 閾値以下が N 回連続したとき FABRIC_PORT を include（unisolate）
- 値が大きいほど復帰が遅く、安定性が高い

### `monCapacityThreshWarn` (uint8, 5..100, デフォルト 10)
- up 状態のファブリックリンクが全体の N% を下回ったとき警告ログ

## cross-cutting
- monState 変更はホットに反映（fabricmgr が subscribe）。再起動不要
- monPollThresh* はポーリング周期依存。プラットフォーム実装がポーリング周期を決定する
