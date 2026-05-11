---
title: 用語集 (Glossary)
area: reference
verification: meta
last_verified: 2026-05-11
sources:
  - repo: sonic-net/SONiC
    path: README.md
    ref: master
related:
  config_db: []
  cli: []
  yang: []
---

# 用語集 (Glossary)

SONiC NOS で頻出する固有用語・略語・コンポーネント名・データベース名・デーモン名を、アルファベット順に整理した日本語用語集です。各エントリは「用語 / 略称 / 日本語訳 / 簡潔な説明 / 関連ページ」の形式で記載しています。

!!! info "本ページの位置づけ"
    本ページはメタ情報（プロジェクト独自の用語整理）であり、特定の HLD や実装に直接対応するものではありません。詳細な仕様は各機能ページを参照してください。

## A

### APPL_DB

- **略称**: APPL_DB
- **日本語訳**: アプリケーション DB
- **説明**: SONiC の Redis 上 DB の 1 つ（DB ID 0）。`*mgrd` 系デーモンが CONFIG_DB を加工して書き、`orchagent` 等の SwSS コンポーネントが購読する。「望ましいアプリケーション状態」を表現する。
- **関連**: [SONiC アーキテクチャ](../architecture/index.md)、[CONFIG_DB Reference](./config-db/index.md)

### ARP

- **略称**: ARP (Address Resolution Protocol)
- **日本語訳**: ARP
- **説明**: IPv4 アドレスを MAC アドレスに解決するプロトコル。SONiC では `arp_update` / カーネル ARP テーブルが NEIGH_TABLE 経由で `neighsyncd` → `orchagent` → SAI に流れる。
- **関連**: [NEIGH](./config-db/index.md)

### ASIC_DB

