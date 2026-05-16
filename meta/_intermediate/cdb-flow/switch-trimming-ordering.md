# SWITCH_TRIMMING 書込み順序依存調査

調査日: 2026-05-16
ソース: `sonic-swss/orchagent/switchorch.cpp`, `orchdaemon.cpp`, `orchagent/switch/trimming/capabilities.cpp`

## 概要

`SWITCH_TRIMMING` は `SwitchOrch` が `CONFIG_DB` の `CFG_SWITCH_TRIMMING_TABLE_NAME` を
`SubscriberStateTable` で購読するシングルテーブル。他のテーブルへの依存はほぼなく、
順序制約は SAI 初期化とキー形式の 2 点に集約される。

## 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | SAI スイッチオブジェクト初期化 (`gSwitchId` 確立) → `SWITCH_TRIMMING|GLOBAL` 書込み | **先行必須** (capabilities.cpp コンストラクタが `sai_switch_api->query_attribute_capability` を即呼び出し) | orchagent が SAI 初期化を完了してから CONFIG_DB に書き込む |
| 2 | `SwitchTrimmingCapabilities` の capability クエリ (orchagent 起動時) → `SWITCH_TRIMMING` SET 処理 | **先行必須** (起動シーケンス内で保証済み; 外部から順序変更不可) | 不要 (orchagent 内部保証) |
| 3 | `dscp_value=from-tc` → `tc_value` も同一エントリに設定 | **推奨同時** (`tc_value` 欠如時は symmetric DSCP モードと判定され TC 設定が SAI に送られない) | 同一 `hset` コマンドで両フィールドを渡す |
| 4 | `queue_index` = 数値 → `dscp_value` との組み合わせを事前検討 | **設計上の注意** (`dscp_value=from-tc` + `queue_index=dynamic` は導出元が循環し非推奨) | どちらか一方のみを dynamic/from-tc にする |
| 5 | `SWITCH_TRIMMING|GLOBAL` DEL は不可 | **禁止** (orchagent が `operation is not supported` を返し `return false`) | 削除が必要な場合は orchagent 再起動後に再設定 |

## 主要な制約詳細

**SAI 初期化先行必須 (依存 #1, #2)**:
`SwitchOrch` コンストラクタ (orchdaemon.cpp L213) が実行される時点で
`SwitchTrimmingCapabilities` メンバー変数のコンストラクタ
(`capabilities.cpp L142–146`) が `queryCapabilities()` を呼び出し、
`sai_switch_api->query_attribute_capability(gSwitchId, ...)` を通じて各属性の
SAI サポート有無を確認する。この結果が `trimCap` に格納され、以降の全 SET 処理の
フィルタとして機能する。よって `gSwitchId` が確立する前に CONFIG_DB に
`SWITCH_TRIMMING` を書き込んでも、orchagent 起動後に能力クエリ完了 → CONFIG_DB
リプレイという順序で処理される (問題なし)。

**`dscp_value` + `tc_value` の同時設定 (依存 #3)**:
`from-tc` モードでは `tc_value` が SAI の TC 属性に設定される。
しかし SET ハンドラは受け取ったフィールド群を一括 parse し、
`parseTrimConfig` の中で `dscp.mode` と `tc` を同時評価する。
フィールドを複数回に分けて書いても orchagent は最新の DB スナップショットを
取得するため実害は少ないが、中間状態（`dscp_value=from-tc` だけ書いた状態）では
`tc_value` が `is_set = false` のままになり SAI の TC 属性は前回値を保持する。
一貫性のため 2 フィールドを同一トランザクションで書くことを推奨。

evidence:
- `orchdaemon.cpp` L200–213
- `capabilities.cpp` L142–146, L665–682
- `switchorch.cpp` L1087–1207 (フィールド評価順序: size → dscp.mode → dscp → tc → queue.mode → queue.index)
