---
title: システム
description: "システム — reboot、warm restart、telemetry、logging、security、techsupport など装置共通の運用機能を扱う章。"
area: system
verification: meta
last_verified: 2026-05-13
---

# システム
reboot、warm restart、telemetry、logging、security、techsupport など装置共通の運用機能を扱う章。
## この章の読み方
目的の機能名からページを選び、設定名や CLI 名が必要な場合はリファレンス章を併読する。`Discrepancy-found` は [HLD](../reference/glossary.md#term-hld) と現行実装に差分が見つかったページなので、設計値として読む前に本文の注記を確認する。
## 検証状況
- ページ数: 76
- 分布: Code-verified: 58 / Discrepancy-found: 7 / HLD-only: 9 / Issue-confirmed: 1 / Meta: 1

## 実装差分があるページ
- [kdump（kexec ベース kernel crash dump / makedumpfile）](kdump.md)
- [SONiC FIPS 140-3 デプロイ（FIPS table と /etc/fips/fips_enabled）](sonic-fips-deployment.md)
- [SONiC NTP client（chrony / NTP_SERVER / mgmt VRF）](sonic-network-time-protocol-ntp-client-configuration.md)
- [SONiC Secure Boot（shim/grub/vmlinuz/KO の chain of trust）](hld-secure-boot.md)
- [SWSS docker の Warm Restart 実装メモ（開発時リファレンス）](swss-docker-warm-restart-code-reference.md)
- [SysLogger 拡張（runtime log level + LOGGER.require_manual_refresh + SIGHUP）](sonic-python-logger-enhancement.md)
- [libsairedis API idempotence（warm restart 用 OID キャッシュと duplicate 抑止）](sonic-libsairedis-api-idempotence-support.md)

## HLD-only のページ
- [Dataplane Telemetry (DTel) テストプラン（INT source/sink/transit + Postcard + Drop/Queue report）](dataplane-telemetry-test-plan.md)
- [Fast-reboot Flow Improvements（finalizer / reconciliation）](fast-reboot-flow-improvements-hld.md)
- [Syslog Source IP（SSIP / rsyslog omfwd / VRF / IP_FREEBIND）](sonic-syslog-source-ip.md)
- [System Health Monitor（critical service / Monit / peripheral）](sonic-system-health-monitor-high-level-design.md)
- [TWAMP Light（Session-Sender / Session-Reflector）](twamp-light-hld.md)
- [Transceiver / DOM Sensor Monitoring（xcvrd / TRANSCEIVER_*）](transceiver-and-sensor-monitoring-hld.md)
- [Warmboot Manager（shutdown orchestration / reconciliation 統一）](warmboot-manager-hld.md)
- [クリティカルリソースモニタリング (CRM) 要件](critical-resource-monitoring.md)
- [ローカルユーザパスワード init 時リセット（long reset button + reset-local-users-passwords.service）](reset-local-users-passwords-during-init-hld.md)

## ページ一覧

| ページ | 検証 |
|---|---|
| [ASIC 内部温度センサのポーリング（ASIC_SENSORS / ASIC_TEMPERATURE_INFO）](asic-thermal-monitoring-high-level-design.md) | Code-verified |
| [Critical Resource Monitoring（CRM・SAI 表枯渇のしきい値監視）](critical-resource-monitoring-in-sonic.md) | Code-verified |
| [Dataplane Telemetry (DTel) テストプラン（INT source/sink/transit + Postcard + Drop/Queue report）](dataplane-telemetry-test-plan.md) | HLD-only |
| [Dataplane Telemetry（DTel / INT / Postcard / Drop / Queue Report）](dataplane-telemetry-in-sonic.md) | Code-verified |
| [Entity MIB / Entity Sensor MIB 拡張（chassis 階層化と sensor / fan / PSU 追加）](sonic-entity-mib-and-entity-sensor-mib-extension.md) | Code-verified |
| [Event-Driven TechSupport / Coredump 管理（auto-techsupport / rate-limit / quota）](event-driven-techsupport-invocation-coredump-mgmt.md) | Code-verified |
| [Express Reboot（Cisco 8000 向けサブ秒データプレーン断のリブート）](sonic-express-reboot-hld-spec.md) | Code-verified |
| [FEATURE テーブルによるオプショナル機能の有効/無効制御](sonic-optional-feature-control-enhancement.md) | Code-verified |
| [FRR 用 sysctl チューニングのデフォルト](useful-sysctl-settings.md) | Code-verified |
| [Fast-reboot Flow Improvements（finalizer / reconciliation）](fast-reboot-flow-improvements-hld.md) | HLD-only |
| [Generic SAI Extension テーブルの CRM（CRM_EXT_TABLE）](generic-sai-extension-critical-resource-monitoring-crm.md) | Code-verified |
| [Management Framework 経由の show techsupport（REST/gNMI/IETF since 形式）](show-techsupport.md) | Code-verified |
| [Multi-ASIC warm reboot（namespace 横断の協調 shutdown / boot）](multi-asic-warm-reboot.md) | Code-verified |
| [OpenSSL FIPS 140-3（SymCrypt engine + sonic_fips=1）](sonic-openssl-fips-140-3-hld.md) | Code-verified |
| [PCIe Monitoring Services（pcied / pcieinfo / lnkSta / AER）](sonic-pcie-monitoring-services-hld.md) | Code-verified |
| [PMON の Multi-ASIC 対応（global DB と per-ASIC namespace の役割分担）](platform-monitor-design-for-multi-asic-platforms.md) | Code-verified |
| [Process / Docker stats のテレメトリ公開（PROCESS_STATS / DOCKER_STATS）](process-and-docker-stats-availability-via-telemetry-agent.md) | Code-verified |
| [Reboot-cause 履歴の STATE_DB / テレメトリ公開](reboot-cause-information-via-telemetry-agent.md) | Code-verified |
| [SNMP IPv6 応答の SRC IP 不整合と SNMP_AGENT_ADDRESS_CONFIG による回避](sonic-snmp-changes-to-support-ipv6.md) | Code-verified |
| [SNMP TABLE スキーマ提案（SNMP / SNMP_COMMUNITY / SNMP_USER）](sonic-snmp-table-schema-proposal.md) | Code-verified |
| [SNMP Transceiver Monitoring テストプラン（Entity MIB / Entity Sensor MIB）](snmp-transceiver-monitoring-testbed-test-plan.md) | Code-verified |
| [SNMP 設定の snmp.yml → CONFIG_DB 移行](snmp-migration-from-snmp-yml-to-configdb.md) | Code-verified |
| [SSH 接続時の「Too many authentication failures」エラー](ssh-authentication-failures.md) | Issue-confirmed |
| [SONiC BMC Platform Management & Monitoring（pmon ↔ BMC 連携）](sonic-bmc-platform-management-monitoring.md) | Code-verified |
| [SONiC Boot Chart（systemd-bootchart 統合）](sonic-boot-chart.md) | Code-verified |
| [SONiC ビルドシステム既知問題](buildimage-build-system-known-issues.md) | Code-verified |
| [SONiC Container Hardening（capability / read-only / privileged 削減）](sonic-container-hardening.md) | Code-verified |
| [SONiC Debian アップグレード方針（base / container / 廃止 cadence）](sonic-debian-upgrade-cadence.md) | Code-verified |
| [SONiC Disk I/O 削減（writer 分析と tmpfs 化）](analysis-of-disk-writers-in-sonic-devices.md) | Code-verified |
| [SONiC FIPS 140-3 デプロイ（FIPS table と /etc/fips/fips_enabled）](sonic-fips-deployment.md) | Discrepancy-found |
| [SONiC Feature Quality 定義（Alpha / Beta / GA とリリースノート連動）](sonic-feature-quality-definition.md) | Meta |
| [SONiC Logging & System Dumps（要件レベル仕様）](sonic-logging-system-dumps-arch-spec.md) | Code-verified |
| [SONiC NTP client（chrony / NTP_SERVER / mgmt VRF）](sonic-network-time-protocol-ntp-client-configuration.md) | Discrepancy-found |
| [SONiC OS と Docker イメージのセマンティックバージョニング](sonic-os-sonic-docker-images-versioning.md) | Code-verified |
| [SONiC Secure Boot（shim/grub/vmlinuz/KO の chain of trust）](hld-secure-boot.md) | Discrepancy-found |
| [SONiC Warm Reboot（要件・順序・docker 別 warm restart）](sonic-warm-reboot.md) | Code-verified |
| [SWSS docker warm restart（state restore / consistency / sync up）](sonic-swss-docker-warm-restart.md) | Code-verified |
| [SWSS docker の Warm Restart 実装メモ（開発時リファレンス）](swss-docker-warm-restart-code-reference.md) | Discrepancy-found |
| [Secure Upgrade（image 署名検証 / SECURE_UPGRADE_MODE）](secure-upgrade.md) | Code-verified |
| [SensorMon（PMON 内の voltage / current センサ監視）](sonic-pmon-sensor-monitoring-enhancement.md) | Code-verified |
| [Smart Switch DPU IP アドレス割当（midplane bridge / DHCP server）](smart-switch-ip-address-assignment.md) | Code-verified |
| [Smart Switch: DPU 独立アップグレード（gNOI 経路）](independent-dpu-upgrade.md) | Code-verified |
| [SmartSwitch reboot 順序（NPU → 各 DPU の gNOI HALT → PCI detach → 個別 reboot）](smart-switch-reboot-high-level-design.md) | Code-verified |
| [SysLogger 拡張（runtime log level + LOGGER.require_manual_refresh + SIGHUP）](sonic-python-logger-enhancement.md) | Discrepancy-found |
| [Syslog Source IP（SSIP / rsyslog omfwd / VRF / IP_FREEBIND）](sonic-syslog-source-ip.md) | HLD-only |
| [System Health Monitor（critical service / Monit / peripheral）](sonic-system-health-monitor-high-level-design.md) | HLD-only |
| [System Ready（sysmonitor + per-app closest UP status の event 集約）](system-ready-hld.md) | Code-verified |
| [System-wide Warmboot（going down / up path / SAI 期待値）](system-wide-warmboot.md) | Code-verified |
| [TWAMP Light（Session-Sender / Session-Reflector）](twamp-light-hld.md) | HLD-only |
| [Transceiver / DOM Sensor Monitoring（xcvrd / TRANSCEIVER_*）](transceiver-and-sensor-monitoring-hld.md) | HLD-only |
| [Warm Reboot 開発フェーズと OID 復元戦略（idempotent libsairedis vs syncd view comparison）](what-are-the-development-phases-and-scope-for-warm-reboot.md) | Code-verified |
| [Warmboot Manager（shutdown orchestration / reconciliation 統一）](warmboot-manager-hld.md) | HLD-only |
| [YANG モデル既知問題と検証](yang-model-issues-and-validation.md) | Code-verified |
| [Zero Touch Provisioning（ZTP・DHCP option / plugin / state machine）](zero-touch-provisioning-ztp.md) | Code-verified |
| [config-setup サービス（first-boot config 生成 / 版間 migration）](sonic-configuration-setup-service.md) | Code-verified |
| [gNMI dial-out モード（dialout_client_cli + gNMIDialOut.Publish）](sonic-telemetry-in-dial-out-mode.md) | Code-verified |
| [kdump リモート転送（SSH）](kdump-remote-ssh.md) | Code-verified |
| [kdump（kexec ベース kernel crash dump / makedumpfile）](kdump.md) | Discrepancy-found |
| [libsairedis API idempotence（warm restart 用 OID キャッシュと duplicate 抑止）](sonic-libsairedis-api-idempotence-support.md) | Discrepancy-found |
| [ntpd → chrony 移行（slew 専念 / kernel time discipline 維持）](sonic-migration-to-chrony.md) | Code-verified |
| [pmon 強化（PSU/FAN/syseeprom 周辺データ STATE_DB 集約）](platform-monitor-enhancement-design.md) | Code-verified |
| [reboot コマンドの blocking mode（reboot.conf / -b / -v）](reboot-support-blockingmode-in-sonic.md) | Code-verified |
| [show techsupport での SFP EEPROM ページダンプ取り込み](dump-sfp-eeprom-page-data-in-show-techsupport-command.md) | Code-verified |
| [storagemond（SSD / eMMC の health 監視）](sonic-storage-monitoring-daemon-design.md) | Code-verified |
| [syslog rate limit のコンテナ単位設定（SYSLOG_CONFIG / SYSLOG_CONFIG_FEATURE）](sonic-syslog-message-rate-limit-configuration-per-container.md) | Code-verified |
| [telemetry dial-out モード（gNMIDialOut.Publish / TELEMETRY_CLIENT）](sonic-telemetry-in-dial-out-mode-2.md) | Code-verified |
| [クリティカルリソースモニタリング (CRM) 要件](critical-resource-monitoring.md) | HLD-only |
| [シャーシサブシステムにおける Platform Monitor 要件（Mandatory + Future）](platform-monitor-requirement-for-chassis-subsystem.md) | Code-verified |
| [バナーメッセージ（login / motd / logout）](banner-messages-hld.md) | Code-verified |
| [メモリ統計収集（memorystatsd と MEMORY_STATISTICS テーブル）](memory-statistics-feature-in-sonic.md) | Code-verified |
| [ログレベルの永続化（LOGLEVEL_DB → CONFIG_DB.LOGGER への移行）](persistent-log-level-hld.md) | Code-verified |
| [ローカルユーザパスワード init 時リセット（long reset button + reset-local-users-passwords.service）](reset-local-users-passwords-during-init-hld.md) | HLD-only |
| [動的ポートブレイクアウト（dynamic port breakout・lanes / interface再構成）](sonic-dynamic-port-breakout-feature-high-level-design.md) | Code-verified |
| [動的ポートブレイクアウト（DPB）既知問題と YANG モデル](dynamic-port-breakout-known-issues.md) | Code-verified |
| [ウォームブート既知問題とトラブルシューティング](warmboot-known-issues-and-troubleshooting.md) | Code-verified |
| [静的 DNS 設定（DNS_NAMESERVER と resolvconf 連携）](static-dns-configuration.md) | Code-verified |

<!-- glossary-links-injected: 167700005048 -->
