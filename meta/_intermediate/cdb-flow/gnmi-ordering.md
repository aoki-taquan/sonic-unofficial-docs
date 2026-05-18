# GNMI / GNMI_CLIENT_CERT — 書込み順序調査メモ (Phase B)

## 調査対象

- `sonic-buildimage/dockers/docker-sonic-gnmi/gnmi-native.sh` (startup script)
- `sonic-gnmi/telemetry/telemetry.go` (gNMI server binary)
- `sonic-gnmi/gnmi_server/clientCertAuth.go`

## 発見した順序依存

### 1. GNMI|certs / DEVICE_METADATA|localhost.x509 → GNMI|gnmi より先に解決

`gnmi-native.sh` は TELEMETRY_VARS テンプレートを展開して `CERTS` / `X509` / `GNMI` 変数を取得した後、TLS 引数を先に構築してからポート・閾値・認証を追加する。起動スクリプトは**一度だけ**実行されるため、`GNMI|certs` が起動前に設定されていないと `--noTLS` フォールバックで起動してしまう。

証跡: `gnmi-native.sh:32-61` (CERTS → X509 → noTLS フォールバック順)

### 2. DEVICE_METADATA|localhost.subtype → SmartSwitch ZMQ 設定より先

`gnmi-native.sh:89-92` で `DEVICE_METADATA|localhost` の `subtype` フィールドを読む。これは GNMI エントリ評価より前に実行されるが、実際には同じ `sonic-cfggen -d` 展開内に含まれるため起動時一括読み込み。

### 3. MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled → 起動前に設定必須

`gnmi-native.sh:95-98` で `MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled` をチェックして `--vrf mgmt` を付与。telemetry が起動した後に `mgmtVrfEnabled` を変更しても反映されない（再起動必要）。

### 4. GNMI_CLIENT_CERT エントリ → user_auth=cert 有効前に設定

`user_auth = cert` モードでは、クライアント接続時に `GNMI_CLIENT_CERT|<CN>` を参照してロールを決定する (`clientCertAuth.go:254-284`)。`GNMI|gnmi.user_auth=cert` を設定した状態で `GNMI_CLIENT_CERT` エントリが存在しない場合、すべてのクライアントが `codes.Unauthenticated` で拒否される。

### 5. GNMI エントリ全体 → telemetry コンテナ起動より先

`gnmi-native.sh` はコンテナ起動シェルスクリプトであり、起動時に一回だけ読む。CONFIG_DB への変更はコンテナ再起動なしには反映されない。

## 結論

主要な順序制約は「起動前設定」に集中する。コンテナ起動後のランタイム変更はすべて再起動が必要。
