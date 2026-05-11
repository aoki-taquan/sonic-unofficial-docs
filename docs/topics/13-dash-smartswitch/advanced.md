---
title: gNOI 連携と他章との境界
description: "gNOI 連携と他章との境界 — DASH / SmartSwitch は単独で完結する機能ではなく、管理面 (gNMI / gNOI)、Multi-ASIC / VOQ、Platform 章と境界を持ちます。ここでは「どこから先は別の章が主」かを整理します。"
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

[DASH](../../reference/glossary.md#term-dash) / [SmartSwitch](../../reference/glossary.md#term-smartswitch) は単独で完結する機能ではなく、管理面 ([gNMI](../../reference/glossary.md#term-gnmi) / [gNOI](../../reference/glossary.md#term-gnoi))、Multi-ASIC / [VOQ](../../reference/glossary.md#term-voq)、Platform 章と境界を持ちます。ここでは「どこから先は別の章が主」かを整理します。

## gNOI 系との関係

SmartSwitch の reboot / shutdown / upgrade は、SONiC の gNOI 実装をそのまま使います。

| gNOI API | この章での使い方 |
|---|---|
| `gnoi.system.Reboot` | [DPU](../../reference/glossary.md#term-dpu) 個別 reboot、graceful shutdown のトリガ |
| `gnoi.system.Time` 等 system API | [NPU](../../reference/glossary.md#term-npu) / DPU の管理共通基盤 |
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

`DashCounter` による per-[ENI](../../reference/glossary.md#term-eni) / per-flow counter や、metering の集約は DASH [HLD](../../reference/glossary.md#term-hld) で定義されますが、外部への配送経路は **telemetry / streaming telemetry の共通基盤** を使います。export 設定・gNMI subscribe・ストリーミング先のスケーリングは管理章の範囲です。本章は「counter がどこに溜まるか」までを扱い、export 設計は管理章に渡します。

## まとめ: どの章へ次に進むか

- gNMI / gNOI / streaming telemetry の詳細を知りたい → 管理章
- Multi-ASIC / VOQ Chassis の DB 分離を知りたい → Multi-ASIC / VOQ 章
- DPU の物理 / PMON / firmware を知りたい → Platform 章
- [ACL](../../reference/glossary.md#term-acl) 全体（ENI_REDIRECT 以外の通常 ACL）を知りたい → [ACL / CoPP / Mirror 章](../07-acl-copp-mirror/index.md)
- VxLAN / [EVPN](../../reference/glossary.md#term-evpn) underlay を知りたい → [VXLAN EVPN 章](../03-vxlan-evpn/index.md)

## 関連ページ

- [gNOI System APIs HLD](../../management/gnoi-hld-for-system-apis.md)
- [gNOI OS APIs HLD](../../management/gnoi-hld-for-os-apis.md)
- [DPU 独立アップグレード](../../system/independent-dpu-upgrade.md)
- [SmartSwitch reboot 順序](../../system/smart-switch-reboot-high-level-design.md)
- [DPU Graceful Shutdown](../../platform/smartswitch-dpu-graceful-shutdown.md)

## 発展トピック

- **DASH ENI scale**: 単一 DPU あたり数万〜数十万 ENI を扱うため、flow table / connection tracking / metering の memory 設計が要点。[SAI](../../reference/glossary.md#term-sai) DASH API の `SAI_OBJECT_TYPE_ENI` と pipeline 構造が論点。
- **flow HA / connection sync**: ENI ごとの flow state を peer DPU と同期する HA 設計。SmartSwitch HA HLD で議論。
- **gNMI による DASH 設定 push**: 大量 ENI を controller から流し込む使い方で、gRPC streaming と batch update の最適化が必要。
- **DPU の P4 pipeline 拡張**: DASH pipeline 自体は P4 に近い形で書かれ、新規 service (ELB、stateful FW など) の追加が pipeline 拡張で行われる。
- **NPU / DPU 連携の ACL**: NPU 側 `ENI_REDIRECT` ACL と DPU 側 ACL が二段で動く。redirect 判定の責務分割と order が運用上の注意点。

## 既知の制約と回避方法

- **DPU と NPU の独立 reboot 順序**: DPU 単独 reboot 中の flow 切替を peer DPU が引き受けるための graceful shutdown 手順が必須。順序を間違えると connection drop が発生する。
- **per-DPU [Redis](../../reference/glossary.md#term-redis) のメモリ消費**: ENI scale が大きいと per-DPU redis が膨らむ。`SDN_APPL_DB` の TTL / eviction を SDN controller 側でも考慮。
- **DASH counter export の遅延**: per-flow counter は数が多く、export pipeline で遅延が出やすい。`DashCounter` の aggregation 粒度を controller 側で調整する。
- **[VNET](../../reference/glossary.md#term-vnet) tunnel との競合**: ENI redirect が VNET tunnel nexthop と組合せる場合、優先度を ACL priority で明示しないと意図と異なる経路に乗る。

## 将来計画 / ロードマップ

- DASH SAI API の SAI 標準化が進行中。`dash-pipeline` の P4 ベースモデルが community SAI に統合される方向。
- SmartSwitch HA / flow sync の HLD は段階的に拡充される予定 (`smart-switch-ha-*` 系)。
- DPU 独立 upgrade と NPU upgrade の orchestration を統合するモデルが議論中。

## 関連 RFC / 仕様書

- [P4 Language Specification](https://p4.org/specs/) — DASH pipeline の表現
- [RFC 8174](https://datatracker.ietf.org/doc/html/rfc8174) — keyword 規約 (DASH HLD で参照)
- [RFC 5575](https://datatracker.ietf.org/doc/html/rfc5575) — [BGP](../../reference/glossary.md#term-bgp) Flow Spec (DASH ACL の参考モデル)
- [SAI DASH proposal](https://github.com/opencomputeproject/SAI) — Open Compute Project SAI repo

## upstream 開発の最新動向

- `sonic-dash-api` repo で proto / pipeline 定義の拡張が続く。controller との互換は proto バージョンで管理。
- `sonic-buildimage` の SmartSwitch 関連 PR が活発で、independent DPU upgrade、graceful shutdown、reboot 順序、health monitoring など分野が広がる。
- DASH P4 reference implementation (DASH repo) と SONiC sai 実装の bridging が継続して進む。

<!-- glossary-links-injected: ca666ecaafdc -->
