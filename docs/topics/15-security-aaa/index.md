---
title: Security / AAA / FIPS / Hardening
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/management/aaa-improvements.md
  - docs/architecture/pw-hardening-design.md
  - docs/system/sonic-container-hardening.md
  - docs/management/tacacs-authentication.md
  - docs/management/sonic-tacacs-improvement.md
  - docs/management/tacacs-test-plan.md
  - docs/management/tacacs-passkey-encryption.md
  - docs/management/radius-management-user-authentication.md
  - docs/management/hld-ldap.md
  - docs/management/default-credential-management-for-california-sb-327-conformance.md
  - docs/reference/cli/config-aaa.md
  - docs/reference/config-db/tacplus-server.md
  - docs/reference/config-db/ldap-server.md
  - docs/reference/yang/sonic-system-aaa.md
  - docs/management/ssh-server-global-config-hld.md
  - docs/management/serial-console-global-config-hld.md
  - docs/system/banner-messages-hld.md
  - docs/system/reset-local-users-passwords-during-init-hld.md
  - docs/switching/macsec-sonic-high-level-design-document.md
  - docs/switching/sonic-hld-deterministic-macsec-backend-selection-for-gearbox-ports.md
  - docs/switching/sonic-sai-post-support-for-macsec.md
  - docs/system/sonic-openssl-fips-140-3-hld.md
  - docs/system/sonic-fips-deployment.md
  - docs/system/hld-secure-boot.md
  - docs/system/secure-upgrade.md
keywords:
  - Security
  - AAA
  - TACACS+
  - RADIUS
  - FIPS
  - hardening
  - 認証
  - 認可
  - auditd
  - SSH
---

# Security / AAA / FIPS / Hardening

この章は、SONiC で「誰がログインできるか」「どの経路で管理できるか」「データプレーンの暗号と完全性」「起動とアップグレードの信頼チェーン」を一望するための入口です。既存ページは AAA、SSH、MACsec、FIPS、secure boot などの HLD 単位に分かれているため、ここでは管理者が「セキュリティ要件をどこに落とすか」を考える順に並べ直します。

SONiC のセキュリティは大きく三つの層に分かれます。第一は control plane で、TACACS+ / RADIUS / LDAP / local user による認証と、SSH / serial console / banner などの管理面ポリシーが該当します。第二は data plane で、MACsec / MKA とその ASIC / Gearbox サイドの実装が該当します。第三は platform で、OpenSSL FIPS、secure boot、secure upgrade、container hardening、SAI POST が該当します。本章ではこの分類で既存 HLD を再配置します。

## この章で答える質問

- AAA、TACACS+、RADIUS、LDAP、local user はどの順番で読むのか。
- FIPS、MACsec、MKA、secure boot、secure upgrade は同じ章で扱うのか、それぞれどう違うのか。
- password hardening、default credential、SSH / serial console policy はどの設定に入るのか。
- container hardening、OpenSSL FIPS、SAI POST はどの層の保護で、どの章と接続するのか。

## 読み進め方

1. [概念](concept.md): control plane / data plane / platform security の三層分類と用語整理。
2. [アーキテクチャ](architecture.md): AAA login flow、`hostcfgd`、PAM、NSS、`config-db` の経路。
3. [設定](setup.md): TACACS+ / RADIUS / LDAP / local user / SSH / banner の最小構成。
4. [運用](operations.md): password policy、default credential、reset、トラブルシュート。
5. [内部実装](internals.md): MACsec / MKA、Gearbox backend、SAI POST のデータプレーン側。
6. [発展トピック](advanced.md): OpenSSL FIPS、secure boot、secure upgrade、container hardening。

## 関連章

- [SONiC 全体像と設定基盤](../01-overview/index.md): `CONFIG_DB` と daemon の前提。
- [ACL / CoPP / Mirror](../07-acl-copp-mirror/index.md): 管理プレーン保護として CoPP を併用する場合の接続点。
- [Reboot / Upgrade / Lifecycle](../11-reboot/index.md): secure upgrade とライフサイクルの全体像。

## 関連ページ

- [AAA improvements](../../management/aaa-improvements.md)
- [Password hardening 設計](../../architecture/pw-hardening-design.md)
- [Container hardening](../../system/sonic-container-hardening.md)

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)

**派生で読むべき章**

- [gNMI / gNOI / OpenConfig / YANG](../10-gnmi-openconfig/index.md)

**補完的に読む章**

- [Telemetry / SNMP / Observability](../09-telemetry-snmp/index.md)
- [NAT / DHCP Relay / Time-DNS Services](../16-nat-dhcp-dns/index.md)
- [Build / Packaging / Application Extension](../19-build-packaging/index.md)

