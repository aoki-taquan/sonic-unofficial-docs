# pki-trusted-certs — Phase H platform 調査メモ

## 調査対象

- `sonic-gnmi/gnmi_server/gnsi_certz.go` 全行精読
- `sonic-gnmi/gnmi_server/server.go` — TLS 設定・証明書読み込み部
- `sonic-gnmi/gnmi_server/gnsi_certz.go` — DEVICE_METADATA / multi-asic / namespace / SmartSwitch キーワード検索 → 0 ヒット
- `sonic-mgmt-common/cvl/testdata/schema/sonic-pki.yang` — YANG スキーマ定義

## 結論

`SECURITY_PROFILES` / `SECURITY_GLOBAL` / gNSI Certz 実装において、ASIC 種別・multi-asic・VOQ chassis・SmartSwitch などのプラットフォーム条件による分岐は **一切検出されなかった**。

### ASIC 種別 (Broadcom / Mellanox / Marvell / Innovium 等)

gNSI Certz は SAI を経由しない。証明書管理はファイルシステムのシンボリックリンクと STATE_DB への HSET のみで完結するため、ASIC 種別は無関係。

### multi-asic (`is_multi_npu`)

`gnsi_certz.go` に `namespace` / `multi_asic` / `is_multi_npu` の参照なし。CONFIG_DB の `SECURITY_PROFILES` を消費する production ハンドラも community master に未実装のため、namespace ごとの差異も生じない。

### VOQ chassis (supervisor + line cards)

gNSI Certz は host スコープで動作し、スーパーバイザ / ラインカードの区別を行わない。各 host で独立動作。

### SmartSwitch (NPU + DPU)

`gnsi_certz.go` に `SmartSwitch` / `subtype` / `DEVICE_METADATA` の参照なし。SmartSwitch 向けの特殊処理は検出されなかった。

## 証拠

- `sonic-gnmi/gnmi_server/gnsi_certz.go` — `grep -n "multi_asic\|namespace\|chassis\|SmartSwitch\|DEVICE_METADATA\|subtype\|is_multi_npu"` → 0 ヒット
- `sonic-mgmt-common/cvl/testdata/schema/sonic-pki.yang` — platform 条件の YANG extension なし
