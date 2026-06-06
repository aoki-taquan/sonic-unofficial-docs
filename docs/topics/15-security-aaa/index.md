---
title: Security / AAA / FIPS / Hardening
description: Security / AAA / FIPS / Hardening — この章は、SONiC で「誰がログインできるか」「どの経路で管理できるか」「データプレーンの暗号と完全性」「起動とアップグレードの信頼チェーン」を一望するための入口です。
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources: []
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
related:
  cli:
  - config aaa
  - show aaa
  - config acl
  - show acl
  - config banner
  - config interface
  - config vrf
  config_db:
  - AAA
  - RADIUS
  - TACPLUS
  - TACPLUS_SERVER
  - RADIUS_SERVER
  - ACL_RULE
  - ACL_TABLE
  yang:
  - sonic-copp
  - sonic-ssh-server
  - sonic-system-aaa
  - sonic-system-ldap
  - sonic-system-tacacs
  - sonic-vrf
  - sonic-crm
---

# Security / AAA / FIPS / Hardening

この章は、[SONiC](../../reference/glossary.md#term-sonic) で「誰がログインできるか」「どの経路で管理できるか」「データプレーンの暗号と完全性」「起動とアップグレードの信頼チェーン」を一望するための入口です。既存ページは [AAA](../../reference/glossary.md#term-aaa)、SSH、[MACsec](../../reference/glossary.md#term-macsec)、FIPS、secure boot などの [HLD](../../reference/glossary.md#term-hld) 単位に分かれているため、ここでは管理者が「セキュリティ要件をどこに落とすか」を考える順に並べ直します。

SONiC のセキュリティは大きく三つの層に分かれます。第一は control plane で、TACACS+ / [RADIUS](../../reference/glossary.md#term-radius) / LDAP / local user による認証と、SSH / serial console / banner などの管理面ポリシーが該当します。第二は data plane で、MACsec / MKA とその [ASIC](../../reference/glossary.md#term-asic) / Gearbox サイドの実装が該当します。第三は platform で、OpenSSL FIPS、secure boot、secure upgrade、container hardening、[SAI](../../reference/glossary.md#term-sai) POST が該当します。本章ではこの分類で既存 HLD を再配置します。

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
- [ACL / CoPP / Mirror](../07-acl-copp-mirror/index.md): 管理プレーン保護として [CoPP](../../reference/glossary.md#term-copp) を併用する場合の接続点。
- [Reboot / Upgrade / Lifecycle](../11-reboot/index.md): secure upgrade とライフサイクルの全体像。

## 関連ページ

- [AAA improvements](../../management/aaa-improvements.md)
- [Password hardening 設計](../../architecture/pw-hardening-design.md)
- [Container hardening](../../system/sonic-container-hardening.md)

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 行数 | 状態 | verification | 主目的 |
|---|---|---|---|---|
| advanced | 105 | ✅ 完成 | meta | 発展トピック |
| architecture | 81 | ⚠️ プレースホルダ | meta | アーキテクチャ・データフロー |
| concept | 154 | ✅ 完成 | meta | 概念・位置付け |
| internals | 138 | ✅ 完成 | code-verified | 内部実装 |
| operations | 193 | ✅ 完成 | meta | 運用・デバッグ |
| setup | 211 | ✅ 完成 | meta | セットアップ手順 |

<!-- /chapter-progress -->

<!-- next-reads -->
## 次に読むべき記事

**この章を読み進める順**

- [概要: 概念](concept.md)
- [アーキテクチャ](architecture.md)
- [設定](setup.md)
- [運用](operations.md)
- [内部実装](internals.md)
- [発展トピック](advanced.md)

**関連する HLD 7 件**

- [AAA Improvements（PAM / NSS / D-Bus / RBAC 多重ロール）](../../management/aaa-improvements.md)
- [TACACS+ 認証（pam_tacplus / nss_tacplus と AAA / TACPLUS テーブル）](../../management/tacacs-authentication.md)
- [TACACS+ 認証テストプラン（pam_tacplus + ssh login）](../../management/tacacs-test-plan.md)
- [P4Runtime PacketIO（generic netlink + send_to_ingress）](../../management/packetio.md)
- [Send to Ingress（CPU から ingress pipeline へパケット注入する hostif）](../../management/send-to-ingress-hld.md)
- [TACACS+ コマンド authorization / accounting（patched bash + audisp-tacplus）](../../management/sonic-tacacs-improvement.md)
- [config reload の event-driven 化（FEATURE.delayed + PortInitDone）](../../management/config-reload-enhancement.md)

**関連トラブルシュート 5 件**

- [SAI failure / syncd リスタート多発](../../reference/runbooks/sai-failure.md)
- [APPL_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)
- [orchagent が CPU 100% で詰まる](../../reference/runbooks/swss-orchagent-busy-loop.md)
- [ACL ルールが効かない / counter が増えない](../../reference/runbooks/acl-rule-no-hit.md)
- [DHCP Relay で IP が払い出されない](../../reference/runbooks/dhcp-relay.md)

<!-- /next-reads -->

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

<!-- glossary-links-injected: ae6c3c279b05 -->
