# errordb — 書込み順依存 (Phase B)

slug: errordb
phase: ordering (Phase B)
generated: 2026-05-18

## 調査対象

- `SONiC/doc/error-handling/error_handling_design_spec.md` Rev 0.1 (2019-05-06), Section 3.3.1
- `sonic-swss-common/common/status_code_util.h`

## 判明した順序依存

| # | 依存関係 | 方向 | 根拠 |
|---|----------|------|------|
| 1 | syncd ASIC_DB 単一通知チャネル → OrchAgent 受信 | 強制先行 | HLD 3.3.1: "single notification channel ensures that order of the notifications is retained" |
| 2 | SAI 型 → SWSS_RC_* 翻訳 → HSET → publish | 強制先行 | HLD 3.3.1 失敗パス手順 |
| 3 | 失敗 HSET → publish | 強制先行 | ErrorListener コールバック時に必ずエントリ存在 |
| 4 | 成功時 DEL → publish | 強制先行（逆向き） | HLD 3.3.1 成功パス: "Removes entry...Publishes notifications" |
| 5 | `sonic-clear` → 通知なし削除 | CLI 直接削除 | HLD 3.3.3 |
| 6 | warm reboot → ERROR_DB クリア | 起動時リセット | HLD Section 6 |

## 実装状況

ERROR_DB / ErrorReporter / ErrorListener は 2026-05 時点で master 未マージ。
上記の順序依存は HLD 設計仕様からの推論であり、実装コードによる確認は未実施。
SWSS_RC_* enum (`status_code_util.h`) のみ実装済み。
