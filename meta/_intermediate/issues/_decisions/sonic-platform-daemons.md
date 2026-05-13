# sonic-platform-daemons Issue Decisions

## #612: Regression failure: snmp/test_snmp_phy_entity.py::test_transceiver_info in branch 202503 [OPEN]
**判定: SKIP** — テスト回帰問題。内容なし、調査中。

## #395: thermalctld no longer adds 'speed_tolerance' to the Redis database [OPEN]
**判定: DOC → docs/platform/thermalctld-speed-tolerance-api-change.md**
`speed_tolerance` フィールドが廃止され `is_under_speed` / `is_over_speed` API に置き換えられた API 変更。health_checker.py の更新が必要。後方互換性への影響がある重要変更。

## #356: Add intelligence to xcvrd to understand process restart and config reload [CLOSED]
**判定: SKIP** — クローズ済み。設計議論のみ、確定内容は他 HLD でカバー。

## #136: psu daemon doesn't update PSU FAN information [CLOSED]
**判定: SKIP** — クローズ済み、古い問題。

## #110: Invalid port info in state DB after configuring split port in config_db.json without changing port_config.ini/platform.json [CLOSED]
**判定: SKIP** — クローズ済み。xcvrd が Config DB からポート設定を読む設計変更で解決。
