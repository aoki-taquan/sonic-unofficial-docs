# TELEMETRY_CLIENT — Phase H プラットフォーム差調査

## 調査対象

- `sonic-net/sonic-gnmi` @ eb635b7679b260c3fd0786a6d0734fc8e82c9a22
  - `dialout/dialout_client/dialout_client.go`
- `sonic-net/sonic-buildimage` @ 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - `dockers/docker-sonic-gnmi/Dockerfile.j2`
  - `rules/config`
  - `platform/**/*.mk`（全プラットフォーム）

## 調査結果

### ビルドフラグ

`rules/config:160` に `INCLUDE_SYSTEM_GNMI = y` がデフォルト定義されている。
`platform/` 配下の全 `.mk` ファイルに `INCLUDE_SYSTEM_GNMI` への上書きは **0 ヒット**。
すべてのプラットフォームで `docker-sonic-gnmi` がビルドされる。

### dialout_client.go のプラットフォーム分岐

`dialout_client.go` 746 行全行をスキャンした結果:

- `platform`、`DEVICE_METADATA`、`ASIC`、`asic_id`、`namespace`、`multi_npu`、`chassis`、`linecard` への参照 **0 ヒット**
- プラットフォーム・ASIC 種別・multi-ASIC namespace に基づく条件分岐は **存在しない**

### TLS 設定

`dialout_client.go:267`:
```go
if clientCfg.TLS != nil {
    opts = append(opts, grpc.WithTransportCredentials(credentials.NewTLS(clientCfg.TLS)))
}
```

TLS 設定は `ClientConfig.TLS` フィールド経由で渡されるが、その有無は起動オプション（`ccfg`）に依存し、プラットフォームによる固定上書きはない。

### Dockerfile.j2

`dockers/docker-sonic-gnmi/Dockerfile.j2` にプラットフォーム固有の条件 (`{% if platform %}` 等) は存在しない。
ベースイメージは `docker-config-engine-bookworm` のみ。SAI / ASIC SDK への依存なし。

### multi-ASIC / namespace

dialout クライアントは `sonic_db_config` パッケージを通じて CONFIG_DB に接続するが、
`dialout_client.go` 内では `asicN` namespace への接続切り替えロジックが実装されていない。
multi-ASIC 構成でも host CONFIG_DB の `TELEMETRY_CLIENT` テーブルのみを購読する。
`sonic_data_client/db_client.go:524` の namespace サポートは dial-in (subscriber) 側の実装であり、dial-out クライアントには適用されない。

## 結論

**プラットフォーム差なし。** TELEMETRY_CLIENT テーブルの dial-out クライアントは全プラットフォームで同一動作する。
