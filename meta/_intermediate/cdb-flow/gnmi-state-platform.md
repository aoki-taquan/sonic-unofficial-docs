# gnmi-state platform 調査メモ (Phase H)

調査対象: `sonic-net/sonic-gnmi`
調査日: 2026-05-19

## 調査方法

- `gnmi_server/connection_manager.go` 全行精読
- `gnmi_server/client_subscribe.go` — setConnectionManager / PrepareRedis 呼び出しフロー
- `gnmi_server/server.go` — Subscribe RPC ハンドラ
- `sonic_db_config/db_config.go` — GetDbDefaultNamespace の実装確認
- platform / hwsku / DEVICE_METADATA / SAI 関連 grep（全ファイル）

## 主な知見

### プラットフォーム非依存

- `connection_manager.go` は SAI API を一切 import しない
- `DEVICE_METADATA|localhost.platform` / `hwsku` を参照しない
- ASIC 種別に応じた分岐コードなし
- HSet 値は `"active"` 固定、テーブル名は `"TELEMETRY_CONNECTIONS"` 固定

### namespace 依存

- `PrepareRedis()` は `GetDbDefaultNamespace()` を呼ぶ
  - `sonic_db_config/db_config.go:28-30`: `return SONIC_DEFAULT_NAMESPACE, nil` — 常に空文字列
- multi-ASIC 環境でも **デフォルト namespace の STATE_DB のみ** を対象とする
- `telemetry` デーモンは通常 1 プロセス（multi-asic 対応のマルチインスタンス起動なし）

### VS (Virtual Switch)

- Redis が動作していれば実 ASIC と同一動作
- SAI capability フォールバックのような特別処理なし

## grep 証跡

```
grep -rn "platform\|DEVICE_METADATA\|hwsku\|TLS\|tls\|ASIC\|sai_" gnmi_server/connection_manager.go
# → 0 件

grep -rn "MULTI_ASIC\|multi.asic\|CheckDbMultiNamespace" gnmi_server/connection_manager.go gnmi_server/client_subscribe.go
# → 0 件

grep -n "GetDbDefaultNamespace" sonic_db_config/db_config.go
# → L28: func GetDbDefaultNamespace() (ns string, err error) {
# → L30:     return SONIC_DEFAULT_NAMESPACE, nil
```
