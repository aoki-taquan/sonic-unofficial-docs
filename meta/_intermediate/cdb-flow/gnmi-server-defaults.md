# GNMI / TELEMETRY_CLIENT フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象テーブル: CONFIG_DB `GNMI` (gnmi サブキー) / `TELEMETRY_CLIENT`

## 調査対象ファイル

- `sonic-buildimage/dockers/docker-sonic-gnmi/gnmi-native.sh` — gNMI サーバ起動スクリプト (メイン)
- `sonic-buildimage/dockers/docker-sonic-telemetry/telemetry.sh` — 旧 telemetry docker 起動スクリプト
- `sonic-buildimage/dockers/docker-sonic-gnmi/telemetry_vars.j2` — CONFIG_DB → 変数変換テンプレート
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-gnmi.yang` — YANG 型制約
- `sonic-gnmi/telemetry/telemetry.go` — flag パース・デフォルト値定義
- `sonic-gnmi/dialout/dialout_client/dialout_client.go` — TELEMETRY_CLIENT 読み出し処理

---

## テーブル: GNMI|gnmi

`telemetry_vars.j2` にて `GNMI["gnmi"]` サブキーを参照。

### `port`

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

`GNMI|gnmi` エントリが存在しない場合、またはエントリが存在しても `port` が未設定の場合 (`null` を返す)、正規表現 `^[0-9]+$` にマッチしないため `exit 2` (INCORRECT_TELEMETRY_VALUE) になる。
GNMI エントリ自体が空の場合 (`-z "$GNMI"`) のみ `8080` がデフォルトになる。

flag 側 (`telemetry.go:174`):
```go
Port: fs.Int("port", -1, "port to listen on"),
```
flag デフォルト値は `-1` だが、`-1 <= 0` かつ `UnixSocket=""` の場合はエラー終了 (`fmt.Errorf("port must be > 0 ...")`)。
実質的には起動スクリプトが必ず `--port` を渡す。

---

### `log_level`

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

`log_level` が未設定または非数値なら `-v=2` が使用される。
flag 側デフォルトも同様 (`telemetry.go:176`: `fs.Int("v", 2, "log level of process")`).

telemetry.go での追加バリデーション:
```go
# telemetry.go:247-250
case *telemetryCfg.LogLevel < 0:
    *telemetryCfg.LogLevel = 2
    log.Infof("Log level must be greater than 0, setting to default value of 2")
```

---

### `client_auth`

**コード由来デフォルト**: `false` (クライアント証明書を要求しない)

```bash
# gnmi-native.sh:76-79 (旧 docker-sonic-telemetry の telemetry.sh)
CLIENT_AUTH=$(extract_field "$GNMI" '.client_auth')
if [ -z $CLIENT_AUTH ] || [ $CLIENT_AUTH == "false" ]; then
    TELEMETRY_ARGS+=" --allow_no_client_auth"
fi
```

未設定 (`-z`) または `"false"` の場合 `--allow_no_client_auth` フラグが付与される。

YANG 型: `boolean` (`sonic-gnmi.yang:60`)

flag 側デフォルト:
```go
# telemetry.go:182
AllowNoClientCert: fs.Bool("allow_no_client_auth", false, "..."),
```

---

### `user_auth`

**コード由来デフォルト**: `"cert"` (gnmi-native.sh) / 未設定時 `--allow_no_client_auth` (telemetry.sh)

```bash
# gnmi-native.sh:126-147
USER_AUTH=$(extract_field "$GNMI" '.user_auth')
# If user_auth is not set, default to certs
if [ $USER_AUTH == "null" ]; then
    USER_AUTH="cert"
fi
if [ ! -z "$USER_AUTH" ] && [  $USER_AUTH != "null" ] && [  $USER_AUTH != "none" ]; then
    TELEMETRY_ARGS+=" --client_auth $USER_AUTH"

    if [ $USER_AUTH == "cert" ]; then
        TELEMETRY_ARGS+=" --config_table_name GNMI_CLIENT_CERT"
        ...
    fi
