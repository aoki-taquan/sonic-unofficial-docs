---
title: Container / Build system 関連
area: categories
verification: meta
last_verified: 2026-05-10
---

# Container / Build system 関連

## 概要

Container、Docker、build system、image、Debian、sonic-buildimage、upgrade / packaging を横断して追う入口です。

主要キーワード: `container`, `Docker`, `build`, `image`, `Debian`, `sonic-buildimage`

## 関連ページ

- [ビルドプロファイル（rules/profiles/*.mk）](../architecture/build-profiles.md) (area: `architecture`, verification: `discrepancy-found`)
- [ビルド時間最適化（Dockerfile レイヤ削減 / BuildKit / 並列 dh / sairedis 分離）](../architecture/build-system-improvements.md) (area: `architecture`, verification: `code-verified`)
- [RFS Split build（build_debian.sh の 2 段化と squashfs 中間配備）](../architecture/rfs-split-build-improvements-hld.md) (area: `architecture`, verification: `code-verified`)
- [NPU MDIO アクセスと gbsyncd 単一 docker 化](../platform/sonic-npu-mdio-access-support-and-gbsyncd-docker-enhancement-hld.md) (area: `platform`, verification: `code-verified`)
- [DHCPv6 リレー（dhcp-relay docker 内の dhcrelay -6 プロセス）](../routing/dhcp-relay-for-ipv6-hld.md) (area: `routing`, verification: `code-verified`)
- [Process / Docker stats のテレメトリ公開（PROCESS_STATS / DOCKER_STATS）](../system/process-and-docker-stats-availability-via-telemetry-agent.md) (area: `system`, verification: `code-verified`)
- [Secure Upgrade（image 署名検証 / SECURE_UPGRADE_MODE）](../system/secure-upgrade.md) (area: `system`, verification: `code-verified`)
- [SONiC Container Hardening（capability / read-only / privileged 削減）](../system/sonic-container-hardening.md) (area: `system`, verification: `code-verified`)
- [SONiC Debian アップグレード方針（base / container / 廃止 cadence）](../system/sonic-debian-upgrade-cadence.md) (area: `system`, verification: `code-verified`)
- [SONiC OS と Docker イメージのセマンティックバージョニング](../system/sonic-os-sonic-docker-images-versioning.md) (area: `system`, verification: `code-verified`)
- [SWSS docker warm restart（state restore / consistency / sync up）](../system/sonic-swss-docker-warm-restart.md) (area: `system`, verification: `code-verified`)
- [syslog rate limit のコンテナ単位設定（SYSLOG_CONFIG / SYSLOG_CONFIG_FEATURE）](../system/sonic-syslog-message-rate-limit-configuration-per-container.md) (area: `system`, verification: `code-verified`)
- [SONiC Warm Reboot（要件・順序・docker 別 warm restart）](../system/sonic-warm-reboot.md) (area: `system`, verification: `code-verified`)
- [SWSS docker の Warm Restart 実装メモ（開発時リファレンス）](../system/swss-docker-warm-restart-code-reference.md) (area: `system`, verification: `discrepancy-found`)

## 関連カテゴリ

- [Warm-Reboot / Fast-Reboot 関連](reboot.md)
- [SmartSwitch 関連](smartswitch.md)
- [SAI 拡張属性追加系](sai-extensions.md)
- [gNMI / gNOI / OpenConfig 関連](gnmi-openconfig.md)
