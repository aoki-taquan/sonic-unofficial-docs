# SWITCH_TRIMMING — 失敗挙動調査 (Phase D)

> 調査根拠: `sonic-swss/orchagent/switchorch.cpp` `doCfgSwitchTrimmingTableTask()` L1310–1363 および `setSwitchTrimming()` L1066–1302 全体精読 (2026-05-19)

## 失敗パス一覧

| # | 失敗トリガー | 挙動 | リトライ | SAI 影響 |
|---|------------|------|--------|---------|
| 1 | ASIC が packet trimming 非対応 (`isSwitchTrimmingSupported() = false`) | `SWSS_LOG_WARN` を出力して `return true`（**成功扱いの no-op**） | なし（capability 変化なし） | SAI 属性設定なし；CONFIG_DB 値は残存 |
| 2 | `size` フィールドの SAI `set_switch_attribute` 失敗 | `SWSS_LOG_ERROR("Failed to set switch trimming size in SAI")` → `setSwitchTrimming` が `false` を返す | なし（エントリは erase） | SAI 未反映；`trimHlpr` キャッシュ更新なし |
| 3 | `dscp_value` モードが ASIC capability 非対応 | `SWSS_LOG_ERROR("Failed to validate switch trimming DSCP mode: capability is not supported")` → `false` | なし | SAI 未反映 |
| 4 | `dscp_value` の SAI set 失敗 | `SWSS_LOG_ERROR("Failed to set switch trimming DSCP mode in SAI")` → `false` | なし | SAI 未反映；DSCP mode キャッシュ更新なし |
| 5 | `tc_value` が ASIC capability 非対応 | `SWSS_LOG_ERROR("Failed to validate switch trimming TC value: capability is not supported")` → `false` | なし | SAI 未反映 |
| 6 | `tc_value` の SAI set 失敗 | `SWSS_LOG_ERROR("Failed to set switch trimming TC value in SAI")` → `false` | なし | SAI 未反映；TC キャッシュ更新なし |
| 7 | `queue_index` モードが ASIC capability 非対応 | `SWSS_LOG_ERROR("Failed to validate switch trimming queue mode: capability is not supported")` → `false` | なし | SAI 未反映 |
| 8 | `queue_index` の SAI set 失敗 | `SWSS_LOG_ERROR("Failed to set switch trimming queue index in SAI")` → `false` | なし | SAI 未反映；queue キャッシュ更新なし |
| 9 | 既存設定の削除試行（`size`/`dscp`/`tc`/`queue` DEL） | `SWSS_LOG_ERROR("Failed to remove switch trimming * configuration: operation is not supported")` → `false` | なし | 削除不可；CONFIG_DB / SAI の状態乖離 |
| 10 | `parseTrimConfig` がバリデーション失敗（全フィールド無効） | `LOG_ERROR("Validation error: missing valid fields")` → `parseTrimConfig` が `false` を返す | なし（エントリ erase） | SAI 未反映；エントリ消去 |
| 11 | key が空文字列 | `SWSS_LOG_ERROR("Failed to parse switch trimming key: empty string")` → erase | なし | SAI 未反映 |
| 12 | DEL オペレーション | `SWSS_LOG_ERROR("Failed to remove switch trimming: operation is not supported: ASIC and CONFIG DB are diverged")` | なし | 削除不可；CONFIG_DB と SAI が乖離 |
| 13 | 未知 operation | `SWSS_LOG_ERROR("Unknown operation(%s)")` → erase | なし | SAI 未反映 |

## 詳細

### 1. 非対応 ASIC での no-op（最重要）

`setSwitchTrimming()` 冒頭 (`switchorch.cpp:1081–1085`) で `isSwitchTrimmingSupported()` を確認する。
この関数は `SwitchTrimmingCapabilities` コンストラクタが SAI `query_attribute_capability` で問い合わせた結果を返す。
非対応のとき `SWSS_LOG_WARN` のみ出力して `return true`（成功扱い）のため、**呼び出し元の `doCfgSwitchTrimmingTableTask()` はエラーとみなさずエントリを erase する**。
CONFIG_DB に `SWITCH_TRIMMING|GLOBAL` の値が残っていても SAI には一切反映されない。

> `STATE_DB:SWITCH_CAPABILITY|switch.SWITCH_TRIMMING_CAPABLE` の値を確認することで ASIC の対応有無を判断できる。

### 2〜8. SAI set 失敗のキャッシュ未更新問題

`setSwitchTrimming()` は各属性 set 成功後にのみ `trimHlpr.setConfig(trim)` でローカルキャッシュを更新する（`switchorch.cpp:1298–1302`）。
途中の属性 set が失敗すると `false` を返し、**キャッシュ更新を行わないまま**処理を中断する。
呼び出し元 `doCfgSwitchTrimmingTableTask()` はこの戻り値を受けて `SWSS_LOG_ERROR("Failed to set switch trimming: ASIC and CONFIG DB are diverged")` を出力するが、**エントリを erase してリトライなし**（`switchorch.cpp:1347–1351`, `1362`）。
これにより SAI 上には一部の属性のみが適用された中間状態が固定されうる。

### 9 & 12. 削除操作の完全非サポート

`SWITCH_TRIMMING|GLOBAL` の全フィールド削除（DEL）および既存値の削除オペレーションはいずれも `false` を返して拒否される。
一度設定した trimming 設定をリセットする公式の方法は存在せず、orchagent 再起動後に CONFIG_DB を新値で書き直すことで間接的に再適用するしかない。

### バックアップ/リストア挙動

`dscpBak`・`tcBak`・`queueBak` フラグ群（`switchorch.cpp:1072–1074`）は DSCP モード切替時に前回値を SAI にリストアするためのものだが、バックアップ前の属性の SAI set が失敗した場合はバックアップ処理自体がスキップされ（`1276–1300`）、中途状態のまま終了する。

> **Evidence**: `sonic-swss` `orchagent/switchorch.cpp:1066–1364`、`orchagent/switch/trimming/capabilities.cpp:142–188,724`
