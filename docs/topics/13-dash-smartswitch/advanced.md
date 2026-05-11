---
title: gNOI 連携と他章との境界
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/management/gnoi-hld-for-system-apis.md
  - docs/management/gnoi-hld-for-os-apis.md
  - docs/system/independent-dpu-upgrade.md
  - docs/system/smart-switch-reboot-high-level-design.md
  - docs/platform/smartswitch-dpu-graceful-shutdown.md
---

# gNOI 連携と他章との境界

DASH / SmartSwitch は単独で完結する機能ではなく、管理面 (gNMI / gNOI)、Multi-ASIC / VOQ、Platform 章と境界を持ちます。ここでは「どこから先は別の章が主」かを整理します。

## gNOI 系との関係

SmartSwitch の reboot / shutdown / upgrade は、SONiC の gNOI 実装をそのまま使います。

| gNOI API | この章での使い方 |
|---|---|
| `gnoi.system.Reboot` | DPU 個別 reboot、graceful shutdown のトリガ |
| `gnoi.system.Time` 等 system API | NPU / DPU の管理共通基盤 |
| `gnoi.os.Install` / `Activate` 等 | DPU 独立アップグレードの image 配布 / 切替 |

gNOI 自体の API 設計・認証・transport は管理章の責務です。本章では「SmartSwitch 運用フローのどこで gNOI を呼ぶか」だけ示し、API 仕様は [gNOI System APIs HLD](../../management/gnoi-hld-for-system-apis.md) と [gNOI OS APIs HLD](../../management/gnoi-hld-for-os-apis.md) を参照してください。

## Multi-ASIC / VOQ との境界

SmartSwitch の DPU per-instance redis は、multi-ASIC の per-namespace redis と同じ `featured` 機構を使います。両者は似た形に見えますが、目的が異なります。

| 観点 | Multi-ASIC / VOQ | SmartSwitch |
|---|---|---|
| 何が複数あるか | ASIC（同種 forwarding chip） | DPU（overlay 処理 SoC） |
| トラフィック関係 | 同一筐体内で fabric を通じて結合 | NPU が underlay、DPU が overlay |
| DB 分割の動機 | namespace ごとに ASIC を抱える | DPU メモリ節約 / API 単純化 |
| 該当章 | Multi-ASIC / VOQ Chassis 章（章 12） | 本章 |

両者が同じ基盤を使うため、`has_per_dpu_scope` / `has_per_asic_scope` / `has_global_scope` の関係や `featured` の動作は [Multi-ASIC / VOQ 章](../../topics/01-overview/index.md) 寄りで扱われる想定です。混同を避けるため、本章では「DPU レイヤの話だけ」を扱います。

## Platform 章との境界

DPU の PCIe / midplane / 電源 / リセットといった物理層は Platform 章 (PMON / sensor / firmware) と重なります。本章では運用フローの中で必要な範囲のみ触れ、ハードウェア抽象や `platform.json` の詳細は Platform 章に委ねます。

## telemetry / counter

`DashCounter` による per-ENI / per-flow counter や、metering の集約は DASH HLD で定義されますが、外部への配送経路は **telemetry / streaming telemetry の共通基盤** を使います。export 設定・gNMI subscribe・ストリーミング先のスケーリングは管理章の範囲です。本章は「counter がどこに溜まるか」までを扱い、export 設計は管理章に渡します。

## まとめ: どの章へ次に進むか

- gNMI / gNOI / streaming telemetry の詳細を知りたい → 管理章
- Multi-ASIC / VOQ Chassis の DB 分離を知りたい → Multi-ASIC / VOQ 章
- DPU の物理 / PMON / firmware を知りたい → Platform 章
- ACL 全体（ENI_REDIRECT 以外の通常 ACL）を知りたい → [ACL / CoPP / Mirror 章](../07-acl-copp-mirror/index.md)
- VxLAN / EVPN underlay を知りたい → [VXLAN EVPN 章](../03-vxlan-evpn/index.md)

## 関連ページ

- [gNOI System APIs HLD](../../management/gnoi-hld-for-system-apis.md)
- [gNOI OS APIs HLD](../../management/gnoi-hld-for-os-apis.md)
- [DPU 独立アップグレード](../../system/independent-dpu-upgrade.md)
- [SmartSwitch reboot 順序](../../system/smart-switch-reboot-high-level-design.md)
- [DPU Graceful Shutdown](../../platform/smartswitch-dpu-graceful-shutdown.md)
