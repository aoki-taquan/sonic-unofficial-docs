---
title: gNSI 設定と運用（gNMI フラグ / YANG / 運用イメージ）
description: gNSI を有効化する gNMI サーバの設定フラグ、関連 OpenConfig YANG モデル、CONFIG_DB / CLI と、Certz
  / Credentialz の運用 rotate イメージを扱う。
area: management
verification: discrepancy-found
last_verified: 2026-05-11
page_kind: split-child
monitor: partially_implemented
sources:
- repo: sonic-net/SONiC
  path: doc/mgmt/gnmi/gnsi.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - TELEMETRY
  - GNMI
  - SYSLOG_SERVER
  - SYSLOG_CONFIG
  - SYSLOG_CONFIG_FEATURE
  - PORT
  - PORTCHANNEL
  cli:
  - show interfaces
  - show ip
  - config syslog
  yang:
  - openconfig-gnsi-certz
  - openconfig-gnsi-authz
  - openconfig-gnsi-pathz
  - openconfig-gnsi-credentialz
  - sonic-system-defaults
  - sonic-syslog
---

# gNSI 設定と運用

このページは [gNSI（概要ハブ）](gnsi-hld.md) の派生で、**設定経路と運用イメージ** に絞る。概念は [gnsi-hld-concepts.md](gnsi-hld-concepts.md)、内部実装は [gnsi-hld-internals.md](gnsi-hld-internals.md)、制限と HLD 乖離は [gnsi-hld-limitations.md](gnsi-hld-limitations.md) を参照。

## 1. gNMI / sonic-gnmi 側のフラグ追加

[HLD](../reference/glossary.md#term-hld) は gNMI server に以下のフラグを追加する想定[^1]:

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
    実装での flag 名は `AuthzPolicy` / `PathzPolicy`（bool）+ `AuthzPolicyFile` / `PathzPolicyFile`（path）、CRL は `CertCRLConfig`。詳細は [gnsi-hld-limitations.md](gnsi-hld-limitations.md) を参照。

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

## 引用元

[^1]: `sonic-net/SONiC` `doc/mgmt/gnmi/gnsi.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
