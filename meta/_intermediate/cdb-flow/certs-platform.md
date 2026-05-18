# CREDENTIALS|CERT — プラットフォーム差調査 (Phase H)

## 調査対象

- `sonic-net/sonic-gnmi` `gnmi_server/gnsi_certz.go` (ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- `sonic-net/sonic-gnmi` `telemetry/telemetry.go` (同 ref)
- `sonic-net/sonic-gnmi` `gnmi_server/` ディレクトリ全体

## 調査方法

```
grep -n "platform|asic|multi_npu|chassis|vendor|broadcom|mellanox|ASIC" gnsi_certz.go
grep -rn "platform|asic|multi_npu|chassis|vendor" gnmi_server/ --include="*.go"
grep -rn "platform|asic|multi_npu|chassis|vendor" telemetry/telemetry.go
```

## 結果

全コマンド 0 ヒット (gnsi_certz.go / telemetry.go 内にプラットフォーム分岐なし)。

## 観点別結論

| 観点 | 結果 | 根拠 |
|------|------|------|
| ASIC 種別 (Broadcom / Mellanox / Marvell 等) | 影響なし | `CREDENTIALS|CERT` は STATE_DB への freshness 記録のみ。SAI 非経由 |
| multi-asic (`is_multi_npu`) | 影響なし | `gnsi_certz.go` は global STATE_DB (dbName="STATE_DB") を直接 HSet。namespace iteration なし |
| VOQ chassis | 影響なし | gNSI Certz は host 単位の gRPC サービス。chassis 集中管理機構なし |
| ベンダー固有実装 | なし | community master。`gnsi_certz.go` は標準 Go TLS / gRPC のみ使用 |
| CRL ディレクトリパス | 実行時設定依存 | `--cert_crl_dir` フラグ (デフォルト `/mtls/crl`) で変更可能だが、platform 条件分岐ではない |

## 総評

`CREDENTIALS|CERT` テーブルの書き込みロジックはプラットフォーム差を持たない。ASIC 種別・multi-asic・VOQ chassis・ベンダー固有設定のいずれにも依存しない。
