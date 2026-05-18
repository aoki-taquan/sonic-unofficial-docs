# TELEMETRY_CLIENT 暗黙テーブル参照 (Phase C) 調査メモ

## 調査対象

- `sonic-buildimage/dockers/docker-sonic-gnmi/gnmi-native.sh`
- `sonic-buildimage/dockers/docker-sonic-gnmi/supervisord.conf`
- `sonic-buildimage/dockers/docker-sonic-gnmi/telemetry_vars.j2`
- `sonic-gnmi/dialout/dialout_client/dialout_client.go`

## 発見した暗黙参照

### 1. CONFIG_DB.TELEMETRY (dial-in 設定)

`gnmi-native.sh` は起動時に `sonic-cfggen -d -t telemetry_vars.j2` で `TELEMETRY|gnmi` および
`TELEMETRY|certs` を読み込み、gnmi-native プロセスの起動引数を構築する。
`dialout` プロセスは `supervisord.conf` の `dependent_startup_wait_for=gnmi-native:running` により
gnmi-native が running になるまで起動しない。つまり TELEMETRY_CLIENT は間接的に TELEMETRY テーブルに依存。

証跡: `gnmi-native.sh:L18-62`, `supervisord.conf:L70`

### 2. CONFIG_DB.DEVICE_METADATA|x509 (旧 TLS 設定)

`telemetry_vars.j2` が `DEVICE_METADATA["x509"]` を参照。`TELEMETRY|certs` が空の場合のフォールバック。
`gnmi-native.sh` が `x509.server_crt` / `x509.server_key` を TLS 証明書として使用。

証跡: `telemetry_vars.j2:L4`, `gnmi-native.sh:L44-55`

### 3. CONFIG_DB.DEVICE_METADATA|localhost.subtype (SmartSwitch 判定)

`gnmi-native.sh:L88-90`:
```bash
LOCALHOST_SUBTYPE=`sonic-db-cli CONFIG_DB hget "DEVICE_METADATA|localhost" "subtype"`
if [[ x"${LOCALHOST_SUBTYPE}" == x"SmartSwitch" ]]; then
    TELEMETRY_ARGS+=" -zmq_port=8100"
fi
```
SmartSwitch 環境では ZMQ ポートが追加される。TELEMETRY_CLIENT の dial-out は gnmi-native 経由の
パスデータ取得がこの設定に依存する。

証跡: `gnmi-native.sh:L88-90`

### 4. CONFIG_DB.MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled (管理 VRF)

`gnmi-native.sh:L93-96`:
```bash
MGMT_VRF_ENABLED=`sonic-db-cli CONFIG_DB hget "MGMT_VRF_CONFIG|vrf_global" "mgmtVrfEnabled"`
if [[ x"${MGMT_VRF_ENABLED}" == x"true" ]]; then
    TELEMETRY_ARGS+=" --vrf mgmt"
fi
```
管理 VRF が有効の場合、gnmi サーバが mgmt VRF にバインドされる。
dial-out クライアントの送信元も mgmt VRF の経路を使う必要がある。

証跡: `gnmi-native.sh:L93-96`

### 5. dial-out クライアント自身の読み取り (TELEMETRY_CLIENT のみ)

`dialout_client.go` の `DialOutRun()` は CONFIG_DB.TELEMETRY_CLIENT のみを購読。
他のテーブルは直接参照しない。TELEMETRY や DEVICE_METADATA への参照は gnmi-native.sh 経由の間接参照のみ。

## 暗黙参照マトリクス

| 参照先 | 種別 | 方向 | 直接/間接 | ソース |
|--------|------|------|-----------|--------|
| `CONFIG_DB.TELEMETRY\|certs` / `TELEMETRY\|gnmi` | CONFIG テーブル | TELEMETRY_CLIENT → TELEMETRY | 間接（gnmi-native.sh→supervisord→dialout 起動依存） | `gnmi-native.sh:L18`, `supervisord.conf:L70` |
| `CONFIG_DB.DEVICE_METADATA\|x509` | CONFIG テーブル | TELEMETRY_CLIENT → DEVICE_METADATA | 間接（gnmi-native.sh TLS フォールバック） | `telemetry_vars.j2:L4` |
| `CONFIG_DB.DEVICE_METADATA\|localhost.subtype` | CONFIG テーブル | TELEMETRY_CLIENT → DEVICE_METADATA | 間接（gnmi-native.sh SmartSwitch 判定） | `gnmi-native.sh:L88` |
| `CONFIG_DB.MGMT_VRF_CONFIG\|vrf_global.mgmtVrfEnabled` | CONFIG テーブル | TELEMETRY_CLIENT → MGMT_VRF_CONFIG | 間接（gnmi-native.sh VRF バインド） | `gnmi-native.sh:L93` |
