# pfc-wd 例外条件エビデンス

## 調査ソース

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-pfcwd.yang`
- `sonic-swss/orchagent/pfcwdorch.cpp`

## 例外条件まとめ

### スキーマ検証 (YANG)
- `ifname` = `GLOBAL` の場合: `action` / `detection_time` / `restoration_time` は禁止 (`must "../ifname != 'GLOBAL'"`)。違反は YANG validate で reject。
- `POLL_INTERVAL` はグローバルエントリ専用 (`must "../ifname = 'GLOBAL'"`)。
- `detection_time` および `restoration_time` は `POLL_INTERVAL` 以上必須: `error-message "detection_time must be greater than or equal to POLL_INTERVAL"`。
- `detection_time` range: 100..5000 ms。`restoration_time` range: 100..60000 ms。`POLL_INTERVAL` range: 100..1000 ms。
- `action` enum: `drop` / `forward` / `alert`。
- `pfc_stat_history`: `enable` または `disable` のみ。

### consumer (pfcwdorch) 例外動作
- `PLATFORM` 環境変数未設定: `Platform environment variable is not defined` → SWSS_LOG_ERROR (pfcwdorch.cpp:51)
- 非物理ポートへの適用: `Interface %s is not physical port` → SWSS_LOG_ERROR (pfcwdorch.cpp:201)
- platform 非対応 action: `Unsupported action %s for platform %s` → SWSS_LOG_ERROR (pfcwdorch.cpp:234)
- switch-level PFC DLR との競合: `Invalid PFC Watchdog action %s as switch level action %s is set` → SWSS_LOG_ERROR (pfcwdorch.cpp:260)
- `detection_time` 欠如: `PFC_WD_DETECTION_TIME missing` → SWSS_LOG_ERROR (pfcwdorch.cpp:302)
- pfc_stat_history 不正値: `%s is invalid value for PFC_STAT_HISTORY` → SWSS_LOG_ERROR (pfcwdorch.cpp:307)
- queue index 範囲外/不正: `Invalid argument` / `Out of range argument` → SWSS_LOG_ERROR (pfcwdorch.cpp:821-826)
- queue が storm state にない場合の restore: `Port %s queue %s not in PFC_WD_IN_STORM` → SWSS_LOG_ERROR (pfcwdorch.cpp:839)
- Lua スクリプトやポーリング間隔の設定失敗: SWSS_LOG_WARN (pfcwdorch.cpp:718)
