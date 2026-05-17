# TELEMETRY — Phase F 副次 DB 書込・副次効果調査メモ

対象テーブル: `TELEMETRY` (`TELEMETRY|certs`, `TELEMETRY|gnmi`)
調査日: 2026-05-17

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-gnmi/gnmi_server/server.go` | gNMI サーバ本体 — TLS 証明書シンボリックリンク生成、gNMI Set 後の config save |
| `sonic-gnmi/gnmi_server/gnsi_certz.go` | 証明書アトミック更新ロジック (`atomicSetSrvCertKeyPair`, `atomicSetCACert`) |
| `sonic-gnmi/telemetry/telemetry.go` | プロセスエントリポイント — `save_on_set` フラグ設定、fsnotify 監視 |
| `sonic-gnmi/common_utils/notification_producer.go` | STATE_DB 通知チャネル (gNOI reboot 専用、TELEMETRY 設定には無関係) |
| `sonic-buildimage/dockers/docker-sonic-telemetry/telemetry.sh` | 起動スクリプト — STATE_DB chassis_serial_number 書込 (watchdog オプション) |

---

## 1. ファイルシステム副次効果 — TLS 証明書シンボリックリンク

`SrvAdvConfig()` (`server.go:L380-440`) は起動時に `TELEMETRY|certs` から読んだ証明書パスを
シンボリックリンクとして配置する。

| 生成パス | 内容 | 条件 |
|---------|------|------|
| `/keys/server_cert.lnk` → `<server_crt>` | サーバ証明書への symlink | `server_crt` + `server_key` が両方設定されている場合 |
| `/keys/server_key.lnk` → `<server_key>` | サーバ秘密鍵への symlink | 同上 |
| `/keys/ca_cert.lnk` → `<ca_crt>` | CA 証明書への symlink | `ca_crt` が設定されている場合 |

> evidence: `gnmi_server/gnsi_certz.go:925-990` (`atomicSetSrvCertKeyPair`, `atomicSetCACert`)

**アトミック更新**: 既存の symlink を削除 → 新規 symlink 作成の順で実行され、失敗時は旧 symlink を
復元する。gRPC の TLS ハンドシェイク時に `tls.LoadX509KeyPair(cfg.SrvCertLnk, cfg.SrvKeyLnk)` で
symlink 経由の証明書が読み込まれるため、symlink の差し替えのみで証明書ローテーションが可能。

> evidence: `gnmi_server/gnsi_certz.go:928-960`

---

## 2. ファイルシステム副次効果 — config_db.json 保存 (save_on_set=true)

`save_on_set=true` 設定時、gNMI Set RPC 完了後に `SaveOnSetEnabled()` が実行される。

```go
func SaveOnSetEnabled() error {
    sc, err := ssc.NewDbusClient()
    // ...
    sc.ConfigSave("/etc/sonic/config_db.json")
}
```

> evidence: `gnmi_server/server.go:1051-1068`

- **書込先**: `/etc/sonic/config_db.json` (ホストファイルシステム、hostcfgd 経由)
- **条件**: `TELEMETRY|gnmi.save_on_set == "true"` かつ gNMI Set RPC が成功した場合
- **失敗時**: dbus エラーをログ出力のみ (`log.V(0).Infof`) で Set RPC 自体は成功扱い。
  CONFIG_DB への変更は永続化されない（再起動時に消える）。

---

## 3. STATE_DB 副次書込 — chassis_serial_number (watchdog オプション)

`telemetry.sh` の先頭 (L3-22) に watchdog ロジックがある。環境変数
`TELEMETRY_WATCHDOG_SERIALNUMBER_PROBE_ENABLED=true` が設定されている場合、
起動時に `decode-syseeprom -s` でシリアル番号を取得し STATE_DB に書込む。

| DB | テーブル | フィールド | 書込条件 |
|----|---------|-----------|---------|
| `STATE_DB` | `DEVICE_METADATA\|localhost` | `chassis_serial_number` | watchdog オプション有効かつシリアル番号が変わっている場合 |

> evidence: `dockers/docker-sonic-telemetry/telemetry.sh:3-22`

この書込は TELEMETRY テーブルの内容とは無関係で、watchdog オプションの有効/無効のみに依存する。

---

## 4. CONFIG_DB への間接書込 — gNMI Set RPC (GnmiNativeWrite / TranslibWrite)

gnmi_server は `--gnmi_native_write=false` オプション (telemetry.sh:132 でハードコード) で起動する。
ただし `--gnmi_translib_write` は YANG トランスレーション経由で CONFIG_DB を更新できる。

`TELEMETRY` テーブルを読んで動作するサーバが、gNMI Set RPC 経由で CONFIG_DB を変更する場合、
変更対象は `TELEMETRY` に限らず、任意の translib 対応テーブルになる。
これは TELEMETRY テーブル設定の直接副次効果ではなく、gNMI サーバの動作による一般的な副次効果。

---

## 5. APPL_DB / COUNTERS_DB — 書込なし

`gnmi_server` および `telemetry.sh` は APPL_DB / COUNTERS_DB への直接書込を行わない。
gNMI の内部メトリクス (Get/Set/Subscribe カウンタ) はプロセス内メモリ (`common_utils/context.go` の
`globalCounters`) で管理され、DB には書込まれない。

> evidence: `common_utils/context.go:147-180`; `common_utils/shareMem.go` (共有メモリ経由、DB 非使用)

---

## 副次効果サマリ

| 種別 | 対象 | 条件 | evidence |
|------|------|------|---------|
| ファイル書込 (symlink) | `/keys/server_cert.lnk`, `/keys/server_key.lnk`, `/keys/ca_cert.lnk` | TLS 設定あり（起動時一回） | `gnsi_certz.go:925-990` |
| ファイル書込 | `/etc/sonic/config_db.json` | `save_on_set=true` + gNMI Set RPC 成功 | `server.go:1051-1068` |
| STATE_DB 書込 | `DEVICE_METADATA\|localhost.chassis_serial_number` | watchdog オプション有効時 | `telemetry.sh:3-22` |
| APPL_DB 書込 | なし | — | — |
| COUNTERS_DB 書込 | なし | — | — |
