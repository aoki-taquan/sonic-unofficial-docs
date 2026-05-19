# Task F Phase H: pki-trusted-certs プラットフォーム差異調査

Task F Phase H: `SECURITY_PROFILES` / `SECURITY_GLOBAL` テーブルおよび gNSI Certz 実装のプラットフォーム差異を `sonic-gnmi` と `sonic-mgmt-common` から調査した結果。

## 調査結果

### gNSI Certz はホスト OS レベルで動作

`gnsi_certz.go` は `docker-sonic-telemetry` コンテナ内で動作し、CONFIG_DB / ASIC_DB / SAI への書き込みを一切行わない。証明書管理はファイルシステム上のシンボリックリンク (`/keys/*.lnk`) と STATE_DB への HSET のみ。

### プラットフォーム分岐の不在

`gnsi_certz.go` / `gnmi_server.go` / `server.go` 全体を `getenv("platform")` / `#ifdef` / `os.Getenv("PLATFORM")` で grep した結果 **0 ヒット**。ASIC 種別・multi-asic 構成・VOQ chassis に関する条件分岐は一切存在しない。

### YANG スキーマ（sonic-pki.yang）

`sonic-pki.yang` は `sonic-mgmt-common/cvl/testdata/schema/` にのみ存在し、`sonic-buildimage` 本体 YANG には未マージ。YANG 定義にプラットフォーム依存フィールドや deviation はない。

### multi-asic 構成

`SECURITY_PROFILES` / `SECURITY_GLOBAL` は host-scoped CONFIG_DB を対象とする設計であり、`asicN` namespace に対応するハンドラは実装されていない（community master 2026-05 時点でハンドラ自体未実装）。

### SmartSwitch / DPU

gNSI Certz はネットワーク管理プレーン (gNMI/gRPC) を担うコンポーネントであり、DPU 上では起動しない。NPU 側の `docker-sonic-telemetry` のみで稼働する。

## エビデンス

- `sonic-gnmi/gnmi_server/gnsi_certz.go` 全体 — `platform` / `getenv` 検索 0 ヒット
- `sonic-gnmi/gnmi_server/server.go` 全体 — プラットフォーム分岐なし
- `sonic-mgmt-common/cvl/testdata/schema/sonic-pki.yang` — deviation / platform-specific leaf なし
