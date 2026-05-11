---
title: 設定
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 設定

仮想 lab の bring-up は「環境の選択 → image 取得 → topology / console 配線 → CONFIG_DB 投入」の順に進めます。SONiC の章本文で扱う CLI / CONFIG_DB / YANG の操作は実機と同じなので、ここでは lab 固有の前段だけを並べます。

## どこから始めるか

| 目的 | 最初に開くページ |
| --- | --- |
| 1 台の SONiC を libvirt で立ち上げる | [SONiC-VS のビルドと libvirt 起動手順](../../architecture/steps-to-bring-up-sonic-vs.md) |
| GNS3 で複数台をつなぐ | [GNS3 VM 上での SONiC 動作](../../architecture/sonic-on-gns3-vm.md) |
| Kubernetes / KNE で並べる | [Alpine 仮想 SONiC](../../architecture/alpine-high-level-design.md) |
| DPU / DASH を評価する | [DASH SONiC KVM](../../overlay/dash-sonic-kvm.md) |

各ページに前提パッケージ、image 生成、libvirt 設定、ネットワーク bridge の作り方が書かれています。重複した記載をここで再掲はしません。

## SONiC-VS 起動後の最低限の確認

bring-up 後は、実機と同じ順序で CONFIG_DB を読みます。`docker ps`、`show version`、`show interfaces status`、`show ip bgp summary` のような最小確認は、章本文（[BGP の運用](../02-bgp/operations.md) など）の手順と同じです。VS で起こる差分は主に次の点です。

- ASIC counter（SAI が VS のため、capability 表示が実機と異なる）
- optics / port speed（実 PHY がないため capability から外れる）
- thermal / PSU / fan（platform docker が dummy 動作）

これらの差は機能の良し悪しではなく、SONiC-VS の対象外です。

## 物理 lab の console / 配線

物理機材で lab を組む場合は、SONiC NOS の前に console / シリアル配線が必要になります。SONiC は console switch としても動くため、その設計を再利用できます。

- [SONiC console switch](../../management/sonic-console-switch.md): SONiC スイッチを console concentrator にする方法。CONFIG_DB の `CONSOLE_PORT` / `CONSOLE_SWITCH` を含む。
- [Portable console device design](../../management/portable-console-device-design.md): 持ち運び型 console 装置としての設計。
- [udev rules design for terminal server](../../architecture/1-udev-rules-design-for-terminal-server.md): USB シリアルを安定したデバイス名に貼り付ける udev 設計。

## test plan で扱われる configuration

CI / test plan に出てくる configuration（VRF VS test、ACL ingress/egress test など）は、本章の他のページや機能章本文の CONFIG_DB スキーマに従います。test plan は「どの設定をどう投入し、どう検証するか」の合意であり、初期投入の手順書ではありません。読む順序は機能章 → test plan です。
