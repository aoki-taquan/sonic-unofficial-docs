# TELEMETRY_CONNECTIONS (STATE_DB) — Phase F 副次 DB 書込スキャンノート

調査日: 2026-05-19
対象テーブル: TELEMETRY_CONNECTIONS (STATE_DB)
ソース: sonic-net/sonic-gnmi gnmi_server/connection_manager.go, telemetry/telemetry.go

## 結論

TELEMETRY_CONNECTIONS テーブルは **終端テーブル** であり、他の DB への副次書込を発生させない。

## 根拠

connection_manager.go 全体精読:
- `storeKeyRedis()` / `deleteKeyRedis()` は STATE_DB.TELEMETRY_CONNECTIONS への HSet / HDel のみ実行
- これら関数の呼び出し後に他 DB へ書き込む処理は存在しない
- APPL_DB, ASIC_DB, CONFIG_DB, COUNTERS_DB, FLEX_COUNTER_DB への書込はなし

## 読み取り経路（副次書込なし）

TELEMETRY_CONNECTIONS を読み取るコンポーネント:
1. `show gnmi` CLI (sonic-utilities) — 表示目的のみ
2. `gnmi_server/server_test.go` — 単体テスト検証

これらはいずれも他 DB への書込を行わない。

## CONFIG_DB との関係

TELEMETRY_CONNECTIONS は STATE_DB テーブルであり、Config_DB への書き戻しは発生しない。
GNMI|gnmi.threshold (CONFIG_DB) は TELEMETRY_CONNECTIONS のエントリ数上限に影響するが、
TELEMETRY_CONNECTIONS 自体の変化が CONFIG_DB に影響することはない。
