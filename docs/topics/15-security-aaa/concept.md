---
title: 概念
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/management/aaa-improvements.md
  - docs/architecture/pw-hardening-design.md
  - docs/system/sonic-container-hardening.md
---

# 概念

SONiC のセキュリティ機能は、ひとつの巨大なサブシステムではなく、Linux の標準スタック（PAM、NSS、OpenSSL、systemd）と SONiC 固有のデーモン（`hostcfgd`、`macsecmgr`、SAI）に薄く重なって実装されています。最初に「どの層のどの問題を解いているか」を分類しておくと、個別 HLD を読む順番が決まります。

## 三層のセキュリティ境界

| 層 | 守るもの | 主な機能 | 主な実装 |
| --- | --- | --- | --- |
| Control plane | 誰がスイッチを操作できるか | AAA、TACACS+、RADIUS、LDAP、local user、SSH、serial console、banner、password policy | PAM / NSS、`hostcfgd`、`config-db` |
| Data plane | リンク上の暗号と完全性 | MACsec、MKA、Gearbox 経由の MACsec | `macsecmgr`、`wpa_supplicant`、SAI、PHY |
| Platform | 起動・実行・更新の真正性 | OpenSSL FIPS、secure boot、secure upgrade、container hardening、SAI POST | GRUB、shim、OpenSSL FIPS provider、Docker、SAI |

このマトリクスは [概要](index.md) で示した三層と対応しています。以降のページは概ねこの順で並べます。

## AAA の語彙

AAA（Authentication / Authorization / Accounting）は、SONiC では Linux の PAM/NSS を介して TACACS+ / RADIUS / LDAP / local の各バックエンドに振り分けられます。詳細な実装は [AAA improvements](../../management/aaa-improvements.md) に集約されており、login flow とフォールバック順序の改善が議論されています。

- Authentication: ユーザーが本人であることの確認。`login_method` で複数のバックエンドを順序付けます。
- Authorization: そのユーザーが実行できるコマンドの範囲。TACACS+ の per-command 認可や、local の sudoers でカバーされます。
- Accounting: 実行履歴のログ送信。主に TACACS+ で利用されます。

local user の取り扱いは [password hardening 設計](../../architecture/pw-hardening-design.md) と [default credential management](../../management/default-credential-management-for-california-sb-327-conformance.md) で別途厳格化されています。これは初期パスワードや弱いパスワードの利用を防ぐためのもので、認証バックエンドの選択とは独立した層です。

## 管理面ポリシーの位置付け

SSH や serial console、banner は「認証の入口の設定」であり、AAA とは別レイヤーで動きます。`hostcfgd` が `CONFIG_DB` を購読し、`/etc/ssh/sshd_config` などのファイルへ反映します。詳細は [SSH server global config HLD](../../management/ssh-server-global-config-hld.md) と [serial console global config HLD](../../management/serial-console-global-config-hld.md) を参照してください。banner は [banner messages HLD](../../system/banner-messages-hld.md) にまとまっています。

## Data plane security の輪郭

MACsec はリンク単位の L2 暗号化で、SAI MACsec object と、ホスト側の `wpa_supplicant` ベースの MKA 実装を組み合わせて動きます。本章では [内部実装](internals.md) で扱い、設定面は [設定](setup.md) では深く触れません。MACsec の前提は [MACsec HLD](../../switching/macsec-sonic-high-level-design-document.md) を直接読むのが早道です。

## Platform security の輪郭

OpenSSL FIPS、secure boot、secure upgrade、container hardening は、いずれも「コードや鍵が改ざんされていないか」を担保する仕組みです。それぞれ独立した HLD があり、本章では [発展トピック](advanced.md) でまとめて扱います。SAI POST は MACsec 系の起動時健全性チェックで、[SAI POST support for MACsec](../../switching/sonic-sai-post-support-for-macsec.md) を参照します。

## 章の境界

- 管理プレーン向け CoPP（Control Plane Policing）は本章ではなく [ACL / CoPP / Mirror](../07-acl-copp-mirror/index.md) で扱います。本章は「誰が触れるか」の認証面、CoPP 章は「触ってよいパケットの帯域」の制御面と切り分けます。
- secure upgrade はライフサイクル全体の [Reboot / Upgrade / Lifecycle](../11-reboot/index.md) と重複しますが、本章では「信頼チェーン」の観点に限定し、warm/fast/SONiC-To-SONiC の手順は 11 章に委ねます。
