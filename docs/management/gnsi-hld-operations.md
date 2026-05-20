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
    本ページが扱うフラグ / YANG / 運用フローのうち、**Certz 系の設定経路（`EnableCrl` / `CertCRLConfig` など）と Rotate / Finalize 運用は master に取り込み済** で動作する。一方 **Authz / Pathz / Credentialz 系のフラグ（`EnableAuthzPolicy` / `EnablePathzPolicy` / `SshCredMetaFile` など）は未実装** で対応 PR が未取り込み。詳細は [gnsi-hld-limitations.md](gnsi-hld-limitations.md) を参照。

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

!!! info "Phase 別の実装済 / 未実装 サマリ"
    本ページは `monitor: partially_implemented` で、HLD で示された一連の機能
    が **段階的に取り込まれている** 状態を扱う。フェーズ毎の実装境界を
    1 枚の表に集約する (詳細は本ページ上部の `diff` admonition および
    [discrepancy-index](../reference/verification/discrepancy-index.md) を参照)。

    | Phase | 範囲 (機能 / 段階) | 実装済 (master 取り込み済) | 未実装 (HLD 提案のみ) |
    |---|---|---|---|
    | Phase 1 — 基本機能 | HLD §概要 / §設計の中核ユースケース | 取り込み済 — 本ページの「実装の概観」「実装詳細」節および `diff` admonition の現状側を参照 | — (Phase 1 は実装済) |
    | Phase 2 — 拡張機能 | HLD §拡張 / §追加要件 / §周辺統合 | 一部のみ取り込み済 — 本ページ「実装詳細」の補足参照 | 未実装 / 未マージ — HLD §未対応箇所、本ページ「制限事項」および `diff` admonition の差分側に列挙 |
    | Phase 3 — 将来拡張 | HLD §Future Work / §将来課題 | — | 未実装 — HLD 提案段階。対応 PR は確認されていない (last_verified 時点) |

    凡例: 「実装済」=現行 master で動作確認できる範囲 / 「未実装」=HLD には記載があるが対応 PR が未マージまたは設計のみで code が存在しない範囲。
<!-- /phase-boundary -->

## 引用元

[^1]: `sonic-net/SONiC` `doc/mgmt/gnmi/gnsi.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- glossary-links-injected: 658dfbdca882 -->
