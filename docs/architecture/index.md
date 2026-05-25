---
title: アーキテクチャ
description: "アーキテクチャ — SONiC 全体構成、ビルド、管理基盤、共通設計を横断的に扱う章。"
area: architecture
verification: meta
last_verified: 2026-05-13
---

# アーキテクチャ
[SONiC](../reference/glossary.md#term-sonic) 全体構成、ビルド、管理基盤、共通設計を横断的に扱う章。
## この章の読み方
まず全体像や実装単位のページを読み、必要に応じて関連する機能別章またはリファレンス章に移動する。
## 検証状況
- ページ数: 41
- 分布: code-verified: 27 / Discrepancy-found: 9 / [HLD](../reference/glossary.md#term-hld)-only: 5

## 実装差分があるページ
- [DIP=SIP PTF 検証テスト](dip-sip-ptf-validation-high-level-design.md)
- [Debug Framework（コンポーネント dump 登録 / assert 拡張）](debug-framework-in-sonic.md)
- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](error-handling-framework-in-sonic.md)
- [SAG（Static Anycast Gateway）for SONiC](sag-high-level-design-for-sonic.md)
- [SSD ヘルスチェック（show platform ssdhealth + ssdutil プラグイン）](ssdhealth-design.md)
- [SmartSwitch HA: HAMgrD（NPU 側 actor 分割と DPU 連携）](smartswitch-high-availability-manager-daemon-hamgrd-design.md)
- [sFlow（hsflowd / sflowmgrd / SAI sample-packet）](sflow-high-level-design.md)
- [ビルドプロファイル（rules/profiles/*.mk）](build-profiles.md)
- [ポート不正パケットドロップ設計（Interface MIB / L3 カウンタ拡張）](port-illegal-packets-drop-design.md)

## HLD-only のページ
- [Bulk Counter（sai_bulk_object_get_stats / chunk size）](sonic-bulk-counter-design.md)
- [Packet Trimming（symmetric / asymmetric DSCP / ACL disable）](sonic-packet-trimming.md)
- [Policy Based Hashing（PBH: NVGRE / VxLAN inner 5-tuple）](sonic-policy-based-hashing.md)
- [Port Auto FEC（SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE / FEC=auto）](sonic-port-auto-fec-design.md)
- [Sub-port Interface（dot1q encap / VRF RIF / 命名規則）](sonic-sub-port-interface-high-level-design.md)

## ページ一覧

| ページ | 検証 |
|---|---|
| [Alpine 仮想 SONiC（ALViS / KNE デプロイ）](alpine-high-level-design.md) | code-verified |
| [Bulk Counter（sai_bulk_object_get_stats / chunk size）](sonic-bulk-counter-design.md) | HLD-only |
| [Clock 設定（config clock date/timezone, DEVICE_METADATA.timezone）](clock-managment-design.md) | code-verified |
| [DHCPv4 Relay Agent（dhcpmon / dhcrelay / option-82 / circuit-id）](dhcpv4-relay-agent.md) | code-verified |
| [DHCPv6 Relay Agent（Option 79 / dual ToR loopback）](dhcpv6-relay-agent.md) | code-verified |
| [DIP=SIP PTF 検証テスト](dip-sip-ptf-validation-high-level-design.md) | Discrepancy-found |
| [Debug Framework（コンポーネント dump 登録 / assert 拡張）](debug-framework-in-sonic.md) | Discrepancy-found |
| [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](error-handling-framework-in-sonic.md) | Discrepancy-found |
| [GNS3 VM 上での SONiC 動作（sonic-vs.img と Qemu テンプレート）](sonic-on-gns3-vm.md) | code-verified |
| [Generic Config Update / Rollback（GCU・JSON Patch・checkpoint）](sonic-generic-configuration-update-and-rollback.md) | code-verified |
| [Generic Hash（ECMP / LAG ハッシュフィールドとアルゴリズムの統一制御）](sonic-generic-hash.md) | code-verified |
| [IP インタフェース ループバックアクション（同一 RIF 出戻りの drop/forward）](sonic-ip-interface-loopback-action.md) | code-verified |
| [JSON Change Application（apply-change / table 単位 alphabetical 適用）](json-change-application.md) | code-verified |
| [NAT in SONiC（natsyncd / NatOrch / iptables ↔ SAI）](nat-in-sonic.md) | code-verified |
| [Packet Trimming（symmetric / asymmetric DSCP / ACL disable）](sonic-packet-trimming.md) | HLD-only |
| [Policy Based Hashing（PBH: NVGRE / VxLAN inner 5-tuple）](sonic-policy-based-hashing.md) | HLD-only |
| [Port Auto FEC（SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE / FEC=auto）](sonic-port-auto-fec-design.md) | HLD-only |
| [Port Profile Init（SAI bulk port API による fast-boot 高速化）](port-profile-init-hld.md) | code-verified |
| [RFS Split build（build_debian.sh の 2 段化と squashfs 中間配備）](rfs-split-build-improvements-hld.md) | code-verified |
| [S3IP sysfs（/sys_switch 統一ハードウェアアクセス層）](s3ip-sysfs-specification-and-s3ip-sysfs-framework-hld.md) | code-verified |
| [SAG（Static Anycast Gateway）for SONiC](sag-high-level-design-for-sonic.md) | Discrepancy-found |
| [SONiC Application Extension Infrastructure（sonic-package-manager / SPM）](sonic-application-extension-infrastructure.md) | code-verified |
| [SONiC の ARM (armhf / arm64) ビルドサポート（PLATFORM_ARCH と qemu-static）](sonic-arm-architecture-support.md) | code-verified |
| [SONiC-VS のビルドと libvirt 起動手順](steps-to-bring-up-sonic-vs.md) | code-verified |
| [SSD ヘルスチェック（show platform ssdhealth + ssdutil プラグイン）](ssdhealth-design.md) | Discrepancy-found |
| [Smart Switch のデータベース構成（NPU 上の DPU overlay DB）](smart-switch-database-design.md) | code-verified |
| [SmartSwitch HA - DPU-Scope-DPU-Driven 構成](smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md) | code-verified |
| [SmartSwitch HA: HAMgrD（NPU 側 actor 分割と DPU 連携）](smartswitch-high-availability-manager-daemon-hamgrd-design.md) | Discrepancy-found |
| [Sub-port Interface（dot1q encap / VRF RIF / 命名規則）](sonic-sub-port-interface-high-level-design.md) | HLD-only |
| [Trap Flow Counter（Host I/F Trap 単位の Generic Counter 集計）](sonic-trap-flow-counter-design.md) | code-verified |
| [port_config.ini パーサ統合（portconfig.py 一元化）](sonic-port-configuration-refactor-design.md) | code-verified |
| [reset-factory（keep-basic / keep-all-config / only-config）](reset-factory-design.md) | code-verified |
| [sFlow テストプラン（hsflowd + 2 collector / sampling rate / agent-id / counter polling）](sflow-test-plan.md) | code-verified |
| [sFlow（hsflowd / sflowmgrd / SAI sample-packet）](sflow-high-level-design.md) | Discrepancy-found |
| [ターミナルサーバの ttyUSB 安定 symlink を作る udev rules 設計](1-udev-rules-design-for-terminal-server.md) | code-verified |
| [パスワード強化（password hardening / aging / complexity / history）](pw-hardening-design.md) | code-verified |
| [ビルドプロファイル（rules/profiles/*.mk）](build-profiles.md) | Discrepancy-found |
| [ビルド時間最適化（Dockerfile レイヤ削減 / BuildKit / 並列 dh / sairedis 分離）](build-system-improvements.md) | code-verified |
| [ポート Auto-Negotiation（advertised-speeds / interface-type）](sonic-port-auto-negotiation-design.md) | code-verified |
| [ポートリンクトレーニング（IEEE 802.3 clause 72/93 / SAI 動的 FIR）](sonic-port-link-training-design.md) | code-verified |
| [ポート不正パケットドロップ設計（Interface MIB / L3 カウンタ拡張）](port-illegal-packets-drop-design.md) | Discrepancy-found |

<!-- glossary-links-injected: 8ba32e5aa69d -->
