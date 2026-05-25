---
title: プラットフォーム
description: "プラットフォーム — SAI、PMON、センサー、トランシーバ、プラットフォーム API、シャーシ機能を扱う章。"
area: platform
verification: meta
last_verified: 2026-05-13
---

# プラットフォーム
[SAI](../reference/glossary.md#term-sai)、PMON、センサー、トランシーバ、プラットフォーム API、シャーシ機能を扱う章。
## この章の読み方
目的の機能名からページを選び、設定名や CLI 名が必要な場合はリファレンス章を併読する。`Discrepancy-found` は [HLD](../reference/glossary.md#term-hld) と現行実装に差分が見つかったページなので、設計値として読む前に本文の注記を確認する。
## 検証状況
- ページ数: 51
- 分布: code-verified: 33 / Discrepancy-found: 10 / HLD-only: 4 / Community-report: 4

## 実装差分があるページ
- [FEC FLR（Frame Loss Ratio）算出と予測（port_flr.lua / counterpoll port flr-interval-factor）](fec-flr-support-in-sonic.md)
- [SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB）](hld-for-handling-sai-failures.md)
- [SAI 失敗時の dump 取得（syncd_dump.sh / SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP）](dump-on-sai-failure.md)
- [[SONiC](../reference/glossary.md#term-sonic) ポート命名規則の変更案（et[sX]pY[abcd]）](sonic-port-naming-convention-change.md)
- [Smart Switch DPU Graceful Shutdown（gnoi_reboot_daemon HALT）](smartswitch-dpu-graceful-shutdown.md)
- [液冷漏洩検出（LiquidCoolingBase + thermalctld + system-health gNMI イベント）](liquid-cooling-leakage-detection-in-sonic.md)
- [FEC FLR 概念（FLR / CER / interleaving / observed vs predicted）](fec-flr-support-in-sonic-concepts.md)
- [FEC FLR 内部実装（port_flr.lua / FlexCounterOrch / SAI counter mapping）](fec-flr-support-in-sonic-internals.md)
- [FEC FLR 制限事項と HLD との乖離（CLI 未取り込み / ハードコード値）](fec-flr-support-in-sonic-limitations.md)
- [FEC FLR 設定・運用（counterpoll / show interfaces counters fec-stats / portstat -f）](fec-flr-support-in-sonic-operations.md)

## コミュニティ報告ページ
- [SfpUtilBase の EEPROM 解析欠損](sfp-eeprom-parsing-gaps.md)
- [SFF-8472 外部キャリブレーション SFP の Rx パワー変換誤り](sfp-sff8472-rx-power-calibration.md)
- [thermalctld の speed_tolerance API 廃止と移行](thermalctld-speed-tolerance-api-change.md)
- [xcvrd クラッシュ（MediaInterfaceIDApp 未定義）](xcvrd-cmis-mediainterface-crash.md)

## HLD-only のページ
- [BMC / Redfish 統合（platform_common RedfishClient + show platform bmc）](support-bmc-flows-in-sonic.md)
- [VLAN Subnet Decap（Netscan 用 IPinIP MP2MP デカプスル）](subnet-decapsulation-with-sonic.md)
- [VoQ Chassis での Everflow ミラー（recycle port 経由の rewrite）](everflow-support-on-voq-chassis.md)
- [拡張 LPO デバッグレジスタ（VMA / OMA per-lane モニタを Redis に公開）](enhanced-lpo-debug-registers-hld.md)

## ページ一覧

| ページ | 検証 |
|---|---|
| [1.6T Ethernet 対応（200G SerDes / SFF-8024 / xcvrd / PortsOrch）](1-6t-support-in-sonic.md) | code-verified |
| [ASIC / SDK Health Event のハンドリング（SAI notification → STATE_DB → action）](handle-asic-sdk-health-event.md) | code-verified |
| [BMC / Redfish 統合（platform_common RedfishClient + show platform bmc）](support-bmc-flows-in-sonic.md) | HLD-only |
| [CMIS Custom SI 設定（optics_si_setting.json と CMIS FSM の EC=1 適用）](custom-si-settings-for-cmis-modules.md) | code-verified |
| [Chassis Line Card 自動プロビジョニング（sonic-provisiond / provision_module）](automatic-module-provisioning-for-chassis.md) | code-verified |
| [FEC FLR（Frame Loss Ratio）算出と予測（port_flr.lua / counterpoll port flr-interval-factor）](fec-flr-support-in-sonic.md) | Discrepancy-found |
| [Gearbox 動的チューニング（gb_line_* / gb_system_* in media_settings.json）](sonic-dynamic-gearbox-tuning-design-plan.md) | code-verified |
| [ICMP Hardware Offload（DualToR link prober の NPU 化）](icmp-hardware-offload.md) | code-verified |
| [Media-based Port Settings（media_settings.json による SerDes プロファイル）](media-based-port-settings-in-sonic.md) | code-verified |
| [Multi-ASIC Single JSON Configuration（Golden Config に namespace layer）](multi-asic-single-json-configuration-design.md) | code-verified |
| [NPU MDIO アクセスと gbsyncd 単一 docker 化](sonic-npu-mdio-access-support-and-gbsyncd-docker-enhancement-hld.md) | code-verified |
| [Port FEC BER（Pre/Post FEC BER の算出と show fec-stat 拡張）](sonic-port-fec-ber.md) | code-verified |
| [S3IP sysfs 仕様（platform 情報を /sys_switch/ で公開）](s3ip-sysfs-specification.md) | code-verified |
| [SAI API バージョン整合チェック（sai_query_api_version + ビルド時検査）](sai-api-version-check.md) | code-verified |
| [SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB）](hld-for-handling-sai-failures.md) | Discrepancy-found |
| [SAI 失敗時の dump 取得（syncd_dump.sh / SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP）](dump-on-sai-failure.md) | Discrepancy-found |
| [SFP リファクタ（XcvrApi / XcvrEeprom / spec 自動判別）](sonic-sfp-refactoring.md) | code-verified |
| [SONiC Fast Link-Up（リンク再起動時の EQ 再利用）](sonic-fast-link-up.md) | code-verified |
| [SONiC on Multi-ASIC platforms（namespace / per-asic Redis / sonic-net）](1-sonic-on-multi-asic-platforms.md) | code-verified |
| [SONiC ポート命名規則の変更案（et[sX]pY[abcd]）](sonic-port-naming-convention-change.md) | Discrepancy-found |
| [Smart Switch DPU Graceful Shutdown（gnoi_reboot_daemon HALT）](smartswitch-dpu-graceful-shutdown.md) | Discrepancy-found |
| [SmartSwitch PMON（NPU 側 pmon と DPU 連携の境界）](smartswitch-pmon-high-level-design.md) | code-verified |
| [Thermal Control テストプラン](thermal-control-test-plan.md) | code-verified |
| [Thermal Control（thermalctld + ポリシー駆動 fan / cooling 制御）](sonic-thermal-control-design.md) | code-verified |
| [VLAN Subnet Decap（Netscan 用 IPinIP MP2MP デカプスル）](subnet-decapsulation-with-sonic.md) | HLD-only |
| [VOQ シャシでの recirculation port サポート（Inb / Rec ポートロール）](recirculation-port-support-on-voq-chassis.md) | code-verified |
| [VOQ シャーシの Fabric ポート（fabric ASIC 管理 / link monitoring）](fabric-port-support-on-sonic.md) | code-verified |
| [VoQ Chassis での Everflow ミラー（recycle port 経由の rewrite）](everflow-support-on-voq-chassis.md) | HLD-only |
| [VoQ SONiC（distributed VoQ chassis / system-port / fabric）](voq-sonic.md) | code-verified |
| [ZR / ZR+ 向け CMIS / C-CMIS サポート（xcvrd / DSP / coherent optics）](cmis-and-c-cmis-support-for-zr.md) | code-verified |
| [fwutil（platform component firmware の install / update / show）](sonic-fw-utility.md) | code-verified |
| [multi-ASIC 用 Golden Config 単一 JSON フォーマット（localhost / asic0 / asic1 ...）](db-design-for-multi-asic-scenarios.md) | code-verified |
| [pcieutil / show platform pcieinfo（PCIe デバイス検査と pcie.yaml 比較）](pcieinfo-design.md) | code-verified |
| [platform.json の capabilities 拡張（LED 色 / fan speed 範囲 / controllable）](platform-capability-file-enhancement.md) | code-verified |
| [psud（PSU 監視デーモン / power threshold ヒステリシス）](sonic-psu-daemon-design.md) | code-verified |
| [sai_query_stats_capability による Counter Capability 一括取得](query-stats-capability-new-sai-api-indroduction.md) | code-verified |
| [sfputil read-eeprom / write-eeprom（page+offset 単位の生 EEPROM 読み書き）](sfputil-add-the-ability-to-read-write-any-byte-from-eerpom-both-by-page-and-offset.md) | code-verified |
| [ポート / LAG の TPID 設定（0x8100/0x9100/0x9200/0x88A8）](sonictpidsettinghld1.md) | code-verified |
| [単一 ASIC VoQ 固定システム（chassisdb.conf による is_voq_chassis 分岐）](single-asic-voq-fixed-system-sonic.md) | code-verified |
| [拡張 LPO デバッグレジスタ（VMA / OMA per-lane モニタを Redis に公開）](enhanced-lpo-debug-registers-hld.md) | HLD-only |
| [新 Platform API（sonic_platform / Chassis / PSU/Fan/Sfp の Python クラス階層）](global-platform-specific-psuutil-class-instance.md) | code-verified |
| [液冷漏洩検出（LiquidCoolingBase + thermalctld + system-health gNMI イベント）](liquid-cooling-leakage-detection-in-sonic.md) | Discrepancy-found |
| [FEC FLR 概念（FLR / CER / interleaving / observed vs predicted）](fec-flr-support-in-sonic-concepts.md) | Discrepancy-found |
| [FEC FLR 内部実装（port_flr.lua / FlexCounterOrch / SAI counter mapping）](fec-flr-support-in-sonic-internals.md) | Discrepancy-found |
| [FEC FLR 制限事項と HLD との乖離（CLI 未取り込み / ハードコード値）](fec-flr-support-in-sonic-limitations.md) | Discrepancy-found |
| [FEC FLR 設定・運用（counterpoll / show interfaces counters fec-stats / portstat -f）](fec-flr-support-in-sonic-operations.md) | Discrepancy-found |
| [SfpUtilBase の EEPROM 解析欠損](sfp-eeprom-parsing-gaps.md) | Community-report |
| [SFF-8472 外部キャリブレーション SFP の Rx パワー変換誤り](sfp-sff8472-rx-power-calibration.md) | Community-report |
| [thermalctld の speed_tolerance API 廃止と移行](thermalctld-speed-tolerance-api-change.md) | Community-report |
| [xcvrd クラッシュ（MediaInterfaceIDApp 未定義）](xcvrd-cmis-mediainterface-crash.md) | Community-report |

<!-- glossary-links-injected: 8ba32e5aa69d -->
