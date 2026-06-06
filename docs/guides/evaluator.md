---
title: 評価者向けガイド
description: ラボで SONiC を試用する読者向けに、仮想環境または評価機で起動し、管理 IP、ポート、VLAN、BGP などの基本設定を入れて状態確認まで辿る導線と、最小 bring-up 例を提供する。
area: guides
verification: meta
last_verified: 2026-06-06
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

評価者がそのまま打てる最小構成として、image インストールから管理 IP 投入・1 物理ポート up・VLAN 作成・BGP neighbor 投入、最後に状態確認までの 6 ステップを示す。BGP は `config bgp` CLI が neighbor 追加コマンドを持たないため、ラボでは [vtysh](../reference/glossary.md#term-vtysh) から [FRR](../reference/glossary.md#term-frr) を直接設定するのが最短である (恒久化したい場合は `config_db.json` の `BGP_NEIGHBOR` テーブル編集 + `config reload`)。詳細パラメータは上記 reading path のリファレンスを参照すること。

```bash
# 1. SONiC image をインストールして再起動
sudo sonic-installer install sonic-broadcom.bin

# 2. 管理 IP を投入する (eth0 = MGMT_INTERFACE)
sudo config interface ip add eth0 192.0.2.10/24 192.0.2.1

# 3. 物理ポートを admin-up にする
sudo config interface startup Ethernet0

# 4. VLAN 100 を作成しメンバーポートを追加
sudo config vlan add 100
sudo config vlan member add 100 Ethernet0

# 5. BGP neighbor を投入する (vtysh 経由)
sudo vtysh -c 'configure terminal' \
           -c 'router bgp 65000' \
           -c 'neighbor 10.0.0.1 remote-as 65001'

# 6. 投入結果を確認する (ポート / VLAN / BGP neighbor)
show interfaces status
show vlan brief
show ip bgp summary
```

`config interface ip add` は `eth0` に対しては `MGMT_INTERFACE` テーブルへ `(eth0, <ip/prefix>)` キーで書き込み、ゲートウェイ指定時は `gwaddr` を併記する<!-- evidence: sonic-utilities config/main.py:5676-5716 (add_interface_ip: eth0 分岐で MGMT_INTERFACE set_entry) -->。`config interface startup` の引数は単一インタフェース名で、内部で `PORT` テーブルの `admin_status` を `up` に更新する<!-- evidence: sonic-utilities config/main.py:5184-5210 -->。`config vlan add` は `vlan.py` で実装されており、`VLAN` テーブルに `Vlan<vid>` エントリを作成する<!-- evidence: sonic-utilities config/vlan.py:95-142 -->。BGP については `config bgp` 直下のサブコマンドが neighbor ごとの `shutdown` / `startup` / `remove` と、`device-global` (TSA / W-ECMP 等) ・ `aggregate-address` の追加グループに限られ、neighbor を新規に作成する `add` 系コマンドは存在しない<!-- evidence: sonic-utilities config/main.py:4918-5054 (bgp group: shutdown/startup/remove サブグループ)、config/main.py:4926-4927 (bgp_cli.DEVICE_GLOBAL / AGGREGATE_ADDRESS を add_command) -->。設定本体は FRR が握っているため、評価ラボでは `vtysh` から直接 FRR を叩くか、`config_db.json` の `BGP_NEIGHBOR` / `DEVICE_NEIGHBOR` テーブルを編集して `config reload` する流れになる ([config bgp](../reference/cli/config-bgp.md) も参照)。

確認系のうち `show interfaces status` は内部で `intfutil -c status` を起動し、admin/oper 状態と速度・MTU 等の一覧を表示する<!-- evidence: sonic-utilities show/interfaces/__init__.py:148-160 (status: intfutil -c status を subprocess 起動) -->。`show vlan brief` は CONFIG_DB の `VLAN` / `VLAN_INTERFACE` / `VLAN_MEMBER` テーブルを直接読み、VLAN ID・IP アドレス・メンバーポート・モード (tagged/untagged) を grid 表で出力する<!-- evidence: sonic-utilities show/vlan.py:119-141 (brief: get_table('VLAN'/'VLAN_INTERFACE'/'VLAN_MEMBER') → tabulate) -->ので、ステップ 4 で投入した `Vlan100` とメンバーの `Ethernet0` が反映されているかをここで確認する。`show ip bgp summary` は `bgp` サブグループの `summary` サブコマンドで実装され、内部で全 BGP インスタンスから summary を取り出し、neighbor ごとの State/PfxRcd 等を表示する<!-- evidence: sonic-utilities show/bgp_frr_v4.py:36-40 (summary subcommand) / show/bgp_frr_v4.py:160-164 (summary_helper: get_bgp_summary_from_all_bgp_instances → display_bgp_summary) -->ため、ステップ 5 で投入した `10.0.0.1` の neighbor が `Established` に到達しているかをここで判別できる (対向側未設定なら `Active` / `Idle` のまま停まる)。

## 評価シナリオ別の分岐

- 仮想評価 ([SONiC-VS](../reference/glossary.md#term-vs) / [GNS3](../architecture/sonic-on-gns3-vm.md)): 上記ステップ 1 は不要で、`steps-to-bring-up-sonic-vs` の libvirt 起動から開始する。
- 単体スイッチ評価: 上記 6 ステップが基本フロー。管理 IP 投入後に必要に応じて NTP / DNS を追加する。
- ToR 評価: VLAN / portchannel / BGP の組み合わせが必要で、reading path の portchannel と config_db の各テーブルを併読する。

## 既知のコンテンツ不足

- 「ラボ評価 30 分チュートリアル」専用ページは未整備で、本ページの bring-up 例はあくまで最小サブセットである。起動、初期ログイン、管理 IP、NTP / DNS、ポート up、VLAN、BGP neighbor、確認コマンドまでを直線で辿るチュートリアルは今後の整備対象。

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: SONiC 全体像と設定基盤](../topics/01-overview/index.md)
- [Topics: Lab / Virtual SONiC / Developer Entry](../topics/21-lab-vs-developer/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 14bb29c924c8 -->
