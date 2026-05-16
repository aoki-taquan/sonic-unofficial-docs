# GNMI / GNMI_CLIENT_CERT フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14  
対象テーブル: CONFIG_DB `GNMI` / `GNMI_CLIENT_CERT`

## 調査対象ファイル

- `sonic-gnmi/telemetry/telemetry.go` — `setupFlags()` CLI フラグ定義 (デフォルト値含む)
- `sonic-buildimage/dockers/docker-sonic-gnmi/gnmi-native.sh` — ConfigDB → CLI 引数変換ロジック
- `sonic-buildimage/dockers/docker-sonic-gnmi/telemetry_vars.j2` — ConfigDB Jinja2 テンプレート
- `sonic-gnmi/gnmi_server/clientCertAuth.go` — `PopulateAuthStructByCommonName()` (GNMI_CLIENT_CERT 読み出し)
- `sonic-buildimage/dockers/docker-telemetry-sidecar/systemd_stub.py` — GNMI_CLIENT_CERT 書き込みロジック
- `sonic-utilities/scripts/db_migrator.py` — `migrate_gnmi()` (TELEMETRY → GNMI マイグレーション)

---

## テーブル構造

### GNMI|gnmi エントリ

gNMI サーバの動作パラメータを格納する。

### GNMI|certs エントリ

TLS 証明書ファイルパスを格納する。

### GNMI_CLIENT_CERT|`<cname>` エントリ

クライアント証明書の CN (Common Name) と認可ロールのマッピング。  
`gnmi-native.sh` で `user_auth=cert` 時に `--config_table_name GNMI_CLIENT_CERT` として参照される。

---

## フィールド別 暗黙デフォルト

### GNMI|gnmi — `port`

**コード由来デフォルト**: `8080`

```bash
# gnmi-native.sh:64-72
if [ -z "$GNMI" ]; then
    PORT=8080
else
    PORT=$(extract_field "$GNMI" '.port')
    if ! [[ $PORT =~ ^[0-9]+$ ]]; then
        echo "Incorrect port value ${PORT}, expecting positive integers" >&2
        exit $INCORRECT_TELEMETRY_VALUE
    fi
fi
```

DB に `GNMI` エントリが無い場合、またはエントリがあっても `port` キーが無い場合 (`jq -r '.port'` が `null` → `^[0-9]+$` にマッチしない → 不正値扱い)、`PORT=8080` が使われる。

**重要**: DB に `GNMI|gnmi` エントリが存在しても `port` フィールドが欠如している場合は起動失敗になるため、事実上 `8080` は「DB が空の場合のフォールバック」。

---

### GNMI|gnmi — `client_auth`

**コード由来デフォルト**: `allow_no_client_auth` 有効 (クライアント証明書要求しない)

```bash
# gnmi-native.sh:76-79
CLIENT_AUTH=$(extract_field "$GNMI" '.client_auth')
if [ -z $CLIENT_AUTH ] || [ $CLIENT_AUTH == "false" ]; then
    TELEMETRY_ARGS+=" --allow_no_client_auth"
fi
```

`client_auth` が未設定 (空) または `"false"` の場合、`--allow_no_client_auth` フラグが付与される。  
これはサーバがクライアント証明書を要求するが、検証しないモード (`tls.RequestClientCert`)。

---

### GNMI|gnmi — `log_level`

**コード由来デフォルト**: `2`

```bash
# gnmi-native.sh:81-86
LOG_LEVEL=$(extract_field "$GNMI" '.log_level')
if [[ $LOG_LEVEL =~ ^[0-9]+$ ]]; then
    TELEMETRY_ARGS+=" -v=$LOG_LEVEL"
else
    TELEMETRY_ARGS+=" -v=2"
fi
```

Go CLI フラグ定義でも `fs.Int("v", 2, ...)` として `2` がデフォルト (`telemetry.go:176`)。

---

### GNMI|gnmi — `threshold`

**コード由来デフォルト**: `100`

```bash
# gnmi-native.sh:101-111
THRESHOLD_CONNECTIONS=$(extract_field "$GNMI" '.threshold')
if [[ $THRESHOLD_CONNECTIONS =~ ^[0-9]+$ ]]; then
    TELEMETRY_ARGS+=" --threshold $THRESHOLD_CONNECTIONS"
else
    if [ -z "$GNMI" ] || [[ $THRESHOLD_CONNECTIONS == "null" ]]; then
        TELEMETRY_ARGS+=" --threshold 100"
    else
        echo "Incorrect threshold value, expecting positive integers" >&2
        exit $INCORRECT_TELEMETRY_VALUE
    fi
fi
```

