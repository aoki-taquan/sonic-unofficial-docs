---
title: gNSI 内部実装（Certz / Authz / Pathz / Credentialz handler と host service）
description: gNSI 各サービスの内部実装。Certz の Profile / CSR、Authz / Pathz のポリシー適用経路、Credentialz の gnsi_console / ssh_mgmt host service モジュールの責務を整理する。
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
  cli: []
  yang:
  - openconfig-gnsi-certz
  - openconfig-gnsi-authz
  - openconfig-gnsi-pathz
  - openconfig-gnsi-credentialz
---

# gNSI 内部実装

このページは [gNSI（概要ハブ）](gnsi-hld.md) の派生で、**4 サービスの内部実装と host service** に絞る。概念は [gnsi-hld-concepts.md](gnsi-hld-concepts.md)、設定 / 運用は [gnsi-hld-operations.md](gnsi-hld-operations.md)、制限と [HLD](../reference/glossary.md#term-hld) 乖離は [gnsi-hld-limitations.md](gnsi-hld-limitations.md) を参照。

!!! note "実装状況の境界（partially implemented）"
    以下の内部実装記述のうち、**Certz / Authz / Pathz の handler は `sonic-gnmi` に実装済**（`gnmi_server/gnsi_certz.go` / `gnsi_authz.go` / `gnsi_pathz.go`）で master 上で動作する。一方 **Credentialz の gNMI server handler のみ未配線** で、HLD 提案段階のまま対応 PR が未取り込み。具体的な PR 一覧と未対応 RPC は [gnsi-hld-limitations.md](gnsi-hld-limitations.md) を参照。

## 1. Certz

`Certz.Rotate` は **bidirectional streaming RPC** で以下を入れ替える[^1]:

- Server Certificate
- Root Certificate Bundle (Trust Bundle)
- Certificate Revocation List (CRL)
- Authentication Policy

### Profile

PKI 群を **SSL profile** 単位で束ねる。デフォルトは `gnxi` プロファイル（[gNMI](../reference/glossary.md#term-gnmi) / [gNOI](../reference/glossary.md#term-gnoi) / gNSI 自身が使う）[^1]:

| RPC | 用途 |
|-----|------|
| `GetProfileList` | プロファイル列挙 |
| `AddProfile` | 新規追加 |
| `DeleteProfile` | 削除（**`gnxi` は削除不可**）[^1] |

### CSR

server がオプションで対応すれば、`Rotate` ストリーム内で CSR を生成し、外部 CA に署名させて取り込める[^1]:

- `CanGenerateCSR()` で能力照会
- `Rotate(GenerateCSRRequest)` で CSR 取得 → 外部署名 → `Rotate` で証明書取り込み

## 2. Authz

gRPC アクセスのポリシーベース認可。policy は **JSON 文字列**（[gRPC A43](https://github.com/grpc/proposal/blob/master/A43-grpc-authorization-api.md) スキーマ）で記述し、gRPC server に file watcher + Interceptor で適用する[^1]。

- `Authz.Rotate()`: ポリシー差し替え（Certz と同じ Finalize/rollback 動作）
- `Authz.Probe()`: 現行ポリシーで指定リクエストが通るかテスト

## 3. Pathz

**gNMI パス単位** で read/write を絞り込む認可。ポリシープロセッサが gNMI request の冒頭で評価する[^1]。

- `Pathz.Rotate()` / `Pathz.Probe()`

## 4. Credentialz

コンソールユーザと SSH の鍵・パスワード管理。host service モジュール経由で `/etc/passwd` / `/etc/shadow` / `/etc/sshd/...` 等を直接書き換える[^1]。

### Console (`gnsi_console` host service module)

```mermaid
sequenceDiagram
    participant FE as gNSI Credentialz FE
    participant HS as gnsi_console
    FE->>HS: create_checkpoint
    HS->>HS: cp /etc/passwd /etc/shadow → backup
    FE->>HS: set (JSON: ConsolePasswords[])
    HS->>HS: replace /etc/passwd /etc/shadow
    alt Finalize 受領
        FE->>HS: delete_checkpoint
        HS->>HS: backup を破棄
    else 未 Finalize で stream 終了
        FE->>HS: restore_checkpoint
        HS->>HS: backup を上書き復元
        HS->>HS: backup を破棄
    end
```

`set` の payload[^1]:

```json
{ "ConsolePasswords": [ {"name": "alice", "password": "..."} ] }
```

### SSH (`ssh_mgmt` host service module)

`gnsi_console` と同じ checkpoint / set / restore / delete 構造。バックアップ対象ファイルが SSH 系全般（`sshd_config`、host key、各 home の `authorized_keys` / `authorized_users`、CA 公開鍵）に拡大される[^1]。

`set` のリクエスト種別[^1]:

| 種別 | キー | 動作 |
|------|------|------|
| 認可鍵 | `SshAccountKeys` | `/home/<account>/.ssh/authorized_keys` を置換 + sshd 再起動 |
| 認可ユーザ | `SshAccountUsers` | `/home/<account>/.ssh/authorized_users` を置換 + sshd 再起動 |
| CA 公開鍵 | `SshCaPublicKey` | `/etc/sshd/ssh_ca_pub_key` を置換 + sshd 再起動 |

`options` には OpenSSH の `from=...` 等の鍵オプションをそのまま渡せる[^1]。

<!-- phase-boundary -->
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

<!-- glossary-links-injected: fb8223262e3a -->
