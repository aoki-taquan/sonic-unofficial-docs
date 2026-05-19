---
title: P4RT テーブル (PINS p4rt 設定)
description: "P4RT テーブル — PINS (P4 Integrated Network Stack) の P4Runtime gRPC サーバ設定。ポート・TLS 証明書・認可ポリシー・genetlink オプションを保持し、p4rt コンテナ起動時に読み込まれる。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-buildimage
    path: dockers/docker-sonic-p4rt/p4rt.sh
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: dockers/docker-sonic-p4rt/p4rt_vars.j2
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/SONiC
    path: doc/pins/p4rt_app_hld.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - P4RT
    - DEVICE_METADATA
  yang: []
---

# P4RT テーブル（PINS p4rt 設定）

## 概要

[PINS](../../reference/glossary.md#term-pins)（P4 Integrated Network Stack）の **P4Runtime gRPC サーバ設定**を保持するテーブル[^1]。
`p4rt` コンテナ（`docker-sonic-p4rt`）が起動時に [CONFIG_DB](../../reference/glossary.md#term-config_db) を一回読み込み、
gRPC ポート・TLS 証明書・認可ポリシー・genetlink 設定などを `p4rt` バイナリの起動引数に変換する。

専用 YANG モデルは存在しない。スキーマ強制は `p4rt.sh` 内の `jq` 参照のみで実装される。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>P4RT")]
  P4RT["p4rt (docker-sonic-p4rt)"]
  CDB --> P4RT
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
P4RT|certs       # TLS 証明書設定
P4RT|p4rt_app    # P4Runtime gRPC アプリ設定
```

## P4RT|certs

| フィールド | 型 | 説明 |
|-----------|----|------|
| `server_crt` | string (パス) | サーバ証明書ファイルパス |
| `server_key` | string (パス) | サーバ秘密鍵ファイルパス |
| `ca_crt` | string (パス) | CA 証明書ファイルパス（mTLS 用） |
| `cert_crl_dir` | string (パス) | CRL（Certificate Revocation List）ディレクトリ |

## P4RT|p4rt_app

| フィールド | 型 | 説明 |
|-----------|----|------|
| `port` | string (数字) | P4Runtime gRPC 待受 TCP ポート |
| `use_genetlink` | boolean string | Linux Generic Netlink (genetlink) 経由のパケット I/O を使用するか |
| `use_port_ids` | boolean string | ポート識別に SONiC port ID を使用するか（デフォルト: ifindex） |
| `save_forwarding_config_file` | string (パス) | P4Runtime forwarding config を保存するファイルパス |
| `authz_policy` | string (パス) | 認可ポリシー JSON ファイルパス |
| `p4rt_unix_socket` | string (パス) | UNIX ドメインソケットパス（gRPC over UDS） |

## 購読者

- `p4rt` コンテナ（`docker-sonic-p4rt`）: 起動時に `p4rt.sh` → `sonic-cfggen` → `p4rt_vars.j2` 経由で読み込む

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `DEVICE_METADATA` (`x509` サブキー — TLS fallback)
- YANG モデル: なし（P4RT 専用 YANG 未定義）
- 関連 CLI: なし（config load / 手動 DB 書き込み）

<!-- ref-triangle:start -->

## 関連リファレンス

- HLD: [PINS（P4 Integrated Network Stack）](../../management/pins-hld.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: 起動スクリプト: `p4rt.sh`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/dockers/docker-sonic-p4rt/p4rt.sh>

<!-- ops-hint -->
## 運用ヒント

### 典型値

```json
"P4RT": {
  "certs": {
    "server_crt": "/keys/server_cert.lnk",
    "server_key": "/keys/server_key.lnk",
    "ca_crt": "/keys/ca_cert.lnk",
    "cert_crl_dir": "/keys/crl"
  },
  "p4rt_app": {
    "port": "9559",
    "use_genetlink": "false",
    "use_port_ids": "false",
    "save_forwarding_config_file": "/etc/sonic/p4rt_forwarding_config.pb.txt",
    "authz_policy": "/keys/authorization_policy.json"
  }
}
```

### よくある誤設定

- `server_crt` / `server_key` のいずれか一方のみ設定すると insecure モードになる（両方必須）。
- `P4RT|certs` を未設定のまま `DEVICE_METADATA|localhost|x509` にも証明書がない場合、
  自動的に `--use_insecure_server_credentials` で起動する（平文 gRPC）。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'P4RT|p4rt_app'
sonic-db-cli CONFIG_DB hgetall 'P4RT|certs'
systemctl status p4rt
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `use_genetlink` (boolean string)

| 値 | 挙動 |
|----|------|
| `"true"` | `--use_genetlink=true` を p4rt バイナリに渡す。Linux genetlink 経由でパケット I/O |
| `"false"` / 未設定 | genetlink 引数なし → バイナリデフォルト（false） |

### `use_port_ids` (boolean string)

| 値 | 挙動 |
|----|------|
| `"true"` | `--use_port_ids=true`。SONiC port ID で P4Runtime ポート識別 |
| `"false"` / 未設定 | ifindex ベースのポート識別（バイナリデフォルト） |

### TLS / 証明書フォールバック

| 条件 | 挙動 |
|------|------|
| `P4RT\|certs` に `server_crt` + `server_key` あり | TLS 有効 |
| `P4RT\|certs` が存在せず `DEVICE_METADATA\|localhost\|x509` に cert あり | x509 設定を代用 |
| どちらも未設定 | `--use_insecure_server_credentials`（平文 gRPC）|
| `ca_crt` あり | mTLS 有効 |
| `cert_crl_dir` あり (かつ `ca_crt` あり) | CRL チェック有効 |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

- **起動時のみ参照**: `p4rt` コンテナは起動時に一回だけ CONFIG_DB を読み込む。設定変更は `systemctl restart p4rt` まで反映されない。
- **YANG モデルなし**: スキーマ検証がない。不明フィールドは `jq` が `// empty` として無視し、対応するバイナリ引数が渡されない。
- **`server_crt` / `server_key` 片方のみ**: 両方揃わないと `--use_insecure_server_credentials` にフォールバックする（証明書エラーではなく insecure 起動）。
- **`authz_policy` 未設定**: 認可ポリシーなし（全 P4RT クライアントが管理者相当で接続可能）。
- **`p4rt_unix_socket` 設定時**: ソケットディレクトリが存在しない場合、`mkdir -p` で自動作成する（`p4rt.sh` L92-94）。

<!-- /cdb-exceptions -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- `p4rt.sh` が `sonic-cfggen -d -t p4rt_vars.j2` で CONFIG_DB を読み込み、JSON として `P4RT` テーブルを展開。

### 段階 2: CFG → バイナリ引数変換

- `p4rt.sh` が各フィールドを `jq -r '.field // empty'` で取得し、非空の場合のみ `p4rt` バイナリの引数に追加。
- APP_DB / STATE_DB への書き込みなし。

### 段階 3: p4rt バイナリ起動

- `exec /usr/local/bin/p4rt ${P4RT_ARGS}` で P4Runtime gRPC サーバが起動。
- SAI 経由で ASIC の P4 パイプラインを制御。

### 段階 4: タイミング + 副作用

- 設定変更は `systemctl restart p4rt` 後に有効（コンテナ再起動が必要）。
- P4Runtime クライアント（コントローラ）は再接続が必要。

<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

### CLI

- 専用 CLI なし — `config load` または手動 `sonic-db-cli` で書き込む

### minigraph / sonic-cfggen

- なし（`minigraph.py` に P4RT テーブル生成処理なし）

### REST / gNMI

- なし（YANG モデル未定義のため REST/gNMI トランスフォーマーなし）

### db_migrator

- なし

### ビルド時デフォルト (build-time default)

- `config_db.json` への手動追加のみ（`p4rt_app_hld.md` L172 参照）

### ハードコードデフォルト / ランタイム注入

- なし（全フィールド任意）

<!-- /entry-points -->

<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

なし。`P4RT` テーブルはランタイム書き込みなし。

### Phase 7: 条件付き登録

| 条件 | 動作 |
|------|------|
| `P4RT|certs` が存在する | certs フィールドを TLS 設定に使用 |
| `P4RT|certs` が存在しない | `DEVICE_METADATA|localhost|x509` を代わりに参照（`p4rt_vars.j2` L4） |

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler 内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---------|---------|------|----------|
| `p4rt.sh` | `server_crt` + `server_key` あり | TLS 有効起動 | `p4rt.sh` L22-27 |
| `p4rt.sh` | certs なし / 不完全 | `--use_insecure_server_credentials` | `p4rt.sh` L55-56 |
| `p4rt.sh` | `ca_crt` あり | mTLS 有効 (`--ca_certificate_file`) | `p4rt.sh` L30-37 |
| `p4rt.sh` | `cert_crl_dir` あり | CRL チェック有効 (`--cert_crl_dir`) | `p4rt.sh` L34-37 |
| `p4rt.sh` | `authz_policy` あり | `--authz_policy_enabled --authorization_policy_file=<path>` | `p4rt.sh` L60-63 |
| `p4rt.sh` | `port` あり | `--p4rt_grpc_port=<port>` | `p4rt.sh` L66-69 |
| `p4rt.sh` | `use_genetlink` あり | `--use_genetlink=<val>` | `p4rt.sh` L72-75 |
| `p4rt.sh` | `use_port_ids` あり | `--use_port_ids=<val>` | `p4rt.sh` L78-81 |
| `p4rt.sh` | `save_forwarding_config_file` あり | `--save_forwarding_config_file=<path>` | `p4rt.sh` L84-87 |
| `p4rt.sh` | `p4rt_unix_socket` あり | `--p4rt_unix_socket=<path>` + ディレクトリ作成 | `p4rt.sh` L90-97 |

<!-- /handler-branching -->

<!-- defaults -->
## フィールドデフォルト (コード由来)

### YANG デフォルト vs 実行時 fallback

P4RT テーブルには専用 YANG モデルが存在しない。全デフォルトは `p4rt.sh` のランタイム動作で決まる。

### P4RT|p4rt_app

| フィールド | HLD 記述値 | 未設定時の動作 | 設定元 |
|-----------|-----------|--------------|--------|
| `port` | `"9559"` | `--p4rt_grpc_port` 引数なし → バイナリ内デフォルト `9559` | `p4rt.sh` L66-69; `p4rt_app_hld.md` L184 |
| `use_genetlink` | `"false"` | `--use_genetlink` 引数なし → バイナリ内デフォルト `false` | `p4rt.sh` L72-75; `p4rt_app_hld.md` L185 |
| `use_port_ids` | `"false"` | `--use_port_ids` 引数なし → バイナリ内デフォルト `false` | `p4rt.sh` L78-81; `p4rt_app_hld.md` L186 |
| `save_forwarding_config_file` | `/etc/sonic/p4rt_forwarding_config.pb.txt` | 引数なし → 転送設定ファイルへの保存なし | `p4rt.sh` L84-87 |
| `authz_policy` | `/keys/authorization_policy.json` | 引数なし → 認可ポリシー無効（全クライアントフルアクセス） | `p4rt.sh` L60-63 |
| `p4rt_unix_socket` | (HLD 未記載) | 引数なし → UNIX socket リスナーなし | `p4rt.sh` L90-97 |

### P4RT|certs

| フィールド | HLD 記述値 | 未設定時の動作 | 設定元 |
|-----------|-----------|--------------|--------|
| `server_crt` | `/keys/server_cert.lnk` | 片方でも未設定 → insecure モード | `p4rt.sh` L22-27 |
| `server_key` | `/keys/server_key.lnk` | 片方でも未設定 → insecure モード | `p4rt.sh` L22-27 |
| `ca_crt` | `/keys/ca_cert.lnk` | 未設定 → mTLS 無効 | `p4rt.sh` L30-32 |
| `cert_crl_dir` | `/keys/crl` | 未設定 → CRL チェックなし | `p4rt.sh` L33-37 |

> **隠れデフォルト（YANG 未定義）**: `P4RT|certs` エントリが CONFIG_DB に存在しない場合、
> `p4rt_vars.j2` L4 が `DEVICE_METADATA|localhost|x509` にフォールバックする。
> `x509` も未設定であれば `--use_insecure_server_credentials` で平文 gRPC 起動（`p4rt.sh` L56）。
> この動作は YANG モデルに記述されておらず、`p4rt_vars.j2` / `p4rt.sh` のみで実装される。

### コード由来デフォルトの乖離サマリ

| フィールド | HLD 記述 | 実装 | 乖離 |
|-----------|---------|------|------|
| `port` | `"9559"` | 未設定時もバイナリが 9559 を使う | 実質なし |
| `use_genetlink` | `"false"` | 未設定時もバイナリが false を使う | 実質なし |
| `use_port_ids` | `"false"` | 未設定時もバイナリが false を使う | 実質なし |
| TLS なし時 | (明示なし) | 自動的に `--use_insecure_server_credentials` | HLD に明記なし（隠れ動作） |
| `P4RT|certs` 非存在 | (明示なし) | `DEVICE_METADATA|x509` へフォールバック | HLD に明記なし（隠れ動作） |

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

`p4rt` コンテナは起動時に `sonic-cfggen -d -t p4rt_vars.j2` で CONFIG_DB を**一度だけ**読み込む。
このため `P4RT|certs` / `P4RT|p4rt_app` の書込み順と存在タイミングがコンテナの TLS モード・機能設定を確定させる。

<!-- evidence: meta/_intermediate/cdb-flow/pin-config-ordering.md -->

### 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | CONFIG_DB への書込み → `p4rt` コンテナ起動 | **強制先行** | 起動後の DB 変更は `systemctl restart p4rt` まで無効 |
| 2 | `P4RT\|certs` 存否 → `DEVICE_METADATA\|localhost\|x509` フォールバック参照 | 条件分岐（先行優先） | `P4RT\|certs` が存在する場合、`x509` は参照されない |
| 3 | `server_crt` + `server_key` の同時存在 → TLS 有効化 | **同時必須** | 片方のみ書込み時に起動すると平文 gRPC になる |
| 4 | `ca_crt` 存在 → `cert_crl_dir` が有効化 | **先行必須** | `ca_crt` なしで `cert_crl_dir` を設定しても CRL チェックは機能しない |

### 主要な制約詳細

**起動時単回読込み (依存 #1)**: `p4rt.sh` L13 の `sonic-cfggen -d -t ${P4RT_VARS_FILE}` は**コンテナ起動時に 1 回だけ**実行される。`p4rt` プロセスは DB 変更を watch しない。したがって `P4RT|certs` や `P4RT|p4rt_app` の変更は `systemctl restart p4rt` によるコンテナ再起動後にのみ反映される。証明書の更新・ポート変更・設定追加を行った場合は必ず再起動が必要（evidence: `p4rt.sh:L13`）。

**`P4RT|certs` → `DEVICE_METADATA|x509` フォールバック順序 (依存 #2)**: `p4rt_vars.j2` L2–4 は `P4RT["certs"]` を先に評価し、存在しない場合のみ `DEVICE_METADATA["x509"]` を代替として `p4rt.sh` に渡す。`p4rt.sh` L21–57 も同様の条件分岐で `${CERTS}` 非空を優先する。`P4RT|certs` が CONFIG_DB に存在する限り、`DEVICE_METADATA|localhost|x509` の内容は完全に無視される（evidence: `p4rt_vars.j2:L2–4`, `p4rt.sh:L21–57`）。

**`server_crt` / `server_key` のアトミック書込み (依存 #3)**: `p4rt.sh` L24–25 は `server_crt` と `server_key` の**両方**が非空かどうかをチェックし、いずれか一方でも空の場合は `--use_insecure_server_credentials` を付与する（エラーにはならない）。TLS を有効化するには、2 つのフィールドを**同一トランザクションで書き込んだ後**にコンテナを起動する必要がある（evidence: `p4rt.sh:L22–28`）。

**`ca_crt` → `cert_crl_dir` の階層依存 (依存 #4)**: CRL チェックを有効にする `--cert_crl_dir` 引数は `p4rt.sh` L33–36 の `ca_crt` 存在ブロック内でのみ評価される。`ca_crt` が未設定の場合、`cert_crl_dir` をどれだけ設定しても CRL チェックは起動せず、引数も付与されない（evidence: `p4rt.sh:L30–37`）。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

P4RT テーブルには専用 YANG モデルが存在しないため leafref は一切なし。以下はすべてスクリプトレベルの暗黙参照。

<!-- evidence: meta/_intermediate/cdb-flow/pin-config-cross-refs.md -->

| 参照先テーブル / リソース | 参照方向 | 条件 | 参照元 evidence |
|--------------------------|---------|------|----------------|
| `DEVICE_METADATA\|localhost\|x509` | 読み取り（TLS 代替設定） | `P4RT\|certs` が CONFIG_DB に存在しない場合のみ。`P4RT\|certs` が存在すれば完全に無視される | `p4rt_vars.j2:L4`, `p4rt.sh:L38–56` |
| ファイルシステム（証明書・ソケットパス） | ランタイム参照（パス解決） | 各 string フィールドに設定されたパスをバイナリ起動引数に変換。存在チェックなし（`p4rt_unix_socket` のディレクトリのみ `mkdir -p` 自動作成） | `p4rt.sh:L21–97` |

!!! note "orch レベルの参照なし"
    `p4rt` コンテナは orchagent (`sonic-swss`) とは独立して動作し、APP_DB / STATE_DB の生成・購読を行わない。
    `sonic-swss/orchagent/p4orch/` の各コンポーネントは APPL_DB の `P4RT_*` テーブルを参照するが、
    CONFIG_DB の `P4RT` テーブルを直接参照する経路は存在しない。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動マトリクス (Phase D)

ソース: `sonic-net/sonic-buildimage/dockers/docker-sonic-p4rt/p4rt.sh` (コミット `9ea932ec`)

`p4rt` テーブルは orchagent ではなく `p4rt.sh` スクリプトが起動時単回読込みするため、失敗は「サイレントフォールバック」または「起動中断」の二択になる。

<!-- evidence: meta/_intermediate/cdb-flow/pin-config-failure.md -->

### 失敗挙動マトリクス

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `p4rt_vars.j2` テンプレートファイル不在 | `p4rt.sh:L6–9` | `exit 1` — gRPC サーバ起動せず (`systemctl failed`) | `"P4rt vars template file not found"` を stdout | `p4rt.sh:L8` |
| `server_crt` または `server_key` が空 | `p4rt.sh:L24–25` | `--use_insecure_server_credentials` で平文 gRPC 起動（エラーなし） | なし | `p4rt.sh:L25` |
| `P4RT\|certs` も `DEVICE_METADATA\|localhost\|x509` も不在 | `p4rt.sh:L55–57` | `--use_insecure_server_credentials` で平文 gRPC 起動（エラーなし） | なし | `p4rt.sh:L56` |
| `ca_crt` なしで `cert_crl_dir` のみ設定 | `p4rt.sh:L30–37` | `cert_crl_dir` が無視され CRL チェックなしで TLS 起動 | なし | `p4rt.sh:L30–37` |
| `p4rt_unix_socket` ディレクトリ不在 | `p4rt.sh:L92–96` | `mkdir -p` で自動作成（権限不足時は p4rt バイナリが socket bind エラー） | なし（mkdir 失敗時はバイナリ側でエラー） | `p4rt.sh:L94–95` |
| 未知フィールド / typo フィールド | 各 `jq -r '.field // empty'` | 該当引数なしで起動（サイレント無視）— YANG モデルなしのため CLI 事前バリデーションもなし | なし | `p4rt.sh:L60–97` |

### 補足

**テンプレートファイル不在のみが `exit 1` となる唯一の hard failure**。それ以外の設定誤り（証明書欠如・フィールド typo）はすべてサイレントフォールバックであり、`p4rt` コンテナ自体は起動してしまう。意図しない平文 gRPC 起動を検知するには `systemctl status p4rt` の起動引数を確認するか、`p4rt` プロセスの `/proc/<pid>/cmdline` で `--use_insecure_server_credentials` の有無を確認する必要がある。

<!-- /failure -->

<!-- hardcoded-constants -->
## ハードコード定数 (Phase E)

<!-- evidence: meta/_intermediate/cdb-flow/pin-config-constants.md -->
<!-- source: sonic-net/sonic-buildimage/dockers/docker-sonic-p4rt/p4rt.sh (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd) -->
<!-- source: sonic-net/sonic-buildimage/dockers/docker-sonic-p4rt/p4rt_vars.j2 (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd) -->

`p4rt.sh` および `p4rt_vars.j2` に含まれるハードコード定数。いずれも CONFIG_DB / YANG では設定不可。

| 定数 | 値 | 定義箇所 | 用途 |
|------|----|---------|------|
| `EXIT_P4RT_VARS_FILE_NOT_FOUND` | `1` | `p4rt.sh:L3` | テンプレートファイル不在時の exit code。supervisord / 配備スクリプトが起動失敗を検知するために参照する |
| `P4RT_VARS_FILE` | `/usr/share/sonic/templates/p4rt_vars.j2` | `p4rt.sh:L4` | CONFIG_DB → 起動引数変換テンプレートのハードコードパス。変更不可（スクリプト内 `readonly`） |
| `--use_insecure_server_credentials` | ― (引数文字列リテラル) | `p4rt.sh:L25,L42,L56` | 証明書設定が不完全または全くない場合のデフォルトフォールバック引数。3 経路すべてで同じ文字列が使用される |
| `"certs"` | ― (サブキー識別子) | `p4rt_vars.j2:L2` | `P4RT` テーブルの証明書サブキー名。YANG モデル外のリテラル |
| `"p4rt_app"` | ― (サブキー識別子) | `p4rt_vars.j2:L3` | `P4RT` テーブルのアプリ設定サブキー名。YANG モデル外のリテラル |
| `"x509"` | ― (サブキー識別子) | `p4rt_vars.j2:L4` | `DEVICE_METADATA` テーブルのフォールバック証明書サブキー名。YANG モデル外のリテラル |

### 定数の影響詳細

**`P4RT_VARS_FILE` のハードコード**: `p4rt.sh` L4 で `readonly` 宣言されており、実行時の変更は不可。パスを変更するにはイメージの再ビルドが必要。テンプレートファイルが `/usr/share/sonic/templates/p4rt_vars.j2` に存在しない場合、`exit ${EXIT_P4RT_VARS_FILE_NOT_FOUND}` (= `exit 1`) で即終了し、gRPC サーバは起動しない。

**フォールバック文字列リテラル (`--use_insecure_server_credentials`)**: `p4rt.sh` に 3 箇所（L25, L42, L56）同じ文字列リテラルが記述されている。`server_crt` / `server_key` のいずれかが空の場合（L25）、`X509` フォールバックでも同じ条件（L42）、または `P4RT|certs` も `DEVICE_METADATA|localhost|x509` も存在しない場合（L56）に付与される。いずれの場合もエラーなしで平文 gRPC 起動となる。

**サブキー識別子のリテラル固定**: `p4rt_vars.j2` の `"certs"`、`"p4rt_app"`、`"x509"` はすべて文字列リテラルとして固定されており、YANG モデルに対応する `key` 定義は存在しない。CONFIG_DB のキー名がこれらのリテラルと一致しない場合、`jq -r '.field // empty'` が空文字列を返してサイレントに無視される（CLI の事前バリデーションもなし）。

### YANG 定義との乖離

専用 YANG モデルが存在しないため、上記の定数・キー名・フォールバック動作はすべてスクリプトレベルのみで実装される。gRPC デフォルトポート `9559` は `p4rt` バイナリ内部のデフォルトであり、`p4rt.sh` には記述されない（CONFIG_DB に `port` フィールドがなければ `--p4rt_grpc_port` 引数自体を渡さない）。

<!-- /hardcoded-constants -->

<!-- glossary-links-injected -->