Go CLI フラグ定義でも `fs.Int("threshold", 100, ...)` として `100` がデフォルト (`telemetry.go:187`)。  
`GNMI|gnmi` エントリが無い (`-z "$GNMI"`) か、フィールドが `null` の場合に `100` が適用される。

---

### GNMI|gnmi — `idle_conn_duration`

**コード由来デフォルト**: `5` (秒)

```bash
# gnmi-native.sh:113-124
IDLE_CONN_DURATION=$(extract_field "$GNMI" '.idle_conn_duration')
if [[ $IDLE_CONN_DURATION =~ ^[0-9]+$ ]]; then
    TELEMETRY_ARGS+=" --idle_conn_duration $IDLE_CONN_DURATION"
else
    if [ -z "$GNMI" ] || [[ $IDLE_CONN_DURATION == "null" ]]; then
        TELEMETRY_ARGS+=" --idle_conn_duration 5"
    else
        echo "Incorrect idle_conn_duration value, expecting positive integers" >&2
        exit $INCORRECT_TELEMETRY_VALUE
    fi
fi
```

Go CLI フラグ定義でも `fs.Int("idle_conn_duration", 5, ...)` として `5` がデフォルト (`telemetry.go:190`)。

---

### GNMI|gnmi — `user_auth`

**コード由来デフォルト**: `"cert"` (gnmi-native.sh レベル)

```bash
# gnmi-native.sh:126-129
USER_AUTH=$(extract_field "$GNMI" '.user_auth')
# If user_auth is not set, default to certs
if [ $USER_AUTH == "null" ]; then
    USER_AUTH="cert"
fi
```

DB に `user_auth` が無い場合、`cert` として扱われ `--client_auth cert` が渡される。  
さらに `user_auth=cert` の場合、`--config_table_name GNMI_CLIENT_CERT` が自動追加される (`gnmi-native.sh:135`)。

**Go レベルの実行時デフォルト** (telemetry.go):
```go
// telemetry.go:173, 216-222
telemetryCfg := &TelemetryConfig{
    UserAuth: gnmi.AuthTypes{"password": false, "cert": false, "jwt": false},
    ...
}
// GnmiTranslibWrite が true の場合:
defUserAuth = gnmi.AuthTypes{"password": true, "cert": false, "jwt": true}
// false の場合:
defUserAuth = gnmi.AuthTypes{"jwt": false, "password": false, "cert": false}
```

スクリプトレベルと Go 内部レベルで層が分かれる。スクリプトが `--client_auth cert` を渡すと Go 側は `cert=true` として動作する。

---

### GNMI|gnmi — `enable_crl`

**コード由来デフォルト**: 未設定 = CRL 無効

```bash
# gnmi-native.sh:137-140
ENABLE_CRL=$(echo $GNMI | jq -r '.enable_crl')
if [ $ENABLE_CRL == "true" ]; then
    TELEMETRY_ARGS+=" --enable_crl"
fi
```

`enable_crl` が `"true"` の場合のみ `--enable_crl` フラグが付与される。  
Go CLI フラグ定義でも `fs.Bool("enable_crl", false, ...)` として `false` がデフォルト (`telemetry.go:193`)。

---

### GNMI|gnmi — `crl_expire_duration`

**コード由来デフォルト**: `86400` 秒 (24 時間)

```bash
# gnmi-native.sh:142-145
CRL_EXPIRE_DURATION=$(extract_field "$GNMI" '.crl_expire_duration')
if [ ! -z "$CRL_EXPIRE_DURATION" ] && [ $CRL_EXPIRE_DURATION != "null" ]; then
    TELEMETRY_ARGS+=" --crl_expire_duration $CRL_EXPIRE_DURATION"
fi
```

DB に設定がない場合は引数なし → Go CLI デフォルトが適用される。  
Go CLI フラグ: `fs.Int("crl_expire_duration", 86400, ...)` (`telemetry.go:194`)。  
clientCertAuth.go でも `const DEFAULT_CRL_EXPIRE_DURATION time.Duration = 24 * 60 * 60 * time.Second` として定義 (`clientCertAuth.go:22`)。

---

### GNMI|certs — `server_crt` / `server_key` / `ca_crt`

**コード由来デフォルト**:
- `server_crt` / `server_key`: 未設定の場合 `--insecure` フラグが付与される
- `ca_crt`: 未設定の場合はオプショナル — CA 証明書なしで動作 (クライアント証明書検証なし)