- **略称**: ASIC_DB
- **日本語訳**: ASIC DB
- **説明**: Redis DB ID 1。`syncd` が SAI オブジェクトの状態を反映する DB。SAI オブジェクト ID をキーに、属性のシリアライズ済み表現を保持する。
- **関連**: [SAI](#sai)、[syncd](#syncd)

### AsterNOS

- **略称**: AsterNOS
- **日本語訳**: AsterNOS (ベンダー版)
- **説明**: Asterfusion による SONiC ベースの商用 NOS。本ドキュメントのスコープ外。

## B

### BFD

- **略称**: BFD (Bidirectional Forwarding Detection)
- **日本語訳**: 双方向フォワーディング検出
- **説明**: 高速な対向疎通検出プロトコル (RFC 5880)。SONiC では `bfdorch` / `bfd_offload` 等で扱う。
- **関連**: [BFD HLD ページ群](../routing/index.md)

### BGP

- **略称**: BGP (Border Gateway Protocol)
- **日本語訳**: BGP
- **説明**: ルーティングプロトコル (RFC 4271)。SONiC では FRR の `bgpd` を使用し、`fpmsyncd` 経由でカーネル経由 APPL_DB へ反映する。
- **関連**: [BGP トピック](../topic/bgp.md)、[FRR](#frr)、[fpmsyncd](#fpmsyncd)

### bgpcfgd

- **略称**: bgpcfgd
- **日本語訳**: BGP 設定デーモン
- **説明**: CONFIG_DB の BGP 関連テーブル変更を購読し、FRR (`vtysh`) に流し込む Python デーモン (`sonic-buildimage/dockers/docker-fpm-frr/bgpcfgd`)。
- **関連**: [BGP トピック](../topic/bgp.md)

### Buffer Model

- **略称**: Buffer Model
- **日本語訳**: バッファモデル
- **説明**: SONiC の QoS バッファ管理モデル。`traditional` と `dynamic` の 2 種類があり、`BUFFER_POOL` / `BUFFER_PROFILE` / `BUFFER_PG` 等で構成される。
- **関連**: [QoS / Buffer](../acl-qos/index.md)

## C

### CONFIG_DB

- **略称**: CONFIG_DB
- **日本語訳**: 設定 DB
- **説明**: Redis DB ID 4。SONiC の正規の設定保持先。CLI / REST / gNMI / YANG いずれの経路から設定しても最終的にここに書かれる。`*mgrd` がここを購読して APPL_DB に変換する。
- **関連**: [CONFIG_DB Reference](./config-db/index.md)

### config_db.json

- **略称**: config_db.json
- **日本語訳**: 設定 DB スナップショット
- **説明**: CONFIG_DB の全エントリを JSON 化したファイル (`/etc/sonic/config_db.json`)。起動時に `sonic-cfggen` がロードする。

### config-setup

- **略称**: config-setup
- **日本語訳**: 設定セットアップ
- **説明**: 起動時に `config_db.json` を Redis にロードし、`minigraph.xml` から CONFIG_DB を生成する仕組み (`sonic-buildimage/files/scripts/config-setup`)。

### COUNTERS_DB

- **略称**: COUNTERS_DB
- **日本語訳**: カウンタ DB
- **説明**: Redis DB ID 2。`syncd` 配下の `FlexCounter` がポート / キュー / PG / バッファプール等の SAI 統計値を定期取得し、ここに書き込む。
- **関連**: [Counter / FlexCounter](../system/index.md)

### CoPP

- **略称**: CoPP (Control Plane Policing)
- **日本語訳**: 制御プレーンポリシング
- **説明**: 制御プレーン宛トラフィックをトラップして CPU に転送する SAI Hostif Trap 機能。SONiC では `copp_cfg.json` と `copporch` で制御。
- **関連**: [ACL/CoPP/Mirror トピック](../topic/07-acl-copp-mirror.md)

### CounterSyncd

- **略称**: CounterSyncd
- **日本語訳**: カウンタ同期
- **説明**: `syncd` 内のスレッド群で、SAI のカウンタを COUNTERS_DB に定期反映する。

### CRM

- **略称**: CRM (Critical Resource Monitor)
- **日本語訳**: 重要リソース監視
- **説明**: SAI オブジェクト数（ACL エントリ数、FDB 数、ルート数等）の上限と利用率を監視する機能。`crmorch` が担当。

## D

### DASH

- **略称**: DASH (Disaggregated API for SONiC Hosts)
- **日本語訳**: DASH
- **説明**: SmartSwitch / DPU 上でクラウドプロバイダ向けの SDN 機能を提供する SONiC サブシステム。VNET / ENI / Routing Rules 等を扱う。
- **関連**: [DASH ドキュメント群](../overlay/index.md)

### DHCP Relay

- **略称**: DHCP Relay
- **日本語訳**: DHCP リレー
- **説明**: ToR や leaf で DHCP メッセージを中継する機能。`dhcp_relay` コンテナで `isc-dhcp-relay` を実行。

### DPU

- **略称**: DPU (Data Processing Unit)
- **日本語訳**: データ処理ユニット
- **説明**: SmartSwitch の各ライン上に搭載される SoC。SONiC は NPU 側と DPU 側でそれぞれインスタンスを動かす。
- **関連**: [SmartSwitch](#smartswitch)

## E

### ECMP

- **略称**: ECMP (Equal-Cost Multi-Path)
- **日本語訳**: 等コストマルチパス
- **説明**: 同コストの複数経路に対しハッシュベースでフローを分散する機能。SONiC では SAI Next Hop Group で実装。
- **関連**: [VRF/ECMP トピック](../topic/vrf-ecmp.md)

### ENI

- **略称**: ENI (Elastic Network Interface)
- **日本語訳**: ENI
- **説明**: DASH における仮想 NIC 概念。テナント単位のポリシーバインド単位。
- **関連**: [DASH](#dash)

### EVPN

- **略称**: EVPN (Ethernet VPN)
- **日本語訳**: EVPN
- **説明**: BGP EVPN (RFC 7432) を用いた L2/L3 オーバーレイ制御プレーン。SONiC では FRR `bgpd` で実装。
- **関連**: [VXLAN EVPN VNET トピック](../topic/vxlan-evpn-vnet.md)

## F

### FDB

- **略称**: FDB (Forwarding Database)
- **日本語訳**: MAC 学習テーブル
- **説明**: L2 MAC アドレス学習テーブル。SAI FDB エントリとして ASIC に書かれる。`fdbsyncd` がカーネル ↔ APPL_DB の同期を行う。

### fdbsyncd

- **略称**: fdbsyncd
- **日本語訳**: FDB 同期デーモン
- **説明**: Linux カーネルブリッジの FDB エントリと APPL_DB の `FDB_TABLE` を同期する SwSS コンポーネント。

### FlexCounter

- **略称**: FlexCounter
- **日本語訳**: 柔軟カウンタ
- **説明**: `syncd` 内でポーリング対象 SAI オブジェクト群を動的に管理し、COUNTERS_DB に書き込む仕組み。

### FPM

- **略称**: FPM (Forwarding Plane Manager)
- **日本語訳**: 転送プレーンマネージャ
- **説明**: FRR のルートを外部プロセスに渡すための Quagga 由来プロトコル。SONiC では `zebra` → `fpmsyncd` → APPL_DB の経路で使われる。

### fpmsyncd

- **略称**: fpmsyncd
- **日本語訳**: FPM 同期デーモン
- **説明**: FRR `zebra` からの FPM メッセージを受信し、APPL_DB の `ROUTE_TABLE` / `LABEL_ROUTE_TABLE` に書き込む SwSS コンポーネント。
- **関連**: [FRR](#frr)、[BGP トピック](../topic/bgp.md)

### FRR

- **略称**: FRR (FRRouting)
- **日本語訳**: FRRouting
- **説明**: SONiC が採用するルーティングスタック。`bgpd` / `zebra` / `staticd` 等を含む。`docker-fpm-frr` コンテナ内で動く。
- **関連**: [BGP トピック](../topic/bgp.md)

## G

### gNMI

- **略称**: gNMI (gRPC Network Management Interface)
- **日本語訳**: gNMI
- **説明**: gRPC ベースのテレメトリ / 設定プロトコル。SONiC では `sonic-gnmi` (旧 `sonic-telemetry`) で実装。

### GCU

- **略称**: GCU (Generic Config Updater)
- **日本語訳**: 汎用設定更新
- **説明**: JSON Patch (RFC 6902) を CONFIG_DB に適用する仕組み。`sonic-utilities` の `config apply-patch` で利用。

## H

### HLD

- **略称**: HLD (High Level Design)
- **日本語訳**: 高位設計書
- **説明**: SONiC の機能設計ドキュメント。`sonic-net/SONiC` リポの `doc/` 配下に集約される。本ドキュメントは HLD を再構成して書かれている。

### hostcfgd

- **略称**: hostcfgd
- **日本語訳**: ホスト設定デーモン
- **説明**: CONFIG_DB の `AAA` / `TACPLUS` / `NTP` / `FEATURE` 等を購読し、Linux ホスト側の設定ファイル (`/etc/`) と `systemctl` を操作するデーモン。

## I

### intfmgrd

- **略称**: intfmgrd
- **日本語訳**: インターフェース設定マネージャ
- **説明**: CONFIG_DB の `INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` 等を購読し、APPL_DB の `INTF_TABLE` に変換する SwSS デーモン。

### intfsyncd

- **略称**: intfsyncd
- **日本語訳**: インターフェース同期
- **説明**: Netlink からインターフェース状態を読み APPL_DB に反映する SwSS デーモン（プロジェクトにより役割が `portmgrd` 等に分割）。

## L

### LACP

- **略称**: LACP (Link Aggregation Control Protocol)
- **日本語訳**: LACP
- **説明**: IEEE 802.1AX のリンク集約プロトコル。SONiC では `teamd` (libteam) で実装。
- **関連**: [L2/VLAN/LAG トピック](../topic/l2-vlan-lag.md)

### LAG

- **略称**: LAG (Link Aggregation Group) / PortChannel
- **日本語訳**: リンク集約 / ポートチャネル
- **説明**: 複数物理ポートを 1 論理リンクに束ねる機能。CONFIG_DB では `PORTCHANNEL` テーブルで表現。

### linkmgrd

- **略称**: linkmgrd
- **日本語訳**: リンクマネージャ
- **説明**: Dual-ToR (active-standby) 構成での MUX ポート状態管理デーモン。`sonic-linkmgr` リポで実装。
- **関連**: [Dual-ToR / MUX](../overlay/index.md)

### LLDP

- **略称**: LLDP (Link Layer Discovery Protocol)
- **日本語訳**: LLDP
- **説明**: 隣接装置発見プロトコル (IEEE 802.1AB)。SONiC は `lldpd` を `docker-lldp` で動かす。

## M

### MCLAG

- **略称**: MCLAG (Multi-Chassis LAG)
- **日本語訳**: MCLAG
- **説明**: 2 台の物理装置で共有 LAG を提供する機能。SONiC では `iccpd` 経由で同期。

### minigraph.xml

- **略称**: minigraph
- **日本語訳**: ミニグラフ
- **説明**: Microsoft 由来のトポロジ記述 XML。`sonic-cfggen -m` で CONFIG_DB に変換される起動時設定ソース。

### MUX

- **略称**: MUX
- **日本語訳**: MUX (Dual-ToR セレクタ)
- **説明**: Dual-ToR 構成でサーバ側 NIC を Active 側 ToR に向けるための Y ケーブル / smartNIC スイッチング機構。

## N

### NAT

- **略称**: NAT (Network Address Translation)
- **日本語訳**: NAT
- **説明**: SONiC の NAT 機能。`natmgrd` / `natsyncd` / `natorch` で構成。

### natmgrd / natsyncd

- **略称**: natmgrd / natsyncd
- **日本語訳**: NAT 管理 / 同期デーモン
- **説明**: CONFIG_DB の `NAT` 関連テーブルを APPL_DB / カーネル NAT (conntrack) に橋渡しする SwSS デーモン。

### neighsyncd

- **略称**: neighsyncd
- **日本語訳**: 隣接同期デーモン
- **説明**: Linux カーネルの neighbor (ARP/NDP) テーブルを Netlink で監視し、APPL_DB の `NEIGH_TABLE` に反映する。

### Netlink

- **略称**: Netlink
- **日本語訳**: Netlink
- **説明**: Linux カーネルとユーザ空間間の通信ソケット。SONiC では FRR / `*syncd` が広く利用。

### NPU

- **略称**: NPU (Network Processing Unit)
- **日本語訳**: NPU (スイッチ ASIC 側)
- **説明**: SmartSwitch における従来のスイッチ ASIC ホスト側の呼称。DPU の対概念。

## O

### orchagent

- **略称**: orchagent
- **日本語訳**: オーケストレーションエージェント
- **説明**: SwSS の中核プロセス。APPL_DB を購読し、SAI 操作を計画して `syncd` に渡す。`PortsOrch` / `RouteOrch` / `NeighOrch` / `AclOrch` 等多数の Orch を含む。
- **関連**: [SwSS / orchagent アーキテクチャ](../architecture/index.md)

## P

### PFC

- **略称**: PFC (Priority-based Flow Control)
- **日本語訳**: 優先度ベースフロー制御
- **説明**: IEEE 802.1Qbb。SONiC では `pfcwd` (PFC Watchdog) と組み合わせて運用する。

### PFC Watchdog

- **略称**: pfcwd
- **日本語訳**: PFC ウォッチドッグ
- **説明**: PFC でデッドロックしているキューを検出して一時的にドレインする仕組み。

### portmgrd

- **略称**: portmgrd
- **日本語訳**: ポート設定マネージャ
- **説明**: CONFIG_DB の `PORT` テーブルを購読し、APPL_DB に書き出す SwSS デーモン。

### portsyncd

- **略称**: portsyncd
- **日本語訳**: ポート同期デーモン
- **説明**: `port_config.ini` / `platform.json` を読み込み、初期 PORT エントリを APPL_DB に登録する SwSS デーモン。

### PortChannel

- **略称**: PortChannel
- **日本語訳**: ポートチャネル
- **説明**: SONiC の LAG の呼称。CONFIG_DB テーブル名も `PORTCHANNEL`。

## Q

### QoS

- **略称**: QoS (Quality of Service)
- **日本語訳**: QoS
- **説明**: `TC_TO_QUEUE_MAP` / `DSCP_TO_TC_MAP` / `SCHEDULER` 等で構成される SONiC のキューイング・スケジューリング・マーキング機構。

## R

### Redis

- **略称**: Redis
- **日本語訳**: Redis
- **説明**: SONiC のすべての DB (CONFIG_DB / APPL_DB / STATE_DB / ASIC_DB / COUNTERS_DB / LOGLEVEL_DB 等) のバックエンド。`docker-database` コンテナ内で動く。

### RIF

- **略称**: RIF (Router Interface)
- **日本語訳**: ルータインターフェース
- **説明**: SAI における L3 インターフェースオブジェクト。`IntfsOrch` が管理。

### ROUTE_TABLE

- **略称**: ROUTE_TABLE
- **日本語訳**: ルートテーブル (APPL_DB)
- **説明**: APPL_DB 上のルート受け皿。`fpmsyncd` が書き、`RouteOrch` が購読して SAI Route Entry に変換する。

## S

### SAI

- **略称**: SAI (Switch Abstraction Interface)
- **日本語訳**: スイッチ抽象化インターフェース
- **説明**: SONiC とベンダー ASIC の境界となる C API。OCP 標準化。`sonic-sairedis` がプロセス境界でラップ。
- **関連**: [SAI Reference](./index.md)

### sonic-buildimage

- **略称**: sonic-buildimage
- **日本語訳**: SONiC ビルドイメージ
- **説明**: SONiC 全体のビルドシステム / 各ベンダーイメージ生成リポ。

### sonic-cfggen

- **略称**: sonic-cfggen
- **日本語訳**: 設定ジェネレータ
- **説明**: minigraph / Jinja テンプレート / JSON から CONFIG_DB を生成する起動時ツール。

### sonic-mgmt

- **略称**: sonic-mgmt
- **日本語訳**: SONiC 管理 (テスト)
- **説明**: Ansible ベースの E2E テストフレームワークが置かれるリポ。

### sonic-swss

- **略称**: sonic-swss
- **日本語訳**: SwSS リポ
- **説明**: orchagent / portsyncd / fdbsyncd 等 SwSS デーモン群のソース。

### sonic-swss-common

- **略称**: sonic-swss-common
- **日本語訳**: SwSS 共通ライブラリ
- **説明**: SwSS / syncd / 各 mgrd が共有する Redis ラッパや ProducerStateTable / ConsumerStateTable を提供する C++ ライブラリ。

### sonic-sairedis

- **略称**: sonic-sairedis
- **日本語訳**: SAI Redis シム
- **説明**: orchagent ↔ syncd 間で SAI 呼び出しを Redis 上のキューに乗せるプロセス境界実装。`syncd` 本体もここに含まれる。

### sonic-utilities

- **略称**: sonic-utilities
- **日本語訳**: SONiC CLI ユーティリティ
- **説明**: `config` / `show` / `sonic-installer` 等の Python CLI が置かれるリポ。
- **関連**: [CLI Reference](./cli/index.md)

### SmartSwitch

- **略称**: SmartSwitch
- **日本語訳**: SmartSwitch
- **説明**: NPU + 複数 DPU を 1 シャーシに搭載するアーキテクチャ。DASH と組み合わせて使う。

### STATE_DB

- **略称**: STATE_DB
- **日本語訳**: 状態 DB
- **説明**: Redis DB ID 6。各コンポーネントの「現在の運用状態」を表現する DB。`*mgrd` 系がここを読んで設定収束を判定する。

### swssconfig

- **略称**: swssconfig
- **日本語訳**: SwSS 設定ローダ
- **説明**: 静的 JSON ファイル (例: `qos_config.json` / `copp_cfg.json`) を APPL_DB へ流し込むユーティリティ。

### syncd

- **略称**: syncd
- **日本語訳**: ASIC 同期デーモン
- **説明**: SAI を直接コールする唯一のプロセス。`docker-syncd-<vendor>` コンテナ内で動く。ASIC_DB を購読して SAI 呼び出しに変換する。

## T

### teamd / teamsyncd / teammgrd

- **略称**: teamd / teamsyncd / teammgrd
- **日本語訳**: teamd 系 LAG デーモン
- **説明**: Linux `libteam` ベースの LACP 実装。`teammgrd` が CONFIG_DB 購読、`teamsyncd` が Netlink ↔ APPL_DB 同期、`teamd` が LACP プロトコル本体。

### tunnelmgrd

- **略称**: tunnelmgrd
- **日本語訳**: トンネル管理デーモン
- **説明**: CONFIG_DB の `TUNNEL` / `MUX_TUNNEL` 等を購読し APPL_DB に変換する SwSS デーモン。

## V

### VLAN

- **略称**: VLAN
- **日本語訳**: VLAN
- **説明**: CONFIG_DB では `VLAN` / `VLAN_MEMBER` / `VLAN_INTERFACE` で表現。Linux カーネルブリッジと SAI 双方に反映される。

### vlanmgrd

- **略称**: vlanmgrd
- **日本語訳**: VLAN 管理デーモン
- **説明**: CONFIG_DB の `VLAN` テーブルを購読し、Linux ブリッジと APPL_DB を整合させる SwSS デーモン。

### VNET

- **略称**: VNET (Virtual Network)
- **日本語訳**: VNET
- **説明**: SONiC オーバーレイ / DASH 双方で使われるテナント仮想ネットワーク概念。CONFIG_DB の `VNET` テーブルで定義。
- **関連**: [VXLAN EVPN VNET トピック](../topic/vxlan-evpn-vnet.md)

### VRF

- **略称**: VRF (Virtual Routing and Forwarding)
- **日本語訳**: VRF
- **説明**: ルーティングテーブル分離機構。Linux VRF デバイスと SAI Virtual Router の双方で実現。
- **関連**: [VRF/ECMP トピック](../topic/vrf-ecmp.md)

### vrfmgrd

- **略称**: vrfmgrd
- **日本語訳**: VRF 管理デーモン
- **説明**: CONFIG_DB の `VRF` テーブルを購読し Linux VRF デバイスと APPL_DB を整合させる SwSS デーモン。

### VXLAN

- **略称**: VXLAN (Virtual eXtensible LAN)
- **日本語訳**: VXLAN
- **説明**: L2 over UDP オーバーレイカプセル化 (RFC 7348)。SONiC では `VxlanMgr` / `VxlanOrch` で扱う。

### vxlanmgrd

- **略称**: vxlanmgrd
- **日本語訳**: VXLAN 管理デーモン
- **説明**: CONFIG_DB の `VXLAN_TUNNEL` / `VXLAN_TUNNEL_MAP` 等を購読し APPL_DB に流し、Linux 側 VXLAN デバイスも作成。

## W

### WRED

- **略称**: WRED (Weighted Random Early Detection)
- **日本語訳**: 重み付きランダム早期検出
- **説明**: バッファ輻輳前にパケットをランダムドロップ / ECN マークする QoS 機能。CONFIG_DB の `WRED_PROFILE` で定義。

## Y

### YANG

- **略称**: YANG
- **日本語訳**: YANG
- **説明**: RFC 7950 のモデリング言語。SONiC は `sonic-yang-models` で CONFIG_DB スキーマを YANG 化している。
- **関連**: [YANG Reference](./yang/index.md)

### yang-validator

- **略称**: yang-validator
- **日本語訳**: YANG バリデータ
- **説明**: `sonic-yang-mgmt` が提供する Python ライブラリ。CONFIG_DB の内容が YANG スキーマに合致するか検証する。

## Z

### zebra

- **略称**: zebra
- **日本語訳**: zebra
- **説明**: FRR の中核 RIB / ルート再配布デーモン。SONiC では FPM 経由で `fpmsyncd` にルートを渡す。

### ZTP

- **略称**: ZTP (Zero Touch Provisioning)
- **日本語訳**: ゼロタッチプロビジョニング
- **説明**: 初期起動時に DHCP option 経由でプロビジョニング URL を取得し設定を自動投入する仕組み。`sonic-ztp` で実装。

## 関連

- [SONiC アーキテクチャ概要](../architecture/index.md)
- [CONFIG_DB Reference](./config-db/index.md)
- [CLI Reference](./cli/index.md)
- [YANG Reference](./yang/index.md)

## 引用元

- sonic-net/SONiC (master): リポジトリ全体の README および `doc/` 配下の各 HLD
- sonic-net/sonic-swss (master): SwSS デーモン群実装
- sonic-net/sonic-sairedis (master): syncd / SAI Redis シム
- sonic-net/sonic-buildimage (master): 各 Docker / 起動スクリプト
- sonic-net/sonic-utilities (master): CLI 実装
- sonic-net/sonic-yang-models (master): YANG モデル

本ページは個別 commit に紐付かないメタ情報のため、`sources` は `ref: master` として代表ファイルのみ示している。
