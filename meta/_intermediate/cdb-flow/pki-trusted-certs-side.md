# pki-trusted-certs side-effects (Phase F) 調査メモ

調査日: 2026-05-19
対象: `SECURITY_PROFILES` / `SECURITY_GLOBAL` / gNSI Certz

## 概要

`SECURITY_PROFILES` / `SECURITY_GLOBAL` を書き込む production ハンドラ (orchagent / translib) は community master に存在しない。そのため CONFIG_DB 操作に直接起因する副次 DB 書込はない。副次作用は gNSI Certz の Rotate RPC・起動処理から発生する。

## STATE_DB 副次書込

### CREDENTIALS|CERT|<profileID>

- **タイミング**: gNSI Certz 起動時 (bootstrapDefaultProfile) + Rotate RPC activateEntity + finalizeProfile
- **操作**: HSET
- **フィールド**: `certificate_version`, `certificate_created_on`, `ca_trust_bundle_version`, `ca_trust_bundle_created_on`, `certificate_revocation_list_bundle_version`, `authentication_policy_version`
- **DB番号**: 6 (STATE_DB) — `common_utils/notification_producer.go:16`
- **証拠**:
  - `gnsi_certz.go:134-138` — bootstrapDefaultProfile で writeEntityFreshness × 4
  - `gnsi_certz.go:502` — activateEntity で writeEntityFreshness
  - `gnsi_certz.go:688-715` — writeEntityFreshness 実装
  - `gnsi_certz.go:1036-1057` — writeCredentialsMetadataToDB (HSET, REDIS unavailable ハンドリング)

Redis が利用不可の場合は `"REDIS is not available: ..."` をログ出力して継続。証明書ファイル自体には影響しない。

## ファイルシステム副作用 — シンボリックリンク更新

| シンボリックリンク | 更新関数 | タイミング | 証拠 |
|-------------------|---------|----------|------|
| `cfg.SrvCertLnk` (`/keys/server_cert.lnk`) | `atomicSetSrvCertKeyPair` | Rotate certType エンティティ activateEntity | `gnsi_certz.go:472, 924-963` |
| `cfg.SrvKeyLnk` (`/keys/server_key.lnk`) | `atomicSetSrvCertKeyPair` | 同上 | `gnsi_certz.go:472, 924-963` |
| `cfg.CaCertLnk` (`/keys/ca_cert.lnk`) | `atomicSetCACert` | Rotate tbType エンティティ activateEntity | `gnsi_certz.go:481, 966-989` |

これらのリンクは gRPC サーバが新規接続ごとに読み直す (`server.go:425-434`)。リンク更新後に張られた新規 TLS セッションは自動的に新証明書を使用。gRPC サーバ再起動は不要。`muPath.RWMutex` で読み書きの競合を防ぐ (`gnsi_certz.go:382-383`, `server.go:426-427`).

## CertzMetaFile — JSON ファイル更新

- **パス**: `/keys/grpc-version.json` (デフォルト。`Config.CertzMetaFile` で上書き可能)
- **タイミング**: gNSI Certz 起動直後 (`gnsi_certz.go:141`) + finalizeProfile 完了後 (`gnsi_certz.go:683-685`)
- **内容**: プロファイルごとの証明書バージョンメタデータ (JSON)
- **証拠**: `gnsi_certz.go:717-735` — saveCertzMetadata 実装

## CONFIG_DB / APPL_DB / ASIC_DB

副次書込なし。`SECURITY_PROFILES` を消費する translib / orchagent ハンドラが community master に存在しないため、伝播経路が存在しない。