```bash
# gnmi-native.sh:32-44
if [ -n "$CERTS" ]; then
    SERVER_CRT=$(extract_field "$CERTS" '.server_crt')
    SERVER_KEY=$(extract_field "$CERTS" '.server_key')
    if [ -z $SERVER_CRT  ] || [ -z $SERVER_KEY  ]; then
        TELEMETRY_ARGS+=" --insecure"
    else
        TELEMETRY_ARGS+=" --server_crt $SERVER_CRT --server_key $SERVER_KEY "
    fi

    CA_CRT=$(extract_field "$CERTS" '.ca_crt')
    if [ ! -z $CA_CRT ]; then
        TELEMETRY_ARGS+=" --ca_crt $CA_CRT"
    fi
```

`GNMI|certs` も `GNMI|certs.server_crt`/`server_key` も無い場合は `DEVICE_METADATA|localhost.x509` にフォールバック。  
両方とも無い場合は `--noTLS` (TLS 完全無効) で起動する。

---

### GNMI_CLIENT_CERT|`<cname>` — `role`

**コード由来デフォルト**: なし (DB にエントリが存在しない場合は認証失敗)

```go
// clientCertAuth.go:263-283
var fieldValuePairs = configDbConnector.Get_entry(serviceConfigTableName, certCommonName)
if fieldValuePairs.Size() > 0 {
    if fieldValuePairs.Has_key("role@") {
        var role = fieldValuePairs.Get("role@")
        auth.Roles = strings.Split(role, ",")
    } else if fieldValuePairs.Has_key("role") {
        // Backward compatibility for single role DB schema
        var role = fieldValuePairs.Get("role")
        auth.Roles = []string{role}
    }
} else {
    glog.Warningf("Failed to retrieve cert common name mapping; %s", certCommonName)
}

if len(auth.Roles) == 0 {
    return status.Errorf(codes.Unauthenticated,
        "Invalid cert cname:'%s', not a trusted cert common name.", certCommonName)
}
```

`role` フィールドが存在しない → `auth.Roles` 空 → `codes.Unauthenticated` エラー。  
**フォールバックなし** — エントリが存在しない、または `role` キーがない場合は接続拒否。

**後方互換性**: `role@` (配列型、カンマ区切り) と `role` (単一値) の両方をサポート。  
`systemd_stub.py` は `role` (単一値) で書き込む (sidecar:181):
```python
if db_hset(key, "role", role):
    logger.log_notice(f"Created {key} with role={role}")
```

レガシー環境での `GNMI_CLIENT_ROLE` 環境変数デフォルト: `"gnmi_show_readonly"` (`systemd_stub.py:52`)。

---

## 要約表

### GNMI|gnmi フィールド

| フィールド | コード由来デフォルト | ソース (主) |
|-----------|-------------------|------------|
| `port` | `8080` | `gnmi-native.sh:65` |
| `client_auth` | `"false"` → `allow_no_client_auth` | `gnmi-native.sh:77` |
| `log_level` | `2` | `gnmi-native.sh:85`, `telemetry.go:176` |
| `threshold` | `100` | `gnmi-native.sh:106`, `telemetry.go:187` |
| `idle_conn_duration` | `5` (秒) | `gnmi-native.sh:119`, `telemetry.go:190` |
| `user_auth` | `"cert"` | `gnmi-native.sh:129` |
| `enable_crl` | `false` | `gnmi-native.sh:138`, `telemetry.go:193` |
| `crl_expire_duration` | `86400` (秒) | `telemetry.go:194`, `clientCertAuth.go:22` |

### GNMI|certs フィールド

| フィールド | コード由来デフォルト | ソース (主) |
|-----------|-------------------|------------|
| `server_crt` | 未設定 → `--insecure` | `gnmi-native.sh:35-36` |
| `server_key` | 未設定 → `--insecure` | `gnmi-native.sh:35-36` |
| `ca_crt` | 未設定 → CA 検証なし | `gnmi-native.sh:41-43` |

### GNMI_CLIENT_CERT|`<cname>` フィールド

| フィールド | コード由来デフォルト | ソース (主) |
|-----------|-------------------|------------|
| `role` | なし (エントリ不在 = 認証失敗) | `clientCertAuth.go:279-283` |
| `role@` | なし (role の配列版; 優先) | `clientCertAuth.go:265-267` |

---

## マイグレーション挙動 (db_migrator.py)

`migrate_gnmi()` (`db_migrator.py:634-656`):

1. `GNMI|gnmi` と `GNMI|certs` が両方存在する場合: スキップ (マイグレーション不要)
2. `config_src_data` に `GNMI` セクションがある場合: そこから `gnmi`/`certs` をコピー
3. それ以外 (`TELEMETRY|gnmi` からの移行): `TELEMETRY|gnmi` の内容を `GNMI|gnmi` にコピー

**注意**: マイグレーションは `GNMI|gnmi` エントリの有無を確認するだけで、個別フィールドの補完はしない。
