# gnmi-dialin Phase C — 暗黙参照テーブル調査メモ

調査日: 2026-05-19
対象ページ: `docs/reference/config-db/gnmi-dialin.md`
フェーズ: Phase C (暗黙参照テーブル)

## 調査対象ソース

| ファイル | リポジトリ | SHA | 役割 |
|---------|-----------|-----|------|
| `dockers/docker-sonic-gnmi/gnmi-native.sh` | sonic-net/sonic-buildimage | 9ea932ec | 起動スクリプト。CONFIG_DB 参照の起点 |
| `dockers/docker-sonic-gnmi/telemetry_vars.j2` | sonic-net/sonic-buildimage | 9ea932ec | Jinja2 テンプレート。GNMI / DEVICE_METADATA を参照 |
| `gnmi_server/clientCertAuth.go` | sonic-net/sonic-gnmi | eb635b76 | runtime 中の GNMI_CLIENT_CERT 参照 |
| `sonic_data_client/mixed_db_client.go` | sonic-net/sonic-gnmi | eb635b76 | SmartSwitch DPU ZMQ アドレス解決で CONFIG_DB 参照 |
| `pkg/bypass/bypass.go` | sonic-net/sonic-gnmi | eb635b76 | bypass validation 機能で DEVICE_METADATA.hwsku 参照 |

## 発見した暗黙参照テーブル

### 1. GNMI テーブル自体 (GNMI|gnmi, GNMI|certs) — 直接設定読み取り

`gnmi-native.sh` が `sonic-cfggen -d -t telemetry_vars.j2` で一括読み取り。
- `telemetry_vars.j2:2`: `GNMI["certs"]`
- `telemetry_vars.j2:3`: `GNMI["gnmi"]`
- Phase B で詳述済み。本表では関連テーブルとして整理。

### 2. DEVICE_METADATA|localhost.x509 — 旧 TLS 証明書パス (レガシーフォールバック)

`telemetry_vars.j2:4` が `DEVICE_METADATA["x509"]` を参照。
`GNMI|certs` が未設定の場合のフォールバック TLS 設定として機能する。
- evidence: `dockers/docker-sonic-gnmi/telemetry_vars.j2:4`
- `gnmi-native.sh:21,46-58` で X509 変数として読み取り

### 3. DEVICE_METADATA|localhost.subtype — SmartSwitch 判定

`gnmi-native.sh:89-92` が `sonic-db-cli CONFIG_DB hget "DEVICE_METADATA|localhost" "subtype"` で直接読み取り。
`SmartSwitch` の場合のみ `-zmq_port=8100` フラグを追加。
- evidence: `gnmi-native.sh:89-92`

### 4. MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled — 管理 VRF 設定

`gnmi-native.sh:95-98` が `sonic-db-cli CONFIG_DB hget "MGMT_VRF_CONFIG|vrf_global" "mgmtVrfEnabled"` で直接読み取り。
`true` の場合のみ `--vrf mgmt` フラグを追加。
- evidence: `gnmi-native.sh:95-98`

### 5. GNMI_CLIENT_CERT|<CommonName> — クライアント証明書 CN → ロールマッピング (runtime)

`gnmi_server/clientCertAuth.go:263` が `configDbConnector.Get_entry(serviceConfigTableName, certCommonName)` で runtime 中に参照。
`serviceConfigTableName` は `gnmi-native.sh:135` で `--config_table_name GNMI_CLIENT_CERT` としてバイナリに渡される (`user_auth=cert` 時のみ)。
- evidence: `gnmi_server/clientCertAuth.go:254-277`

### 6. MID_PLANE_BRIDGE|GLOBAL, DPUS|<dpuId>, DHCP_SERVER_IPV4_PORT|<key> — SmartSwitch DPU ZMQ アドレス解決

`sonic_data_client/mixed_db_client.go:118-150` の `getDpuAddress()` 関数が ZMQ クライアント接続時に CONFIG_DB を読み取る。
SmartSwitch 構成 (`-zmq_port=8100`) が有効な場合のみ呼ばれる。
- evidence: `sonic_data_client/mixed_db_client.go:118-151`

### 7. DEVICE_METADATA|localhost.hwsku — bypass validation (SmartSwitch 向け)

`pkg/bypass/bypass.go:156` が `DEVICE_METADATA|localhost` の `hwsku` フィールドを参照。
`AllowedSKUPrefixes` と照合し、gNMI Set RPC 時の CVL validation bypass を許可するかどうかを決定。
- evidence: `pkg/bypass/bypass.go:148-168`

## 参照タイミング分類

| 参照先 | 読み取りタイミング | 変更反映 |
|-------|-----------------|---------|
| `GNMI\|gnmi` / `GNMI\|certs` | 起動時 1 回 (sonic-cfggen) | コンテナ再起動が必要 |
| `DEVICE_METADATA\|localhost.x509` | 起動時 1 回 (sonic-cfggen) | コンテナ再起動が必要 |
| `DEVICE_METADATA\|localhost.subtype` | 起動時 1 回 (sonic-db-cli) | コンテナ再起動が必要 |
| `MGMT_VRF_CONFIG\|vrf_global.mgmtVrfEnabled` | 起動時 1 回 (sonic-db-cli) | コンテナ再起動が必要 |
| `GNMI_CLIENT_CERT\|<CN>` | 各 gNMI RPC リクエスト毎 (runtime) | 即時反映（コンテナ再起動不要） |
| `MID_PLANE_BRIDGE` / `DPUS` / `DHCP_SERVER_IPV4_PORT` | ZMQ 接続確立時 (runtime) | 再接続時に反映 |
| `DEVICE_METADATA\|localhost.hwsku` | 各 gNMI Set RPC 時 (runtime) | 即時反映（コンテナ再起動不要） |
