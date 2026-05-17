---
title: TELEMETRY テーブル
description: "TELEMETRY テーブル — gRPC ストリーミングテレメトリ / gNMI サーバの設定。TLS 証明書パスと gNMI ランタイムオプションを保持する。telemetry コンテナ (docker-telemetry、docker-gnmi) が起動時に CONFIG_DB を読み込む。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-telemetry.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - TELEMETRY
  cli:
    - config telemetry
  yang:
    - sonic-telemetry
---

# TELEMETRY テーブル

## 概要

gRPC ストリーミングテレメトリ / [gNMI](../../reference/glossary.md#term-gnmi) サーバの設定。TLS 証明書パスと [gNMI](../../reference/glossary.md#term-gnmi) ランタイムオプションを保持する[^1]。`telemetry` コンテナ (`docker-telemetry`、`docker-gnmi`) が起動時に [CONFIG_DB](../../reference/glossary.md#term-config_db) を読み込む。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>TELEMETRY")]
  DM["telemetry"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
TELEMETRY|certs        # TLS 証明書
TELEMETRY|gnmi         # gNMI サーバオプション
```

## TELEMETRY|certs

| フィールド | 型 | 説明 |
|-----------|----|------|
| `ca_crt` | string (`*.cer` パス) | CA 証明書のローカルパス |
| `server_crt` | string (`*.cer`) | サーバ証明書 |
| `server_key` | string (`*.key`) | サーバ秘密鍵 |

## TELEMETRY|gnmi

| フィールド | 型 | 説明 |
|-----------|----|------|
| `client_auth` | boolean | クライアント認証要求 |
| `log_level` | uint8 (0..100) | [gNMI](../../reference/glossary.md#term-gnmi) ログレベル |
| `port` | inet:port-number | gNMI 待受 TCP ポート |
| `save_on_set` | boolean | `Set` RPC 完了時に config 永続化 |
| `enable_crl` | boolean | CRL (Certificate Revocation List) 有効化 |
| `crl_expire_duration` | uint32 | CRL キャッシュ期限 [秒] |
| `user_auth` | string `password`/`jwt`/`cert`/`none` | ユーザ認証方式 |

## 購読者

- `telemetry` (`docker-telemetry`) / `gnmi` (`docker-gnmi`): プロセス起動時にこのテーブルを読む

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `GNMI_CLIENT_CERT` (gNMI クライアント証明書 fingerprint)
- 関連 CLI: `config telemetry config-db`、`config telemetry server`、`gnoi-system reboot` 等
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-telemetry`、`sonic-gnmi`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): `sonic-telemetry`
- CLI: `config telemetry`

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-telemetry.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-telemetry.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Telemetry / SNMP / Observability](../../topics/09-telemetry-snmp/index.md)

<!-- /topics-back-ref -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `user_auth` (string pattern): `password` / `jwt` / `cert` / `none`

### `client_auth` (boolean): `true` / `false`

### `save_on_set` (boolean): `true` / `false`

### `enable_crl` (boolean): `true` / `false`

