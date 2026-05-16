# RESTAPI コード由来デフォルト調査 (Task F Phase A)

target page: `docs/reference/config-db/restapi.md`

## 調査対象ソース

- `sonic-buildimage/dockers/docker-sonic-restapi/restapi.sh` (`go-server-server` 起動ラッパ)
- `sonic-buildimage/dockers/docker-sonic-mgmt-framework/rest-server.sh` (`rest_server` 起動ラッパ、sonic-mgmt-framework 系)
- `sonic-buildimage/dockers/docker-sonic-mgmt-framework/mgmt_vars.j2`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-restapi.yang`

SHA: `sonic-buildimage` = `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

## 検出した code-derived デフォルト

### 1. `log_level` fallback = `trace` (docker-sonic-restapi)

`restapi.sh:33-38`:

```bash
LOG_LEVEL=`sonic-cfggen -d -v "RESTAPI['config']['log_level']"`
if [ ! -z $LOG_LEVEL ]; then
    RESTAPI_ARGS+=" -loglevel=$LOG_LEVEL"
else
    RESTAPI_ARGS+=" -loglevel=trace"
fi
```

YANG `sonic-restapi.yang:68-` の `log_level` には `default` 宣言なし。
従って `RESTAPI|config:log_level` 未設定時はラッパスクリプトの fallback `trace` が使われる。
YANG とのギャップ: YANG 側は無宣言、コード fallback = `trace` (デバッグ寄り)。

### 2. `allow_insecure` 起動引数 fallback = `-enablehttp=false`

`restapi.sh:13-17`:

```bash
if [[ $allow_insecure == 'true' ]]; then
    RESTAPI_ARGS=" -enablehttp=true"
else
    RESTAPI_ARGS=" -enablehttp=false"
fi
```

YANG `default false` (`sonic-restapi.yang:77`) と整合。CONFIG_DB absent / `false` のどちらでも HTTP 平文は無効になる。

### 3. `client_auth` 起動条件 — `true` のみで cert ロードに進む

`restapi.sh:10`: `if [[ $client_auth == 'true' ]]; then`
YANG `default true` (`sonic-restapi.yang:64`) と整合。`client_auth=false` または未設定（無効化）だと cert チェックループが進まず `go-server-server` は起動しない（実質 client_auth=true 前提のサービス）。

### 4. mgmt-framework 側 `CLIENT_AUTH` default = `user` (REST_SERVER テーブル経由)

`rest-server.sh:20`: `CLIENT_AUTH=$(echo $REST_SERVER | jq -r '.client_auth // "user"')`
`rest-server.sh:29-31`: 再度 `[ -z "$CLIENT_AUTH" ]` → `"user"` を fallback。

注: これは `RESTAPI` テーブル本体ではなく `REST_SERVER`（mgmt_vars.j2 経由）の話だが、ページの「purpose 全体」が REST API である以上、user_auth モード fallback が code-only で担保される点は記録しておく。本ページの Phase 8 表で `client_auth==user_auth` を扱っているため整合性あり。

### 5. mgmt-framework 側 cert path fallback = `/tmp/cert.pem` `/tmp/key.pem`

`rest-server.sh:45-50`:

```bash
if [ -z $SERVER_CRT ] && [ -z $SERVER_KEY ]; then
    echo "Generating temporary TLS server certificate ..."
    (cd /tmp && /usr/sbin/generate_cert --host="localhost,127.0.0.1")
    SERVER_CRT=/tmp/cert.pem
    SERVER_KEY=/tmp/key.pem
fi
```

CONFIG_DB に server_crt/server_key 未設定 → `/tmp/cert.pem` `/tmp/key.pem` 自己生成 cert に fallback。
YANG にはこの fallback 定義なし。code-only。

## 既存ページ block との整合

- `<!-- value-behavior -->` には `client_auth`/`log_level`/`allow_insecure` の値別挙動が既に記載済み
- `<!-- defaults -->` block は未挿入 → 今回追加対象
- `cdb-exceptions` `derivation` `handler-branching` `runtime-trace` `entry-points` 等は保持

## 配置位置

`<!-- value-behavior -->` block の直後、`<!-- cdb-exceptions -->` の前に `<!-- defaults --> ... <!-- /defaults -->` を挿入する。
