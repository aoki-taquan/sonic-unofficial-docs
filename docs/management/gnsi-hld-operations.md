---
title: gNSI 設定と運用（gNMI フラグ / YANG / 運用イメージ）
description: gNSI を有効化する gNMI サーバの設定フラグ、関連 OpenConfig YANG モデル、CONFIG_DB / CLI と、Certz
  / Credentialz の運用 rotate イメージを扱う。Certz / Authz / Pathz は master 取り込み済、Credentialz
  は HLD 提案のみで未実装。
area: management
verification: discrepancy-found
last_verified: 2026-05-11
page_kind: split-child
monitor: partially_implemented
sources:
- repo: sonic-net/SONiC
  path: doc/mgmt/gnmi/gnsi.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
- repo: sonic-net/sonic-gnmi
  path: gnmi_server/server.go
  ref: master
related:
  config_db:
  - TELEMETRY
  - GNMI
  yang:
  - openconfig-gnsi-certz
  - openconfig-gnsi-authz
  - openconfig-gnsi-pathz
  - openconfig-gnsi-credentialz
  - sonic-system-defaults
---

# gNSI 設定と運用

このページは [gNSI（概要ハブ）](gnsi-hld.md) の派生で、**設定経路と運用イメージ** に絞る。概念は [gnsi-hld-concepts.md](gnsi-hld-concepts.md)、内部実装は [gnsi-hld-internals.md](gnsi-hld-internals.md)、制限と HLD 乖離は [gnsi-hld-limitations.md](gnsi-hld-limitations.md) を参照。

!!! note "実装状況の境界（partially implemented）"
    本ページが扱うフラグ / YANG / 運用フローのうち、**Certz / Authz / Pathz の設定フラグと server 実装は master 取り込み済**（`sonic-gnmi` の `gnmi_server/gnsi_certz.go` / `gnsi_authz.go` / `gnsi_pathz.go`、および `Config` 構造体の `CertCRLConfig` / `AuthzPolicy` / `AuthzPolicyFile` / `AuthzMetaFile` / `PathzPolicy` / `PathzPolicyFile` / `PathzMetaFile`）[^2]。一方 **Credentialz 系のフラグ（HLD 記載の `SshCredMetaFile` / `ConsoleCredMetaFile` / `CredEntitiesMetaFile`）と gNSI server 側の Credentialz ハンドラは未実装** で、`sonic-gnmi` の `gnmi_server/` 配下に `gnsi_credentialz.go` が存在しない（`sonic_service_client/dbus_client.go` に dbus 経由の API stub のみ）[^2]。詳細は [gnsi-hld-limitations.md](gnsi-hld-limitations.md) を参照。

## 1. gNMI / sonic-gnmi 側のフラグ追加

