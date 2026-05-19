# pki-trusted-certs — Phase H プラットフォーム差異調査メモ

## 調査対象

- `sonic-gnmi/gnmi_server/gnsi_certz.go` (ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- `sonic-gnmi/gnmi_server/server.go`
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

### 結論

全プラットフォームで動作差異なし。CONFIG_DB ハンドラ未実装のため、
ASIC_DB / SAI へのパスも存在しない。Phase H として記載できる差異は
VS / SmartSwitch DPU の特記事項程度。
