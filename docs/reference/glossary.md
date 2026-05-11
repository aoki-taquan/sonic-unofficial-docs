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

### APPL_DB {#term-appl_db}

- **略称**: APPL_DB
- **日本語訳**: アプリケーション DB
- **説明**: SONiC の Redis 上 DB の 1 つ（DB ID 0）。`*mgrd` 系デーモンが CONFIG_DB を加工して書き、`orchagent` 等の SwSS コンポーネントが購読する。「望ましいアプリケーション状態」を表現する。
- **関連**: [SONiC アーキテクチャ](../architecture/index.md)、[CONFIG_DB Reference](./config-db/index.md)

### ARP {#term-arp}

- **略称**: ARP (Address Resolution Protocol)
- **日本語訳**: ARP
- **説明**: IPv4 アドレスを MAC アドレスに解決するプロトコル。SONiC では `arp_update` / カーネル ARP テーブルが NEIGH_TABLE 経由で `neighsyncd` → `orchagent` → SAI に流れる。
- **関連**: [NEIGH](./config-db/index.md)

### ASIC_DB {#term-asic_db}

- **略称**: ASIC_DB
- **日本語訳**: ASIC DB
- **説明**: Redis DB ID 1。`syncd` が SAI オブジェクトの状態を反映する DB。SAI オブジェクト ID をキーに、属性のシリアライズ済み表現を保持する。
- **関連**: [SAI](#sai)、[syncd](#syncd)

### AsterNOS {#term-asternos}

- **略称**: AsterNOS
- **日本語訳**: AsterNOS (ベンダー版)
- **説明**: Asterfusion による SONiC ベースの商用 NOS。本ドキュメントのスコープ外。

## B

### BFD {#term-bfd}

- **略称**: BFD (Bidirectional Forwarding Detection)
- **日本語訳**: 双方向フォワーディング検出
- **説明**: 高速な対向疎通検出プロトコル (RFC 5880)。SONiC では `bfdorch` / `bfd_offload` 等で扱う。
- **関連**: [BFD HLD ページ群](../routing/index.md)

### BGP {#term-bgp}

- **略称**: BGP (Border Gateway Protocol)
- **日本語訳**: BGP
- **説明**: ルーティングプロトコル (RFC 4271)。SONiC では FRR の `bgpd` を使用し、`fpmsyncd` 経由でカーネル経由 APPL_DB へ反映する。
- **関連**: [BGP トピック](../topics/02-bgp/index.md)、[FRR](#frr)、[fpmsyncd](#fpmsyncd)

### bgpcfgd {#term-bgpcfgd}

- **略称**: bgpcfgd
- **日本語訳**: BGP 設定デーモン
- **説明**: CONFIG_DB の BGP 関連テーブル変更を購読し、FRR (`vtysh`) に流し込む Python デーモン (`sonic-buildimage/dockers/docker-fpm-frr/bgpcfgd`)。
- **関連**: [BGP トピック](../topics/02-bgp/index.md)

### Buffer Model {#term-buffer-model}

- **略称**: Buffer Model
- **日本語訳**: バッファモデル
- **説明**: SONiC の QoS バッファ管理モデル。`traditional` と `dynamic` の 2 種類があり、`BUFFER_POOL` / `BUFFER_PROFILE` / `BUFFER_PG` 等で構成される。
- **関連**: [QoS / Buffer](../acl-qos/index.md)

## C

### CONFIG_DB {#term-config_db}

- **略称**: CONFIG_DB
- **日本語訳**: 設定 DB
- **説明**: Redis DB ID 4。SONiC の正規の設定保持先。CLI / REST / gNMI / YANG いずれの経路から設定しても最終的にここに書かれる。`*mgrd` がここを購読して APPL_DB に変換する。
- **関連**: [CONFIG_DB Reference](./config-db/index.md)

### config_db.json {#term-config_db.json}

- **略称**: config_db.json
- **日本語訳**: 設定 DB スナップショット
- **説明**: CONFIG_DB の全エントリを JSON 化したファイル (`/etc/sonic/config_db.json`)。起動時に `sonic-cfggen` がロードする。

### config-setup {#term-config-setup}

- **略称**: config-setup
- **日本語訳**: 設定セットアップ
- **説明**: 起動時に `config_db.json` を Redis にロードし、`minigraph.xml` から CONFIG_DB を生成する仕組み (`sonic-buildimage/files/scripts/config-setup`)。

### COUNTERS_DB {#term-counters_db}

- **略称**: COUNTERS_DB
- **日本語訳**: カウンタ DB
- **説明**: Redis DB ID 2。`syncd` 配下の `FlexCounter` がポート / キュー / PG / バッファプール等の SAI 統計値を定期取得し、ここに書き込む。
- **関連**: [Counter / FlexCounter](../system/index.md)

### CoPP {#term-copp}

- **略称**: CoPP (Control Plane Policing)
- **日本語訳**: 制御プレーンポリシング
- **説明**: 制御プレーン宛トラフィックをトラップして CPU に転送する SAI Hostif Trap 機能。SONiC では `copp_cfg.json` と `copporch` で制御。
- **関連**: [ACL/CoPP/Mirror トピック](../topics/07-acl-copp-mirror/index.md)

### CounterSyncd {#term-countersyncd}

- **略称**: CounterSyncd
- **日本語訳**: カウンタ同期
- **説明**: `syncd` 内のスレッド群で、SAI のカウンタを COUNTERS_DB に定期反映する。

### CRM {#term-crm}

- **略称**: CRM (Critical Resource Monitor)
- **日本語訳**: 重要リソース監視
- **説明**: SAI オブジェクト数（ACL エントリ数、FDB 数、ルート数等）の上限と利用率を監視する機能。`crmorch` が担当。

## D

### DASH {#term-dash}

- **略称**: DASH (Disaggregated API for SONiC Hosts)
- **日本語訳**: DASH
- **説明**: SmartSwitch / DPU 上でクラウドプロバイダ向けの SDN 機能を提供する SONiC サブシステム。VNET / ENI / Routing Rules 等を扱う。
- **関連**: [DASH ドキュメント群](../overlay/index.md)

### DHCP Relay {#term-dhcp-relay}

- **略称**: DHCP Relay
- **日本語訳**: DHCP リレー
- **説明**: ToR や leaf で DHCP メッセージを中継する機能。`dhcp_relay` コンテナで `isc-dhcp-relay` を実行。

### DPU {#term-dpu}

- **略称**: DPU (Data Processing Unit)
- **日本語訳**: データ処理ユニット
- **説明**: SmartSwitch の各ライン上に搭載される SoC。SONiC は NPU 側と DPU 側でそれぞれインスタンスを動かす。
- **関連**: [SmartSwitch](#smartswitch)

## E

### ECMP {#term-ecmp}

- **略称**: ECMP (Equal-Cost Multi-Path)
- **日本語訳**: 等コストマルチパス
- **説明**: 同コストの複数経路に対しハッシュベースでフローを分散する機能。SONiC では SAI Next Hop Group で実装。
- **関連**: [VRF/ECMP トピック](../topics/04-vrf-ecmp/index.md)

### ENI {#term-eni}

- **略称**: ENI (Elastic Network Interface)
- **日本語訳**: ENI
- **説明**: DASH における仮想 NIC 概念。テナント単位のポリシーバインド単位。
- **関連**: [DASH](#dash)

### EVPN {#term-evpn}

- **略称**: EVPN (Ethernet VPN)
- **日本語訳**: EVPN
- **説明**: BGP EVPN (RFC 7432) を用いた L2/L3 オーバーレイ制御プレーン。SONiC では FRR `bgpd` で実装。
- **関連**: [VXLAN EVPN VNET トピック](../topics/03-vxlan-evpn/index.md)

## F

### FDB {#term-fdb}

- **略称**: FDB (Forwarding Database)
- **日本語訳**: MAC 学習テーブル
- **説明**: L2 MAC アドレス学習テーブル。SAI FDB エントリとして ASIC に書かれる。`fdbsyncd` がカーネル ↔ APPL_DB の同期を行う。

### fdbsyncd {#term-fdbsyncd}

- **略称**: fdbsyncd
- **日本語訳**: FDB 同期デーモン
- **説明**: Linux カーネルブリッジの FDB エントリと APPL_DB の `FDB_TABLE` を同期する SwSS コンポーネント。

### FlexCounter {#term-flexcounter}

- **略称**: FlexCounter
- **日本語訳**: 柔軟カウンタ
- **説明**: `syncd` 内でポーリング対象 SAI オブジェクト群を動的に管理し、COUNTERS_DB に書き込む仕組み。

### FPM {#term-fpm}

- **略称**: FPM (Forwarding Plane Manager)
- **日本語訳**: 転送プレーンマネージャ
- **説明**: FRR のルートを外部プロセスに渡すための Quagga 由来プロトコル。SONiC では `zebra` → `fpmsyncd` → APPL_DB の経路で使われる。

### fpmsyncd {#term-fpmsyncd}

- **略称**: fpmsyncd
- **日本語訳**: FPM 同期デーモン
- **説明**: FRR `zebra` からの FPM メッセージを受信し、APPL_DB の `ROUTE_TABLE` / `LABEL_ROUTE_TABLE` に書き込む SwSS コンポーネント。
- **関連**: [FRR](#frr)、[BGP トピック](../topics/02-bgp/index.md)

### FRR {#term-frr}

- **略称**: FRR (FRRouting)
- **日本語訳**: FRRouting
- **説明**: SONiC が採用するルーティングスタック。`bgpd` / `zebra` / `staticd` 等を含む。`docker-fpm-frr` コンテナ内で動く。
- **関連**: [BGP トピック](../topics/02-bgp/index.md)

## G

### gNMI {#term-gnmi}

- **略称**: gNMI (gRPC Network Management Interface)
- **日本語訳**: gNMI
- **説明**: gRPC ベースのテレメトリ / 設定プロトコル。SONiC では `sonic-gnmi` (旧 `sonic-telemetry`) で実装。

### GCU {#term-gcu}

- **略称**: GCU (Generic Config Updater)
- **日本語訳**: 汎用設定更新
- **説明**: JSON Patch (RFC 6902) を CONFIG_DB に適用する仕組み。`sonic-utilities` の `config apply-patch` で利用。

## H

### HLD {#term-hld}

- **略称**: HLD (High Level Design)
- **日本語訳**: 高位設計書
- **説明**: SONiC の機能設計ドキュメント。`sonic-net/SONiC` リポの `doc/` 配下に集約される。本ドキュメントは HLD を再構成して書かれている。

### hostcfgd {#term-hostcfgd}

- **略称**: hostcfgd
- **日本語訳**: ホスト設定デーモン
- **説明**: CONFIG_DB の `AAA` / `TACPLUS` / `NTP` / `FEATURE` 等を購読し、Linux ホスト側の設定ファイル (`/etc/`) と `systemctl` を操作するデーモン。

## I

### intfmgrd {#term-intfmgrd}

- **略称**: intfmgrd
- **日本語訳**: インターフェース設定マネージャ
- **説明**: CONFIG_DB の `INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` 等を購読し、APPL_DB の `INTF_TABLE` に変換する SwSS デーモン。

### intfsyncd {#term-intfsyncd}

- **略称**: intfsyncd
- **日本語訳**: インターフェース同期
- **説明**: Netlink からインターフェース状態を読み APPL_DB に反映する SwSS デーモン（プロジェクトにより役割が `portmgrd` 等に分割）。

## L

### LACP {#term-lacp}

- **略称**: LACP (Link Aggregation Control Protocol)
- **日本語訳**: LACP
- **説明**: IEEE 802.1AX のリンク集約プロトコル。SONiC では `teamd` (libteam) で実装。
- **関連**: [L2/VLAN/LAG トピック](../topics/06-l2-vlan-lag/index.md)

### LAG {#term-lag}

- **略称**: LAG (Link Aggregation Group) / PortChannel
- **日本語訳**: リンク集約 / ポートチャネル
- **説明**: 複数物理ポートを 1 論理リンクに束ねる機能。CONFIG_DB では `PORTCHANNEL` テーブルで表現。

### linkmgrd {#term-linkmgrd}

- **略称**: linkmgrd
- **日本語訳**: リンクマネージャ
- **説明**: Dual-ToR (active-standby) 構成での MUX ポート状態管理デーモン。`sonic-linkmgr` リポで実装。
- **関連**: [Dual-ToR / MUX](../overlay/index.md)

### LLDP {#term-lldp}

- **略称**: LLDP (Link Layer Discovery Protocol)
- **日本語訳**: LLDP
- **説明**: 隣接装置発見プロトコル (IEEE 802.1AB)。SONiC は `lldpd` を `docker-lldp` で動かす。

## M

### MCLAG {#term-mclag}

- **略称**: MCLAG (Multi-Chassis LAG)
- **日本語訳**: MCLAG
- **説明**: 2 台の物理装置で共有 LAG を提供する機能。SONiC では `iccpd` 経由で同期。

### minigraph.xml {#term-minigraph.xml}

- **略称**: minigraph
- **日本語訳**: ミニグラフ
- **説明**: Microsoft 由来のトポロジ記述 XML。`sonic-cfggen -m` で CONFIG_DB に変換される起動時設定ソース。

### MUX {#term-mux}

- **略称**: MUX
- **日本語訳**: MUX (Dual-ToR セレクタ)
- **説明**: Dual-ToR 構成でサーバ側 NIC を Active 側 ToR に向けるための Y ケーブル / smartNIC スイッチング機構。

## N

### NAT {#term-nat}

- **略称**: NAT (Network Address Translation)
- **日本語訳**: NAT
- **説明**: SONiC の NAT 機能。`natmgrd` / `natsyncd` / `natorch` で構成。

### natmgrd / natsyncd {#term-natmgrd-natsyncd}

- **略称**: natmgrd / natsyncd
- **日本語訳**: NAT 管理 / 同期デーモン
- **説明**: CONFIG_DB の `NAT` 関連テーブルを APPL_DB / カーネル NAT (conntrack) に橋渡しする SwSS デーモン。

### neighsyncd {#term-neighsyncd}

- **略称**: neighsyncd
- **日本語訳**: 隣接同期デーモン
- **説明**: Linux カーネルの neighbor (ARP/NDP) テーブルを Netlink で監視し、APPL_DB の `NEIGH_TABLE` に反映する。

### Netlink {#term-netlink}

- **略称**: Netlink
- **日本語訳**: Netlink
- **説明**: Linux カーネルとユーザ空間間の通信ソケット。SONiC では FRR / `*syncd` が広く利用。

### NPU {#term-npu}

- **略称**: NPU (Network Processing Unit)
- **日本語訳**: NPU (スイッチ ASIC 側)
- **説明**: SmartSwitch における従来のスイッチ ASIC ホスト側の呼称。DPU の対概念。

## O

### orchagent {#term-orchagent}

- **略称**: orchagent
- **日本語訳**: オーケストレーションエージェント
- **説明**: SwSS の中核プロセス。APPL_DB を購読し、SAI 操作を計画して `syncd` に渡す。`PortsOrch` / `RouteOrch` / `NeighOrch` / `AclOrch` 等多数の Orch を含む。
- **関連**: [SwSS / orchagent アーキテクチャ](../architecture/index.md)

## P

### PFC {#term-pfc}

- **略称**: PFC (Priority-based Flow Control)
- **日本語訳**: 優先度ベースフロー制御
- **説明**: IEEE 802.1Qbb。SONiC では `pfcwd` (PFC Watchdog) と組み合わせて運用する。

### PFC Watchdog {#term-pfc-watchdog}

- **略称**: pfcwd
- **日本語訳**: PFC ウォッチドッグ
- **説明**: PFC でデッドロックしているキューを検出して一時的にドレインする仕組み。

### portmgrd {#term-portmgrd}

- **略称**: portmgrd
- **日本語訳**: ポート設定マネージャ
- **説明**: CONFIG_DB の `PORT` テーブルを購読し、APPL_DB に書き出す SwSS デーモン。

### portsyncd {#term-portsyncd}

- **略称**: portsyncd
- **日本語訳**: ポート同期デーモン
- **説明**: `port_config.ini` / `platform.json` を読み込み、初期 PORT エントリを APPL_DB に登録する SwSS デーモン。

### PortChannel {#term-portchannel}

- **略称**: PortChannel
- **日本語訳**: ポートチャネル
- **説明**: SONiC の LAG の呼称。CONFIG_DB テーブル名も `PORTCHANNEL`。

## Q

### QoS {#term-qos}

- **略称**: QoS (Quality of Service)
- **日本語訳**: QoS
- **説明**: `TC_TO_QUEUE_MAP` / `DSCP_TO_TC_MAP` / `SCHEDULER` 等で構成される SONiC のキューイング・スケジューリング・マーキング機構。

## R

### Redis {#term-redis}

- **略称**: Redis
- **日本語訳**: Redis
- **説明**: SONiC のすべての DB (CONFIG_DB / APPL_DB / STATE_DB / ASIC_DB / COUNTERS_DB / LOGLEVEL_DB 等) のバックエンド。`docker-database` コンテナ内で動く。

### RIF {#term-rif}

- **略称**: RIF (Router Interface)
- **日本語訳**: ルータインターフェース
- **説明**: SAI における L3 インターフェースオブジェクト。`IntfsOrch` が管理。

### ROUTE_TABLE {#term-route_table}

- **略称**: ROUTE_TABLE
- **日本語訳**: ルートテーブル (APPL_DB)
- **説明**: APPL_DB 上のルート受け皿。`fpmsyncd` が書き、`RouteOrch` が購読して SAI Route Entry に変換する。

## S

### SAI {#term-sai}

- **略称**: SAI (Switch Abstraction Interface)
- **日本語訳**: スイッチ抽象化インターフェース
- **説明**: SONiC とベンダー ASIC の境界となる C API。OCP 標準化。`sonic-sairedis` がプロセス境界でラップ。
- **関連**: [SAI Reference](./index.md)

### sonic-buildimage {#term-sonic-buildimage}

- **略称**: sonic-buildimage
- **日本語訳**: SONiC ビルドイメージ
- **説明**: SONiC 全体のビルドシステム / 各ベンダーイメージ生成リポ。

### sonic-cfggen {#term-sonic-cfggen}

- **略称**: sonic-cfggen
- **日本語訳**: 設定ジェネレータ
- **説明**: minigraph / Jinja テンプレート / JSON から CONFIG_DB を生成する起動時ツール。

### sonic-mgmt {#term-sonic-mgmt}

- **略称**: sonic-mgmt
- **日本語訳**: SONiC 管理 (テスト)
- **説明**: Ansible ベースの E2E テストフレームワークが置かれるリポ。

### sonic-swss {#term-sonic-swss}

- **略称**: sonic-swss
- **日本語訳**: SwSS リポ
- **説明**: orchagent / portsyncd / fdbsyncd 等 SwSS デーモン群のソース。

### sonic-swss-common {#term-sonic-swss-common}

- **略称**: sonic-swss-common
- **日本語訳**: SwSS 共通ライブラリ
- **説明**: SwSS / syncd / 各 mgrd が共有する Redis ラッパや ProducerStateTable / ConsumerStateTable を提供する C++ ライブラリ。

### sonic-sairedis {#term-sonic-sairedis}

- **略称**: sonic-sairedis
- **日本語訳**: SAI Redis シム
- **説明**: orchagent ↔ syncd 間で SAI 呼び出しを Redis 上のキューに乗せるプロセス境界実装。`syncd` 本体もここに含まれる。

### sonic-utilities {#term-sonic-utilities}

- **略称**: sonic-utilities
- **日本語訳**: SONiC CLI ユーティリティ
- **説明**: `config` / `show` / `sonic-installer` 等の Python CLI が置かれるリポ。
- **関連**: [CLI Reference](./cli/index.md)

### SmartSwitch {#term-smartswitch}

- **略称**: SmartSwitch
- **日本語訳**: SmartSwitch
- **説明**: NPU + 複数 DPU を 1 シャーシに搭載するアーキテクチャ。DASH と組み合わせて使う。

### STATE_DB {#term-state_db}

- **略称**: STATE_DB
- **日本語訳**: 状態 DB
- **説明**: Redis DB ID 6。各コンポーネントの「現在の運用状態」を表現する DB。`*mgrd` 系がここを読んで設定収束を判定する。

### swssconfig {#term-swssconfig}

- **略称**: swssconfig
- **日本語訳**: SwSS 設定ローダ
- **説明**: 静的 JSON ファイル (例: `qos_config.json` / `copp_cfg.json`) を APPL_DB へ流し込むユーティリティ。

### syncd {#term-syncd}

- **略称**: syncd
- **日本語訳**: ASIC 同期デーモン
- **説明**: SAI を直接コールする唯一のプロセス。`docker-syncd-<vendor>` コンテナ内で動く。ASIC_DB を購読して SAI 呼び出しに変換する。

## T

### teamd / teamsyncd / teammgrd {#term-teamd-teamsyncd-teammgrd}

- **略称**: teamd / teamsyncd / teammgrd
- **日本語訳**: teamd 系 LAG デーモン
- **説明**: Linux `libteam` ベースの LACP 実装。`teammgrd` が CONFIG_DB 購読、`teamsyncd` が Netlink ↔ APPL_DB 同期、`teamd` が LACP プロトコル本体。

### tunnelmgrd {#term-tunnelmgrd}

- **略称**: tunnelmgrd
- **日本語訳**: トンネル管理デーモン
- **説明**: CONFIG_DB の `TUNNEL` / `MUX_TUNNEL` 等を購読し APPL_DB に変換する SwSS デーモン。

## V

### VLAN {#term-vlan}

- **略称**: VLAN
- **日本語訳**: VLAN
- **説明**: CONFIG_DB では `VLAN` / `VLAN_MEMBER` / `VLAN_INTERFACE` で表現。Linux カーネルブリッジと SAI 双方に反映される。

### vlanmgrd {#term-vlanmgrd}

- **略称**: vlanmgrd
- **日本語訳**: VLAN 管理デーモン
- **説明**: CONFIG_DB の `VLAN` テーブルを購読し、Linux ブリッジと APPL_DB を整合させる SwSS デーモン。

### VNET {#term-vnet}

- **略称**: VNET (Virtual Network)
- **日本語訳**: VNET
- **説明**: SONiC オーバーレイ / DASH 双方で使われるテナント仮想ネットワーク概念。CONFIG_DB の `VNET` テーブルで定義。
- **関連**: [VXLAN EVPN VNET トピック](../topics/03-vxlan-evpn/index.md)

### VRF {#term-vrf}

- **略称**: VRF (Virtual Routing and Forwarding)
- **日本語訳**: VRF
- **説明**: ルーティングテーブル分離機構。Linux VRF デバイスと SAI Virtual Router の双方で実現。
- **関連**: [VRF/ECMP トピック](../topics/04-vrf-ecmp/index.md)

### vrfmgrd {#term-vrfmgrd}

- **略称**: vrfmgrd
- **日本語訳**: VRF 管理デーモン
- **説明**: CONFIG_DB の `VRF` テーブルを購読し Linux VRF デバイスと APPL_DB を整合させる SwSS デーモン。

### VXLAN {#term-vxlan}

- **略称**: VXLAN (Virtual eXtensible LAN)
- **日本語訳**: VXLAN
- **説明**: L2 over UDP オーバーレイカプセル化 (RFC 7348)。SONiC では `VxlanMgr` / `VxlanOrch` で扱う。

### vxlanmgrd {#term-vxlanmgrd}

- **略称**: vxlanmgrd
- **日本語訳**: VXLAN 管理デーモン
- **説明**: CONFIG_DB の `VXLAN_TUNNEL` / `VXLAN_TUNNEL_MAP` 等を購読し APPL_DB に流し、Linux 側 VXLAN デバイスも作成。

## W

### WRED {#term-wred}

- **略称**: WRED (Weighted Random Early Detection)
- **日本語訳**: 重み付きランダム早期検出
- **説明**: バッファ輻輳前にパケットをランダムドロップ / ECN マークする QoS 機能。CONFIG_DB の `WRED_PROFILE` で定義。

## Y

### YANG {#term-yang}

- **略称**: YANG
- **日本語訳**: YANG
- **説明**: RFC 7950 のモデリング言語。SONiC は `sonic-yang-models` で CONFIG_DB スキーマを YANG 化している。
- **関連**: [YANG Reference](./yang/index.md)

### yang-validator {#term-yang-validator}

- **略称**: yang-validator
- **日本語訳**: YANG バリデータ
- **説明**: `sonic-yang-mgmt` が提供する Python ライブラリ。CONFIG_DB の内容が YANG スキーマに合致するか検証する。

## Z

### zebra {#term-zebra}

- **略称**: zebra
- **日本語訳**: zebra
- **説明**: FRR の中核 RIB / ルート再配布デーモン。SONiC では FPM 経由で `fpmsyncd` にルートを渡す。

### ZTP {#term-ztp}

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

## 用語別 逆引き索引

<!-- glossary-xref -->

本ページの各用語が、ドキュメント内のどのページで言及されているかをまとめた逆引き索引です（言及回数の多い順に最大 5 ページ）。`gen_glossary_xref.py` により自動生成されます。

### [APPL_DB](#term-appl_db)

- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (25)
- [swss-schema（APPL_DB / STATE_DB の中心スキーマ参照）](../internals/swss-schema.md) (18)
- [概要](../topics/20-swss-sai-redis/concept.md) (15)
- [内部実装](../topics/06-l2-vlan-lag/internals.md) (14)
- [ポート Auto-Negotiation（advertised-speeds / interface-type）](../architecture/sonic-port-auto-negotiation-design.md) (12)

### [ARP](#term-arp)

- [L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd / show arp）](../internals/l3-scaling-and-performance-enhancements.md) (35)
- [Active-Standby Dual ToR（y-cable + linkmgrd state machine + IPinIP tunnel）](../overlay/active-standby-dual-tor.md) (13)
- [ICCPd 内部構成（MC-LAG / MLACP FSM ファイル別マップ）](../switching/brief-introduction-of-iccp-code.md) (11)
- [VNET の Local Endpoint Forwarding（DPU 直結 nexthop の最適化）](../overlay/vnet-local-endpoint-forwarding.md) (9)
- [ARP / Neighbor エントリが古い IP-MAC を保持し続ける](runbooks/arp-entry-stuck.md) (7)

### [ASIC_DB](#term-asic_db)

- [VRF VS テストプラン（vrfmgrd / intfmgrd / Orchagent → APP_DB / ASIC_DB / kernel）](../routing/vrf-vs-test-plan.md) (13)
- [アーキテクチャ](../topics/20-swss-sai-redis/architecture.md) (11)
- [概念と読み始め方](../topics/01-overview/concept.md) (9)
- [内部実装](../topics/01-overview/internals.md) (9)
- [概要](../topics/20-swss-sai-redis/concept.md) (9)

### [AsterNOS](#term-asternos)

- [このドキュメントについて](../about.md) (1)
- [SAG（Static Anycast Gateway）for SONiC](../architecture/sag-high-level-design-for-sonic.md) (1)

### [BFD](#term-bfd)

- [BGP セッション向け BFD ハードウェアオフロード（bfdsyncd 経路）](../routing/bfd-hw-offload-for-bgp-session.md) (72)
- [BFD ハードウェアオフロード（BfdOrch / BFD_SESSION）](../routing/bfd-hw-offload.md) (63)
- [頻出 SAI 属性早見表](sai-attributes.md) (20)
- [Overlay ECMP with BFD monitoring（VxLAN VNet ルートと BFD 連動）](../routing/overlay-ecmp-with-bfd-monitoring.md) (18)
- [Overlay ECMP の Primary/Secondary・カスタム監視・BFD タイマ拡張](../routing/overlay-ecmp-enhancements.md) (17)

### [BGP](#term-bgp)

- [sonic-bgp-neighbor YANG](yang/sonic-bgp-neighbor.md) (240)
- [sonic-bgp-peergroup YANG](yang/sonic-bgp-peergroup.md) (228)
- [sonic-bgp-global YANG](yang/sonic-bgp-global.md) (208)
- [VoQ シャーシでの BGP 構成（iBGP フルメッシュ + addpath / multipath-relax）](../routing/bgp-setup-for-voq-chassis.md) (58)
- [内部実装](../topics/02-bgp/internals.md) (58)

### [bgpcfgd](#term-bgpcfgd)

- [Reliable TSA（VoQ Chassis 全体での TSA を CHASSIS_APP_DB で同期）](../routing/reliable-tsa.md) (16)
- [内部実装](../topics/02-bgp/internals.md) (16)
- [FRR-BGP Unified Mgmt Framework（frrcfgd / OpenConfig BGP）](../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md) (13)
- [bgpcfgd の dynamic BGP peer 動的変更（update.conf.j2 / delete.conf.j2）](../routing/bgpcfgd-dynamic-peer-modification-support.md) (12)
- [概要](../topics/02-bgp/concept.md) (11)

### [CONFIG_DB](#term-config_db)

- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (22)
- [multi-ASIC 用 Golden Config 単一 JSON フォーマット（localhost / asic0 / asic1 ...）](../platform/db-design-for-multi-asic-scenarios.md) (20)
- [リファレンス](index.md) (20)
- [ログレベルの永続化（LOGLEVEL_DB → CONFIG_DB.LOGGER への移行）](../system/persistent-log-level-hld.md) (19)
- [設定](../topics/02-bgp/setup.md) (19)

### [config_db.json](#term-config_db.json)

- [multi-ASIC 用 Golden Config 単一 JSON フォーマット（localhost / asic0 / asic1 ...）](../platform/db-design-for-multi-asic-scenarios.md) (11)
- [gNOI File.Remove と FactoryReset.Start（gNMI/UMF + DBUS host service）](../management/gnoi-hld-for-file-and-factory-reset-apis.md) (10)
- [CONFIG_DB の永続化が失敗する](runbooks/config-db-persistence-failure.md) (9)
- [minigraph 適用後に reload が完了しない / 起動が固まる](runbooks/minigraph-reload-stuck.md) (8)
- [config reload が完了しない / hang する](runbooks/config-reload-stuck.md) (7)

### [config-setup](#term-config-setup)

- [config-setup サービス（first-boot config 生成 / 版間 migration）](../system/sonic-configuration-setup-service.md) (32)
- [reset-factory（keep-basic / keep-all-config / only-config）](../architecture/reset-factory-design.md) (24)
- [内部実装](../topics/01-overview/internals.md) (5)
- [Smart Switch DPU IP アドレス割当（midplane bridge / DHCP server）](../system/smart-switch-ip-address-assignment.md) (2)
- [内部実装](../topics/11-reboot/internals.md) (2)

### [COUNTERS_DB](#term-counters_db)

- [バイト/パケットレートとポート使用率（RATES テーブル + EMA）](../internals/byte-packet-rates-port-utilization-in-sonic.md) (9)
- [DHCP Relay per-interface counter（dhcpmon マルチスレッド + COUNTERS_DB 永続化）](../routing/dhcp-relay-per-interface-counter.md) (9)
- [flexcounter の queue/PG map 生成と watermark 有効化の整合](../acl-qos/align-watermark-flow-with-port-configuration-hld.md) (7)
- [ポート不正パケットドロップ設計（Interface MIB / L3 カウンタ拡張）](../architecture/port-illegal-packets-drop-design.md) (7)
- [概念](../topics/09-telemetry-snmp/concept.md) (7)

### [CoPP](#term-copp)

- [概念](../topics/07-acl-copp-mirror/concept.md) (21)
- [DHCP DoS 緩和（ポート単位 DHCP レート制限・Linux TC ベース）](../acl-qos/dhcp-dos-mitigation-in-sonic.md) (15)
- [発展トピック](../topics/07-acl-copp-mirror/advanced.md) (13)
- [L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd / show arp）](../internals/l3-scaling-and-performance-enhancements.md) (12)
- [運用](../topics/18-p4-pins/operations.md) (10)

### [CRM](#term-crm)

- [Generic SAI Extension テーブルの CRM（CRM_EXT_TABLE）](../system/generic-sai-extension-critical-resource-monitoring-crm.md) (38)
- [クリティカルリソースモニタリング (CRM) 要件](../system/critical-resource-monitoring.md) (19)
- [アーキテクチャ](../topics/09-telemetry-snmp/architecture.md) (17)
- [概念](../topics/09-telemetry-snmp/concept.md) (14)
- [sonic-crm YANG](yang/sonic-crm.md) (11)

### [DASH](#term-dash)

- [SmartSwitch HA: HAMgrD（NPU 側 actor 分割と DPU 連携）](../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md) (69)
- [SONiC-DASH（Disaggregated APIs for SONiC Hosts）アーキテクチャ概観](../overlay/sonic-dash-hld.md) (49)
- [NPU-DPU DB と ENI ベース転送の内部構造](../topics/13-dash-smartswitch/internals.md) (46)
- [DPU の IP 割当・gNMI 連携・KVM 検証](../topics/13-dash-smartswitch/setup.md) (43)
- [DASH と SmartSwitch の考え方](../topics/13-dash-smartswitch/concept.md) (38)

### [DHCP Relay](#term-dhcp-relay)

- [変更履歴](../_meta/changelog.md) (2)
- [DHCP Relay per-interface counter（dhcpmon マルチスレッド + COUNTERS_DB 永続化）](../routing/dhcp-relay-per-interface-counter.md) (2)
- [DHCP DoS 緩和（ポート単位 DHCP レート制限・Linux TC ベース）](../acl-qos/dhcp-dos-mitigation-in-sonic.md) (1)
- [ターミナルサーバの ttyUSB 安定 symlink を作る udev rules 設計](../architecture/1-udev-rules-design-for-terminal-server.md) (1)
- [DHCPv4 Relay Agent（dhcpmon / dhcrelay / option-82 / circuit-id）](../architecture/dhcpv4-relay-agent.md) (1)

### [DPU](#term-dpu)

- [HA / PMON / reboot / upgrade の運用](../topics/13-dash-smartswitch/operations.md) (107)
- [SmartSwitch HA: HAMgrD（NPU 側 actor 分割と DPU 連携）](../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md) (82)
- [DASH と SmartSwitch の考え方](../topics/13-dash-smartswitch/concept.md) (69)
- [SmartSwitch HA - DPU-Scope-DPU-Driven 構成](../architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md) (67)
- [DPU の IP 割当・gNMI 連携・KVM 検証](../topics/13-dash-smartswitch/setup.md) (66)

### [ECMP](#term-ecmp)

- [ECMP Family](../topics/04-vrf-ecmp/ecmp.md) (28)
- [Fine Grained ECMP（FG_NHG / fgnhgorch）](../routing/sonic-fine-grained-ecmp.md) (25)
- [L3 基盤と VRF](../topics/04-vrf-ecmp/concept.md) (23)
- [VoQ シャーシでの BGP 構成（iBGP フルメッシュ + addpath / multipath-relax）](../routing/bgp-setup-for-voq-chassis.md) (16)
- [Ordered ECMP（IP ソート順で nexthop に sequence_id を付け同一フローを同 ToR/Appliance に固定）](../routing/high-level-design-document.md) (16)

### [ENI](#term-eni)

- [SmartSwitch ENI Based Forwarding（DashEniFwdOrch / ENI_REDIRECT ACL）](../overlay/smartswitch-eni-based-forwarding.md) (37)
- [DASH と SmartSwitch の考え方](../topics/13-dash-smartswitch/concept.md) (35)
- [NPU-DPU DB と ENI ベース転送の内部構造](../topics/13-dash-smartswitch/internals.md) (28)
- [SONiC-DASH（Disaggregated APIs for SONiC Hosts）アーキテクチャ概観](../overlay/sonic-dash-hld.md) (21)
- [sonic-passwh YANG](yang/sonic-passw-hardening.md) (13)

### [EVPN](#term-evpn)

- [EVPN VXLAN（FRR BGP-EVPN / VTEP / VRF / Type-2/Type-5）](../routing/evpn-vxlan-hld.md) (52)
- [VXLAN / VNET / EVPN の概要](../topics/03-vxlan-evpn/concept.md) (45)
- [EVPN VXLAN Multihoming（ESI / DF election / split-horizon）](../routing/evpn-vxlan-multihoming.md) (33)
- [Overlay 設定](../topics/03-vxlan-evpn/setup.md) (20)
- [Overlay 運用](../topics/03-vxlan-evpn/operations.md) (19)

### [FDB](#term-fdb)

- [内部実装](../topics/06-l2-vlan-lag/internals.md) (37)
- [L2 Forwarding 強化（FDB flush / aging / static MAC / VLAN range）](../switching/layer-2-forwarding-enhancements.md) (24)
- [L2 運用確認](../topics/06-l2-vlan-lag/operations.md) (20)
- [頻出 SAI 属性早見表](sai-attributes.md) (14)
- [L2 のアーキテクチャ](../topics/06-l2-vlan-lag/architecture.md) (11)

### [fdbsyncd](#term-fdbsyncd)

- [内部実装](../topics/06-l2-vlan-lag/internals.md) (4)
- [ログレベルの永続化（LOGLEVEL_DB → CONFIG_DB.LOGGER への移行）](../system/persistent-log-level-hld.md) (2)
- [L2 運用確認](../topics/06-l2-vlan-lag/operations.md) (2)
- [内部実装](../topics/20-swss-sai-redis/internals.md) (2)
- [EVPN VXLAN Multihoming（ESI / DF election / split-horizon）](../routing/evpn-vxlan-multihoming.md) (1)

### [FlexCounter](#term-flexcounter)

- [flexcounter の queue/PG map 生成と watermark 有効化の整合](../acl-qos/align-watermark-flow-with-port-configuration-hld.md) (19)
- [FlexCounter リファクタ（CounterContext テンプレート化）](../internals/sonic-flexcounter-refactor.md) (18)
- [sai_query_stats_capability による Counter Capability 一括取得](../platform/query-stats-capability-new-sai-api-indroduction.md) (8)
- [内部実装](../topics/09-telemetry-snmp/internals.md) (8)
- [Bulk Counter（sai_bulk_object_get_stats / chunk size）](../architecture/sonic-bulk-counter-design.md) (7)

### [FPM](#term-fpm)

- [概要](../topics/02-bgp/concept.md) (16)
- [fpmsyncd NextHop Group 拡張（dplane_fpm_nl / NEXTHOP_GROUP_TABLE）](../routing/fpmsyncd-nexthop-group-enhancement-high-level-design-document.md) (8)
- [内部実装](../topics/02-bgp/internals.md) (8)
- [概念](../topics/17-srv6-mpls/concept.md) (8)
- [RIB-FIB と Route Object 生成](../topics/04-vrf-ecmp/architecture.md) (7)

### [fpmsyncd](#term-fpmsyncd)

- [BGP PIC（Prefix Independent Convergence / NHG 階層）](../routing/bgp-prefix-independent-convergence-architecture-document.md) (13)
- [fpmsyncd NextHop Group 拡張（dplane_fpm_nl / NEXTHOP_GROUP_TABLE）](../routing/fpmsyncd-nexthop-group-enhancement-high-level-design-document.md) (13)
- [BGP Route Install Error Handling（ERROR_ROUTE_TABLE / FIB-install pending）](../routing/bgp-route-install-error-handling.md) (12)
- [新 FRR-SONiC 通信チャネル（dplane_fpm_sonic モジュール）](../routing/new-frr-sonic-communication-channel.md) (12)
- [内部実装](../topics/02-bgp/internals.md) (11)

### [FRR](#term-frr)

- [概要](../topics/02-bgp/concept.md) (51)
- [SRv6 Static SID/Locator 設定（CONFIG_DB → bgpcfgd → FRR）](../routing/static-configuration-of-srv6-in-sonic-hld.md) (20)
- [FRR-BGP Unified Mgmt Framework（frrcfgd / OpenConfig BGP）](../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md) (19)
- [概念](../topics/17-srv6-mpls/concept.md) (17)
- [BGP Suppress FIB Pending（dplane_fpm_nl + RTM_F_OFFLOAD）](../routing/bgp-suppress-announcements-of-routes-not-installed-in-hw.md) (16)

### [gNMI](#term-gnmi)

- [gNMI / gNOI / OpenConfig 関連](../categories/gnmi-openconfig.md) (28)
- [概要](../topics/10-gnmi-openconfig/concept.md) (23)
- [DPU の IP 割当・gNMI 連携・KVM 検証](../topics/13-dash-smartswitch/setup.md) (23)
- [gNSI（Certz / Authz / Pathz / Credentialz）の Rotate モデル](../management/gnsi-hld.md) (18)
- [内部実装](../topics/10-gnmi-openconfig/internals.md) (17)

### [GCU](#term-gcu)

- [YANG モデルによる ConfigDB 更新検証（GCU + ConfigDBConnector デコレータ）](../management/sonic-config-update-validation-via-yang.md) (19)
- [Generic Config Update / Rollback（GCU・JSON Patch・checkpoint）](../architecture/sonic-generic-configuration-update-and-rollback.md) (6)
- [概念と読み始め方](../topics/01-overview/concept.md) (5)
- [gNMI / gNOI / OpenConfig 関連](../categories/gnmi-openconfig.md) (4)
- [SONiC gNMI Server インタフェース設計（CONFIG_DB / SONiC YANG / Generic Config Updater 連携）](../management/sonic-gnmi-server-interface-design.md) (4)

### [HLD](#term-hld)

- [HLD と実装の乖離 一覧（discrepancy-index）](verification/discrepancy-index.md) (53)
- [BGP セッション向け BFD ハードウェアオフロード（bfdsyncd 経路）](../routing/bfd-hw-offload-for-bgp-session.md) (28)
- [gNMI Master Arbitration（election ID と SetRequest 拡張）](../management/gnmi-master-arbitration-hld.md) (27)
- [DIP=SIP PTF 検証テスト](../architecture/dip-sip-ptf-validation-high-level-design.md) (25)
- [SSD ヘルスチェック（show platform ssdhealth + ssdutil プラグイン）](../architecture/ssdhealth-design.md) (25)

### [hostcfgd](#term-hostcfgd)

- [TACACS+ passkey 暗号化（key_encrypt + master key /etc/cipher_pass）](../management/tacacs-passkey-encryption.md) (28)
- [FEATURE テーブルによるオプショナル機能の有効/無効制御](../system/sonic-optional-feature-control-enhancement.md) (16)
- [config reload の event-driven 化（FEATURE.delayed + PortInitDone）](../management/config-reload-enhancement.md) (14)
- [運用入口](../topics/01-overview/operations.md) (9)
- [パスワード強化（password hardening / aging / complexity / history）](../architecture/pw-hardening-design.md) (8)

### [intfmgrd](#term-intfmgrd)

- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (8)
- [IP / LAG / MTU の Incremental Update（portmgrd / intfmgrd / teammgrd 分担）](../switching/sonic-ip-lag-incremental-update.md) (5)
- [VRF VS テストプラン（vrfmgrd / intfmgrd / Orchagent → APP_DB / ASIC_DB / kernel）](../routing/vrf-vs-test-plan.md) (4)
- [IP インタフェース ループバックアクション（同一 RIF 出戻りの drop/forward）](../architecture/sonic-ip-interface-loopback-action.md) (3)
- [LOOPBACK_INTERFACE テーブル](config-db/loopback-interface.md) (3)

### [intfsyncd](#term-intfsyncd)

- [VOQ_INBAND_INTERFACE テーブル](config-db/voq-inband-interface.md) (1)
- [SWSS docker warm restart（state restore / consistency / sync up）](../system/sonic-swss-docker-warm-restart.md) (1)

### [LACP](#term-lacp)

- [ICCPd 内部構成（MC-LAG / MLACP FSM ファイル別マップ）](../switching/brief-introduction-of-iccp-code.md) (19)
- [Warm-reboot 中の LACP retry count 拡張（LACP version 0xf1 / 新規 TLV）](../switching/increasing-lacp-pdu-timeout-during-warm-reboot.md) (10)
- [PortChannel メンバーで LACP が確立しない](runbooks/portchannel-lacp-not-established.md) (9)
- [Reboot 運用と障害調査](../topics/11-reboot/operations.md) (9)
- [config portchannel サブコマンド](cli/config-portchannel.md) (7)

### [LAG](#term-lag)

- [分散 VOQ シャシでの LAG（SYSTEM_LAG_TABLE と system_lag_id）](../switching/lag-on-distributed-voq-system.md) (63)
- [sonic-mclag YANG](yang/sonic-mclag.md) (60)
- [内部実装](../topics/06-l2-vlan-lag/internals.md) (50)
- [MCLAG Enhancements（dynamic config / unique IP / isolation group / static MAC）](../switching/mclag-enhancements.md) (33)
- [ポート / LAG の TPID 設定（0x8100/0x9100/0x9200/0x88A8）](../platform/sonictpidsettinghld1.md) (29)

### [linkmgrd](#term-linkmgrd)

- [linkmgrd のデフォルトルート連動（DualToR mux 制御）](../routing/default-route.md) (20)
- [Mux 制御の内部構造](../topics/05-dual-tor/internals.md) (18)
- [Active-Standby Dual ToR（y-cable + linkmgrd state machine + IPinIP tunnel）](../overlay/active-standby-dual-tor.md) (17)
- [Dual-ToR の運用](../topics/05-dual-tor/operations.md) (16)
- [Active-Active Dual ToR（gRPC ベース cable control + prefix-based neighbor）](../overlay/active-active-dual-tor.md) (13)

### [LLDP](#term-lldp)

- [sonic-lldp YANG](yang/sonic-lldp.md) (27)
- [LLDP / LLDP_PORT テーブル](config-db/lldp.md) (18)
- [LLDP_PORT テーブル](config-db/lldp-port.md) (10)
- [show lldp サブコマンド](cli/show-lldp.md) (6)
- [LLDP 隣接が頻繁に up/down する](runbooks/lldp-neighbor-flapping.md) (6)

### [MCLAG](#term-mclag)

- [sonic-mclag YANG](yang/sonic-mclag.md) (60)
- [MCLAG Enhancements（dynamic config / unique IP / isolation group / static MAC）](../switching/mclag-enhancements.md) (27)
- [config mclag サブコマンド](cli/config-mclag.md) (26)
- [MCLAG_DOMAIN / MCLAG_INTERFACE / MCLAG_UNIQUE_IP テーブル](config-db/mclag-domain.md) (18)
- [show mclag (mclagdctl) コマンド](cli/show-mclag.md) (11)

### [minigraph.xml](#term-minigraph.xml)

- [CONFIG_DB save / load が反映されない](runbooks/config-save-load.md) (5)
- [minigraph 適用後に reload が完了しない / 起動が固まる](runbooks/minigraph-reload-stuck.md) (5)
- [SYSTEM_DEFAULTS テーブルによる SONiC 既定値の集約](../switching/control-sonic-behaviors-with-system-defaults-table.md) (5)
- [SONiC User Manual の位置づけと SONiC CLI / 運用フローの全体像](../management/sonic-user-manual.md) (3)
- [sonic-cfggen コマンド](cli/sonic-cfggen.md) (2)

### [MUX](#term-mux)

- [Active-Standby Dual ToR（y-cable + linkmgrd state machine + IPinIP tunnel）](../overlay/active-standby-dual-tor.md) (43)
- [sonic-mux-cable YANG](yang/sonic-mux-cable.md) (30)
- [Dual-ToR の設定](../topics/05-dual-tor/setup.md) (20)
- [MUX_LINKMGR テーブル](config-db/mux-linkmgr.md) (17)
- [show muxcable サブコマンド](cli/show-muxcable.md) (14)

### [NAT](#term-nat)

- [sonic-nat YANG](yang/sonic-nat.md) (81)
- [内部実装](../topics/16-nat-dhcp-dns/internals.md) (58)
- [NAT in SONiC（natsyncd / NatOrch / iptables ↔ SAI）](../architecture/nat-in-sonic.md) (44)
- [NAT_GLOBAL / NAT_POOL テーブル](config-db/nat.md) (44)
- [config nat サブコマンド](cli/config-nat.md) (33)

### [natmgrd / natsyncd](#term-natmgrd-natsyncd)

- [運用](../topics/16-nat-dhcp-dns/operations.md) (2)
- [NAT in SONiC（natsyncd / NatOrch / iptables ↔ SAI）](../architecture/nat-in-sonic.md) (1)

### [neighsyncd](#term-neighsyncd)

- [WARM_RESTART テーブル](config-db/warm-restart.md) (7)
- [Reboot / warm restart の設定](../topics/11-reboot/setup.md) (6)
- [config warm_restart サブコマンド](cli/config-warm_restart.md) (4)
- [ARP / Neighbor エントリが古い IP-MAC を保持し続ける](runbooks/arp-entry-stuck.md) (4)
- [sonic-warm-restart YANG](yang/sonic-warm-restart.md) (4)

### [Netlink](#term-netlink)

- [新 FRR-SONiC 通信チャネル（dplane_fpm_sonic モジュール）](../routing/new-frr-sonic-communication-channel.md) (5)
- [BGP / EVPN 関連](../categories/bgp-evpn.md) (1)
- [アーキテクチャ](../topics/02-bgp/architecture.md) (1)

### [NPU](#term-npu)

- [SmartSwitch reboot 順序（NPU → 各 DPU の gNOI HALT → PCI detach → 個別 reboot）](../system/smart-switch-reboot-high-level-design.md) (43)
- [DASH と SmartSwitch の考え方](../topics/13-dash-smartswitch/concept.md) (38)
- [DPU の IP 割当・gNMI 連携・KVM 検証](../topics/13-dash-smartswitch/setup.md) (24)
- [NPU-DPU DB と ENI ベース転送の内部構造](../topics/13-dash-smartswitch/internals.md) (22)
- [VoQ SONiC（distributed VoQ chassis / system-port / fabric）](../platform/voq-sonic.md) (20)

### [orchagent](#term-orchagent)

- [SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB）](../platform/hld-for-handling-sai-failures.md) (23)
- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (17)
- [運用](../topics/20-swss-sai-redis/operations.md) (17)
- [ポートの動的 add / del（zero-port 起動と post-init 操作）](../acl-qos/enhancements-to-add-or-del-ports-dynamically.md) (15)
- [SWSS docker の Warm Restart 実装メモ（開発時リファレンス）](../system/swss-docker-warm-restart-code-reference.md) (13)

### [PFC](#term-pfc)

- [PFC 履歴統計（PFCWD lua スクリプトによる estimate と --history CLI）](../acl-qos/pfc-historical-statistics.md) (33)
- [QoS / Buffer の運用](../topics/08-qos-buffer/operations.md) (31)
- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (26)
- [Asymmetric PFC テストプラン（PTF + sonic-mgmt fixtures）](../acl-qos/asymmetric-pfc-test-plan.md) (25)
- [sonic-pfcwd YANG](yang/sonic-pfcwd.md) (23)

### [PFC Watchdog](#term-pfc-watchdog)

- [sonic-pfcwd YANG](yang/sonic-pfcwd.md) (2)
- [Bulk Counter（sai_bulk_object_get_stats / chunk size）](../architecture/sonic-bulk-counter-design.md) (1)
- [PFC_WD テーブル](config-db/pfc-wd.md) (1)
- [PFC で帯域が出ない / Buffer overflow](runbooks/pfc-bandwidth.md) (1)
- [sonic-flex_counter YANG](yang/sonic-flex_counter.md) (1)

### [portmgrd](#term-portmgrd)

- [DHCP DoS 緩和（ポート単位 DHCP レート制限・Linux TC ベース）](../acl-qos/dhcp-dos-mitigation-in-sonic.md) (11)
- [IP / LAG / MTU の Incremental Update（portmgrd / intfmgrd / teammgrd 分担）](../switching/sonic-ip-lag-incremental-update.md) (7)
- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (4)
- [ポートの動的 add / del（zero-port 起動と post-init 操作）](../acl-qos/enhancements-to-add-or-del-ports-dynamically.md) (3)
- [ポート Auto-Negotiation（advertised-speeds / interface-type）](../architecture/sonic-port-auto-negotiation-design.md) (3)

### [portsyncd](#term-portsyncd)

- [ポートの動的 add / del（zero-port 起動と post-init 操作）](../acl-qos/enhancements-to-add-or-del-ports-dynamically.md) (15)
- [config reload の event-driven 化（FEATURE.delayed + PortInitDone）](../management/config-reload-enhancement.md) (8)
- [内部実装](../topics/06-l2-vlan-lag/internals.md) (6)
- [VOQ シャシでの recirculation port サポート（Inb / Rec ポートロール）](../platform/recirculation-port-support-on-voq-chassis.md) (5)
- [概要](../topics/14-platform-port-optics/concept.md) (3)

### [PortChannel](#term-portchannel)

- [L2 設定パターン](../topics/06-l2-vlan-lag/setup.md) (32)
- [L2 運用確認](../topics/06-l2-vlan-lag/operations.md) (21)
- [PortChannel (LAG) の OpenConfig YANG サポート（REST / gNMI）](../switching/openconfig-support-for-portchannel-aggregate-interface.md) (19)
- [sonic-portchannel YANG](yang/sonic-portchannel.md) (15)
- [Switchport モード（access / trunk / routed）と VLAN CLI 拡張](../switching/switch-port-modes-and-vlan-cli-enhancement.md) (14)

### [QoS](#term-qos)

- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (14)
- [config qos サブコマンド](cli/config-qos.md) (9)
- [MPLS TC → TC map（MPLS パケットの QoS classification）](../routing/mpls-tc-to-tc-map.md) (8)
- [QoS Scheduler / Shaper（SP / WRR / DWRR + min/max bandwidth）](../acl-qos/sonic-qos-scheduler-and-shaping.md) (7)
- [Dual-ToR の発展トピック](../topics/05-dual-tor/advanced.md) (7)

### [Redis](#term-redis)

- [Redis Client Manager（RCM: connection pool / transactional client）](../management/redis-client-manager-rcm-hld.md) (34)
- [VOQ カウンタ集約（chassis supervisor からの aggregate 表示）](../internals/aggregate-voq-counters-in-sonic.md) (19)
- [設定](../topics/20-swss-sai-redis/setup.md) (19)
- [ZMQ ProducerStateTable / ConsumerStateTable 設計](../internals/zmq-producer-consumer-state-table-design.md) (15)
- [内部実装](../topics/09-telemetry-snmp/internals.md) (15)

### [RIF](#term-rif)

- [ルータインタフェース (RIF) カウンタ](../routing/router-interface-counters-in-sonic.md) (40)
- [バイト/パケットレートとポート使用率（RATES テーブル + EMA）](../internals/byte-packet-rates-port-utilization-in-sonic.md) (33)
- [ポート不正パケットドロップ設計（Interface MIB / L3 カウンタ拡張）](../architecture/port-illegal-packets-drop-design.md) (24)
- [Route / Interface / Counter の確認](../topics/04-vrf-ecmp/operations.md) (20)
- [DIP=SIP PTF 検証テスト](../architecture/dip-sip-ptf-validation-high-level-design.md) (17)

### [ROUTE_TABLE](#term-route_table)

- [BGP Route Install Error Handling（ERROR_ROUTE_TABLE / FIB-install pending）](../routing/bgp-route-install-error-handling.md) (18)
- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../architecture/error-handling-framework-in-sonic.md) (12)
- [内部実装](../topics/04-vrf-ecmp/internals.md) (10)
- [内部実装](../topics/02-bgp/internals.md) (8)
- [内部実装](../topics/17-srv6-mpls/internals.md) (8)

### [SAI](#term-sai)

- [頻出 SAI 属性早見表](sai-attributes.md) (241)
- [SAI API バージョン整合チェック（sai_query_api_version + ビルド時検査）](../platform/sai-api-version-check.md) (55)
- [QoS / Buffer の内部実装](../topics/08-qos-buffer/internals.md) (42)
- [内部実装](../topics/20-swss-sai-redis/internals.md) (39)
- [内部実装](../topics/06-l2-vlan-lag/internals.md) (38)

### [sonic-buildimage](#term-sonic-buildimage)

- [SONiC YANG モデル記述ガイドライン（ABNF.json → sonic-*.yang）](../management/sonic-yang-model-guidelines.md) (15)
- [SONiC NTP client（chrony / NTP_SERVER / mgmt VRF）](../system/sonic-network-time-protocol-ntp-client-configuration.md) (13)
- [SONiC ポート命名規則の変更案（et[sX]pY[abcd]）](../platform/sonic-port-naming-convention-change.md) (11)
- [SONiC Secure Boot（shim/grub/vmlinuz/KO の chain of trust）](../system/hld-secure-boot.md) (11)
- [ビルドプロファイル（rules/profiles/*.mk）](../architecture/build-profiles.md) (10)

### [sonic-cfggen](#term-sonic-cfggen)

- [sonic-cfggen コマンド](cli/sonic-cfggen.md) (12)
- [show runningconfiguration / startupconfiguration サブコマンド](cli/show-running-config.md) (7)
- [設定変更の選び方](../topics/01-overview/configuration.md) (6)
- [CONFIG_DB save / load が反映されない](runbooks/config-save-load.md) (5)
- [SYSTEM_DEFAULTS テーブルによる SONiC 既定値の集約](../switching/control-sonic-behaviors-with-system-defaults-table.md) (5)

### [sonic-mgmt](#term-sonic-mgmt)

- [DIP=SIP PTF 検証テスト](../architecture/dip-sip-ptf-validation-high-level-design.md) (15)
- [sonic-mgmt_interface YANG](yang/sonic-mgmt_interface.md) (15)
- [sonic-mgmt_port YANG](yang/sonic-mgmt_port.md) (14)
- [Asymmetric PFC テストプラン（PTF + sonic-mgmt fixtures）](../acl-qos/asymmetric-pfc-test-plan.md) (9)
- [OpenConfig Interfaces YANG（Ethernet 設定の REST/gNMI 対応と sonic-mgmt-common transformer）](../management/openconfig-support-for-ethernet-interfaces.md) (9)

### [sonic-swss](#term-sonic-swss)

- [ポートの動的 add / del（zero-port 起動と post-init 操作）](../acl-qos/enhancements-to-add-or-del-ports-dynamically.md) (18)
- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../architecture/error-handling-framework-in-sonic.md) (17)
- [SmartSwitch HA: HAMgrD（NPU 側 actor 分割と DPU 連携）](../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md) (17)
- [Debug Framework（コンポーネント dump 登録 / assert 拡張）](../architecture/debug-framework-in-sonic.md) (11)
- [SAG（Static Anycast Gateway）for SONiC](../architecture/sag-high-level-design-for-sonic.md) (11)

### [sonic-swss-common](#term-sonic-swss-common)

- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../architecture/error-handling-framework-in-sonic.md) (9)
- [SWSS docker の Warm Restart 実装メモ（開発時リファレンス）](../system/swss-docker-warm-restart-code-reference.md) (8)
- [Debug Framework（コンポーネント dump 登録 / assert 拡張）](../architecture/debug-framework-in-sonic.md) (7)
- [SmartSwitch HA: HAMgrD（NPU 側 actor 分割と DPU 連携）](../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md) (7)
- [VOQ カウンタ集約（chassis supervisor からの aggregate 表示）](../internals/aggregate-voq-counters-in-sonic.md) (4)

### [sonic-sairedis](#term-sonic-sairedis)

- [SAI API バージョン整合チェック（sai_query_api_version + ビルド時検査）](../platform/sai-api-version-check.md) (12)
- [NPU MDIO アクセスと gbsyncd 単一 docker 化](../platform/sonic-npu-mdio-access-support-and-gbsyncd-docker-enhancement-hld.md) (8)
- [Bulk Counter（sai_bulk_object_get_stats / chunk size）](../architecture/sonic-bulk-counter-design.md) (7)
- [libsairedis API idempotence（warm restart 用 OID キャッシュと duplicate 抑止）](../system/sonic-libsairedis-api-idempotence-support.md) (7)
- [Warm Reboot 開発フェーズと OID 復元戦略（idempotent libsairedis vs syncd view comparison）](../system/what-are-the-development-phases-and-scope-for-warm-reboot.md) (4)

### [sonic-utilities](#term-sonic-utilities)

- [FEC FLR（Frame Loss Ratio）算出と予測（port_flr.lua / counterpoll port flr-interval-factor）](../platform/fec-flr-support-in-sonic.md) (11)
- [TACACS+ passkey 暗号化（key_encrypt + master key /etc/cipher_pass）](../management/tacacs-passkey-encryption.md) (10)
- [SONiC CLI 自動生成ツール（YANG → click plugin 自動生成）](../management/sonic-cli-auto-generation-tool.md) (9)
- [SAG（Static Anycast Gateway）for SONiC](../architecture/sag-high-level-design-for-sonic.md) (8)
- [Switchport モード（access / trunk / routed）と VLAN CLI 拡張](../switching/switch-port-modes-and-vlan-cli-enhancement.md) (8)

### [SmartSwitch](#term-smartswitch)

- [DASH と SmartSwitch の考え方](../topics/13-dash-smartswitch/concept.md) (22)
- [SmartSwitch 関連](../categories/smartswitch.md) (16)
- [HA / PMON / reboot / upgrade の運用](../topics/13-dash-smartswitch/operations.md) (13)
- [SmartSwitch reboot 順序（NPU → 各 DPU の gNOI HALT → PCI detach → 個別 reboot）](../system/smart-switch-reboot-high-level-design.md) (11)
- [DPU の IP 割当・gNMI 連携・KVM 検証](../topics/13-dash-smartswitch/setup.md) (11)

### [STATE_DB](#term-state_db)

- [SmartSwitch gNMI フィードバック（DPU APPL_STATE_DB と version_id）](../management/smart-switch-gnmi-feedback-design-omit-in-toc.md) (20)
- [FIPS 向け MACsec SAI POST（FIPS_MACSEC_POST_TABLE）](../switching/sonic-sai-post-support-for-macsec.md) (17)
- [液冷漏洩検出（LiquidCoolingBase + thermalctld + system-health gNMI イベント）](../platform/liquid-cooling-leakage-detection-in-sonic.md) (16)
- [pmon 強化（PSU/FAN/syseeprom 周辺データ STATE_DB 集約）](../system/platform-monitor-enhancement-design.md) (15)
- [Active-Standby Dual ToR（y-cable + linkmgrd state machine + IPinIP tunnel）](../overlay/active-standby-dual-tor.md) (14)

### [swssconfig](#term-swssconfig)

- [ACL の基本設計（ACL_TABLE / ACL_RULE スキーマ）](../acl-qos/acl-support-in-sonic.md) (9)
- [VLAN Subnet Decap（Netscan 用 IPinIP MP2MP デカプスル）](../platform/subnet-decapsulation-with-sonic.md) (6)
- [DPU の IP 割当・gNMI 連携・KVM 検証](../topics/13-dash-smartswitch/setup.md) (5)
- [ACL in SONiC（テーブル型 / マッチ・アクション / SWSS パイプライン）](../acl-qos/acl-in-sonic.md) (3)
- [SONiC ポート命名規則の変更案（et[sX]pY[abcd]）](../platform/sonic-port-naming-convention-change.md) (1)

### [syncd](#term-syncd)

- [NPU MDIO アクセスと gbsyncd 単一 docker 化](../platform/sonic-npu-mdio-access-support-and-gbsyncd-docker-enhancement-hld.md) (35)
- [運用](../topics/20-swss-sai-redis/operations.md) (30)
- [内部実装](../topics/20-swss-sai-redis/internals.md) (29)
- [SAI 失敗時の dump 取得（syncd_dump.sh / SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP）](../platform/dump-on-sai-failure.md) (25)
- [BGP セッション向け BFD ハードウェアオフロード（bfdsyncd 経路）](../routing/bfd-hw-offload-for-bgp-session.md) (23)

### [tunnelmgrd](#term-tunnelmgrd)

- [TUNNEL テーブル](config-db/tunnel.md) (3)
- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (2)
- [TUNNEL_DECAP_TABLE (APPL_DB)](config-db/tunnel-decap-table.md) (2)
- [PEER_SWITCH テーブル](config-db/peer-switch.md) (1)
- [sonic-tunnel YANG](yang/sonic-tunnel.md) (1)

### [VLAN](#term-vlan)

- [sonic-vlan YANG](yang/sonic-vlan.md) (111)
- [L2 設定パターン](../topics/06-l2-vlan-lag/setup.md) (55)
- [sonic-spanning-tree YANG](yang/sonic-spanning-tree.md) (54)
- [Switchport モード（access / trunk / routed）と VLAN CLI 拡張](../switching/switch-port-modes-and-vlan-cli-enhancement.md) (49)
- [config vlan サブコマンド](cli/config-vlan.md) (46)

### [vlanmgrd](#term-vlanmgrd)

- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (4)
- [VLAN_MEMBER テーブル](config-db/vlan-member.md) (3)
- [VLAN メンバーを追加してもタグが付かない](runbooks/vlan-tagging.md) (3)
- [内部実装](../topics/06-l2-vlan-lag/internals.md) (3)
- [VLAN テーブル](config-db/vlan.md) (2)

### [VNET](#term-vnet)

- [sonic-vnet YANG](yang/sonic-vnet.md) (85)
- [VXLAN / VNET / EVPN の概要](../topics/03-vxlan-evpn/concept.md) (47)
- [VNET / VNET_ROUTE テーブル](config-db/vnet.md) (40)
- [VXLAN / VNet 全体設計（VxlanOrch / VnetOrch / VRF mapper）](../overlay/vxlan-sonic.md) (26)
- [内部実装](../topics/03-vxlan-evpn/internals.md) (22)

### [VRF](#term-vrf)

- [L3 基盤と VRF](../topics/04-vrf-ecmp/concept.md) (86)
- [VRF Ansible テストプラン（T0 上で BGP/ACL/loopback/warm-reboot 含む E2E 検証）](../routing/vrf-feature-ansible-test-plan-omit-in-toc.md) (45)
- [config vrf サブコマンド](cli/config-vrf.md) (43)
- [VRF VS テストプラン（vrfmgrd / intfmgrd / Orchagent → APP_DB / ASIC_DB / kernel）](../routing/vrf-vs-test-plan.md) (41)
- [VRF サポート（vrfmgrd / vrforch / FRR vrf-aware）](../routing/sonic-vrf-support-design-spec-draft.md) (38)

### [vrfmgrd](#term-vrfmgrd)

- [VRF VS テストプラン（vrfmgrd / intfmgrd / Orchagent → APP_DB / ASIC_DB / kernel）](../routing/vrf-vs-test-plan.md) (9)
- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (5)
- [VRF サポート（vrfmgrd / vrforch / FRR vrf-aware）](../routing/sonic-vrf-support-design-spec-draft.md) (5)
- [VRF テーブル](config-db/vrf.md) (3)
- [ルーティング](../routing/index.md) (3)

### [VXLAN](#term-vxlan)

- [sonic-vxlan YANG](yang/sonic-vxlan.md) (56)
- [VXLAN / VNet 全体設計（VxlanOrch / VnetOrch / VRF mapper）](../overlay/vxlan-sonic.md) (52)
- [EVPN VXLAN（FRR BGP-EVPN / VTEP / VRF / Type-2/Type-5）](../routing/evpn-vxlan-hld.md) (41)
- [VXLAN / VNET / EVPN の概要](../topics/03-vxlan-evpn/concept.md) (33)
- [config vxlan サブコマンド](cli/config-vxlan.md) (26)

### [vxlanmgrd](#term-vxlanmgrd)

- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (5)
- [Overlay 運用](../topics/03-vxlan-evpn/operations.md) (3)
- [ログレベルの永続化（LOGLEVEL_DB → CONFIG_DB.LOGGER への移行）](../system/persistent-log-level-hld.md) (2)
- [VXLAN / VNET / EVPN の概要](../topics/03-vxlan-evpn/concept.md) (2)
- [VNET / VNET_ROUTE テーブル](config-db/vnet.md) (1)

### [WRED](#term-wred)

- [WRED / ECN 統計（per-queue / per-port、capability ベース）](../acl-qos/wred-and-ecn-statistics.md) (48)
- [sonic-wred-profile YANG](yang/sonic-wred-profile.md) (46)
- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (20)
- [QoS / Buffer の内部実装](../topics/08-qos-buffer/internals.md) (13)
- [sonic-queue YANG](yang/sonic-queue.md) (12)

### [YANG](#term-yang)

- [gNMI / gNOI / OpenConfig 関連](../categories/gnmi-openconfig.md) (52)
- [概要](../topics/10-gnmi-openconfig/concept.md) (35)
- [gNMI クライアントツールの使い方（gnmi_get / gnmi_set / gnmi_cli）](../management/gnmi-usage.md) (21)
- [OpenConfig Interfaces YANG（Ethernet 設定の REST/gNMI 対応と sonic-mgmt-common transformer）](../management/openconfig-support-for-ethernet-interfaces.md) (20)
- [YANG モデルによる ConfigDB 更新検証（GCU + ConfigDBConnector デコレータ）](../management/sonic-config-update-validation-via-yang.md) (19)

### [zebra](#term-zebra)

- [fpmsyncd NextHop Group 拡張（dplane_fpm_nl / NEXTHOP_GROUP_TABLE）](../routing/fpmsyncd-nexthop-group-enhancement-high-level-design-document.md) (28)
- [debug / undebug コマンド群](cli/debug-group.md) (23)
- [新 FRR-SONiC 通信チャネル（dplane_fpm_sonic モジュール）](../routing/new-frr-sonic-communication-channel.md) (11)
- [BGP Route Install Error Handling（ERROR_ROUTE_TABLE / FIB-install pending）](../routing/bgp-route-install-error-handling.md) (8)
- [BGP Suppress FIB Pending（dplane_fpm_nl + RTM_F_OFFLOAD）](../routing/bgp-suppress-announcements-of-routes-not-installed-in-hw.md) (8)

### [ZTP](#term-ztp)

- [Zero Touch Provisioning（ZTP・DHCP option / plugin / state machine）](../system/zero-touch-provisioning-ztp.md) (19)
- [ビルドプロファイル（rules/profiles/*.mk）](../architecture/build-profiles.md) (6)
- [SONiC NOS の設定手段一覧（CLI / sonic-cfggen / config_db.json / RESTCONF / gNMI / ZTP / vtysh / redis / apply-patch）](../management/sonic-nos-configuration-methods.md) (6)
- [config-setup サービス（first-boot config 生成 / 版間 migration）](../system/sonic-configuration-setup-service.md) (6)
- [運用](../topics/15-security-aaa/operations.md) (3)

<!-- /glossary-xref -->
