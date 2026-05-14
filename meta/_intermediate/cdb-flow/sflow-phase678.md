# SFLOW — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`sflowmgrd` が `SFLOW` グローバルテーブルと `SFLOW_SESSION` テーブルを読み、hsflowd の設定ファイルを生成する。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| hsflowd `polling` 設定 | `SFLOW.polling_interval` 未設定 | デフォルト値 (20秒) | `sflowmgrd` |
| hsflowd `sampling` 設定 | `SFLOW_SESSION.sample_rate` 未設定 | ポート速度依存デフォルト | `sflowmgrd` |
| hsflowd `agent` IP | `SFLOW.agent_id` が設定されている場合 | 指定インターフェースの IP を agent IP として使用 | `sflowmgrd` |
| 全ポートサンプリング | `SFLOW_SESSION|all` エントリ | 全ポートに適用 | `sflowmgrd` |

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `sflowmgrd` は常時起動 | `SFLOW` / `SFLOW_SESSION` テーブルは無条件購読 | `sflowmgrd` |
| `SFLOW.admin_state==down` | hsflowd を停止、設定ファイルを生成しない | `sflowmgrd` |
| `SFLOW.admin_state==up` | hsflowd 設定ファイルを生成して hsflowd を起動/再起動 | `sflowmgrd` |
| `agent_id` インターフェースが存在しない | ログ警告、agent IP の設定をスキップ | `sflowmgrd` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `sflowmgrd` | `admin_state==up` | hsflowd 設定ファイル生成 + サービス起動 | `sflowmgrd` |
| `sflowmgrd` | `admin_state==down` | hsflowd サービス停止 | `sflowmgrd` |
| `sflowmgrd` | `agent_id` フィールドあり | 指定 IF の IP を `agent { ip <x> }` として設定 | `sflowmgrd` |
| `sflowmgrd` SFLOW_SESSION | `sample_rate` フィールドあり | ポートごとのサンプリングレートを明示設定 | `sflowmgrd` |
| `sflowmgrd` SFLOW_SESSION | `admin_state==down` | ポートの sFlow を無効化 | `sflowmgrd` |
| `sflowmgrd` SFLOW_SESSION | key が `all` | 全ポートに設定を適用 | `sflowmgrd` |

> **スキャン証跡**: `SFLOW` テーブルは hsflowd 設定生成のための入力。admin_state による主要分岐あり。SAI 経路はなし (ユーザースペース制御)。
