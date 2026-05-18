# gnmi — Phase C 暗黙参照テーブル (cross-refs) 調査メモ

## 対象ページ
`docs/reference/config-db/gnmi.md`（GNMI / GNMI_CLIENT_CERT テーブル）

## 調査対象ソース
- `sonic-buildimage` `dockers/docker-sonic-gnmi/gnmi-native.sh`
- `sonic-buildimage` `dockers/docker-sonic-gnmi/telemetry_vars.j2`
- `sonic-gnmi` `gnmi_server/clientCertAuth.go`

## 参照テーブル一覧

| 参照先 | 方向 | 条件 | 証拠箇所 |
|--------|------|------|----------|
| `GNMI\|gnmi` | 起動引数生成 | 常時 | `gnmi-native.sh:64-148` |
| `GNMI\|certs` | TLS パス解決 | 常時（優先） | `gnmi-native.sh:31-43` |
| `DEVICE_METADATA\|localhost.x509` | TLS パス解決（フォールバック） | `GNMI\|certs` 不在時 | `gnmi-native.sh:44-58`; `telemetry_vars.j2:4` |
| `DEVICE_METADATA\|localhost.subtype` | SmartSwitch 判定 | `subtype == "SmartSwitch"` | `gnmi-native.sh:89-91` |
| `MGMT_VRF_CONFIG\|vrf_global.mgmtVrfEnabled` | 管理 VRF | `mgmtVrfEnabled == "true"` | `gnmi-native.sh:95-98` |
| `GNMI_CLIENT_CERT\|<CN>` | 実行時認可 | `user_auth=cert` 接続時 | `clientCertAuth.go:254-284` |
| `TELEMETRY\|gnmi` | マイグレーション元 | db_migrator 実行時のみ | `db_migrator.py migrate_gnmi()` |

## 重要な設計ポイント

1. **sonic-cfggen 一括読み込み**: `gnmi-native.sh` は起動時 1 回のみ `sonic-cfggen -d -t telemetry_vars.j2` を実行。
   - テンプレートが `GNMI["certs"]`, `GNMI["gnmi"]`, `DEVICE_METADATA["x509"]` を JSON 化する
   - コンテナ稼働中の CONFIG_DB 変更は反映されない（要 `systemctl restart gnmi`）

2. **sonic-db-cli 直接取得**: `subtype` と `mgmtVrfEnabled` は sonic-cfggen テンプレート外で個別取得。

3. **実行時参照**: `GNMI_CLIENT_CERT` は各 gRPC 接続時に `clientCertAuth.go` が直接 CONFIG_DB を参照。
