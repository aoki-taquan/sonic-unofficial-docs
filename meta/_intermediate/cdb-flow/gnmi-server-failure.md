# gnmi-server Phase D — 失敗挙動根拠メモ

## 調査対象ソース

- `sonic-net/sonic-buildimage/dockers/docker-sonic-gnmi/gnmi-native.sh` (sha: 9ea932ec)
- `sonic-net/sonic-gnmi/telemetry/telemetry.go` (sha: eb635b76)
- `sonic-net/sonic-gnmi/dialout/dialout_client/dialout_client.go` (sha: eb635b76)

## gnmi-native.sh 失敗経路

### exit 1 — テンプレートファイル未存在
```bash
if [ ! -f "$TELEMETRY_VARS_FILE" ]; then
    echo "Telemetry vars template file not found"
    exit $EXIT_TELEMETRY_VARS_FILE_NOT_FOUND  # = 1
fi
```
(gnmi-native.sh:12-15)

### exit 2 — port 値不正
```bash
if ! [[ $PORT =~ ^[0-9]+$ ]]; then
    echo "Incorrect port value ${PORT}, expecting positive integers" >&2
    exit $INCORRECT_TELEMETRY_VALUE  # = 2
fi
```
(gnmi-native.sh:68-71)
`GNMI|gnmi.port` が存在するが数値でない場合にトリガー。GNMI エントリ自体が未設定の場合は PORT=8080 のデフォルトが使われ exit 2 にならない。

### exit 2 — threshold 値不正
```bash
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
(gnmi-native.sh:101-111)
GNMI エントリが存在し、threshold が非数値かつ null でない場合にトリガー。

### exit 2 — idle_conn_duration 値不正
同様のパターン (gnmi-native.sh:114-124)。

### TLS フォールバック挙動
- `GNMI|certs.server_crt` または `server_key` が空 → `--insecure` (gnmi-native.sh:35-39)
- `GNMI|certs` も `DEVICE_METADATA|x509` も未設定 → `--noTLS` (gnmi-native.sh:59-61)

## telemetry.go 失敗経路

- TLS 証明書ファイル読み込み失敗 → `log.Fatal` (telemetry.go:252-258, 318-320)

## dialout_client.go 失敗経路

- `dst_group == ""` → return (dialout_client.go:622-625)
- `DestinationGroup` 未登録 → クライアント未生成、後で keyspace 通知で自動回復 (dialout_client.go:514-543)
