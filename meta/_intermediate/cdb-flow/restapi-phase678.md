# RESTAPI — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`REST_API` テーブルは sonic-restapi プロセス (`sonic-gnmi` / `sonic-mgmt-framework`) が読み込む設定テーブル。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| TLS 設定 | `client_auth` が未設定またはデフォルト | `user_auth` モードで起動 | `restapi` / `sonic-gnmi` 起動スクリプト |
| REST API ポート | `port` フィールド未設定 | デフォルト `8080` (または `443` TLS 時) | `restapi` 設定 |

**CONFIG_DB 内フィールド間の自動派生**: 特になし。各フィールドは独立して restapi プロセスの起動引数・設定ファイルに反映される。

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `sonic-mgmt-framework` / `sonic-gnmi` インストール時のみ | `REST_API` テーブルを消費するプロセスが存在する | build-time 依存 |
| restapi サービスが有効化されていない | テーブルを読んでも REST API サービスは起動しない | systemd service 設定 |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `restapi` 起動処理 | `client_auth==user_auth` | ユーザー認証モードで TLS 設定 | restapi 設定処理 |
| `restapi` 起動処理 | `client_auth==cert` | クライアント証明書認証モード | restapi 設定処理 |
| `restapi` 起動処理 | `log_level` 値により | ログ出力レベルを変更 | restapi 設定処理 |

> **スキャン証跡**: `RESTAPI` テーブルは REST API サービス設定の薄いラッパー。CONFIG_DB 内での自動派生なし。主にサービス起動時の設定ファイル生成に使われる。