fi
```

`user_auth` が未設定 (`null`) の場合、gnmi-native.sh は `"cert"` にフォールバックし `--client_auth cert --config_table_name GNMI_CLIENT_CERT` を渡す。
旧 telemetry.sh は `null` 確認なく `--allow_no_client_auth` となる (動作差異あり)。

YANG 型: `string` pattern `password|jwt|cert|none` (`sonic-gnmi.yang:91-95`)

flag 側デフォルト:
```go
# telemetry.go:173, 216-228
UserAuth: gnmi.AuthTypes{"password": false, "cert": false, "jwt": false},
...
if *telemetryCfg.GnmiTranslibWrite {
    defUserAuth = gnmi.AuthTypes{"password": true, "cert": false, "jwt": true}
} else {
    defUserAuth = gnmi.AuthTypes{"jwt": false, "password": false, "cert": false}
}
```

---

### `threshold`

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

GNMI エントリが存在しない (`-z "$GNMI"`) または `threshold` が `null` の場合 → `100`。
flag 側: `fs.Int("threshold", 100, "max number of client connections")` (telemetry.go:187)

---

### `idle_conn_duration`

**コード由来デフォルト**: `5` (秒)

```bash
# gnmi-native.sh:114-124
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

flag 側: `fs.Int("idle_conn_duration", 5, "Seconds before server closes idle connections")` (telemetry.go:190)
`0` は無限 (inf) として扱われる。

---

### `save_on_set`

**コード由来デフォルト**: `false` (未設定時は `--with-save-on-set` フラグなし)

```bash
# telemetry.sh:107-113
readonly SAVE_ON_SET=$(echo $GNMI | jq -r '.save_on_set // empty')
if [ ! -z "$SAVE_ON_SET" ]; then
    TELEMETRY_ARGS+=" --with-save-on-set=$SAVE_ON_SET"
fi
```

未設定の場合 `jq -r '.save_on_set // empty'` が空文字列を返し、フラグは付与されない。
flag 側: `fs.Bool("with-save-on-set", false, "Enables save-on-set.")` (telemetry.go:189)

YANG 型: `boolean` (`sonic-gnmi.yang:76`)

---

### `enable_crl`

**コード由来デフォルト**: `false`

```bash
# gnmi-native.sh:137-140
ENABLE_CRL=$(echo $GNMI | jq -r '.enable_crl')
if [ $ENABLE_CRL == "true" ]; then
    TELEMETRY_ARGS+=" --enable_crl"
fi
```

`user_auth == "cert"` ブロック内でのみ評価される。未設定または `"true"` 以外の場合はフラグなし。
flag 側: `fs.Bool("enable_crl", false, "Enable certificate revocation list")` (telemetry.go:193)

---

### `crl_expire_duration`

**コード由来デフォルト**: `86400` (秒 = 24 時間)

```bash
# gnmi-native.sh:142-145
CRL_EXPIRE_DURATION=$(extract_field "$GNMI" '.crl_expire_duration')
if [ ! -z "$CRL_EXPIRE_DURATION" ] && [ $CRL_EXPIRE_DURATION != "null" ]; then
    TELEMETRY_ARGS+=" --crl_expire_duration $CRL_EXPIRE_DURATION"
fi
```

未設定の場合はフラグなし → flag デフォルト `86400` が使用される。
flag 側: `fs.Int("crl_expire_duration", 86400, "Certificate revocation list cache expire duration")` (telemetry.go:194)

YANG 型: `uint32` (`sonic-gnmi.yang:87`)

---

## テーブル: GNMI|certs

YANG で定義された TLS 証明書パス設定。デフォルト値なし（必須の場合は起動時エラー）。

| フィールド | 型 | YANG pattern |
|-----------|-----|-------------|
| `ca_crt` | string | `(/[a-zA-Z0-9_-]+)*/([a-zA-Z0-9_-]+).cer` |
| `server_crt` | string | `(/[a-zA-Z0-9_-]+)*/([a-zA-Z0-9_-]+).cer` |
| `server_key` | string | `(/[a-zA-Z0-9_-]+)*/([a-zA-Z0-9_-]+).key` |

未設定かつ `noTLS=false, insecure=false` の場合:
```go
# telemetry.go:253-258
case *telemetryCfg.ServerCert == "":
    return nil, nil, fmt.Errorf("serverCert must be set.")
case *telemetryCfg.ServerKey == "":
    return nil, nil, fmt.Errorf("serverKey must be set.")
```

