# GNMI / TELEMETRY_CLIENT — Phase C: 暗黙参照テーブル調査メモ

調査対象: `docs/reference/config-db/gnmi-server.md` Phase C block

## 調査ソース

- `sonic-buildimage` `dockers/docker-sonic-gnmi/gnmi-native.sh` (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-buildimage` `dockers/docker-sonic-gnmi/telemetry_vars.j2` (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-gnmi` `gnmi_server/clientCertAuth.go` (ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- `sonic-gnmi` `telemetry/telemetry.go` (ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)

## 検出された暗黙参照

### 1. DEVICE_METADATA|x509 (レガシー TLS 証明書フォールバック)

`telemetry_vars.j2:4`:
```jinja2
"x509" : {% if "x509" in DEVICE_METADATA.keys() %}{{ DEVICE_METADATA["x509"] }}{% else %}""{% endif %}
```

`gnmi-native.sh:46-58`:
```bash
elif [ -n "$X509" ]; then
    SERVER_CRT=$(extract_field "$X509" '.server_crt')
    SERVER_KEY=$(extract_field "$X509" '.server_key')
    ...
```

`GNMI|certs` エントリが存在しない場合、スクリプトは `DEVICE_METADATA|x509` サブエントリ (フィールド: `server_crt`, `server_key`, `ca_crt`) を TLS 証明書の代替ソースとして使用する。これは `sonic-telemetry` コンテナ時代からのレガシーフォールバック経路。`GNMI|certs` も `DEVICE_METADATA|x509` も存在しない場合は `--noTLS` フラグが付与される。

### 2. DEVICE_METADATA|localhost.subtype (SmartSwitch ZMQ ポート)

`gnmi-native.sh:89-92`:
```bash
LOCALHOST_SUBTYPE=`sonic-db-cli CONFIG_DB hget "DEVICE_METADATA|localhost" "subtype"`
if [[ x"${LOCALHOST_SUBTYPE}" == x"SmartSwitch" ]]; then
    TELEMETRY_ARGS+=" -zmq_port=8100"
fi
```

`DEVICE_METADATA|localhost` の `subtype` フィールドが `"SmartSwitch"` のとき、`-zmq_port=8100` フラグを付与する。GNMI テーブルには対応する設定フィールドなし (ハードコード)。

### 3. MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled (VRF バインド)

`gnmi-native.sh:95-98`:
```bash
MGMT_VRF_ENABLED=`sonic-db-cli CONFIG_DB hget  "MGMT_VRF_CONFIG|vrf_global" "mgmtVrfEnabled"`
if [[ x"${MGMT_VRF_ENABLED}" == x"true" ]]; then
    TELEMETRY_ARGS+=" --vrf mgmt"
fi
```

`MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled == "true"` のとき、telemetry プロセスを `mgmt` VRF にバインドする (`--vrf mgmt`)。GNMI テーブルには対応する設定フィールドなし。

### 4. GNMI_CLIENT_CERT|<cert_cname> (cert 認証ロール解決)

`gnmi_server/clientCertAuth.go:254-283`:
```go
func PopulateAuthStructByCommonName(certCommonName string, auth *common_utils.AuthInfo, serviceConfigTableName string) error {
    var configDbConnector = swsscommon.NewConfigDBConnector()
    configDbConnector.Connect(false)
    var fieldValuePairs = configDbConnector.Get_entry(serviceConfigTableName, certCommonName)
    ...
}
```

`user_auth == "cert"` のとき、gNMI サーバは接続要求ごとに CONFIG_DB の `GNMI_CLIENT_CERT|<cert_cname>` エントリ (`serviceConfigTableName = "GNMI_CLIENT_CERT"`, `certCommonName` = クライアント証明書 CN) をリアルタイムにルックアップしてロールを決定する。

## 参照方向のまとめ

| 参照先テーブル / フィールド | 参照元コンポーネント | 参照タイミング | 方向 |
|--------------------------|-------------------|--------------|------|
| `DEVICE_METADATA\|x509` | `gnmi-native.sh` (via `telemetry_vars.j2`) | コンテナ起動時 1 回 | 読み取り専用 (フォールバック) |
| `DEVICE_METADATA\|localhost.subtype` | `gnmi-native.sh` | コンテナ起動時 1 回 | 読み取り専用 |
| `MGMT_VRF_CONFIG\|vrf_global.mgmtVrfEnabled` | `gnmi-native.sh` | コンテナ起動時 1 回 | 読み取り専用 |
| `GNMI_CLIENT_CERT\|<cert_cname>` | `clientCertAuth.go:PopulateAuthStructByCommonName()` | 接続認証ごと (ランタイム) | 読み取り専用 |

## 結論

gnmi-server の暗黙参照は 4 つに分類される。起動時スナップショット参照が 3 つ（うち 1 つはレガシーフォールバック）、ランタイム参照が 1 つ（cert 認証のロール解決）。いずれも「書き手」としての副次書込みは発生しない（gNMI サーバは CONFIG_DB の消費者のみ）。
