---
title: RESTAPI テーブル
description: "RESTAPI テーブル — go-server-server ベースの SONiC REST API (docker-sonic-restapi) の TLS 設定とランタイム挙動を保持するテーブル。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-restapi.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - RESTAPI
  cli: []
  yang:
    - sonic-restapi
  _no_related_cli: true
---

# RESTAPI テーブル

## 概要

`go-server-server` ベースの SONiC REST API (`docker-sonic-restapi`) の TLS 設定とランタイム挙動を保持するテーブル[^1]。`certs` (証明書パス群) と `config` (動作モード) の 2 つのシングルトン container から構成される。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>RESTAPI")]
  DM["restapi"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
RESTAPI|certs
RESTAPI|config
```

container `RESTAPI` の下に固定キー `certs` / `config` の 2 シングルトン。

## フィールド

### `RESTAPI|certs`

| フィールド | 型 | 説明 |
|-----------|----|------|
| `ca_crt` | string (path pattern `(/[a-zA-Z0-9_-]+)*/([a-zA-Z0-9_-]+).([a-z]+)`) | CA 証明書のローカルパス |
| `server_crt` | string (`*.crt` パス) | サーバ証明書 |
| `server_key` | string (`*.key` パス) | サーバ秘密鍵 |
| `client_crt_cname` | string (カンマ区切り CN リスト、ワイルドカード可) | クライアント証明書許可 CN リスト |

### `RESTAPI|config`

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `client_auth` | boolean | `true` | クライアント証明書認証の要求 |
| `log_level` | enum `trace`/`info` | なし | コンテナログレベル |
| `allow_insecure` | boolean | `false` | 平文 (HTTP) 接続の許可 |

## 制約

- `ca_crt` / `server_crt` / `server_key` / `client_crt_cname` はそれぞれ厳密な正規表現でパス / CN 形式を制約
- 既定では `client_auth = true` / `allow_insecure = false` のため、相互 TLS が必須[^1]

## 購読者

- `docker-sonic-restapi` の起動スクリプト: [CONFIG_DB](../../reference/glossary.md#term-config_db) → `go-server-server` 起動引数 / 環境変数 / 証明書パスを設定

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): なし (`FEATURE.restapi` で有効化される)
- CLI: 標準 CLI ラッパなし。`config restapi` 系コマンドは未提供 ([CONFIG_DB](../../reference/glossary.md#term-config_db) 直接編集または init_cfg 経由)
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-restapi`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-restapi`](../yang/sonic-restapi.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `src/sonic-yang-models/yang-models/sonic-restapi.yang` (container `RESTAPI` / `certs` / `config`). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-restapi.yang>

## 関連ページ
- [CONFIG_DB: FEATURE](feature.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `RESTAPI|certs / config`。
- `client_auth`: `true`、`log_level`: `info`、`server_crt`/`server_key`: パス。

### よくある誤設定

- client_auth=true で client CA を入れ忘れると 401 が出続ける。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'RESTAPI|*'
systemctl status restapi
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `client_auth` 値別挙動
| 値 | 挙動 |
|----|------|
| `true` | クライアント証明書認証必須（mTLS）。デフォルト。`client_crt_cname` の CN 検証も実施。 |
| `false` | クライアント証明書不要。サーバ証明書のみ検証。 |

### `log_level` 値別挙動
| 値 | 挙動 |
|----|------|
| `trace` | 詳細ログ出力（デバッグ用）。 |
| `info` | 通常ログ。 |
| その他 | [YANG](../../reference/glossary.md#term-yang) `pattern "trace|info"` 制約違反でバリデーション拒否。（enum 定義なし、文字列 pattern 制約） |

### `allow_insecure` 値別挙動
| 値 | 挙動 |
|----|------|
| `false` | HTTP 平文接続不可（デフォルト）。HTTPS のみ許可。 |
| `true` | HTTP 平文接続を許可。テスト環境向け。 |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

- **TLS パス pattern 制約**: `ca_crt` / `server_crt` / `server_key` は YANG の `pattern` 制約でファイルパス形式のみ受け入れる。パターン違反は sonic-yang バリデーション時に拒否される。[^2]
- **client_crt_cname のワイルドカード制約**: ワイルドカード (`*.domain`) 表記は許可されるが、カンマ末尾や空白を含む場合は `Pattern` エラーで拒否される。[^2]
- **log_level は trace/info のみ**: YANG `pattern "trace|info"` 制約。それ以外の値はバリデーション拒否。[^2]
- **runtime 読み込みは起動時のみ**: RESTAPI テーブルの変更は `docker-sonic-restapi` コンテナ再起動まで反映されない（hot reload 未対応）。[^2]
- **証明書ファイルの実在チェックなし**: `server_crt` 等のパスが存在しないファイルを指していても CONFIG_DB レベルでは検知されない。サーバ起動時に失敗する。[^2]

[^2]: YANG 定義: `sonic-restapi.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-restapi.yang>


<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

REST_API テーブルの各フィールドはサービス起動引数に直接マッピングされる。CONFIG_DB 内フィールド間の自動付与はなし。`client_auth` 未設定の場合はサービスデフォルトの認証モード（`user_auth`）が使用される。

### Phase 7: 条件付き登録 (add_manager 条件)

restapi サービス (sonic-mgmt-framework / sonic-gnmi) がインストールされている場合のみ `REST_API` テーブルを消費するプロセスが存在する。サービスが有効化されていない場合はテーブルを読んでも REST API サービスは起動しない。

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `restapi` 起動処理 | `client_auth==user_auth` | ユーザー認証モードで TLS 設定 | restapi 設定処理 |
| `restapi` 起動処理 | `client_auth==cert` | クライアント証明書認証モード | restapi 設定処理 |
| `restapi` 起動処理 | `log_level` 値により | ログ出力レベルを変更 | restapi 設定処理 |
| `restapi` 起動処理 | `server_crt` / `server_key` あり | TLS を有効化して起動 | restapi 設定処理 |

> **スキャン証跡**: `RESTAPI` テーブルは REST API サービス設定の薄いラッパー。CONFIG_DB 内での自動派生なし。主にサービス起動時の設定ファイル生成に使われる。

<!-- /handler-branching -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **hostcfgd**: `RESTAPI` テーブルを `ConfigDBConnector` で購読。

### 段階 2: CFG → APPL 翻訳

- hostcfgd が REST API サービス (sonic-restapi / sonic-gnmi) の有効・無効設定を `/etc/sonic/` に書き込む。
- APP_DB への書き込みなし。

### 段階 3: APPL → SAI

- SAI 経由なし。REST API は管理プレーン機能。

### 段階 4: タイミング + 副作用

- hostcfgd が設定を反映後、対象サービスが再起動されるまで数秒。
- 副作用: REST API 無効化中に自動化スクリプトが接続しようとするとタイムアウトが発生。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

RESTAPI テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - 専用 CLI なし

### minigraph / sonic-cfggen

**minigraph.py** が `results['RESTAPI']` に REST API 設定を投入 (sonic-buildimage/src/sonic-config-engine/minigraph.py:2689)

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

**db_migrator.py** が RESTAPI のマイグレーション処理 (`config` / `certs` サブキー) を実装 (sonic-utilities/scripts/db_migrator.py:609–619)

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

`rest-server.sh` 起動スクリプトがコード由来デフォルトを注入する（下記 `<!-- defaults -->` ブロック参照）。

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- defaults -->
## コード由来デフォルト (Phase A)

`docker-sonic-mgmt-framework/rest-server.sh` が CONFIG_DB 値を読み込む際に適用するランタイムデフォルト。YANG スキーマに `default` 文が存在しない場合でも、起動スクリプト側で値が補完される。

| フィールド | コード由来デフォルト | 根拠 |
|-----------|---------------------|------|
| `client_auth` | `"user"` | `CLIENT_AUTH=$(... jq -r '.client_auth // "user"')` — CONFIG_DB 未設定時にユーザー認証モードを強制 |
| `log_level` | （省略 = 引数なし = `trace` 相当の詳細ログ） | `LOG_LEVEL=$(... jq -r '.log_level // empty')` — 空の場合は `-v` 引数が付かず rest_server デフォルト (`trace`) が適用 |
| `server_crt` / `server_key` | `/tmp/cert.pem` / `/tmp/key.pem`（自動生成） | 証明書パスが未設定の場合 `generate_cert --host="localhost,127.0.0.1"` で自己署名証明書を `/tmp/` に生成 |
| `allow_insecure` (HTTP) | 無効 (`-enablehttp` フラグなし) | 起動引数に HTTP 許可フラグが含まれず、HTTPS のみで起動 |
| `port` | rest_server バイナリデフォルト（8443） | `SERVER_PORT=$(... jq -r '.port // empty')` — 空の場合は `-port` 引数なし、rest_server の組み込みデフォルトが有効 |

> **スキャン証跡**: `sonic-buildimage/dockers/docker-sonic-mgmt-framework/rest-server.sh` の起動スクリプトより抽出。YANG `sonic-restapi.yang` には `default` 文なし。コード由来デフォルトのみ。

[^3]: `sonic-buildimage/dockers/docker-sonic-mgmt-framework/rest-server.sh`. <https://github.com/sonic-net/sonic-buildimage/blob/master/dockers/docker-sonic-mgmt-framework/rest-server.sh>

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

> **調査根拠**: `supervisord.conf`, `rest-server.sh`, `mgmt_vars.j2`, `minigraph.py` L2689–2702, `db_migrator.py` L608–619 精読 (2026-05-18)
> 詳細証跡: `meta/_intermediate/cdb-flow/restapi-ordering.md`

### コンテナ起動時シーケンス

`docker-sonic-mgmt-framework` コンテナは supervisord が以下の優先順序でプロセスを制御する:

```
1. rsyslogd 起動 (priority=1)
2. start.sh 実行 (priority=2, wait_for=rsyslogd:running)
3. rest-server.sh 実行 (priority=3, wait_for=start:exited)
   ├─ sonic-cfggen -d -t mgmt_vars.j2 → REST_SERVER / x509 を CONFIG_DB から一括取得
   ├─ RESTAPI|config.client_auth / log_level / port 読込み
   ├─ RESTAPI|certs (server_crt / server_key / ca_crt) 読込み
   ├─ 未設定の場合は DEVICE_METADATA|x509 をフォールバック参照
   └─ 証明書も未設定の場合は /tmp/ に自己署名証明書を自動生成して起動
```

`rest-server.sh` は `start:exited` 待機後に起動するため、CONFIG_DB への書込みが必ず先行する。

### テーブル間の書込み順依存

| # | 依存関係 | 強制度 | 備考 |
|---|----------|--------|------|
| 1 | `RESTAPI|certs` 書込み → `rest-server.sh` 起動 | **起動時保証済み** | supervisord `wait_for=start:exited` が順序を保証 |
| 2 | `DEVICE_METADATA\|localhost.x509` 先行書込み | **任意 (フォールバック)** | `RESTAPI|certs` が未設定の場合のみ参照。minigraph.py が両者を同一パスで生成するため通常は問題なし |
| 3 | `db_migrator` による `RESTAPI` 移植 | **既存エントリ優先** | `config_db.get_entry('RESTAPI', 'config')` が空の場合のみ書込む。既存エントリは上書きしない (`db_migrator.py` L614–619) |
| 4 | `minigraph.py` が `RESTAPI` を生成 | **minigraph 内部** | `FEATURE` テーブルと同一の minigraph 解析パスで生成される (`minigraph.py` L2689-2702) |
| 5 | `RESTAPI|config` / `RESTAPI|certs` 変更 → `docker-sonic-mgmt-framework` 再起動 | **必須後続** | hot reload 未対応。変更反映にはコンテナ再起動が必要 |

### certs の解決優先順位

`rest-server.sh` が証明書パスを決定する順序:

1. `RESTAPI|certs` (CONFIG_DB の `REST_SERVER` テーブル) に `server_crt` / `server_key` / `ca_crt` が設定されている場合はそれを使用
2. 上記が未設定かつ `DEVICE_METADATA|localhost.x509` にパスが設定されている場合はフォールバック参照
3. どちらも未設定の場合は `generate_cert --host="localhost,127.0.0.1"` で `/tmp/cert.pem` / `/tmp/key.pem` を自動生成

本番環境では `RESTAPI|certs` を明示的に設定しないと自己署名証明書が使用される点に注意。

<!-- /ordering -->

<!-- glossary-links-injected: d5320e852f7a -->
