# hardware-platform — Phase H 調査証跡

調査日: 2026-05-19
調査対象: `HARDWARE|ACCESS_LIST` テーブルのプラットフォーム差

## 調査手順

1. `sonic-swss/orchagent/aclorch.cpp` 全体を `COUNTER_MODE`・`LOOKUP_MODE`・`TCAM_SHARING`・`HARDWARE` で grep → **0 件**
2. `sonic-swss/orchagent/` 全ファイルを同キーワードで grep → `saihelper.cpp` の SAI_SWITCH_HARDWARE_ACCESS_BUS（別機能）のみ。HARDWARE テーブル参照 **0 件**
3. `sonic-swss/cfgmgr/`・`sonic-swss/fpmsyncd/` でも同様 → **0 件**
4. `sonic-gnmi/testdata/db_dump.json` に `HARDWARE|ACCESS_LIST` エントリあり（`LOOKUP_MODE: advanced`、`COUNTER_MODE: per-rule`）
5. `sonic-gnmi/testdata/db_dump.json` に `HARDWARE_TABLE|ACCESS_LIST` エントリあり（`LOOKUP_MODE: LEGACY`、`COUNTER_MODE: PER-RULE`）
6. `sonic-mgmt-common/tools/test/dbinit.py` に `HARDWARE|ACCESS_LIST` write あり（`LOOKUP_MODE: optimized`、`COUNTER_MODE: per-rule`）

## 結論

community sonic-swss/orchagent はこのテーブルを**購読しない（dead consumer）**。
ASIC 種別・プラットフォーム文字列（broadcom / mellanox / barefoot / cisco-8000 等）に基づく分岐は存在しない。
LOOKUP_MODE・COUNTER_MODE・TCAM_SHARING の値を解釈するコードが community リポジトリ内にないため、プラットフォーム依存は一切生じない。

testdata で観測された複数値（`advanced`・`optimized`・`LEGACY`）はベンダー向け translib 実装の差を示唆するが、community コードパスでは無関係。