---

## テーブル: GNMI_CLIENT_CERT

`user_auth == "cert"` 有効時に参照される証明書コモンネーム → ロールマッピングテーブル。

```
GNMI_CLIENT_CERT|<cert_cname>
  role = <role1>,<role2>,...
```

`clientCertAuth.go:254-263` の `PopulateAuthStructByCommonName()` が読み出す。

---

## テーブル: TELEMETRY_CLIENT

dial-out (push 型) テレメトリ設定。CONFIG_DB をキースペース通知で監視。

### Global サブキー (`TELEMETRY_CLIENT|Global`)

| フィールド | コード由来デフォルト | 参照箇所 |
|-----------|---------------------|---------|
| `src_ip` | `""` (空文字列) | `dialout_client.go:20` |
| `retry_interval` | `30` 秒 | `dialout_client.go:21`, `dialout_client_cli.go:21,31` |
| `encoding` | `JSON_IETF` (固定、変更不可) | `dialout_client.go:22,502` |
| `unidirectional` | `true` (固定、変更不可) | `dialout_client.go:23,504` |

`encoding` と `unidirectional` は DB から読んでも強制上書きされる:
```go
# dialout_client.go:501-505
case "encoding":
    //Flexible encoding Not supported yet
    clientCfg.Encoding = gpb.Encoding_JSON_IETF
case "unidirectional":
    // No PublishResponse supported yet
    clientCfg.Unidirectional = true
```

### DestinationGroup サブキー (`TELEMETRY_CLIENT|DestinationGroup_<name>`)

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `dst_addr` | string (`IP:PORT,...`) | 送信先アドレスリスト (カンマ区切り) |

### Subscription サブキー (`TELEMETRY_CLIENT|Subscription_<name>`)

| フィールド | コード由来デフォルト | 説明 |
|-----------|---------------------|------|
| `report_interval` | `5000` ミリ秒 | `dialout_client.go:582` |
| `dst_group` | (必須、未設定時 no-op) | 参照 DestinationGroup 名 |
| `report_type` | (未設定時 STREAM 相当) | `periodic`/`stream`/`once` |
| `path_target` | (未設定可) | DB ターゲット名 |
| `paths` | (未設定可) | サブスクライブパスリスト |

---

## VRF / SmartSwitch 連携

gnmi-native.sh (gnmi docker) はスクリプト内で CONFIG_DB を直接参照し VRF / SmartSwitch 設定を適用する:

```bash
# gnmi-native.sh:89-98
LOCALHOST_SUBTYPE=`sonic-db-cli CONFIG_DB hget "DEVICE_METADATA|localhost" "subtype"`
if [[ x"${LOCALHOST_SUBTYPE}" == x"SmartSwitch" ]]; then
    TELEMETRY_ARGS+=" -zmq_port=8100"
fi

MGMT_VRF_ENABLED=`sonic-db-cli CONFIG_DB hget "MGMT_VRF_CONFIG|vrf_global" "mgmtVrfEnabled"`
if [[ x"${MGMT_VRF_ENABLED}" == x"true" ]]; then
    TELEMETRY_ARGS+=" --vrf mgmt"
fi
```

- `DEVICE_METADATA|localhost.subtype == "SmartSwitch"` → ZMQ ポート `8100` を自動付与
- `MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled == "true"` → `--vrf mgmt` を付与

---

## 証拠リンク (SHA: sonic-buildimage eb635b76... / sonic-gnmi eb635b76...)

- `sonic-buildimage:9ea932ec` `dockers/docker-sonic-gnmi/gnmi-native.sh`
- `sonic-buildimage:9ea932ec` `dockers/docker-sonic-telemetry/telemetry.sh`
- `sonic-buildimage:9ea932ec` `src/sonic-yang-models/yang-models/sonic-gnmi.yang`
- `sonic-gnmi:eb635b76` `telemetry/telemetry.go:171-328`
- `sonic-gnmi:eb635b76` `dialout/dialout_client/dialout_client.go:412-640`
- `sonic-gnmi:eb635b76` `dialout/dialout_client_cli/dialout_client_cli.go:18-32`