| フィールド | 値 | 挙動 |
|-----------|-----|-----|
| `user_auth` | `password` | ユーザ名/パスワード認証 |
| `user_auth` | `jwt` | JWT トークン認証 |
| `user_auth` | `cert` | クライアント証明書認証 |
| `user_auth` | `none` | 認証なし |
| `client_auth` | `true` | `ca_crt` 未設定/ファイル不在だとサーバ起動失敗 |
| `client_auth` | `false` | サーバ証明書のみで TLS 接続 |
| `save_on_set` | `true` | gNMI Set RPC 完了時に `config save` を実行 |
| `save_on_set` | `false` | Set は [CONFIG_DB](../../reference/glossary.md#term-config_db) のみに反映。永続化しない |
| `enable_crl` | `true` | CRL チェック有効化。`crl_expire_duration` も設定が必要 |
| `port` | 未設定 / `0` | `unix_socket` も未設定の場合サーバ起動失敗 |
| 全フィールド | 起動後変更 | コンテナ再起動 (`systemctl restart telemetry`) まで反映されない |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-gnmi/gnmi_server/server.go@eb635b7679b260c3fd0786a6d0734fc8e82c9a22 L381-643 -->

- **起動時のみ参照**: `telemetry` コンテナは起動時に CONFIG_DB を一回読み込む。実行中の変更はコンテナ再起動（`systemctl restart telemetry`）なしには反映されない。
- **ポート未設定でサーバ不起動**: `port` が 0 以下かつ `unix_socket` も未設定の場合、`"no listener configured: port must be > 0 or unix_socket must be set"` を返してサーバが起動しない。
- **TCP / UDS リスナー失敗時の縮退動作**: TCP listen 失敗時は `"Failed to open listener port <port>: disabling TCP listener"` を Warningf し UDS のみで継続（その逆も同様）。両方失敗した場合はサーバ起動エラーになる。
- **TLS 証明書の不整合**: `server_crt` / `server_key` のいずれか一方のみ設定されていると `"server certificate or key file path is empty"` を返す。証明書ファイルが存在しない場合も stat エラーを返してサーバが起動しない。
- **CA 証明書ファイル不在**: mTLS 設定時に `ca_crt` パスが存在しない場合 `"CA certificate file not found"` を返す。

<!-- /cdb-exceptions -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `TELEMETRY|<key>` (`gnmi`, `certs` 等)`。
- `port`: `8080`/`50051`、`client_auth`: `true`、`log_level`: `2`。

### よくある誤設定

- client_auth=true なのに CA bundle 設定漏れで gNMI client が TLS handshake に失敗する。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'TELEMETRY|*'
systemctl status telemetry
```
<!-- /ops-hint -->


<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

telemetry サービスが `server_crt` / `server_key` フィールドの有無から TLS 有効/無効を自動決定する。`client_auth` フィールド値から認証モード（JWT / cert / なし）を自動設定する。

### Phase 7: 条件付き登録 (add_manager 条件)

telemetry サービスが有効の場合のみ `TELEMETRY` テーブルを消費する sonic-gnmi が動作する。`TELEMETRY|gnmi` エントリのみ処理するシングルトン制約あり（YANG で強制）。

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `telemetry` | `server_crt` / `server_key` フィールドあり | TLS 有効で gNMI サーバー起動 | `telemetry` |
| `telemetry` | TLS 設定なし | 平文または insecure モードで起動 | `telemetry` |
| `telemetry` | `client_auth==jwt` | JWT 認証ミドルウェアを有効化 | `telemetry` |
| `telemetry` | `client_auth==cert` | クライアント証明書認証を有効化 | `telemetry` |
| `telemetry` | `allow_no_client_auth==true` | mTLS を強制しない | `telemetry` |
| `telemetry` | `log_level` 変化 | ランタイムログレベルを変更 | `telemetry` |

> **スキャン証跡**: `TELEMETRY` は gNMI/gRPC サーバー設定のシングルトン。TLS フィールド有無と `client_auth` 値が起動モードを決定する主要分岐。

<!-- /handler-branching -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **gnmi-telemetry / sonic-gnmi**: `TELEMETRY` テーブルを `ConfigDBConnector` で購読してグローバル設定を適用。

### 段階 2: CFG → APPL 翻訳

- gnmi-telemetry がサーバポート / TLS 証明書 / 認証設定を読み込みリッスンを開始。
- APP_DB への書き込みなし。

### 段階 3: APPL → SAI

- SAI 経由なし。gNMI サーバが DATA_DB / STATE_DB を購読してデータを提供。

### 段階 4: タイミング + 副作用

- 設定変更は gnmi-telemetry 再起動後に有効 (数秒)。クライアントは再接続が必要。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

TELEMETRY テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - 専用 CLI なし — minigraph または手動 `config load` 経由

### minigraph / sonic-cfggen

**minigraph.py** が TELEMETRY エントリを生成 (sonic-buildimage/src/sonic-config-engine/minigraph.py)

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での TELEMETRY マイグレーションなし

### ビルド時デフォルト (build-time default)

**`dockers/docker-sonic-telemetry/telemetry_vars.j2`** が TELEMETRY テーブルを参照して設定を生成 (読み取り側)

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- defaults -->
## フィールドデフォルト (コード由来)

### TELEMETRY|gnmi

| フィールド | デフォルト値 | 設定元 | 備考 |
|-----------|-------------|--------|------|
| `port` | `50051` (minigraph 注入) / `8080` (gnmi キー未存在時) | `minigraph.py` L2680; `telemetry.sh` L85 | gnmi キー自体が CONFIG_DB にない場合 `telemetry.sh` が `8080` にフォールバック |
| `client_auth` | `"true"` (minigraph 注入) / 未設定 → `false` 扱い | `minigraph.py` L2679; `telemetry.sh` L96 | 空または `"false"` のとき `--allow_no_client_auth` を付与して起動 |
| `log_level` | `2` | `minigraph.py` L2681; `telemetry.sh` L104 | 非数値 or 未設定なら `-v=2` にフォールバック |
| `save_on_set` | 未設定（= 無効） | `telemetry.sh` L107 コメント | 明示的に `"true"` を設定した場合のみ有効化 |
| `enable_crl` | 未設定（= 無効） | `telemetry.sh` L150 | `user_auth=cert` かつ `enable_crl=true` のときのみ `--enable_crl` フラグを渡す |
| `crl_expire_duration` | 未設定（gnmiサーバ組み込み値を使用） | `telemetry.sh` L155 | 値がある場合のみ `--crl_expire_duration` を渡す |
| `user_auth` | 未設定（= 認証なし） | `telemetry.sh` L142 | 未設定 / `null` のとき `--client_auth` 引数が渡されない |

> **隠れデフォルト（YANG 未定義）**: `threshold=100`、`idle_conn_duration=5`（秒）は YANG に定義がなく `telemetry.sh` のみで管理される（L121, L134）。

### TELEMETRY|certs

| フィールド | デフォルト値 | 設定元 |
|-----------|-------------|--------|
| `server_crt` | `/etc/sonic/telemetry/streamingtelemetryserver.cer` | `minigraph.py` L2684 |
| `server_key` | `/etc/sonic/telemetry/streamingtelemetryserver.key` | `minigraph.py` L2685 |
| `ca_crt` | `/etc/sonic/telemetry/dsmsroot.cer` | `minigraph.py` L2686 |

> YANG (`sonic-telemetry.yang`) には `default` 文が一切定義されていない。すべてのデフォルトはランタイム側（`telemetry.sh` / `minigraph.py`）で実装される。

<!-- /defaults -->

<!-- ordering -->
## 起動順序・順序依存 (Phase B)

### 前提: FEATURE テーブル有効化

`docker-telemetry-entry.sh` はコンテナ起動直後に `FEATURE|telemetry.state` を 10 秒ごとにポーリングし、`enabled` になるまで supervisord を起動しない。`TELEMETRY` テーブルを設定する前に `FEATURE|telemetry.state = "enabled"` が [CONFIG_DB](../../reference/glossary.md#term-config_db) に存在していること（minigraph.py による自動生成フローでは保証済み）。

> evidence: `dockers/docker-sonic-telemetry/docker-telemetry-entry.sh:39-48`

### systemd 依存順 (telemetry.service.j2)

```
database.service ──┐
swss.service ──────┤ After= / Requires=  →  telemetry.service 起動
syncd.service ──────┘
sonic.target ──────────────────────────────→  After=sonic.target
```

`database.service` (Redis / [CONFIG_DB](../../reference/glossary.md#term-config_db)) が Ready になった後に telemetry が起動するため、CONFIG_DB が未起動の状態で `TELEMETRY` テーブルを読もうとすることはない。

> evidence: `files/build_templates/telemetry.service.j2:3-4`

### supervisord 内部起動順 (supervisord.conf)

| 優先度 | プロセス | 待機条件 |
|--------|---------|---------|
| 1 | `rsyslogd` | — |
| 2 | `start` (`start.sh`) | `rsyslogd:running` |
| 3 | `telemetry` (`telemetry.sh`) | `start:exited` |
| 4 | `dialout` (`dialout.sh`) | `telemetry:running` |

`telemetry.sh` は `start.sh` の正常終了後に起動する。`dialout` (gRPC dial-out ストリーミング) はgNMI サーバが listen 状態になってから起動するため、`TELEMETRY` 設定不整合でサーバが起動失敗した場合 `dialout` も起動しない。

> evidence: `dockers/docker-sonic-telemetry/supervisord.conf:31-68`

### 起動時一括読み込み — runtime 変更は再起動まで無効

`telemetry.sh` は起動時に `sonic-cfggen -d -t telemetry_vars.j2` で `TELEMETRY|certs` / `TELEMETRY|gnmi` / `DEVICE_METADATA|x509` を**一括読み込み**し、起動引数として gnmi_server バイナリに渡す。起動後に [CONFIG_DB](../../reference/glossary.md#term-config_db) を変更しても gnmi_server プロセスには反映されない。

```bash
# 設定変更を反映させる場合
systemctl restart telemetry
```

> evidence: `dockers/docker-sonic-telemetry/telemetry.sh:40-43`

### TLS 証明書ファイルは起動前に配置必須

`gnmi_server/server.go` の `SrvAdvConfig()` は `os.Stat()` で `server_crt` / `server_key` / `ca_crt` の存在を確認し、ファイル不在ならサーバが起動しない。`TELEMETRY|certs` を設定する際は証明書ファイルの実ファイル配置も同時に行うこと。

> evidence: `gnmi_server/server.go:398-418` (`SrvAdvConfig`)

### cert 認証時: GNMI_CLIENT_CERT テーブルを先に書く

`user_auth=cert` を設定すると telemetry サーバは `GNMI_CLIENT_CERT` テーブルを参照してクライアント証明書の fingerprint チェックを行う。`GNMI_CLIENT_CERT` エントリが存在しない状態で `user_auth=cert` に切り替えると、サーバ起動後にすべての接続が認証失敗となる。設定変更の順序は `GNMI_CLIENT_CERT` → `TELEMETRY|gnmi.user_auth=cert` → サーバ再起動。

> evidence: `dockers/docker-sonic-telemetry/telemetry.sh:146-149`

### 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `FEATURE\|telemetry.state=enabled` → telemetry コンテナ起動 | 先行必須（未設定は 10s ポーリング） | minigraph フローでは自動保証 |
| 2 | `database.service` ready → telemetry.service 起動 | systemd `After=` 強制 | Redis 未起動での起動は不可 |
| 3 | `start.sh` 終了 → `telemetry.sh` 実行 | supervisord `dependent_startup` 強制 | FEATURE チェック完了が保証される |
| 4 | `TELEMETRY` 全設定書き込み → `telemetry.sh` 実行（一括読み込み） | 起動時一括読み込みのため先行必須 | runtime 変更は `systemctl restart telemetry` で反映 |
| 5 | TLS 証明書ファイル配置 → `server_crt`/`server_key`/`ca_crt` 設定 | ファイル存在確認が先行必須 | 空の場合は `--insecure` フォールバック |
| 6 | `GNMI_CLIENT_CERT` エントリ → `user_auth=cert` 設定 | 推奨先行（欠如時は接続認証失敗） | サーバ再起動必須 |
| 7 | `DEVICE_METADATA\|x509` → `TELEMETRY\|certs` 未設定時 legacy フォールバック | どちらも未設定なら `--noTLS` 起動 | 設計上の縮退動作 |

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照 — Phase C (cross-table refs)

> **調査根拠**: `docker-sonic-telemetry/docker-telemetry-entry.sh`, `telemetry.sh`, `telemetry_vars.j2`, `gnmi_server/server.go` L380-660 精読 (2026-05-17)

`TELEMETRY` テーブルは YANG leafref を持たないが、実行時に以下のテーブルを暗黙参照する。

| 参照先 | DB | 参照方向 | 条件 | 証拠 |
|--------|-----|---------|------|------|
| `FEATURE\|telemetry.state` | CONFIG_DB | 読み取り (コンテナ起動制御) | 常時 | `docker-telemetry-entry.sh:40` |
| `DEVICE_METADATA\|localhost.x509` | CONFIG_DB | 読み取り (legacy 証明書フォールバック) | `TELEMETRY\|certs` 未設定時 | `telemetry_vars.j2:4`, `telemetry.sh:66-80` |
| `GNMI_CLIENT_CERT\|*` | CONFIG_DB | 読み取り (証明書 fingerprint チェック) | `user_auth=cert` 設定時 | `telemetry.sh:147-148` |
| `DEVICE_METADATA\|localhost.chassis_serial_number` | STATE_DB | 書き込み (シリアル番号更新) | watchdog オプション有効時 | `telemetry.sh:10-13` |
| CONFIG_DB Journal | CONFIG_DB | 書き込み (gNMI Set 変更ログ) | `save_on_set=true` 時 | `server.go:647-649` |

### FEATURE|telemetry — コンテナ起動前提

`docker-telemetry-entry.sh` L39-48 が `redis-cli -n 4 HGET "FEATURE|telemetry" state` でポーリングし、`state == "enabled"` でなければ supervisord を起動しない。`TELEMETRY` テーブルを読む前に `FEATURE|telemetry` が CONFIG_DB に存在していることが実質必須（YANG leafref なし — 実装上の暗黙依存）。

### DEVICE_METADATA|localhost.x509 — legacy 証明書フォールバック

`telemetry_vars.j2` L4 が `DEVICE_METADATA["x509"]` を参照する。`TELEMETRY|certs` が CONFIG_DB に存在しない場合、`telemetry.sh` L66-80 は `DEVICE_METADATA|x509.server_crt` / `server_key` / `ca_crt` を証明書パスとして使用する（legacy 経路）。どちらも未設定の場合は `--noTLS` で起動する。YANG leafref なし。

### GNMI_CLIENT_CERT — cert 認証時の動的参照

`user_auth=cert` を設定すると、`telemetry.sh` L147-148 が `--config_table_name GNMI_CLIENT_CERT` フラグを gnmi_server に渡す。gnmi_server が実行時に `GNMI_CLIENT_CERT` テーブルを参照してクライアント証明書の fingerprint チェックを行う。`GNMI_CLIENT_CERT` エントリが存在しない状態で `user_auth=cert` に切り替えると、接続時に認証失敗となる。

### SAI 参照

なし。telemetry (gnmi_server) は CONFIG_DB / STATE_DB / DATA_DB を gRPC/gNMI 経由でクライアントに公開するが、SAI/ASIC に直接アクセスしない。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動 (Phase D)

> **調査根拠**: `docker-sonic-telemetry/telemetry.sh`, `supervisord.conf`, `gnmi_server/server.go` L381-649, `telemetry/telemetry.go` L440-470 精読 (2026-05-17)

### autorestart=false — 起動失敗時にプロセスが再起動しない

`supervisord.conf` の `[program:telemetry]` は **`autorestart=false`** に設定されている。`telemetry.sh` がエラー終了しても supervisord は再起動を試みない。`dialout` も `dependent_startup_wait_for=telemetry:running` のため、telemetry が起動しなければ dial-out ストリーミングも動作しない。

障害検知: `supervisorctl status telemetry` が `EXITED` を返す。
復旧: フィールド修正後に `docker restart telemetry` または `systemctl restart telemetry`。

> evidence: `dockers/docker-sonic-telemetry/supervisord.conf:50-62`

### 設定値不正による起動失敗 (exitcode=2)

`telemetry.sh` は以下フィールドが正整数でない場合 `exit 2` で終了する:

| フィールド | 期待値 | エラーメッセージ (stderr) |
|-----------|--------|--------------------------|
| `TELEMETRY\|gnmi.port` | 正整数 | `Incorrect port value <PORT>, expecting positive integers` |
| `TELEMETRY\|gnmi.threshold` | 正整数 or 未設定 | `Incorrect threshold value, expecting positive integers` |
| `TELEMETRY\|gnmi.idle_conn_duration` | 正整数 or 未設定 | `Incorrect idle_conn_duration value, expecting positive integers` |

未設定 (`null` / キー不在) の場合は内部デフォルト値が使われるため不正扱いにならない。不正値を設定した場合のみ `exit 2` → supervisord は再起動しない。

> evidence: `dockers/docker-sonic-telemetry/telemetry.sh:83-87,109-115,123-130`

### 証明書ファイル不在・不正による起動失敗

`SrvAdvConfig()` が以下の条件でエラーを返し、gNMI サーバが起動しない:

| 条件 | エラーメッセージ |
|------|----------------|
| `server_crt` XOR `server_key` が空 | `"server certificate or key file path is empty"` |
| `server_crt` パスのファイルが存在しない | `"server certificate file stat error: <err>"` |
| `server_key` パスのファイルが存在しない | `"server key file stat error: <err>"` |
| `ca_crt` パスのファイルが存在しない | `"CA certificate file not found: <err>"` |
| `enable_crl=true` かつ CRL ディレクトリ不在 | `os.ReadDir error` |

> evidence: `gnmi_server/server.go:400-418`

**証明書内容不正の場合は自動回復**: `tls.LoadX509KeyPair()` が失敗すると `telemetry.go` は fsnotify で証明書ファイルの変更を待機するループに入り、ファイルが正しい内容に上書きされると自動でリトライする。この場合はプロセス再起動不要。

> evidence: `telemetry/telemetry.go:463-470`

### user_auth 不正値による起動失敗

`user_auth` に `"cert"`, `"password"`, `"jwt"`, `"none"`, `""` 以外の値を設定すると `AuthTypes.Set()` がエラーを返す:
```
Expecting one or more of 'cert', 'password' or 'jwt'
```
gnmi_server 起動時に検証されプロセスが終了する。`autorestart=false` のため再起動なし。

> evidence: `gnmi_server/server.go:315-327`

### ポート競合 — TCP リスナー縮退 (Warning のみ)

指定ポートへの `net.Listen("tcp", ...)` が失敗した場合、TCP リスナーを無効化して処理を続行する:
```
Failed to open listener port <port>: <err>; disabling TCP listener
```
UnixSocket も未設定の場合は `"no listener configured: port must be > 0 or unix_socket must be set"` エラーでサーバが起動しない。

> evidence: `gnmi_server/server.go:593-600, 643`

### save_on_set=true 時の dbus 失敗 — サイレント

`save_on_set=true` 設定時に gNMI Set RPC が完了した後 `SaveOnSetEnabled()` が dbus で `config save` を実行する。dbus 失敗はログ出力のみで Set RPC 自体は成功とみなされる。CONFIG_DB 変更が永続化されない (再起動で消える) サイレント障害となる。

```
Saving startup config failed to create dbus client: <err>
Saving startup config failed: <err>
```

> evidence: `gnmi_server/server.go:1054-1061`

### 障害サマリ

| 障害 | 検知方法 | 自動回復 | 手動回復 |
|------|----------|----------|---------|
| 不正フィールド値 (port 等) | `supervisorctl status` → EXITED | なし | `sonic-db-cli` 修正 → `docker restart telemetry` |
| 証明書ファイル不在 | `supervisorctl status` → EXITED | なし | ファイル配置 → `docker restart telemetry` |
| 証明書内容不正 | ログ: `could not load server key pair` | ✅ ファイル上書きで自動回復 | — |
| ポート競合 | `WARNING: Failed to open listener port` | なし (UDS のみで縮退動作) | ポート解放 → `docker restart telemetry` |
| save_on_set dbus 失敗 | ログのみ (`log.V(0)`) | なし | hostcfgd / dbus 確認 |

> **Evidence**: `dockers/docker-sonic-telemetry/supervisord.conf:50-62`; `telemetry.sh:83-130`; `gnmi_server/server.go:315-327,400-418,593-649,1054-1061`; `telemetry/telemetry.go:463-470`; 詳細 `meta/_intermediate/cdb-flow/telemetry-failure.md`
<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

`telemetry` プロセス (`sonic-gnmi`) および `telemetry.sh` 起動スクリプトに存在する、CONFIG_DB / YANG で管理されないハードコード定数の一覧。

### プロセス起動フラグデフォルト値 (telemetry.go)

| 定数 / フラグ | 値 | 用途 | ソース |
|--------------|-----|------|--------|
| `--unix_socket` | `/var/run/gnmi/gnmi.sock` | TLS なしローカル接続用 UNIX ドメインソケットパス | `telemetry.go:175` |
| `--jwt_refresh_int` | `900` 秒 | JWT トークンのリフレッシュ可能期間（期限の 15 分前から可能） | `telemetry.go:183` |
| `--jwt_valid_int` | `3600` 秒 | JWT トークン有効期間（1 時間） | `telemetry.go:184` |
| `--threshold` | `100` | 最大クライアント接続数 | `telemetry.go:187` |
| `--idle_conn_duration` | `5` 秒 | アイドル接続を閉じるまでの時間 | `telemetry.go:190` |
| `--crl_expire_duration` | `86400` 秒 | CRL キャッシュ有効期限（24 時間） | `telemetry.go:194` |
| `--img_dir` | `/tmp/host_tmp` | SetPackage 等で転送されるイメージの一時ディレクトリ | `telemetry.go:195` |
| `--max_recv_msg_size` | `4 MiB` (4\*1024\*1024) | gRPC 受信メッセージ最大サイズ | `telemetry.go:209` |
| `--max_send_msg_size` | `4 MiB` (4\*1024\*1024) | gRPC 送信メッセージ最大サイズ | `telemetry.go:210` |

> これらは YANG に定義がなく CONFIG_DB への書き込みも行われない。変更には telemetry.sh の直接編集が必要。

### 証明書シンボリックリンクパス

| フラグ | デフォルトパス | ソース |
|--------|--------------|--------|
| `--ca_cert_lnk` | `/keys/ca_cert.lnk` | `telemetry.go:199` |
| `--server_cert_lnk` | `/keys/server_cert.lnk` | `telemetry.go:200` |
| `--server_key_lnk` | `/keys/server_key.lnk` | `telemetry.go:201` |
| `--cert_crl_dir` | `/mtls/crl` | `telemetry.go:203` |
| `--grpc_meta` | `/keys/grpc-version.json` | `telemetry.go:204` |
| `--authz_meta` | `/keys/authz-version.json` | `telemetry.go:205` |
| `--authorization_policy_file` | `/keys/authorization_policy.json` | `telemetry.go:207` |

### TLS ハードコードパラメータ

| 定数 | 値 | ソース |
|------|----|--------|
| `MinVersion` | `TLS 1.2` | `telemetry.go:482` |
| `CurvePreferences` | P521, P384, P256（強度順） | `telemetry.go:484` |
| `CipherSuites` | 6 ECDHE スイート（AES-256-GCM / ChaCha20 / AES-128-GCM） | `telemetry.go:486-492` |
| `SessionTicketsDisabled` | `true`（前方秘匿性保持） | `telemetry.go:483` |
| keepalive `MinTime` | `20` 秒（クライアント ping 許容最短間隔） | `telemetry.go:547` |
| keepalive `PermitWithoutStream` | `true` | `telemetry.go:548` |

### telemetry.sh フォールバック値（CONFIG_DB 非依存）

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| フォールバックポート | `8080` | `TELEMETRY\|gnmi` キーが CONFIG_DB にない場合 | `telemetry.sh:85` |
| フォールバックログレベル | `2` | `log_level` が非数値または未設定の場合 | `telemetry.sh:104` |
| フォールバック threshold | `100` | `threshold` が null または未設定の場合 | `telemetry.sh:121` |
| フォールバック idle_conn_duration | `5` 秒 | `idle_conn_duration` が null または未設定の場合 | `telemetry.sh:134` |
| GNMI_CLIENT_CERT テーブル名 | `"GNMI_CLIENT_CERT"` | `user_auth=cert` 時に `--config_table_name` へ渡す固定テーブル名 | `telemetry.sh:148` |

> **evidence**: `sonic-gnmi/telemetry/telemetry.go@eb635b7679b260c3fd0786a6d0734fc8e82c9a22` L171-215, L482-549; `sonic-buildimage/dockers/docker-sonic-telemetry/telemetry.sh@9ea932ec2e18f35e58268ec2e4456b1d4afd65cd` L85-158
<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込・副次効果 (Phase F)

<!-- evidence: sonic-gnmi/gnmi_server/server.go@eb635b7679b260c3fd0786a6d0734fc8e82c9a22 L1051-1068 / gnmi_server/gnsi_certz.go@eb635b7679b260c3fd0786a6d0734fc8e82c9a22 L925-990 / dockers/docker-sonic-telemetry/telemetry.sh@9ea932ec2e18f35e58268ec2e4456b1d4afd65cd L3-22 -->

### ファイルシステム副次効果 — TLS 証明書シンボリックリンク

`SrvAdvConfig()` は起動時に `TELEMETRY|certs` で指定された証明書パスへのシンボリックリンクを生成する。

| 生成パス | 内容 | 条件 |
|---------|------|------|
| `/keys/server_cert.lnk` → `<server_crt>` | サーバ証明書への symlink | `server_crt` + `server_key` が両方設定 |
| `/keys/server_key.lnk` → `<server_key>` | サーバ秘密鍵への symlink | 同上 |
| `/keys/ca_cert.lnk` → `<ca_crt>` | CA 証明書への symlink | `ca_crt` が設定されている場合 |

既存の symlink を削除してから新規作成するアトミック更新で実行され、失敗時は旧 symlink を復元する。gRPC の TLS ハンドシェイク時は `tls.LoadX509KeyPair(cfg.SrvCertLnk, cfg.SrvKeyLnk)` で symlink 経由の証明書を参照するため、symlink の差し替えのみで証明書ローテーションが可能。

> evidence: `gnmi_server/gnsi_certz.go:925-990`

### ファイルシステム副次効果 — config_db.json 保存 (save_on_set=true)

`TELEMETRY|gnmi.save_on_set == "true"` の場合、gNMI Set RPC 完了後に `SaveOnSetEnabled()` が dbus 経由で `/etc/sonic/config_db.json` を上書き保存する。失敗時はログ出力のみで Set RPC 自体は成功とみなされる（CONFIG_DB 変更が永続化されないサイレント障害）。

> evidence: `gnmi_server/server.go:1051-1068`

### STATE_DB 副次書込 — chassis_serial_number (watchdog オプション)

環境変数 `TELEMETRY_WATCHDOG_SERIALNUMBER_PROBE_ENABLED=true` が設定されている場合のみ、`telemetry.sh` 起動時に `decode-syseeprom -s` でシリアル番号を取得し、値が異なる場合のみ STATE_DB に書込む。TELEMETRY テーブル内容とは独立した副次効果。

| DB | テーブル | フィールド | 書込条件 |
|----|---------|-----------|---------|
| STATE_DB | `DEVICE_METADATA\|localhost` | `chassis_serial_number` | watchdog オプション有効かつシリアル番号変更時 |

> evidence: `dockers/docker-sonic-telemetry/telemetry.sh:3-22`

### APPL_DB / COUNTERS_DB — 書込なし

`gnmi_server` および `telemetry.sh` は APPL_DB / COUNTERS_DB への直接書込を行わない。内部メトリクス（Get/Set/Subscribe カウンタ）はプロセス内共有メモリで管理され DB には書込まれない。

> evidence: `common_utils/context.go:147-180`; `common_utils/shareMem.go`

### 副次効果サマリ

| 種別 | 対象 | 条件 |
|------|------|------|
| ファイル書込 (symlink) | `/keys/server_cert.lnk`, `/keys/server_key.lnk`, `/keys/ca_cert.lnk` | TLS 設定あり（起動時一回） |
| ファイル書込 | `/etc/sonic/config_db.json` | `save_on_set=true` かつ gNMI Set RPC 成功 |
| STATE_DB 書込 | `DEVICE_METADATA\|localhost.chassis_serial_number` | watchdog オプション有効時のみ |
| APPL_DB 書込 | なし | — |
| COUNTERS_DB 書込 | なし | — |

> **詳細**: `meta/_intermediate/cdb-flow/telemetry-side-effects.md`
<!-- /side-effects -->

<!-- glossary-links-injected: 896d391185a9 -->