[HLD](../reference/glossary.md#term-hld) は [gNMI](../reference/glossary.md#term-gnmi) server に以下のフラグを追加する想定[^1]:

| フラグ | 用途 |
|-------|------|
| `EnableAuthzPolicy` / `AuthzPolicyFile` | Authz ポリシー有効化と JSON ファイルパス |
| `EnablePathzPolicy` / `PathzPolicyFile` | Pathz 同上 |
| `CertCRLConfig` | CRL ディレクトリ。空で無効化 |
| `SshCredMetaFile` / `ConsoleCredMetaFile` | Credentialz メタデータ JSON |
| `CredEntitiesMetaFile` | gRPC クレデンシャルメタ |
| `AuthzMetaFile` / `PathzMetaFile` | 各サービスのメタデータ JSON |

state の保管先として **`STATE_DB`** にプロファイルの freshness / state を入れる（OpenConfig gNSI モデル準拠）[^1]。

!!! warning "実装側のフラグ名は HLD と異なる"
    実装での flag 名は `AuthzPolicy` / `PathzPolicy`（bool）+ `AuthzPolicyFile` / `PathzPolicyFile`（path）、CRL は `CertCRLConfig`、Certz メタは `CertzMetaFile`（HLD では `CredEntitiesMetaFile` 名で言及）[^2]。Credentialz 系の `SshCredMetaFile` / `ConsoleCredMetaFile` は `Config` 構造体に存在せず、未実装に分類される。詳細は [gnsi-hld-limitations.md](gnsi-hld-limitations.md) を参照。

## 2. 関連する CONFIG_DB

[CONFIG_DB](../reference/glossary.md#term-config_db) スキーマの追加は HLD 上「None」[^1]。状態は [STATE_DB](../reference/glossary.md#term-state_db) のみ。

## 3. 関連する CLI

該当する CLI は HLD で言及無し。`gnoi_client` 系のような専用 CLI は HLD 内で未定義。

## 4. 関連する YANG

OpenConfig 公開モデル（`openconfig-gnsi-certz` / `-authz` / `-pathz` / `-credentialz`）のパスを通す[^1]。

## 5. 運用イメージ

```bash
# Certz: gnxi profile に新証明書を流し込む
gnsi_client certz rotate --profile gnxi \
  --cert ./new.pem --bundle ./root.pem --crl-dir ./crls/

# 検証 OK で finalize
gnsi_client certz finalize

# Credentialz: SSH 認可鍵更新
gnsi_client credentialz rotate-account \
  --account root --keys ./new_authorized_keys.json
```

## 6. トラブルシューティング

- `Rotate` 後に証明書が古いまま: `Finalize` を送らずに stream を閉じた可能性。サーバ側のチェックポイント有無を確認
- sshd が再起動ループ: `ssh_mgmt.set` で投入した `authorized_keys` / `sshd_config` が壊れている。`restore_checkpoint` で巻き戻す
- `Pathz` の評価が遅い: gNMI request 冒頭で policy processor が呼ばれる仕様。policy 規模に対するレイテンシを観測

<!-- phase-boundary -->

確認コマンド例:

```bash
# gNOI/gNSI/gNMI クライアント疎通と server 状態
gnmi_cli -a 127.0.0.1:8080 -capabilities -insecure
docker exec gnmi ps aux | grep -E 'telemetry|gnmi'
docker logs gnmi 2>&1 | tail
redis-cli -n 4 hgetall 'GNMI|certs'
```

## 実装フェーズ境界

!!! info "gNSI sub-service 別の実装済 / 未実装 サマリ"
    本ページは `monitor: partially_implemented` で、HLD が提案する gNSI 4 サブサービス
    （Certz / Authz / Pathz / Credentialz）のうち **取り込み状況がサブサービス単位で
    異なる**。実装の有無を 1 枚の表に集約する（裏取りは `sonic-gnmi` の
    `gnmi_server/` 配下を直接確認。[discrepancy-index](../reference/verification/discrepancy-index.md)
    も参照）。

    | サブサービス | HLD 範囲 | 実装済 (master 取り込み済) | 未実装 (HLD 提案のみ) |
    |---|---|---|---|
    | Certz | `Rotate` / `Finalize` / Profiles / CRL / CSR | `gnmi_server/gnsi_certz.go` (1106 行) と `Config.CertCRLConfig` / `CertzMetaFile` が master にあり、CRL ディレクトリ監視と Rotate チェックポイントが動作[^2] | — |
    | Authz | gRPC メソッド単位の authz ポリシー | `gnmi_server/gnsi_authz.go` (292 行) と `Config.AuthzPolicy` / `AuthzPolicyFile` / `AuthzMetaFile`、`FileWatcher` による hot reload[^2] | HLD が示すフラグ名 `EnableAuthzPolicy` は実装に無く、`AuthzPolicy` (bool) に rename されている |
    | Pathz | gNMI path 単位の認可 | `gnmi_server/gnsi_pathz.go` (272 行) と `Config.PathzPolicy` / `PathzPolicyFile` / `PathzMetaFile`、Get/Set 経路の policy 評価が組まれている[^2] | HLD が示すフラグ名 `EnablePathzPolicy` は実装に無く、`PathzPolicy` (bool) に rename されている |
    | Credentialz | SSH / Console / gRPC クレデンシャル管理 | `sonic_service_client/dbus_client.go` の dbus API stub のみ (`// Credentialz service APIs`)[^2] | gNSI server 側のハンドラ (`gnsi_credentialz.go`) が存在せず、`Config.SshCredMetaFile` / `ConsoleCredMetaFile` / `CredEntitiesMetaFile` も未追加。`gnsi_client credentialz ...` の運用フローは HLD 段階で master では未対応 |

    凡例: 「実装済」= `sonic-gnmi` master で source path / 行数が確認できる範囲 /
    「未実装」= HLD には記載があるが対応 PR が未マージ、または server 側 code が存在しない範囲。
<!-- /phase-boundary -->

## 実装との乖離

`monitor: partially_implemented` — 部分実装 — HLD の中核は実装済みだが、フィールド / API / 制約のいくつかが上流に未取り込み、または挙動が緩和されている。 本ページは split-child のため、差分の主要根拠 / 影響 / 回避策は親ページ [gNSI 設定と運用 親ページ](gnsi-hld.md) の同セクション（`## 実装との乖離` または `!!! diff` ブロック）を参照のこと。

## 引用元

[^1]: `sonic-net/SONiC` `doc/mgmt/gnmi/gnsi.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
[^2]: `sonic-net/sonic-gnmi` `gnmi_server/server.go` L230-L247 (`Config` 構造体)、`gnmi_server/gnsi_certz.go` / `gnsi_authz.go` / `gnsi_pathz.go`、および `sonic_service_client/dbus_client.go` L53 (`// Credentialz service APIs` のみ)。master 確認。

<!-- glossary-links-injected: 658dfbdca882 -->
