# pki-trusted-certs — Phase H プラットフォーム差異調査メモ

## 調査対象

- `sonic-gnmi/gnmi_server/gnsi_certz.go` (ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- `sonic-gnmi/gnmi_server/server.go`
- `sonic-buildimage/dockers/docker-sonic-gnmi/gnmi-native.sh`
- `sonic-mgmt-common/cvl/testdata/schema/sonic-pki.yang` (ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)

## 調査結果

### プラットフォーム分岐の有無

`gnsi_certz.go` 全体を走査し、以下のパターンをすべて確認:
- `getenv("platform")` — 存在しない
- `#ifdef` / `#ifndef` — Go ファイルのため存在しない
- 機種固有の定数・型名 — 存在しない

gNSI Certz は SAI API を呼び出さず、ASIC に依存しない証明書管理のみを担う。

### ファイルシステム依存

`/keys/` ディレクトリへの読み書き権限のみに依存。パスは CLI フラグ
(`CaCertLnk`, `SrvCertLnk`, `SrvKeyLnk`, `CertzMetaFile`) で変更可能であり、
環境（コンテナ / 物理 / VS）問わず同一コードパスを使用する。

### ASIC 種別

`gnsi_certz.go` に SAI API 呼び出しなし。証明書管理はファイルシステム (`/keys/`) と gRPC のみ。ASIC 種別に依らない。

### multi-asic

`gnsi_certz.go` 内に `is_multi_npu` / `asicN` namespace 参照なし。`ConfigDBConnector()` は引数なし (host scope)。`sonic-pki.yang` も host scope で定義。

### VOQ chassis

各 host で独立動作。集中管理機構なし。

### SmartSwitch

`gnmi-native.sh:88-91` — SmartSwitch 判定は `DEVICE_METADATA|localhost|subtype == "SmartSwitch"` で ZMQ ポート (`-zmq_port=8100`) を付与するのみ。gNSI Certz の証明書管理ロジックへの影響はない。DPU 側での `SECURITY_PROFILES` ハンドラも community master では未実装。

### コンテナ

`docker-sonic-gnmi` コンテナ内で動作。`/keys/` マウントはプラットフォーム共通。

### 結論

全プラットフォームで動作差異なし。CONFIG_DB ハンドラ未実装のため、
ASIC_DB / SAI へのパスも存在しない。Phase H として記載できる差異はなし。
