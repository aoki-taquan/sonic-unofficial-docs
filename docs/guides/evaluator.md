---
title: 評価者向けガイド
description: ラボで SONiC を試用する読者向けに、仮想環境または評価機で起動し、管理 IP、ポート、VLAN、BGP などの基本設定を入れて状態確認まで辿る導線と、最小 bring-up 例を提供する。
area: guides
verification: meta
last_verified: 2026-06-04
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

## 最小 bring-up 例

評価者がそのまま打てる最小構成として、image インストールから 1 物理ポート up・VLAN 作成・BGP neighbor 投入までの 4 ステップを示す。BGP は `config bgp` CLI が neighbor 追加コマンドを持たないため、ラボでは [vtysh](../reference/glossary.md#term-vtysh) から [FRR](../reference/glossary.md#term-frr) を直接設定するのが最短である (恒久化したい場合は `config_db.json` の `BGP_NEIGHBOR` テーブル編集 + `config reload`)。詳細パラメータは上記 reading path のリファレンスを参照すること。

```bash
# 1. SONiC image をインストールして再起動
sudo sonic-installer install sonic-broadcom.bin

# 2. 物理ポートを admin-up にする
sudo config interface startup Ethernet0

# 3. VLAN 100 を作成しメンバーポートを追加
sudo config vlan add 100
sudo config vlan member add 100 Ethernet0

# 4. BGP neighbor を投入する (vtysh 経由)
sudo vtysh -c 'configure terminal' \
           -c 'router bgp 65000' \
           -c 'neighbor 10.0.0.1 remote-as 65001'
```

`config interface startup` の引数は単一インタフェース名で、内部で `PORT` テーブルの `admin_status` を `up` に更新する<!-- evidence: sonic-utilities config/main.py:5184-5210 -->。`config vlan add` は `vlan.py` で実装されており、`VLAN` テーブルに `Vlan<vid>` エントリを作成する<!-- evidence: sonic-utilities config/vlan.py:95-142 -->。BGP については `config bgp` サブコマンドが `shutdown` / `startup` / `remove` の 3 サブグループのみで neighbor 追加コマンドを持たず<!-- evidence: sonic-utilities config/main.py:4918-5054 (bgp group: shutdown/startup/remove のみ、add 系なし) -->、設定本体は FRR が握っているため、評価ラボでは `vtysh` から直接 FRR を叩くか、`config_db.json` の `BGP_NEIGHBOR` / `DEVICE_NEIGHBOR` テーブルを編集して `config reload` する流れになる ([config bgp](../reference/cli/config-bgp.md) も参照)。

## 評価シナリオ別の分岐

- 仮想評価 ([SONiC-VS](../reference/glossary.md#term-vs) / [GNS3](../architecture/sonic-on-gns3-vm.md)): 上記ステップ 1 は不要で、`steps-to-bring-up-sonic-vs` の libvirt 起動から開始する。
- 単体スイッチ評価: 上記 4 ステップが基本フロー。`sonic-installer install` 後に管理 IP / NTP / DNS を入れる。
- ToR 評価: VLAN / portchannel / BGP の組み合わせが必要で、reading path の portchannel と config_db の各テーブルを併読する。

## 既知のコンテンツ不足

- 「ラボ評価 30 分チュートリアル」専用ページは未整備で、本ページの bring-up 例はあくまで最小サブセットである。起動、初期ログイン、管理 IP、NTP / DNS、ポート up、VLAN、BGP neighbor、確認コマンドまでを直線で辿るチュートリアルは今後の整備対象。

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: SONiC 全体像と設定基盤](../topics/01-overview/index.md)
- [Topics: Lab / Virtual SONiC / Developer Entry](../topics/21-lab-vs-developer/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 14bb29c924c8 -->
