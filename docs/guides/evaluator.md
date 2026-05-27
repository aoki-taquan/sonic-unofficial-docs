---
title: 評価者向けガイド
description: 評価者向けガイド — ラボで SONiC を試用する読者を想定しています。仮想環境または評価機で起動し、管理 IP、ポート、VLAN、BGP
  などの基本設定を入れ、状態確認まで一連の流れを辿るための導線です。
area: guides
verification: meta
last_verified: 2026-05-10
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# 評価者向けガイド

## 想定シナリオ

ラボで [SONiC](../reference/glossary.md#term-sonic) を試用する読者を想定しています。仮想環境または評価機で起動し、管理 IP、ポート、[VLAN](../reference/glossary.md#term-vlan)、[BGP](../reference/glossary.md#term-bgp) などの基本設定を入れ、状態確認まで一連の流れを辿るための導線です。

## 推奨 reading path

1. [SONiC 非公式ドキュメント](../index.md)
2. [GNS3 VM 上での SONiC 動作](../architecture/sonic-on-gns3-vm.md)
3. [SONiC-VS のビルドと libvirt 起動手順](../architecture/steps-to-bring-up-sonic-vs.md)
4. [Zero Touch Provisioning](../system/zero-touch-provisioning-ztp.md)
5. [sonic-installer](../reference/cli/sonic-installer.md)
6. [config interface](../reference/cli/config-interface.md)
7. [config vlan](../reference/cli/config-vlan.md)
8. [config portchannel](../reference/cli/config-portchannel.md)
9. [config bgp](../reference/cli/config-bgp.md)
10. [show interfaces](../reference/cli/show-interfaces.md)
11. [show vlan](../reference/cli/show-vlan.md)
12. [show ip](../reference/cli/show-ip.md)
13. [show bgp](../reference/cli/show-bgp.md)
14. [DEVICE_METADATA テーブル](../reference/config-db/device-metadata.md)
15. [MGMT_INTERFACE テーブル](../reference/config-db/mgmt-interface.md)
16. [PORT テーブル](../reference/config-db/port.md)
17. [VLAN テーブル](../reference/config-db/vlan.md)
18. [BGP_NEIGHBOR テーブル](../reference/config-db/bgp-neighbor.md)

## 不足コンテンツ注記

- 「ラボ評価 30 分チュートリアル」がありません。起動、初期ログイン、管理 IP、NTP / DNS、ポート up、VLAN、BGP neighbor、確認コマンドまでの直線的なページが必要です。
- 既存ページはリファレンスとして強い一方で、評価者がそのまま打てる最小構成例が不足しています。
- GNS3 / [VS](../reference/glossary.md#term-vs) bring-up と実機評価の分岐が明示されていません。仮想評価、単体スイッチ評価、ToR 評価で reading path を少し変える案が必要です。

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: SONiC 全体像と設定基盤](../topics/01-overview/index.md)
- [Topics: Lab / Virtual SONiC / Developer Entry](../topics/21-lab-vs-developer/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 9fb3fca99a59 -->
