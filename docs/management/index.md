---
title: マネジメント
description: "マネジメント — CLI 以外の設定・管理経路、gNMI / REST / YANG / AAA / P4RT など管理プレーンを扱う章。"
area: management
verification: meta
last_verified: 2026-05-13
---

# マネジメント
CLI 以外の設定・管理経路、[gNMI](../reference/glossary.md#term-gnmi) / REST / [YANG](../reference/glossary.md#term-yang) / [AAA](../reference/glossary.md#term-aaa) / [P4RT](../reference/glossary.md#term-p4rt) など管理プレーンを扱う章。
## この章の読み方
目的の機能名からページを選び、設定名や CLI 名が必要な場合はリファレンス章を併読する。`Discrepancy-found` は [HLD](../reference/glossary.md#term-hld) と現行実装に差分が見つかったページなので、設計値として読む前に本文の注記を確認する。
## 検証状況
- ページ数: 43
- 分布: Code-verified: 30 / Discrepancy-found: 6 / HLD-only: 7

## 実装差分があるページ
- [P4RT アプリケーション（PINS の gRPC サービス、port 9559）](p4rt-application-hld.md)
- [Portable Console Device 設計（USB ベンダー console デバイスの抽象化）](portable-console-device-design.md)
- [SONiC YANG モデル記述ガイドライン（ABNF.json → sonic-*.yang）](sonic-yang-model-guidelines.md)
- [TACACS+ passkey 暗号化（key_encrypt + master key /etc/cipher_pass）](tacacs-passkey-encryption.md)
- [gNMI Master Arbitration（election ID と SetRequest 拡張）](gnmi-master-arbitration-hld.md)
- [gNSI（Certz / Authz / Pathz / Credentialz）の Rotate モデル](gnsi-hld.md)

## HLD-only のページ
- [AAA Improvements（PAM / NSS / D-Bus / RBAC 多重ロール）](aaa-improvements.md)
- [Console Switch（serial hub の reverse SSH 集約）](sonic-console-switch.md)
- [RADIUS 管理 user 認証（PAM / NSS / nss-mapper / 多サーバ priority）](radius-management-user-authentication.md)
- [Redis Client Manager（RCM: connection pool / transactional client）](redis-client-manager-rcm-hld.md)
- [SmartSwitch gNMI フィードバック（DPU APPL_STATE_DB と version_id）](smart-switch-gnmi-feedback-design-omit-in-toc.md)
- [TACACS+ 認証テストプラン（pam_tacplus + ssh login）](tacacs-test-plan.md)
- [gNMI Save-On-Set（Set ごとの ConfigDB 永続化）](save-on-set-hld.md)

## ページ一覧

| ページ | 検証 |
|---|---|
| [AAA Improvements（PAM / NSS / D-Bus / RBAC 多重ロール）](aaa-improvements.md) | HLD-only |
| [CMIS モジュール管理拡張（host_tx_signal / host_tx_ready の同期）](enhancement-of-cmis-module-management.md) | Code-verified |
| [Console Switch（serial hub の reverse SSH 集約）](sonic-console-switch.md) | HLD-only |
| [DHCPv4 Relay の giaddr を Primary サブネットに固定（VLAN_INTERFACE secondary）](dhcp-relay-v4-specify-gaaddr-as-primary-interface-s-gateway-explicitly.md) | Code-verified |
| [JSON Patch ordering（YANG 制約に従う apply-patch のステップ分割）](json-patch-ordering-using-yang-models.md) | Code-verified |
| [LDAP 認証（hostcfgd / nslcd / NSS / PAM 連携）](hld-ldap.md) | Code-verified |
| [Mgmt-Framework Transformer の model-based PUT/REPLACE と DELETE](model-based-replace-delete-in-mgmt-framework-transformer.md) | Code-verified |
| [OpenConfig Interfaces YANG（Ethernet 設定の REST/gNMI 対応と sonic-mgmt-common transformer）](openconfig-support-for-ethernet-interfaces.md) | Code-verified |
| [P4RT App の Read キャッシュ（PI 形式の table_entry_cache_）](p4rt-read-cache-hld.md) | Code-verified |
| [P4RT アプリケーション（PINS の gRPC サービス、port 9559）](p4rt-application-hld.md) | Discrepancy-found |
| [P4Runtime PacketIO（generic netlink + send_to_ingress）](packetio.md) | Code-verified |
| [PINS（P4 Integrated Network Stack / SDN 制御 SONiC）](pins-hld.md) | Code-verified |
| [Portable Console Device 設計（USB ベンダー console デバイスの抽象化）](portable-console-device-design.md) | Discrepancy-found |
| [RADIUS 管理 user 認証（PAM / NSS / nss-mapper / 多サーバ priority）](radius-management-user-authentication.md) | HLD-only |
| [Redis Client Manager（RCM: connection pool / transactional client）](redis-client-manager-rcm-hld.md) | HLD-only |
| [SONiC Application Extension 開発・移植ガイド](sonic-application-extension-guide.md) | Code-verified |
| [SONiC CLI 自動生成ツール（YANG → click plugin 自動生成）](sonic-cli-auto-generation-tool.md) | Code-verified |
| [SONiC Management Framework（REST / gNMI / Translib / Transformer）](sonic-management-framework.md) | Code-verified |
| [SONiC NOS の設定手段一覧（CLI / sonic-cfggen / config_db.json / RESTCONF / gNMI / ZTP / vtysh / redis / apply-patch）](sonic-nos-configuration-methods.md) | Code-verified |
| [SONiC User Manual の位置づけと SONiC CLI / 運用フローの全体像](sonic-user-manual.md) | Code-verified |
| [SONiC YANG モデル記述ガイドライン（ABNF.json → sonic-*.yang）](sonic-yang-model-guidelines.md) | Discrepancy-found |
| [SONiC gNMI Server インタフェース設計（CONFIG_DB / SONiC YANG / Generic Config Updater 連携）](sonic-gnmi-server-interface-design.md) | Code-verified |
| [SSH サーバ全体設定（SSH_SERVER.POLICIES）](ssh-server-global-config-hld.md) | Code-verified |
| [Send to Ingress（CPU から ingress pipeline へパケット注入する hostif）](send-to-ingress-hld.md) | Code-verified |
| [SmartSwitch gNMI フィードバック（DPU APPL_STATE_DB と version_id）](smart-switch-gnmi-feedback-design-omit-in-toc.md) | HLD-only |
| [TACACS+ passkey 暗号化（key_encrypt + master key /etc/cipher_pass）](tacacs-passkey-encryption.md) | Discrepancy-found |
| [TACACS+ コマンド authorization / accounting（patched bash + audisp-tacplus）](sonic-tacacs-improvement.md) | Code-verified |
| [TACACS+ 認証テストプラン（pam_tacplus + ssh login）](tacacs-test-plan.md) | HLD-only |
| [TACACS+ 認証（pam_tacplus / nss_tacplus と AAA / TACPLUS テーブル）](tacacs-authentication.md) | Code-verified |
| [YANG モデルによる ConfigDB 更新検証（GCU + ConfigDBConnector デコレータ）](sonic-config-update-validation-via-yang.md) | Code-verified |
| [config reload の event-driven 化（FEATURE.delayed + PortInitDone）](config-reload-enhancement.md) | Code-verified |
| [gNMI Master Arbitration（election ID と SetRequest 拡張）](gnmi-master-arbitration-hld.md) | Discrepancy-found |
| [gNMI Save-On-Set（Set ごとの ConfigDB 永続化）](save-on-set-hld.md) | HLD-only |
| [gNMI クライアントツールの使い方（gnmi_get / gnmi_set / gnmi_cli）](gnmi-usage.md) | Code-verified |
| [gNOI File.Remove と FactoryReset.Start（gNMI/UMF + DBUS host service）](gnoi-hld-for-file-and-factory-reset-apis.md) | Code-verified |
| [gNOI Healthz API（Get / Acknowledge / Artifact + DBUS host service）](gnoi-hld-for-healthz-api.md) | Code-verified |
| [gNOI OS API（Install / Activate / Verify と sonic-installer 連携）](gnoi-hld-for-os-apis.md) | Code-verified |
| [gNOI System Reboot / RebootStatus / CancelReboot（reboot method と sanity check）](gnoi-hld-for-system-apis.md) | Code-verified |
| [gNSI（Certz / Authz / Pathz / Credentialz）の Rotate モデル](gnsi-hld.md) | Discrepancy-found |
| [gRPC client（active-active DualToR / ycabled ↔ SoC 連携）](design-doc.md) | Code-verified |
| [シリアルコンソール全体設定（SERIAL_CONSOLE.POLICIES）](serial-console-global-config-hld.md) | Code-verified |
| [ポートベース IPv4 DHCP Server（kea-dhcp-server + dhcrelay Option 82 連携）](ipv4-port-based-dhcp-server-in-sonic.md) | Code-verified |
| [既定パスワードの初回ログイン強制変更（California SB-327 準拠）](default-credential-management-for-california-sb-327-conformance.md) | Code-verified |

<!-- glossary-links-injected: c0ffc85a39eb -->
