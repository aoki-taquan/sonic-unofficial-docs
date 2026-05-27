---
title: gNSI 制限事項と HLD との乖離（Credentialz 未配線・フラグ名差異）
description: gNSI HLD と sonic-gnmi 実装の乖離。Credentialz サーバ handler 未配線、gNMI server フラグ名の差異、STATE_DB プロファイル状態テーブル不在を整理する。
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

# gNSI 制限事項と HLD との乖離

このページは [gNSI（概要ハブ）](gnsi-hld.md) の派生で、**制限事項と実装乖離** に絞る。概念は [gnsi-hld-concepts.md](gnsi-hld-concepts.md)、設定 / 運用は [gnsi-hld-operations.md](gnsi-hld-operations.md)、内部実装は [gnsi-hld-internals.md](gnsi-hld-internals.md) を参照。

## 1. HLD レベルの制限事項

- **CRL の蓄積**: Go 版 gRPC は起動以降の **CRL 全履歴** を必要とする[^1]。CRL ローテーション回数に応じてメモリ・I/O が線形に増える
- **`gnxi` profile は削除不可**[^1]
- **同時 Rotate 拒否**: 各サービスで Concurrent Rotate を reject する想定（Unit Test cases 明記）[^1]
- [HLD](../reference/glossary.md#term-hld) 自体に `Pathz` の policy 形式詳細は無く、policy processor のライブラリ実装は別途必要[^1]
- Credentialz の `set` で sshd は再起動される。short-window で SSH 接続が拒否される可能性[^1]

## 2. 干渉する機能

- **[gNMI](../reference/glossary.md#term-gnmi) Master Arbitration**: gNSI の `Rotate` は `Set` ではないので Master Arbitration の対象外
- **[gNOI](../reference/glossary.md#term-gnoi) FactoryReset**: `retain_certs=true` で Credentialz / Certz が積んだ証明書を残せるかは gNOI 側のオプション扱い
- **TACACS / Linux PAM**: Credentialz が `/etc/passwd` / `/etc/shadow` を置換するため、TACACS や [RADIUS](../reference/glossary.md#term-radius) 連携の有無で挙動が変わる
- **既存 sshd 設定**: `ssh_mgmt.set` は既存 `authorized_keys` を **置換** する（追記ではない）。warm boot 時の rollback ファイル管理に注意

## 3. HLD と実装の差分

!!! diff "HLD と実装の差分"
    実コード裏取りで判明した HLD との差分（verified at: 2026-05-09, sonic-gnmi @ `eb635b76`）。HLD の 4 サービス（Authz / Certz / Pathz / Credentialz）のうち 3 つは取り込み済みで、Credentialz のみ未取り込みという **一部のみの部分実装** 状態:

    - **Credentialz handler の gNMI server 実装は未取り込み**: HLD は Authz / Certz / Pathz / Credentialz の 4 サービスを並べて記述するが、現行 master の `sonic-gnmi/gnmi_server/` には `gnsi_authz.go` / `gnsi_certz.go` / `gnsi_pathz.go` のみが存在し、`gnsi_credentialz.go` 相当のサーバ側ハンドラは無い。Credentialz 関連は `sonic-gnmi/sonic_service_client/dbus_client.go:53-` の **dbus client 補助コード**として準備されているのみ（`TestCredentialzDbusMethods` 等のテストが存在）。
    - **gNMI server フラグ名の差異**: HLD で言及された `EnableAuthzPolicy` / `EnablePathzPolicy` という flag 名ではなく、`sonic-gnmi/gnmi_server/server.go:240,243` では `AuthzPolicy bool` / `PathzPolicy bool` という config 構造体フィールドとして実装されている。ポリシーファイルパスは `AuthzPolicyFile` / `PathzPolicyFile`、CRL は `CertCRLConfig`（HLD の表記と差異あり）。
    - **STATE_DB gNSI profile state テーブルは未確認**: `sonic-swss-common/common/schema.h` 内に `GNSI` 関連テーブル定義は見当たらなかった（profile 状態は gNMI サーバプロセス内のメモリ／ファイルで保持される実装と推測される）。

    主要な合致点として、`sonic-gnmi/gnmi_server/gnsi_authz.go` (GNSIAuthzServer / Probe / Get / Rotate)、`gnsi_certz.go` (GNSICertzServer)、`gnsi_pathz.go` (GNSIPathzServer)、および `sonic-host-services/host_modules/gnsi_console.py` (`MOD_NAME = 'gnsi_console'`)、`ssh_mgmt.py` (`MOD_NAME = 'ssh_mgmt'`) は HLD どおり実装されている。

    **読者への影響**:

    - **Credentialz の SSH 鍵 / パスワード rotate を gNSI 経由で要求しても、現状はサーバハンドラが無いため `Unimplemented` で失敗する**。dbus client 側のコードは準備されているが、gNMI server からのディスパッチ経路が未配線。
    - HLD どおりに `EnableAuthzPolicy` / `EnablePathzPolicy` という flag 名で telemetry 設定を書こうとすると認識されない。**正しいフィールド名は `AuthzPolicy` / `PathzPolicy`（boolean）と `AuthzPolicyFile` / `PathzPolicyFile`（path）**。
    - STATE_DB から gNSI profile 状態を query するスクリプトを書くと **常に空** が返る（profile 状態は gNMI プロセスのメモリ内保持）。

    **回避策 / 対応方法**:

    - Credentialz が必要な場合は、現状 `ssh_mgmt` host service（dbus 経由）を直接叩くか、`/etc/ssh/sshd_config` / `authorized_keys` をホスト側スクリプトで管理する。gNSI 経由は上流の handler 実装待ち。
    - Authz / Pathz / CRL を有効化する設定は、telemetry config 構造体の `AuthzPolicy = true` / `AuthzPolicyFile = "/path/to/policy.json"` / `PathzPolicy = true` / `PathzPolicyFile = "..."` / `CertCRLConfig = "..."` を設定する。HLD の flag 名表記には引きずられない。
    - gNSI profile state を観測したい場合は、gNMI Probe / Get RPC を直接叩いて handler の戻り値を見る。STATE_DB 経由は機能しない。

    ### 再裏取り追補（2026-05-11）

    - `sonic-gnmi/gnmi_server/gnsi_authz.go` / `gnsi_certz.go` / `gnsi_pathz.go` は実装済みだが、`gnsi_credentialz.go` 相当のサーバハンドラは不在 (`ls .cache/sonic-sources/sonic-gnmi/gnmi_server/gnsi_*.go` で credentialz ファイル無し)。
    - フラグ名差異: HLD `EnableAuthzPolicy` → 実装 `AuthzPolicy` (`server.go:240,243`)、ポリシーファイル `AuthzPolicyFile` / `PathzPolicyFile`、CRL は `CertCRLConfig`。
    - Credentialz の dbus client (`sonic_service_client/dbus_client.go:53-`) は準備済み。`TestCredentialzDbusMethods` テストも存在。サーバ側ディスパッチが未配線。
    - STATE_DB に gNSI profile 状態テーブル無し (`grep -i gnsi .cache/sonic-sources/sonic-swss-common/common/schema.h` 0 件)。状態は gnmi プロセス内メモリ保持。
    - 関連 PR: `sonic-gnmi` の Authz/Pathz/Certz は 2024 年内に複数 PR で merge、Credentialz は draft 段階で停止。
    - **追加回避策コマンド**: SSH 鍵 rotate を gNSI 経由で実施したい場合 — 現状は `dbus-send --system --dest=org.SONiC.HostService --type=method_call /org/SONiC/HostService/ssh_mgmt org.SONiC.HostService.ssh_mgmt.<method>` で dbus 直叩き。

    > 分類: `monitor: partially_implemented` — HLD の 4 サービスのうち 3 つは取り込み済みで、Credentialz のサーバハンドラ部分のみが未配線。

    #### 関連 GitHub Issue / PR

    - [sonic-gnmi #559: Implements the frontend logic for gNSI Certz (merged)](https://github.com/sonic-net/sonic-gnmi/pull/559) — gNSI Certz サブシステムのフロントエンド実装 PR。
    - [sonic-gnmi #616: TestGnsiCertzServer/Rotate_ConcurrentRPC_ReturnsAborted is flaky (open)](https://github.com/sonic-net/sonic-gnmi/issues/616) — Certz Rotate の並行 RPC 試験 flaky issue。実装の成熟度を示す。
    - gNSI Authz / Pathz / Credentialz の包括的トラッキング Issue は確認できず、各サブシステムは個別 PR で順次取り込まれている。

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

## 実装との乖離

`monitor: partially_implemented` — 部分実装 — HLD の中核は実装済みだが、フィールド / API / 制約のいくつかが上流に未取り込み、または挙動が緩和されている。 本ページは split-child のため、差分の主要根拠 / 影響 / 回避策は親ページ [gNSI 制限事項と HLD との乖離 親ページ](gnsi-hld.md) の同セクション（`## 実装との乖離` または `!!! diff` ブロック）を参照のこと。

## 引用元

[^1]: `sonic-net/SONiC` `doc/mgmt/gnmi/gnsi.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- glossary-links-injected: df94ce4c9c04 -->
