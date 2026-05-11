---
title: 運用
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/architecture/pw-hardening-design.md
  - docs/management/default-credential-management-for-california-sb-327-conformance.md
  - docs/system/reset-local-users-passwords-during-init-hld.md
  - docs/management/tacacs-test-plan.md
  - docs/management/aaa-improvements.md
---

# 運用

AAA と管理面ポリシーは「動いている間は気付かれない」種類の機能のため、運用上は事故の予防と回復の手順が中心になります。ここでは password、default credential、reset、フォールバック確認の四つを順に扱います。

## Password hardening

local user のパスワードに対する最低長、強度、履歴、有効期限、ロックアウトなどのポリシーは [password hardening 設計](../../architecture/pw-hardening-design.md) に集約されています。SONiC は Linux 標準の `pam_pwquality` / `pam_faillock` / `chage` を組み合わせ、`CONFIG_DB` 経由で設定をテンプレート展開します。

運用観点では次を確認します。

- 既定パスワードを使い続けていないか。長期運用機で最も多い指摘箇所です。
- パスワード履歴と有効期限が監査要件と一致しているか。
- ロックアウトのしきい値が「正常な誤入力」を巻き込まない値になっているか。

## Default credential management

工場出荷時の `admin/YourPaSsWoRd` のような初期パスワードは、初回ログイン時に強制的に変更させる仕組みが [default credential management](../../management/default-credential-management-for-california-sb-327-conformance.md) で導入されています。California SB-327 をはじめとする規制対応が主目的で、初期 image のリプレース運用や ZTP からの初回起動時に必ず通る経路です。

## Password reset と init 時の挙動

オンサイト作業でローカルアカウントをリセットする手段は、コンソールアクセスを前提に [reset local users passwords during init HLD](../../system/reset-local-users-passwords-during-init-hld.md) で定義されています。初期化トリガー、対象アカウント、ログの残し方の三点を、本番投入前に必ず読み合わせます。

## フォールバック確認

外部 AAA を導入したら、必ず「サーバー全滅時に local で入れるか」を試験で確認します。[TACACS test plan](../../management/tacacs-test-plan.md) には、プライマリ TACACS+ ダウン時のフォールバックや、サーバー応答遅延時の挙動など、現場で詰まりやすい組み合わせが網羅されています。 [AAA improvements](../../management/aaa-improvements.md) には login flow の改善履歴があり、過去バージョンとの差分の根拠を当たれます。

## トラブルシュートの順序

1. `sshd` のログ（`journalctl -u ssh`）で接続拒否か認証失敗かを切り分ける。
2. PAM 経路を疑う場合、`/etc/pam.d/sshd` 等が `hostcfgd` 出力どおりかを比較する。
3. NSS 経路を疑う場合、`getent passwd <user>` でバックエンドの解決状況を確認する。
4. TACACS+ 経路は `/etc/tacplus_*` の中身と、サーバー到達性（management VRF 経由含む）を確認する。
5. ロックアウトが疑われる場合は `pam_faillock` の状態と、シリアル経由の local ログインの可否を確認する。

データプレーンの暗号や platform 信頼チェーンの運用は [内部実装](internals.md) と [発展トピック](advanced.md) で扱います。
