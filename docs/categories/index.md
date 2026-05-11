---
title: 横断カテゴリ
area: categories
verification: meta
last_verified: 2026-05-10
---

# 横断カテゴリ

このドキュメントの本体は `architecture / overlay / routing / switching / platform / management / system / acl-qos / internals / reference` という **area 階層** で構成されていますが、機能ファミリーや運用テーマ（DASH / Dual-ToR / Warm-Reboot / Multi-ASIC / BGP-EVPN など）は 1 つの area に収まりません。たとえば **Warm-Reboot** の話題は `system`（warm-reboot 順序）・`switching`（LACP retry）・`platform`（PMON）・`routing`（FRR の hold-time / suppress-fib）・`reference`（CLI / CONFIG_DB）に分散しています。

横断カテゴリページは、こうした **同じテーマの関連ページを area の壁を越えて 1 か所から辿れる入口** を提供します。各ページは `meta/categories-proposal.md` の抽出ルールに従ってタイトル / area / verification ステータスをまとめた **リンク集** であり、新規の解説は書きません。読み手は「DASH 全体を見たい」「Warm-Reboot 関連を一気読みしたい」といったテーマ志向で入って、area 別の本文ページへ辿る使い方を想定しています。

なお、area を縦割りで読みたい場合は左サイドバー、機能テーマで段階的に学びたい場合は [Topics 章](../topics/index.md)（`02-bgp` / `03-vxlan-evpn` / `05-dual-tor` / `10-gnmi-openconfig` / `11-reboot` / `12-multi-asic-voq` / `13-dash-smartswitch` など）が併用できます。Topics は「concept → setup → operations → architecture → internals → advanced」の順で段階的に読む構成、本カテゴリページは「該当テーマの全関連ページ網羅」が役割です。

## カテゴリ一覧

- [DASH 関連](dash.md) (3 pages) — DPU / SmartNIC オフロード・SONiC-DASH 仮想 DPU・DASH ACL
- [SmartSwitch 関連](smartswitch.md) (10 pages) — NPU/DPU 分担・HA・gNOI 経路・DPU upgrade
- [Dual-ToR 関連](dual-tor.md) (12 pages) — active-active / active-standby・MUX cable・linkmgrd
- [Warm-Reboot / Fast-Reboot 関連](reboot.md) (12 pages) — warm-restart・kexec・SWSS docker 再起動
- [Multi-ASIC / VOQ chassis 関連](multi-asic.md) (20 pages) — namespace / fabric / supervisor / VOQ
- [BGP / EVPN 関連](bgp-evpn.md) (41 pages) — FRR-BGP / EVPN-VXLAN / VNET / BMP / PIC
- [SAI 拡張属性追加系](sai-extensions.md) (9 pages) — SAI capability 問い合わせ・failure handling
- [MIB / SNMP 関連](mib-snmp.md) (8 pages) — Entity / Sensor MIB・SNMP IPv6・migration
- [gNMI / gNOI / OpenConfig 関連](gnmi-openconfig.md) (57 pages) — Management Framework・gNOI System/OS/Healthz
- [Container / Build system 関連](container-build.md) (14 pages) — sonic-buildimage / RFS split / secure upgrade

## 読み方のヒント

- 初めての方は area インデックス（[architecture](../architecture/index.md) / [overlay](../overlay/index.md) / [routing](../routing/index.md) / [system](../system/index.md) など）から area 単位で読むほうが体系的です。
- 機能テーマで「全体像 → 設定 → 運用 → 内部実装」と段階的に学ぶなら [Topics 章](../topics/index.md)。
- 「ある機能の関連ページを area 横断で全部見たい」なら本カテゴリページ。
