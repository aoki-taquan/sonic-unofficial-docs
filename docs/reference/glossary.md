---
title: 用語集 (Glossary)
description: "用語集 (Glossary) — SONiC NOS で頻出する固有用語・略語・コンポーネント名・データベース名・デーモン名を、アルファベット順に整理した日本語用語集です。各エントリは「用語 / 略称 / 日本語訳 / 簡潔な説明 / 関連ページ」の形式で記載しています。"
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
  _no_related: true
---

# 用語集 (Glossary)

SONiC NOS で頻出する固有用語・略語・コンポーネント名・データベース名・デーモン名を、アルファベット順に整理した日本語用語集です。各エントリは「用語 / 略称 / 日本語訳 / 簡潔な説明 / 関連ページ」の形式で記載しています。

!!! info "本ページの位置づけ"
    本ページはメタ情報（プロジェクト独自の用語整理）であり、特定の HLD や実装に直接対応するものではありません。詳細な仕様は各機能ページを参照してください。

## A

### AAA {#term-aaa}

- **略称**: AAA (Authentication, Authorization, Accounting)
- **日本語訳**: AAA
- **説明**: SONiC の管理プレーン認証認可機能。CONFIG_DB の `AAA` / `TACPLUS` / `RADIUS` テーブルを `hostcfgd` が購読し、`/etc/pam.d/` や `/etc/nsswitch.conf` を生成する。
- **関連**: [hostcfgd](#term-hostcfgd)

### ACL {#term-acl}

- **略称**: ACL (Access Control List)
- **日本語訳**: アクセス制御リスト
- **説明**: パケット分類・許可/拒否・ミラー/カウンタ等を行う機能。SONiC では `aclorch` が CONFIG_DB の `ACL_TABLE` / `ACL_RULE` を SAI ACL に変換する。
- **関連**: [ACL/CoPP/Mirror トピック](../topics/07-acl-copp-mirror/index.md)

### AF_XDP {#term-af-xdp}

- **略称**: AF_XDP (Address Family eXpress Data Path)
- **日本語訳**: AF_XDP
- **説明**: Linux カーネルの XDP を用いた高速パケットソケット。SONiC では一部の DPU / vs プラットフォームで NPU バイパス用途に利用される。
- **関連**: [DPDK](#term-dpdk)

### AQM {#term-aqm}

- **略称**: AQM (Active Queue Management)
- **日本語訳**: 能動的キュー管理
- **説明**: 輻輳発生前にキュー長を制御してパケットを早期にドロップ／マーキングするキュー管理の総称。SONiC では WRED / ECN が代表的な AQM 実装で、`qosorch` 経由で SAI Queue / Scheduler に設定される。
- **関連**: [WRED](#term-wred)、[ECN](#term-ecn)、[QoS](#term-qos)

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

### ASIC SDK {#term-asic-sdk}

- **略称**: ASIC SDK
- **日本語訳**: ASIC ソフトウェア開発キット
- **説明**: スイッチ ASIC ベンダーが提供する低レベル C ライブラリ群。SAI 実装 (`libsai*.so`) が SDK を呼び出して ASIC を制御する。SONiC では `syncd` コンテナにベンダー SDK と SAI shim をパッケージし、ハードウェア依存性を局所化する。
- **関連**: [SAI](#term-sai)、[syncd](#term-syncd)

### AsterNOS {#term-asternos}

- **略称**: AsterNOS
- **日本語訳**: AsterNOS (ベンダー版)
- **説明**: Asterfusion による SONiC ベースの商用 NOS。本ドキュメントのスコープ外。

### ASIC {#term-asic}

- **略称**: ASIC (Application Specific Integrated Circuit)
- **日本語訳**: 特定用途向け集積回路
- **説明**: SONiC が制御するスイッチング ASIC / NPU の総称。SAI 経由で `syncd` が抽象化したコマンドを ASIC SDK に渡す。


## B

### BFD {#term-bfd}

- **略称**: BFD (Bidirectional Forwarding Detection)
- **日本語訳**: 双方向フォワーディング検出
- **説明**: 高速な対向疎通検出プロトコル (RFC 5880)。SONiC では `bfdorch` / `bfd_offload` 等で扱う。
- **関連**: [BFD HLD ページ群](../routing/index.md)

### BFM {#term-bfm}

- **略称**: BFM (Buffer Flow Model / Buffer Function Model)
- **日本語訳**: バッファ機能モデル
- **説明**: スイッチ ASIC 内のバッファ／キュー振る舞いを抽象化したモデル。SONiC では `bufferorch` / `BUFFER_PROFILE` を介して MMU の Ingress/Egress バッファプールやしきい値を構成し、ベンダー SAI 実装が ASIC 固有 BFM にマップする。
- **関連**: [Buffer Model](#term-buffer-model)、[MMU](#term-mmu)

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

### Buffer Pool {#term-buffer-pool}

- **略称**: Buffer Pool
- **日本語訳**: バッファプール
- **説明**: MMU 内で確保される共有バッファ領域の単位。SONiC では Ingress / Egress 方向ごとに `BUFFER_POOL` テーブルでサイズと閾値を定義し、`BUFFER_PROFILE` から参照される。Dynamic Buffer Model では `buffermgrd` がポート速度や PG 設定に応じて動的に再配分する。
- **関連**: [Buffer Model](#term-buffer-model)、[MMU](#term-mmu)、[Headroom](#term-headroom)

### Buffer Profile {#term-buffer-profile}

- **略称**: Buffer Profile
- **日本語訳**: バッファプロファイル
- **説明**: バッファプールから割り当てる Reserved / Dynamic Threshold / Xon / Xoff / Headroom などのパラメータをまとめた設定単位。CONFIG_DB の `BUFFER_PROFILE` テーブルで定義し、`BUFFER_PG` (Ingress) / `BUFFER_QUEUE` (Egress) から参照される。`buffermgrd` が APPL_DB へ展開し、最終的に SAI Ingress/Egress Priority Group / Queue 属性に変換される。
- **関連**: [Buffer Pool](#term-buffer-pool)、[Headroom](#term-headroom)、[PG (Priority Group)](#term-pg)

### BUFFER_PG {#term-buffer-pg}

- **略称**: BUFFER_PG
- **日本語訳**: バッファ PG 設定テーブル
- **説明**: CONFIG_DB のテーブルで、ポート × Priority Group (0-7) ごとに参照する Buffer Profile を指定する。PFC を有効化する PG は無損失プロファイル (Xoff/Headroom 付き)、それ以外は損失許容プロファイルを割り当てる運用が一般的。
- **関連**: [Buffer Profile](#term-buffer-profile)、[PG (Priority Group)](#term-pg)、[PFC](#term-pfc)

## C

### Cold Reboot {#term-cold-reboot}

- **略称**: Cold Reboot
- **日本語訳**: コールドリブート
- **説明**: 通常の OS 再起動 (`reboot`)。ASIC を含むハードウェア全体が初期化されるためトラフィック断が最も大きい。`fast-reboot` / `warm-reboot` と対比される。
- **関連**: [Fast Reboot](#term-fast-reboot)、[Warm Reboot](#term-warm-reboot)

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

### ConsumerStateTable {#term-consumerstatetable}

- **略称**: ConsumerStateTable
- **日本語訳**: コンシューマ状態テーブル
- **説明**: `sonic-swss-common` が提供する Redis 上のキー値ストリームを消費する C++ クラス。orchagent や `*mgrd` が APPL_DB / CONFIG_DB の変更通知を購読する基盤。対となる ProducerStateTable と組で使う。
- **関連**: [ProducerStateTable](#term-producerstatetable)、[sonic-swss-common](#term-sonic-swss-common)

### CBF {#term-cbf}

- **略称**: CBF (Class-Based Forwarding)
- **日本語訳**: クラスベース転送
- **説明**: DSCP/TC を Forwarding Class (FC) にマッピングし、FC 単位で next-hop / queue 選択を分岐させる QoS 拡張。`DSCP_TO_FC_MAP` / `EXP_TO_FC_MAP` で構成。


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

### DPB {#term-dpb}

- **略称**: DPB (Dynamic Port Breakout)
- **日本語訳**: 動的ポート分割
- **説明**: 1 物理ポートを複数論理ポート (例: 100G×1 → 25G×4) に動的に再構成する機能。`portmgrd` / SAI Port API で実装され、CLI `config interface breakout` で操作する。
- **関連**: [portmgrd](#term-portmgrd)、[port_config.ini](#term-port-config-ini)

### DPDK {#term-dpdk}

- **略称**: DPDK (Data Plane Development Kit)
- **日本語訳**: DPDK
- **説明**: ユーザ空間で動作する高速パケット処理ライブラリ。SONiC では `sonic-pmd` 系プラットフォームや一部 DPU 実装で利用され、syncd / SAI 実装の下回りで使われることがある。

### DSCP {#term-dscp}

- **略称**: DSCP (Differentiated Services Code Point)
- **日本語訳**: DSCP
- **説明**: IP ヘッダ ToS の上位 6 ビットで定義される QoS マーキング (RFC 2474)。SONiC では `DSCP_TO_TC_MAP` で Ingress 側に TC へ変換し、`TC_TO_DSCP_MAP` で Egress リマーキングを行う。`PORT_QOS_MAP` 経由でポートにバインドされる。
- **関連**: [DSCP-to-TC Map](#term-dscp-to-tc-map)、[TC (Traffic Class)](#term-tc)、[ToS](#term-tos)

### DSCP-to-TC Map {#term-dscp-to-tc-map}

- **略称**: DSCP_TO_TC_MAP
- **日本語訳**: DSCP→TC マッピング
- **説明**: 受信パケットの DSCP 値を内部の Traffic Class (TC) に対応付ける QoS マップ。CONFIG_DB の `DSCP_TO_TC_MAP` テーブルで定義し、`qosorch` が SAI QoS Map (DSCP→TC) として ASIC に適用、`PORT_QOS_MAP` でポートに割り当てる。
- **関連**: [DSCP](#term-dscp)、[TC (Traffic Class)](#term-tc)、[QoS](#term-qos)

### DWRR {#term-dwrr}

- **略称**: DWRR (Deficit Weighted Round Robin)
- **日本語訳**: DWRR
- **説明**: 重み付きラウンドロビンに「赤字 (deficit)」カウンタを加え、可変長パケットでも重み比に近い帯域配分を実現するスケジューリングアルゴリズム。SONiC では `SCHEDULER` テーブルの `type=DWRR` と `weight` で設定し、SAI Scheduler `SAI_SCHEDULING_TYPE_DWRR` に対応する。
- **関連**: [WRR](#term-wrr)、[Scheduler](#term-scheduler)、[Strict Priority](#term-strict-priority)

### DEVICE_METADATA {#term-device_metadata}

- **略称**: DEVICE_METADATA
- **日本語訳**: デバイスメタデータ
- **説明**: CONFIG_DB の最上位テーブル。`localhost` キーにホスト名・hwsku・mac・type・platform 等のシステム識別情報を保持し、ほぼ全コンポーネントが参照する。

### dot1x {#term-dot1x}

- **略称**: dot1x (IEEE 802.1X)
- **日本語訳**: ポート認証 802.1X
- **説明**: ポートベース認証 (IEEE 802.1X)。CONFIG_DB の `DOT1X_PORT_AUTH` テーブルと hostapd 系で構成。RADIUS と連動する。


## E

### ECMP {#term-ecmp}

- **略称**: ECMP (Equal-Cost Multi-Path)
- **日本語訳**: 等コストマルチパス
- **説明**: 同コストの複数経路に対しハッシュベースでフローを分散する機能。SONiC では SAI Next Hop Group で実装。
- **関連**: [VRF/ECMP トピック](../topics/04-vrf-ecmp/index.md)

### ECN {#term-ecn}

- **略称**: ECN (Explicit Congestion Notification)
- **日本語訳**: 明示的輻輳通知
- **説明**: IP ヘッダの ECN ビット (RFC 3168) で輻輳をエンドホストに伝えるマーキング機構。SONiC では `WRED_PROFILE` の `ecn` フィールドで有効化し、SAI Queue / WRED に反映される。DCTCP / DCQCN (RoCEv2) の前提となる。
- **関連**: [WRED](#term-wred)、[AQM](#term-aqm)、[RoCE](#term-roce)

### Egress Queue {#term-egress-queue}

- **略称**: Egress Queue
- **日本語訳**: 送信キュー
- **説明**: 各物理ポートの送信側に存在する優先度別キュー (通常 8 本)。SAI Queue オブジェクトとしてモデル化され、`QUEUE` テーブルでスケジューラ / WRED プロファイルが結び付けられる。COUNTERS_DB に PG / queue 単位の統計が定期収集される。
- **関連**: [Per-port Queue](#term-per-port-queue)、[QoS](#term-qos)、[Buffer Pool](#term-buffer-pool)

### ENI {#term-eni}

- **略称**: ENI (Elastic Network Interface)
- **日本語訳**: ENI
- **説明**: DASH における仮想 NIC 概念。テナント単位のポリシーバインド単位。
- **関連**: [DASH](#dash)

### ETS {#term-ets}

- **略称**: ETS (Enhanced Transmission Selection)
- **日本語訳**: ETS
- **説明**: IEEE 802.1Qaz で規定される DCB 帯域共有機構。Traffic Class グループに最低保証帯域を割り当て、未使用帯域を他 TC が利用する。SONiC では `SCHEDULER` テーブルの `type=DWRR` と `weight` 構成、および `TC_TO_QUEUE_MAP` の組み合わせで ETS 相当の動作を実現する。
- **関連**: [DWRR](#term-dwrr)、[PFC](#term-pfc)、[Scheduler](#term-scheduler)

### EVPN {#term-evpn}

- **略称**: EVPN (Ethernet VPN)
- **日本語訳**: EVPN
- **説明**: BGP EVPN (RFC 7432) を用いた L2/L3 オーバーレイ制御プレーン。SONiC では FRR `bgpd` で実装。
- **関連**: [VXLAN EVPN VNET トピック](../topics/03-vxlan-evpn/index.md)

### EVPN-MH {#term-evpn-mh}

- **略称**: EVPN-MH (EVPN Multi-Homing)
- **日本語訳**: EVPN マルチホーミング
- **説明**: 1 つの CE を複数 PE に冗長接続する EVPN 拡張 (RFC 7432 Section 5)。Ethernet Segment (ES) / DF election / split-horizon label 等を用い、MCLAG の代替手段として FRR で実装される。
- **関連**: [EVPN](#term-evpn)、[MCLAG](#term-mclag)

### EXP {#term-exp}

- **略称**: EXP (MPLS Traffic Class / Experimental bits)
- **日本語訳**: MPLS EXP ビット
- **説明**: MPLS ラベルの 3-bit Traffic Class フィールド (旧称 EXP)。SONiC では `EXP_TO_FC_MAP` 等で内部 FC/TC にマップする。


## F

### Fast Reboot {#term-fast-reboot}

- **略称**: Fast Reboot
- **日本語訳**: ファストリブート
- **説明**: SONiC のホストプロセスとカーネルのみ再起動し、データプレーン (ASIC) を温存する再起動方式。`fast-reboot` スクリプトでトリガし、`kexec` を用いて秒オーダで制御プレーンを復旧する。
- **関連**: [Warm Reboot](#term-warm-reboot)、[Cold Reboot](#term-cold-reboot)

### FDB {#term-fdb}

- **略称**: FDB (Forwarding Database)
- **日本語訳**: MAC 学習テーブル
- **説明**: L2 MAC アドレス学習テーブル。SAI FDB エントリとして ASIC に書かれる。`fdbsyncd` がカーネル ↔ APPL_DB の同期を行う。

### fdbsyncd {#term-fdbsyncd}

- **略称**: fdbsyncd
- **日本語訳**: FDB 同期デーモン
- **説明**: Linux カーネルブリッジの FDB エントリと APPL_DB の `FDB_TABLE` を同期する SwSS コンポーネント。

### FLEX_COUNTER_DB {#term-flex_counter_db}

- **略称**: FLEX_COUNTER_DB
- **日本語訳**: FlexCounter 設定 DB
- **説明**: Redis DB ID 5。`FLEX_COUNTER_GROUP_TABLE` / `FLEX_COUNTER_TABLE` を保持し、`syncd` 内 FlexCounter にポーリング対象とインターバルを指示する制御用 DB。
- **関連**: [FlexCounter](#term-flexcounter)、[COUNTERS_DB](#term-counters_db)

### FlexCounter {#term-flexcounter}

- **略称**: FlexCounter
- **日本語訳**: 柔軟カウンタ
- **説明**: `syncd` 内でポーリング対象 SAI オブジェクト群を動的に管理し、COUNTERS_DB に書き込む仕組み。

### FPGA {#term-fpga}

- **略称**: FPGA (Field Programmable Gate Array)
- **日本語訳**: フィールドプログラマブルゲートアレイ
- **説明**: 再構成可能な論理回路デバイス。一部 SONiC 対応プラットフォームでは光モジュール制御 / Retimer / リファレンス NIC のデータパスに FPGA が搭載され、`pmon` 配下のプラットフォームドライバが SysFS / I2C 経由で制御する。
- **関連**: [NPU](#term-npu)、[NIC ASIC](#term-nic-asic)

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

### Forwarding Database {#term-forwarding-database}

- **略称**: Forwarding Database (FDB)
- **日本語訳**: 転送データベース
- **説明**: MAC アドレスと出力ポートの対応表。FDB の同義語。詳細は [FDB](#term-fdb) を参照。


## G

### gNMI {#term-gnmi}

- **略称**: gNMI (gRPC Network Management Interface)
- **日本語訳**: gNMI
- **説明**: gRPC ベースのテレメトリ / 設定プロトコル。SONiC では `sonic-gnmi` (旧 `sonic-telemetry`) で実装。

### GCU {#term-gcu}

- **略称**: GCU (Generic Config Updater)
- **日本語訳**: 汎用設定更新
- **説明**: JSON Patch (RFC 6902) を CONFIG_DB に適用する仕組み。`sonic-utilities` の `config apply-patch` で利用。

### gNOI {#term-gnoi}

- **略称**: gNOI (gRPC Network Operations Interface)
- **日本語訳**: gNOI
- **説明**: gRPC ベースの運用操作プロトコル (File / OS / FactoryReset / Cert 等の RPC)。SONiC では `sonic-gnmi` コンテナの一部として実装され、`gnoi.system.Reboot` 等が提供される。
- **関連**: [gNMI](#term-gnmi)

### Graceful Restart {#term-graceful-restart}

- **略称**: GR (Graceful Restart)
- **日本語訳**: グレースフルリスタート
- **説明**: ルーティングプロセス再起動時に隣接にルートを保持してもらう機能 (RFC 4724 / 4781 等)。SONiC では FRR の GR と Warm Reboot の連携でデータ転送無停止を実現。
- **関連**: [Warm Reboot](#term-warm-reboot)、[FRR](#term-frr)

## H

### HLD {#term-hld}

- **略称**: HLD (High Level Design)
- **日本語訳**: 高位設計書
- **説明**: SONiC の機能設計ドキュメント。`sonic-net/SONiC` リポの `doc/` 配下に集約される。本ドキュメントは HLD を再構成して書かれている。

### Headroom {#term-headroom}

- **略称**: Headroom
- **日本語訳**: ヘッドルーム
- **説明**: PFC 動作時に「PAUSE 送信から相手側送信停止が効くまでの間に到着するパケット」を吸収するために確保される予備バッファ領域。SONiC では `BUFFER_PG` の `xon` / `xoff` / `size` で構成され、Dynamic Buffer Model では `buffermgrd` がリンク速度・ケーブル長から自動計算する。
- **関連**: [PFC](#term-pfc)、[Buffer Pool](#term-buffer-pool)、[Buffer Model](#term-buffer-model)

### hostcfgd {#term-hostcfgd}

- **略称**: hostcfgd
- **日本語訳**: ホスト設定デーモン
- **説明**: CONFIG_DB の `AAA` / `TACPLUS` / `NTP` / `FEATURE` 等を購読し、Linux ホスト側の設定ファイル (`/etc/`) と `systemctl` を操作するデーモン。

### HwSku {#term-hwsku}

- **略称**: HwSku (Hardware SKU)
- **日本語訳**: ハードウェア SKU
- **説明**: 同一プラットフォーム上のポートマップ・速度プロファイルのバリアントを示す識別子。`/usr/share/sonic/device/<platform>/<hwsku>/` 配下に `port_config.ini` / `hwsku.json` / SAI プロファイル等が置かれる。
- **関連**: [port_config.ini](#term-port-config-ini)

## I

### IFA {#term-ifa}

- **略称**: IFA (In-band Flow Analyzer)
- **日本語訳**: インバンドフローアナライザ
- **説明**: パケットヘッダにフロー解析用メタデータを挿入する INT 系プロトコル (IETF draft-kumar-ippm-ifa)。SONiC では一部 ASIC ベンダーが SAI 拡張で対応し、TAM のテレメトリ手法の 1 つとして扱われる。
- **関連**: [INT](#term-int)、[TAM](#term-tam)

### INT {#term-int}

- **略称**: INT (In-band Network Telemetry)
- **日本語訳**: インバンドネットワークテレメトリ
- **説明**: データパケットにテレメトリメタデータを埋め込む計測手法 (P4.org 仕様)。SONiC では TAM / DASH / PINS の一部で扱われる。

### INT-XD {#term-int-xd}

- **略称**: INT-XD (INT eXport Data)
- **日本語訳**: INT エクスポートデータモード
- **説明**: INT 仕様におけるモードの 1 つで、パケットには変更を加えずスイッチがテレメトリ情報を別途コレクタへエクスポートする方式 (INT-MD / INT-MX と並ぶモード)。SONiC では TAM IFA / Postcard 系実装の根拠仕様として参照される。
- **関連**: [INT](#term-int)、[IFA](#term-ifa)、[TAM](#term-tam)

### Ingress Port Group {#term-ingress-port-group}

- **略称**: PG (Priority Group)
- **日本語訳**: 入力プライオリティグループ
- **説明**: 各物理ポート受信側で優先度ごとに割り当てられるバッファ管理単位 (通常 8 個)。SONiC では `BUFFER_PG` テーブルでサイズ / xon / xoff / プロファイルを設定し、PFC のヘッドルーム計算と直結する。COUNTERS_DB に PG ドロップ統計が記録される。
- **関連**: [PFC](#term-pfc)、[Headroom](#term-headroom)、[Buffer Pool](#term-buffer-pool)
- **関連**: [TAM](#term-tam)、[PINS](#term-pins)

### intfmgrd {#term-intfmgrd}

- **略称**: intfmgrd
- **日本語訳**: インターフェース設定マネージャ
- **説明**: CONFIG_DB の `INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` 等を購読し、APPL_DB の `INTF_TABLE` に変換する SwSS デーモン。

### intfsyncd {#term-intfsyncd}

- **略称**: intfsyncd
- **日本語訳**: インターフェース同期
- **説明**: Netlink からインターフェース状態を読み APPL_DB に反映する SwSS デーモン（プロジェクトにより役割が `portmgrd` 等に分割）。

### IPinIP {#term-ipinip}

- **略称**: IPinIP (IP-in-IP encapsulation)
- **日本語訳**: IPinIP トンネル
- **説明**: IP パケットを別の IP ヘッダでカプセル化する手法 (RFC 2003)。SONiC では Dual-ToR の active-standby 構成で standby ToR から active ToR にトラフィックを流すために使われる。
- **関連**: [MUX](#term-mux)、[linkmgrd](#term-linkmgrd)

### intfsorch {#term-intfsorch}

- **略称**: intfsorch
- **日本語訳**: L3 インタフェース orchestrator
- **説明**: `orchagent` 内部の L3 インタフェース処理サブ orchestrator。INTF_TABLE を購読し、SAI Router Interface (RIF) を作成する。


## L

### LOGLEVEL_DB {#term-loglevel_db}

- **略称**: LOGLEVEL_DB
- **日本語訳**: ログレベル DB
- **説明**: Redis DB ID 3。`*orch` / `*mgrd` 等の SwSS コンポーネントのログレベルを動的制御するための DB。近年は CONFIG_DB の `LOGGER` テーブルに移行が進んでいる。
- **関連**: [Redis](#term-redis)


### LACP {#term-lacp}

- **略称**: LACP (Link Aggregation Control Protocol)
- **日本語訳**: LACP
- **説明**: IEEE 802.1AX のリンク集約プロトコル。SONiC では `teamd` (libteam) で実装。
- **関連**: [L2/VLAN/LAG トピック](../topics/06-l2-vlan-lag/index.md)

### LAG {#term-lag}

- **略称**: LAG (Link Aggregation Group) / PortChannel
- **日本語訳**: リンク集約 / ポートチャネル
- **説明**: 複数物理ポートを 1 論理リンクに束ねる機能。CONFIG_DB では `PORTCHANNEL` テーブルで表現。

### Leaky Bucket {#term-leaky-bucket}

- **略称**: Leaky Bucket
- **日本語訳**: リーキーバケット
- **説明**: 一定速度でトークンが「漏れる」モデルで送出レートを平滑化する古典的アルゴリズム。Shaping (整形) で用いられ、バースト許容のない厳格な平均レート制御に適する。SONiC では SAI Policer / Scheduler 実装の内部アルゴリズムとして、ベンダー ASIC が Token Bucket と組み合わせて採用する。
- **関連**: [Token Bucket](#term-token-bucket)、[Shaper](#term-shaper)、[Policer](#term-policer)

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

### MAC Table {#term-mac-table}

- **略称**: MAC Table
- **日本語訳**: MAC アドレステーブル
- **説明**: スイッチ ASIC が L2 学習結果を保持するハードウェアテーブル。SONiC では FDB と同義で、SAI FDB エントリ経由で書き込まれ COUNTERS_DB / `show mac` 等で参照できる。サイズ上限は CRM の `fdb_entry` で監視される。
- **関連**: [FDB](#term-fdb)、[CRM](#term-crm)、[TCAM](#term-tcam)

### MPLS {#term-mpls}

- **略称**: MPLS (Multiprotocol Label Switching)
- **日本語訳**: MPLS
- **説明**: ラベルスイッチング転送方式 (RFC 3031)。SONiC では FRR の MPLS / Segment Routing 機能経由で `LABEL_ROUTE_TABLE` (APPL_DB) を使い `RouteOrch` が SAI MPLS API に橋渡しする。
- **関連**: [SRv6](#term-srv6)、[fpmsyncd](#term-fpmsyncd)

### MCLAG {#term-mclag}

- **略称**: MCLAG (Multi-Chassis LAG)
- **日本語訳**: MCLAG
- **説明**: 2 台の物理装置で共有 LAG を提供する機能。SONiC では `iccpd` 経由で同期。

### Microburst {#term-microburst}

- **略称**: Microburst
- **日本語訳**: マイクロバースト
- **説明**: ミリ秒未満の極短時間に発生する瞬時の輻輳バースト。秒平均では検出できないため、SONiC では FlexCounter / TAM / watermark (`WATERMARK` テーブル) によるバッファ占有率の高頻度サンプリングや、PFC / ECN マーキング統計で観測する。
- **関連**: [PFC](#term-pfc)、[Buffer Pool](#term-buffer-pool)、[FlexCounter](#term-flexcounter)

### minigraph.xml {#term-minigraph.xml}

- **略称**: minigraph
- **日本語訳**: ミニグラフ
- **説明**: Microsoft 由来のトポロジ記述 XML。`sonic-cfggen -m` で CONFIG_DB に変換される起動時設定ソース。

### MMU {#term-mmu}

- **略称**: MMU (Memory Management Unit)
- **日本語訳**: ASIC メモリ管理ユニット
- **説明**: スイッチ ASIC 内のパケットバッファ管理ブロック。Ingress / Egress バッファプール、PG / Queue 単位の閾値、admission control を担当する。SONiC では `bufferorch` が SAI Buffer Pool / Profile API を通じて MMU を構成する。
- **関連**: [Buffer Pool](#term-buffer-pool)、[Buffer Model](#term-buffer-model)、[BFM](#term-bfm)

### MUX {#term-mux}

- **略称**: MUX
- **日本語訳**: MUX (Dual-ToR セレクタ)
- **説明**: Dual-ToR 構成でサーバ側 NIC を Active 側 ToR に向けるための Y ケーブル / smartNIC スイッチング機構。

### MAC {#term-mac}

- **略称**: MAC (Media Access Control) Address
- **日本語訳**: MAC アドレス
- **説明**: L2 ハードウェアアドレス。SONiC では FDB / VXLAN FDB / ARP 等で扱い、`DEVICE_METADATA.localhost.mac` がスイッチ自身の base MAC を保持する。

### MACsec {#term-macsec}

- **略称**: MACsec (IEEE 802.1AE)
- **日本語訳**: MAC 層暗号化
- **説明**: L2 リンク暗号化規格。SONiC では `macsecmgrd` が CONFIG_DB の `MACSEC_PORT` / `MACSEC_PROFILE` を購読し、SAI MACsec オブジェクト経由で ASIC を構成する。

### Multi-ASIC {#term-multi-asic}

- **略称**: Multi-ASIC
- **日本語訳**: マルチ ASIC 構成
- **説明**: 1 台の SONiC デバイスに複数の ASIC (namespace) を搭載するシャーシ/モジュラ構成。`asic0` / `asic1` 等の namespace を持ち、CLI には `-n <ns>` オプションが追加される。

### muxorch {#term-muxorch}

- **略称**: muxorch
- **日本語訳**: Active-Standby MUX orchestrator
- **説明**: Dual-ToR (Active-Standby MUX) を扱う orchagent サブ orchestrator。`MUX_CABLE` テーブルを購読し、SAI tunnel / next-hop の active 側切替を行う。


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

### Next Hop Group {#term-next-hop-group}

- **略称**: Next Hop Group / NHG
- **日本語訳**: ネクストホップグループ
- **説明**: ECMP / Weighted ECMP 用に複数 next hop を束ねた SAI オブジェクト (`SAI_OBJECT_TYPE_NEXT_HOP_GROUP`)。`RouteOrch` / `NhgOrch` が生成し、route エントリから参照される。
- **関連**: [ECMP](#term-ecmp)

### NDP {#term-ndp}

- **略称**: NDP (Neighbor Discovery Protocol)
- **日本語訳**: 近隣探索プロトコル
- **説明**: IPv6 のリンクローカル隣接探索プロトコル (RFC 4861)。SONiC では Linux カーネルが処理し、`neighsyncd` 経由で APPL_DB の `NEIGH_TABLE` に反映される。
- **関連**: [ARP](#term-arp)、[neighsyncd](#term-neighsyncd)

### NIC ASIC {#term-nic-asic}

- **略称**: NIC ASIC
- **日本語訳**: NIC ASIC
- **説明**: サーバ／DPU 上の高機能 NIC を構成する ASIC。SmartSwitch / DASH 構成では NIC ASIC 側で ENI / 暗号化 / フローオフロードを処理する。SONiC では DPU 側インスタンスが SAI で NIC ASIC を抽象化する。
- **関連**: [DPU](#term-dpu)、[SmartNIC](#term-smartnic)、[SAI](#term-sai)

### NPL {#term-npl}

- **略称**: NPL (Network Programming Language)
- **日本語訳**: ネットワークプログラミング言語
- **説明**: Broadcom 系プログラマブル ASIC (Trident4 等) 向けの高位記述言語。P4 と類似のデータプレーン記述用 DSL で、ASIC SDK / SAI 実装の下回りでパイプライン定義に用いられる。
- **関連**: [P4-Runtime](#term-p4-runtime)、[ASIC SDK](#term-asic-sdk)

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

### PFC Storm {#term-pfc-storm}

- **略称**: PFC Storm
- **日本語訳**: PFC ストーム
- **説明**: 受信側 NIC やスイッチが PFC PAUSE フレームを継続的に送出し続け、上流リンクが慢性的に停止してしまう障害状態。RoCEv2 環境で typified に発生する。SONiC では `pfcwd` が連続 PAUSE をキュー単位で検出してドレインモードに遷移させ、ネットワーク全体への波及を抑止する。
- **関連**: [PFC Watchdog](#term-pfc-watchdog)、[PFC](#term-pfc)、[RoCE](#term-roce)

### Per-port Queue {#term-per-port-queue}

- **略称**: Per-port Queue
- **日本語訳**: ポート単位キュー
- **説明**: 各物理ポートごとに割り当てられた送信キュー集合 (通常 8 本)。SONiC では `QUEUE|<port>|<index>` 形式で CONFIG_DB / APPL_DB に表現され、`SCHEDULER` / `WRED_PROFILE` がポート単位で適用される。VOQ アーキテクチャの ASIC ではキュー粒度がさらに細分化される。
- **関連**: [Egress Queue](#term-egress-queue)、[VOQ](#term-voq)、[QoS](#term-qos)

### PG (Priority Group) {#term-pg}

- **略称**: PG (Priority Group), Ingress Priority Group
- **日本語訳**: プライオリティグループ
- **説明**: Ingress 側で PFC 優先度に対応するバッファ予約単位 (通常 0-7)。SONiC では `BUFFER_PG` テーブルでポート × PG ごとに Buffer Profile を割り当て、PFC を有効化する PG には Xoff / Headroom 付きの無損失プロファイルを適用する。SAI の `SAI_OBJECT_TYPE_INGRESS_PRIORITY_GROUP` に対応。
- **関連**: [BUFFER_PG](#term-buffer-pg)、[Buffer Profile](#term-buffer-profile)、[PFC](#term-pfc)

### portmgrd {#term-portmgrd}

- **略称**: portmgrd
- **日本語訳**: ポート設定マネージャ
- **説明**: CONFIG_DB の `PORT` テーブルを購読し、APPL_DB に書き出す SwSS デーモン。

### portsyncd {#term-portsyncd}

- **略称**: portsyncd
- **日本語訳**: ポート同期デーモン
- **説明**: `port_config.ini` / `platform.json` を読み込み、初期 PORT エントリを APPL_DB に登録する SwSS デーモン。

### port_config.ini {#term-port-config-ini}

- **略称**: port_config.ini
- **日本語訳**: ポート設定 INI
- **説明**: HwSku ディレクトリ配下に置かれるポートマップ定義ファイル。物理ポート名・lane 番号・速度・alias・index 等を記述し、起動時 `portsyncd` が読み込んで PORT エントリを生成する。近年は `platform.json` / `hwsku.json` への移行が進行中。
- **関連**: [HwSku](#term-hwsku)、[portsyncd](#term-portsyncd)

### PINS {#term-pins}

- **略称**: PINS (P4 Integrated Network Stack)
- **日本語訳**: PINS
- **説明**: P4-Runtime と gNMI/gNOI を用いて SONiC を制御する Google 主導の SDN スタック。`p4rt` コンテナ・`P4RT_TABLE` を介して既存 SwSS パイプラインと併存する。
- **関連**: [P4-Runtime](#term-p4-runtime)、[gNMI](#term-gnmi)

### P4-Runtime {#term-p4-runtime}

- **略称**: P4-Runtime
- **日本語訳**: P4-Runtime
- **説明**: P4 パイプラインを gRPC で制御するコントロールプレーン API (p4.org)。SONiC では PINS が `p4rt` サーバを実装し、`P4RT_TABLE` 経由で `orchagent` と連携する。
- **関連**: [PINS](#term-pins)

### ProducerStateTable {#term-producerstatetable}

- **略称**: ProducerStateTable
- **日本語訳**: プロデューサ状態テーブル
- **説明**: `sonic-swss-common` が提供する Redis 上のキー値ストリームに書き込む C++ クラス。`*mgrd` / `fpmsyncd` 等が APPL_DB に通知する基盤。対となる ConsumerStateTable と組で使う。
- **関連**: [ConsumerStateTable](#term-consumerstatetable)、[sonic-swss-common](#term-sonic-swss-common)

### PortChannel {#term-portchannel}

- **略称**: PortChannel
- **日本語訳**: ポートチャネル
- **説明**: SONiC の LAG の呼称。CONFIG_DB テーブル名も `PORTCHANNEL`。

### Policer {#term-policer}

- **略称**: Policer
- **日本語訳**: ポリサー
- **説明**: フロー / ACL に対し帯域上限を計測し、超過パケットをドロップまたはマーキング (re-color) する機構。CONFIG_DB の `POLICER` テーブルで CIR / PIR / CBS / PBS / `meter_type` (packets|bytes) を定義し、ACL ルールや CoPP テーブルから参照される。SAI の `SAI_OBJECT_TYPE_POLICER` に対応する。
- **関連**: [Policing](#term-policing)、[CoPP](#term-copp)、[Token Bucket](#term-token-bucket)

### Policing {#term-policing}

- **略称**: Policing
- **日本語訳**: ポリシング
- **説明**: トラフィックレートを計測し、設定上限を超えたパケットを即座に廃棄またはマーキングする QoS 動作 (RFC 2697 srTCM / RFC 2698 trTCM 等)。Shaping と異なりキューイングせず即時判定するため、低遅延が必要なエッジ制御や CoPP に向く。SONiC では Policer オブジェクトで実装する。
- **関連**: [Policer](#term-policer)、[Shaping](#term-shaping)、[Token Bucket](#term-token-bucket)

### P4RT {#term-p4rt}

- **略称**: P4RT (P4Runtime)
- **日本語訳**: P4 ランタイム
- **説明**: P4 ターゲットを制御する gRPC ベースの API。SONiC では PINS で導入され、`p4rt` コンテナが APPL_DB / SAI と仲介する。

### portsorch {#term-portsorch}

- **略称**: portsorch
- **日本語訳**: Port orchestrator
- **説明**: `orchagent` 内部のポート/LAG/PortChannel 管理サブ orchestrator。`PORT_TABLE` / `LAG_TABLE` を購読し、SAI Port/LAG オブジェクトを管理する。

### Priority Group {#term-priority-group}

- **略称**: Priority Group (PG)
- **日本語訳**: プライオリティグループ
- **説明**: 入力側のクラス分け単位 (Ingress PG)。詳細は [PG (Priority Group)](#term-pg) を参照。


## Q

### QoS {#term-qos}

- **略称**: QoS (Quality of Service)
- **日本語訳**: QoS
- **説明**: `TC_TO_QUEUE_MAP` / `DSCP_TO_TC_MAP` / `SCHEDULER` 等で構成される SONiC のキューイング・スケジューリング・マーキング機構。

### QSGMII {#term-qsgmii}

- **略称**: QSGMII (Quad Serial Gigabit Media Independent Interface)
- **日本語訳**: QSGMII
- **説明**: 1 本の SerDes レーンに 4 ポート分の 1G イーサネットを多重化する SGMII の拡張規格。SONiC では管理ポートや低速フロントパネルポートを持つ一部プラットフォームの `port_config.ini` / `platform.json` で speed/lanes 設定に現れる。
- **関連**: [SerDes](#term-serdes)、[port_config.ini](#term-port-config-ini)

## R

### RoCE {#term-roce}

- **略称**: RoCE (RDMA over Converged Ethernet)
- **日本語訳**: RoCE
- **説明**: イーサネット上で RDMA を実現するプロトコル (RoCEv2 は UDP/4791)。SONiC ではロスレス転送のため PFC + ECN + 動的バッファプロファイルを組み合わせて運用される。
- **関連**: [PFC](#term-pfc)、[QoS](#term-qos)

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

### RADIUS {#term-radius}

- **略称**: RADIUS (Remote Authentication Dial-In User Service)
- **日本語訳**: RADIUS
- **説明**: ネットワーク機器の認証/認可/アカウンティング (AAA) を提供する RFC 2865 ベースのプロトコル。CONFIG_DB の `RADIUS` / `RADIUS_SERVER` テーブルを `hostcfgd` が処理する。

### ROUTE_MAP {#term-route_map}

- **略称**: ROUTE_MAP
- **日本語訳**: ルートマップ
- **説明**: BGP/IGP の経路フィルタ/属性書き換えポリシ。CONFIG_DB の `ROUTE_MAP` / `ROUTE_MAP_SET` を `bgpcfgd` が vtysh コマンドへ変換し FRR に投入する。


## S

### SNMP {#term-snmp}

- **略称**: SNMP (Simple Network Management Protocol)
- **日本語訳**: SNMP
- **説明**: 旧来の運用監視プロトコル (RFC 3416)。SONiC では `docker-snmp` 内で Net-SNMP + `sonic_ax_impl` AgentX サブエージェントが Redis から MIB を提供する。
- **関連**: [Tech Support](#term-tech-support)

### SRAM {#term-sram}

- **略称**: SRAM (Static Random Access Memory)
- **日本語訳**: 静的 RAM
- **説明**: スイッチ ASIC 内蔵の高速メモリ。MAC テーブル・LPM ルートテーブル・カウンタ等の格納に使われる。TCAM とは異なり exact-match 索引が中心。SONiC では資源使用量が CRM 経由で `fdb_entry` / `ipv4_route` / `ipv6_route` 等として可視化される。
- **関連**: [TCAM](#term-tcam)、[CRM](#term-crm)、[MAC Table](#term-mac-table)

### SRv6 {#term-srv6}

- **略称**: SRv6 (Segment Routing over IPv6)
- **日本語訳**: SRv6
- **説明**: IPv6 拡張ヘッダ (SRH) でセグメントリストを運ぶ Segment Routing 方式 (RFC 8754 等)。SONiC では FRR と SwSS の `SRV6_*` テーブル群 + `Srv6Orch` で実装される。
- **関連**: [MPLS](#term-mpls)

### SAI {#term-sai}

- **略称**: SAI (Switch Abstraction Interface)
- **日本語訳**: スイッチ抽象化インターフェース
- **説明**: SONiC とベンダー ASIC の境界となる C API。OCP 標準化。`sonic-sairedis` がプロセス境界でラップ。
- **関連**: [SAI Reference](./index.md)

### SerDes {#term-serdes}

- **略称**: SerDes (Serializer/Deserializer)
- **日本語訳**: SerDes
- **説明**: 高速シリアルレーンと並列バスを変換する ASIC 内ブロック。レーン速度 (例: 56G PAM4 / 112G PAM4) によりフロントパネルポート速度が決まる。SONiC では `port_config.ini` / `platform.json` の lanes 設定と、ベンダー固有 `media_settings.json` / Tx FIR チューニングが SerDes パラメータを供給する。
- **関連**: [port_config.ini](#term-port-config-ini)、[QSGMII](#term-qsgmii)

### sFlow Agent {#term-sflow-agent}

- **略称**: sFlow Agent
- **日本語訳**: sFlow エージェント
- **説明**: スイッチ上でサンプリングしたパケットとカウンタを sFlow Collector に送出するプロセス。SONiC では `docker-sflow` 内の `hsflowd` が CONFIG_DB の `SFLOW` / `SFLOW_SESSION` を読み、SAI Samplepacket オブジェクト経由で ASIC サンプリングを構成する。
- **関連**: [sFlow Collector](#term-sflow-collector)、[TAM](#term-tam)

### sFlow Collector {#term-sflow-collector}

- **略称**: sFlow Collector
- **日本語訳**: sFlow コレクタ
- **説明**: 複数スイッチの sFlow Agent から sFlow データグラム (RFC 3176) を受信する外部ホスト。SONiC では `SFLOW_COLLECTOR` テーブルで IP / UDP ポート / VRF を指定する。
- **関連**: [sFlow Agent](#term-sflow-agent)

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

### saiserver {#term-saiserver}

- **略称**: saiserver
- **日本語訳**: SAI サーバ
- **説明**: SAI 呼び出しを Thrift RPC で外部に公開するテスト用バイナリ (`sonic-sairedis/saiserver`)。`PTF` ベースの SAI 単体試験で利用される。`docker-saiserver` で配布。
- **関連**: [SAI](#term-sai)、[VS](#term-vs)

### Scheduler {#term-scheduler}

- **略称**: Scheduler
- **日本語訳**: スケジューラ
- **説明**: 各 Egress Queue から送出するパケットの順序とレートを決定するアルゴリズム実体。SONiC では `SCHEDULER` テーブル (`type` = `STRICT` / `DWRR` / `WRR`、`weight`、`meter_type`、`pir`/`cir`) で定義し、`QUEUE` テーブルから参照する。`qosorch` が SAI Scheduler オブジェクトに変換する。
- **関連**: [Strict Priority](#term-strict-priority)、[DWRR](#term-dwrr)、[WRR](#term-wrr)、[Shaper](#term-shaper)

### Shaper {#term-shaper}

- **略称**: Shaper
- **日本語訳**: シェイパー
- **説明**: 送信レートに上限を設けて超過分をキューイングし、均された速度で送出する QoS 機構。SONiC では `SCHEDULER` テーブルの `pir` / `meter_type` で表現し、SAI Scheduler の `max_bandwidth_*` 属性として実装される。
- **関連**: [Shaping](#term-shaping)、[Scheduler](#term-scheduler)、[Leaky Bucket](#term-leaky-bucket)

### Shaping {#term-shaping}

- **略称**: Shaping
- **日本語訳**: シェイピング
- **説明**: トラフィックレートを計測し、超過分をキューイングして平滑化する QoS 動作。Policing が即時廃棄するのに対し、Shaping はバッファを使ってジッタを抑える代わりに遅延を許容する。SONiC では Shaper 設定 (Scheduler の PIR) で実現する。
- **関連**: [Shaper](#term-shaper)、[Policing](#term-policing)、[Token Bucket](#term-token-bucket)

### Shared Buffer {#term-shared-buffer}

- **略称**: Shared Buffer
- **日本語訳**: 共有バッファ
- **説明**: 複数ポート / キューが共用する MMU バッファ領域。Reserved (各 PG/Queue に予約) と対比される概念で、突発的なトラフィック (Microburst) を吸収する。SONiC の Dynamic Buffer Model では `BUFFER_POOL.size` から Reserved 合計を差し引いた残量が共有領域となり、`dynamic_th` (α) で各 PG/Queue が利用できる比率が決まる。
- **関連**: [Buffer Pool](#term-buffer-pool)、[Buffer Profile](#term-buffer-profile)、[Microburst](#term-microburst)

### SmartNIC {#term-smartnic}

- **略称**: SmartNIC
- **日本語訳**: SmartNIC
- **説明**: プログラマブルなデータパス／オフロード機能を持つ高機能 NIC の総称。Dual-ToR の MUX 機構や DASH の DPU 側など、SONiC の周辺アーキテクチャで参照される。
- **関連**: [DPU](#term-dpu)、[NIC ASIC](#term-nic-asic)、[MUX](#term-mux)

### SmartSwitch {#term-smartswitch}

- **略称**: SmartSwitch
- **日本語訳**: SmartSwitch
- **説明**: NPU + 複数 DPU を 1 シャーシに搭載するアーキテクチャ。DASH と組み合わせて使う。

### Strict Priority {#term-strict-priority}

- **略称**: SP (Strict Priority)
- **日本語訳**: 厳格優先
- **説明**: 高優先キューにパケットがある限り低優先キューを完全に待たせるスケジューリング方式。SONiC では `SCHEDULER` テーブルの `type=STRICT` で設定し、SAI Scheduler `SAI_SCHEDULING_TYPE_STRICT` に対応する。低遅延制御プレーンや音声/同期トラフィックに用いるが、低優先キューの飢餓に注意。
- **関連**: [Scheduler](#term-scheduler)、[DWRR](#term-dwrr)、[QoS](#term-qos)

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

### Syslog {#term-syslog}

- **略称**: Syslog (RFC 5424)
- **日本語訳**: システムログ
- **説明**: SONiC の各デーモン / コンテナが出力する標準ログ収集機構。ホスト側 `rsyslog` がコンテナログを集約し、デフォルトでは `/var/log/syslog` に出力する。Runbook では障害切り分けの一次資料として参照される。`config syslog server add <ip>` で外部コレクタへの転送設定が可能。

### SONiC {#term-sonic}

- **略称**: SONiC (Software for Open Networking in the Cloud)
- **日本語訳**: SONiC
- **説明**: Linux ベースのオープンソース NOS。本ドキュメントが対象とするコミュニティ版 master ブランチ。詳細は [プロジェクトトップ](../../index.md) を参照。


## T

### TAM {#term-tam}

- **略称**: TAM (Telemetry and Monitoring)
- **日本語訳**: TAM
- **説明**: SAI TAM API (`SAI_OBJECT_TYPE_TAM*`) を用いた帯域内テレメトリ機能群。INT / IFA / Drop monitor / Postcard 等を扱う。SONiC では `TAM_*` CONFIG_DB テーブルと TAM オーチが提供される。
- **関連**: [INT](#term-int)

### TC (Traffic Class) {#term-tc}

- **略称**: TC (Traffic Class)
- **日本語訳**: トラフィッククラス
- **説明**: ASIC 内部での QoS 優先度識別子 (通常 0-7)。Ingress 側で `DSCP_TO_TC_MAP` や `DOT1P_TO_TC_MAP` により決定され、Egress 側で `TC_TO_QUEUE_MAP` / `TC_TO_PG_MAP` / `TC_TO_DSCP_MAP` の入力として使われる。SAI では QoS Map のキー / 値として扱う。
- **関連**: [DSCP-to-TC Map](#term-dscp-to-tc-map)、[TC-to-Queue Map](#term-tc-to-queue-map)、[QoS](#term-qos)

### TC-to-Queue Map {#term-tc-to-queue-map}

- **略称**: TC_TO_QUEUE_MAP
- **日本語訳**: TC→キューマッピング
- **説明**: 内部 Traffic Class を Egress Queue インデックスに対応付ける QoS マップ。CONFIG_DB の `TC_TO_QUEUE_MAP` テーブルで定義し、`PORT_QOS_MAP` でポートに割り当てる。`qosorch` が SAI QoS Map (`SAI_QOS_MAP_TYPE_TC_TO_QUEUE`) として ASIC に書き出す。
- **関連**: [TC (Traffic Class)](#term-tc)、[Egress Queue](#term-egress-queue)、[Scheduler](#term-scheduler)

### TCAM {#term-tcam}

- **略称**: TCAM (Ternary Content Addressable Memory)
- **日本語訳**: 三値連想メモリ
- **説明**: ワイルドカード付きパケット分類を 1 サイクルで実行できる特殊メモリ。ACL ルール / LPM ルート / PBR / Mirror セッションのマッチ部に使われ、容量が ASIC の上限要因となりやすい。SONiC では CRM が ACL TCAM 使用量を `acl_table` / `acl_group` / `acl_entry` などとして監視する。
- **関連**: [ACL](#term-acl)、[CRM](#term-crm)、[SRAM](#term-sram)

### Tech Support {#term-tech-support}

- **略称**: Tech Support / `show techsupport`
- **日本語訳**: テックサポートダンプ
- **説明**: 障害解析用にログ・設定・状態を一括収集するアーカイブ機能。`generate_dump` スクリプトで `/var/dump/sonic_dump_*.tar.gz` を生成し、Redis 全 DB ・syslog ・FRR `vtysh` 出力等を含める。
- **関連**: [sonic-utilities](#term-sonic-utilities)

### teamd / teamsyncd / teammgrd {#term-teamd-teamsyncd-teammgrd}

- **略称**: teamd / teamsyncd / teammgrd
- **日本語訳**: teamd 系 LAG デーモン
- **説明**: Linux `libteam` ベースの LACP 実装。`teammgrd` が CONFIG_DB 購読、`teamsyncd` が Netlink ↔ APPL_DB 同期、`teamd` が LACP プロトコル本体。

### Token Bucket {#term-token-bucket}

- **略称**: Token Bucket
- **日本語訳**: トークンバケット
- **説明**: 一定速度でトークンを生成し、パケット送信時にバケットからトークンを消費するレート制御アルゴリズム。バケット容量分のバーストを許容しつつ平均レートを保証する。SONiC の Policer / Shaper の CIR / CBS / PIR / PBS は Token Bucket パラメータに対応し、RFC 2697 srTCM / RFC 2698 trTCM のメータリングを表現する。
- **関連**: [Leaky Bucket](#term-leaky-bucket)、[Policer](#term-policer)、[Shaper](#term-shaper)

### ToS {#term-tos}

- **略称**: ToS (Type of Service)
- **日本語訳**: ToS フィールド
- **説明**: IPv4 ヘッダのサービス品質指定用 8 ビットフィールド (RFC 791)。現在は上位 6 ビットを DSCP (RFC 2474)、下位 2 ビットを ECN (RFC 3168) として再定義して用いる。IPv6 では Traffic Class フィールドが対応物。
- **関連**: [DSCP](#term-dscp)、[ECN](#term-ecn)

### tunnelmgrd {#term-tunnelmgrd}

- **略称**: tunnelmgrd
- **日本語訳**: トンネル管理デーモン
- **説明**: CONFIG_DB の `TUNNEL` / `MUX_TUNNEL` 等を購読し APPL_DB に変換する SwSS デーモン。

### ToR {#term-tor}

- **略称**: ToR (Top of Rack)
- **日本語訳**: ToR スイッチ
- **説明**: ラック上部に配置されるアクセススイッチの慣用呼称。SONiC では Dual-ToR (Active-Standby MUX) のような構成上のロールとしても用いられる。


## V

### VOQ {#term-voq}

- **略称**: VOQ (Virtual Output Queue)
- **日本語訳**: 仮想出力キュー
- **説明**: 各入力ポートが出力ポートごとに独立キューを持つスイッチング方式。Head-of-Line ブロッキングを回避する。SONiC では分散シャーシ (VoQ Chassis) で `CHASSIS_APP_DB` / global system port 管理と組で扱われる。
- **関連**: [BGP](#term-bgp)

### VS {#term-vs}

- **略称**: VS (Virtual Switch)
- **日本語訳**: 仮想スイッチ
- **説明**: SAI VS バックエンドを用いた SONiC のソフトウェアスイッチ実装 (`docker-sonic-vs`)。CI 上の機能試験・KVM ベースの開発環境 (`sonic-mgmt-vs`) で利用される。
- **関連**: [saiserver](#term-saiserver)、[sonic-mgmt](#term-sonic-mgmt)

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

### VRRP {#term-vrrp}

- **略称**: VRRP (Virtual Router Redundancy Protocol)
- **日本語訳**: VRRP (RFC 5798)
- **説明**: デフォルトゲートウェイ冗長化プロトコル。SONiC では `VRRP` / `VRRP6` テーブルを FRR `vrrpd` 経由で扱う。

### VTEP {#term-vtep}

- **略称**: VTEP (VXLAN Tunnel Endpoint)
- **日本語訳**: VXLAN トンネル端点
- **説明**: VXLAN カプセル化/デカプセル化を行う端点。SONiC では `VXLAN_TUNNEL` テーブルに source IP を設定して構成する。

### vtysh {#term-vtysh}

- **略称**: vtysh
- **日本語訳**: FRR 統合シェル
- **説明**: FRR (zebra/bgpd/ospfd 等) を統合操作する CLI シェル。SONiC では `bgpcfgd` が CONFIG_DB 変更を vtysh コマンドへ変換して投入する。


## W

### Warm Reboot {#term-warm-reboot}

- **略称**: Warm Reboot
- **日本語訳**: ウォームリブート
- **説明**: SONiC のホスト OS / コンテナを再起動しつつ ASIC のデータプレーン状態を温存する手法。FRR Graceful Restart や `syncd` の WARM_BOOT モードを併用し、転送無瞬断 (sub-second) を目標とする。
- **関連**: [Fast Reboot](#term-fast-reboot)、[Cold Reboot](#term-cold-reboot)、[Graceful Restart](#term-graceful-restart)

### WRED {#term-wred}

- **略称**: WRED (Weighted Random Early Detection)
- **日本語訳**: 重み付きランダム早期検出
- **説明**: バッファ輻輳前にパケットをランダムドロップ / ECN マークする QoS 機能。CONFIG_DB の `WRED_PROFILE` で定義。

### WRR {#term-wrr}

- **略称**: WRR (Weighted Round Robin)
- **日本語訳**: 重み付きラウンドロビン
- **説明**: 各キューに割り当てた重みに応じて、ラウンドごとに送出パケット数を比例配分するスケジューリング方式。可変長パケットでは厳密な帯域比にならないため、SONiC / SAI では通常 DWRR を推奨する。`SCHEDULER` テーブルの `type=WRR` で指定可能。
- **関連**: [DWRR](#term-dwrr)、[Scheduler](#term-scheduler)、[Strict Priority](#term-strict-priority)

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

### [AAA](#term-aaa)

- [AAA Improvements（PAM / NSS / D-Bus / RBAC 多重ロール）](../management/aaa-improvements.md) (27)
- [sonic-system-aaa YANG](yang/sonic-system-aaa.md) (24)
- [運用](../topics/15-security-aaa/operations.md) (19)
- [config aaa / tacacs / radius サブコマンド](cli/config-aaa.md) (17)
- [サイトマップ](../_meta/sitemap.md) (16)

### [ACL](#term-acl)

- [サイトマップ](../_meta/sitemap.md) (75)
- [概念](../topics/07-acl-copp-mirror/concept.md) (65)
- [ACL の基本設計（ACL_TABLE / ACL_RULE スキーマ）](../acl-qos/acl-support-in-sonic.md) (63)
- [ACL カウンタの flex counter 化（ACL_COUNTER + COUNTERS_ACL_COUNTER_RULE_MAP）](../acl-qos/acl-flex-counters-support.md) (61)
- [内部実装](../topics/07-acl-copp-mirror/internals.md) (57)

### [AQM](#term-aqm)

- [QoS / Buffer の発展トピック](../topics/08-qos-buffer/advanced.md) (1)
- [発展トピック](../topics/12-multi-asic-voq/advanced.md) (1)

### [APPL_DB](#term-appl_db)

- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (26)
- [swss-schema（APPL_DB / STATE_DB の中心スキーマ参照）](../internals/swss-schema.md) (18)
- [概要](../topics/20-swss-sai-redis/concept.md) (15)
- [ポート Auto-Negotiation（advertised-speeds / interface-type）](../architecture/sonic-port-auto-negotiation-design.md) (14)
- [内部実装](../topics/06-l2-vlan-lag/internals.md) (14)

### [ARP](#term-arp)

- [L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd / show](../internals/l3-scaling-and-performance-enhancements.md) (35)
- [Active-Standby Dual ToR（y-cable + linkmgrd state machine + IPinIP tunnel）](../overlay/active-standby-dual-tor.md) (13)
- [ICCPd 内部構成（MC-LAG / MLACP FSM ファイル別マップ）](../switching/brief-introduction-of-iccp-code.md) (12)
- [Fast-reboot Flow Improvements（finalizer / reconciliation）](../system/fast-reboot-flow-improvements-hld.md) (11)
- [サイトマップ](../_meta/sitemap.md) (10)

### [ASIC_DB](#term-asic_db)

- [VRF VS テストプラン（vrfmgrd / intfmgrd / Orchagent → APP_DB / ASIC_DB / kernel）](../routing/vrf-vs-test-plan.md) (13)
- [アーキテクチャ](../topics/20-swss-sai-redis/architecture.md) (11)
- [内部実装](../topics/20-swss-sai-redis/internals.md) (11)
- [概念と読み始め方](../topics/01-overview/concept.md) (9)
- [内部実装](../topics/01-overview/internals.md) (9)

### [ASIC SDK](#term-asic-sdk)

- [L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd / show](../internals/l3-scaling-and-performance-enhancements.md) (1)
- [P4Runtime PacketIO（generic netlink + send_to_ingress）](../management/packetio.md) (1)
- [FEC FLR 概念（FLR / CER / interleaving / observed vs predicted）](../platform/fec-flr-support-in-sonic-concepts.md) (1)
- [ASIC / SDK Health Event のハンドリング（SAI notification → STATE_DB → action）](../platform/handle-asic-sdk-health-event.md) (1)
- [ASIC 内部温度センサのポーリング（ASIC_SENSORS / ASIC_TEMPERATURE_INFO）](../system/asic-thermal-monitoring-high-level-design.md) (1)

### [AsterNOS](#term-asternos)

- [このドキュメントについて](../about.md) (2)
- [SAG（Static Anycast Gateway）for SONiC](../architecture/sag-high-level-design-for-sonic.md) (1)

### [BFD](#term-bfd)

- [BGP セッション向け BFD ハードウェアオフロード（bfdsyncd 経路）](../routing/bfd-hw-offload-for-bgp-session.md) (77)
- [BFD ハードウェアオフロード（BfdOrch / BFD_SESSION）](../routing/bfd-hw-offload.md) (73)
- [show bfd サブコマンド](cli/show-bfd.md) (24)
- [頻出 SAI 属性早見表](sai-attributes.md) (20)
- [Overlay ECMP with BFD monitoring（VxLAN VNet ルートと BFD 連動）](../routing/overlay-ecmp-with-bfd-monitoring.md) (18)

### [BGP](#term-bgp)

- [sonic-bgp-neighbor YANG](yang/sonic-bgp-neighbor.md) (248)
- [sonic-bgp-peergroup YANG](yang/sonic-bgp-peergroup.md) (233)
- [sonic-bgp-global YANG](yang/sonic-bgp-global.md) (216)
- [サイトマップ](../_meta/sitemap.md) (122)
- [VoQ シャーシでの BGP 構成（iBGP フルメッシュ + addpath / multipath-relax）](../routing/bgp-setup-for-voq-chassis.md) (61)

### [bgpcfgd](#term-bgpcfgd)

- [bgpcfgd の dynamic BGP peer 動的変更（update.conf.j2 / delete.conf.j2）](../routing/bgpcfgd-dynamic-peer-modification-support.md) (19)
- [Reliable TSA（VoQ Chassis 全体での TSA を CHASSIS_APP_DB で同期）](../routing/reliable-tsa.md) (19)
- [内部実装](../topics/02-bgp/internals.md) (17)
- [FRR-BGP Unified Mgmt Framework（frrcfgd / OpenConfig BGP）](../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md) (16)
- [DEVICE_METADATA テーブル](config-db/device-metadata.md) (15)

### [Buffer Pool](#term-buffer-pool)

- [sonic-buffer-pool YANG](yang/sonic-buffer-pool.md) (6)
- [sai_query_stats_capability による Counter Capability 一括取得](../platform/query-stats-capability-new-sai-api-indroduction.md) (2)
- [ポートバッファドロップカウンタ（PORT_BUFFER_DROP FC group）](../acl-qos/port-buffer-drop-counters-in-sonic.md) (1)
- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (1)
- [QoS / Buffer の運用](../topics/08-qos-buffer/operations.md) (1)

### [Buffer Profile](#term-buffer-profile)

- [sonic-buffer-pg YANG](yang/sonic-buffer-pg.md) (1)
- [sonic-buffer-profile YANG](yang/sonic-buffer-profile.md) (1)
- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (1)

### [BUFFER_PG](#term-buffer-pg)

- [sonic-buffer-pg YANG](yang/sonic-buffer-pg.md) (16)
- [BUFFER_PG テーブル](config-db/buffer-pg.md) (10)
- [未使用ポートの予約バッファ回収（reclaim reserved buffer）シーケンス](../acl-qos/reclaim-reserved-buffer-sequence-flow.md) (8)
- [Reclaim Reserved Buffer（admin-down ポートの zero_profile）](../acl-qos/reclaim-reserved-buffer.md) (6)
- [QoS / Buffer の内部実装](../topics/08-qos-buffer/internals.md) (5)

### [CONFIG_DB](#term-config_db)

- [サイトマップ](../_meta/sitemap.md) (84)
- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (24)
- [multi-ASIC 用 Golden Config 単一 JSON フォーマット（localhost / asic0 / asic1 ...）](../platform/db-design-for-multi-asic-scenarios.md) (23)
- [show runningconfiguration / startupconfiguration サブコマンド](cli/show-running-config.md) (23)
- [ポートの動的 add / del（zero-port 起動と post-init 操作）](../acl-qos/enhancements-to-add-or-del-ports-dynamically.md) (22)

### [config_db.json](#term-config_db.json)

- [gNOI File.Remove と FactoryReset.Start（gNMI/UMF + DBUS host service）](../management/gnoi-hld-for-file-and-factory-reset-apis.md) (12)
- [CONFIG_DB の永続化が失敗する](runbooks/config-db-persistence-failure.md) (12)
- [multi-ASIC 用 Golden Config 単一 JSON フォーマット（localhost / asic0 / asic1 ...）](../platform/db-design-for-multi-asic-scenarios.md) (11)
- [reset-factory（keep-basic / keep-all-config / only-config）](../architecture/reset-factory-design.md) (9)
- [SONiC NOS の設定手段一覧（CLI / sonic-cfggen / config_db.json / RESTCONF / gNMI / ZTP](../management/sonic-nos-configuration-methods.md) (8)

### [config-setup](#term-config-setup)

- [config-setup サービス（first-boot config 生成 / 版間 migration）](../system/sonic-configuration-setup-service.md) (39)
- [reset-factory（keep-basic / keep-all-config / only-config）](../architecture/reset-factory-design.md) (25)
- [内部実装](../topics/01-overview/internals.md) (5)
- [HLD と実装の乖離 一覧（discrepancy-index）](verification/discrepancy-index.md) (4)
- [サイトマップ](../_meta/sitemap.md) (2)

### [COUNTERS_DB](#term-counters_db)

- [DHCP Relay per-interface counter（dhcpmon マルチスレッド + COUNTERS_DB 永続化）](../routing/dhcp-relay-per-interface-counter.md) (10)
- [ポート不正パケットドロップ設計（Interface MIB / L3 カウンタ拡張）](../architecture/port-illegal-packets-drop-design.md) (9)
- [バイト/パケットレートとポート使用率（RATES テーブル + EMA）](../internals/byte-packet-rates-port-utilization-in-sonic.md) (9)
- [flexcounter の queue/PG map 生成と watermark 有効化の整合](../acl-qos/align-watermark-flow-with-port-configuration-hld.md) (7)
- [概念](../topics/09-telemetry-snmp/concept.md) (7)

### [CoPP](#term-copp)

- [概念](../topics/07-acl-copp-mirror/concept.md) (21)
- [発展トピック](../topics/07-acl-copp-mirror/advanced.md) (20)
- [サイトマップ](../_meta/sitemap.md) (17)
- [DHCP DoS 緩和（ポート単位 DHCP レート制限・Linux TC ベース）](../acl-qos/dhcp-dos-mitigation-in-sonic.md) (15)
- [L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd / show](../internals/l3-scaling-and-performance-enhancements.md) (12)

### [CRM](#term-crm)

- [Generic SAI Extension テーブルの CRM（CRM_EXT_TABLE）](../system/generic-sai-extension-critical-resource-monitoring-crm.md) (43)
- [クリティカルリソースモニタリング (CRM) 要件](../system/critical-resource-monitoring.md) (32)
- [アーキテクチャ](../topics/09-telemetry-snmp/architecture.md) (17)
- [サイトマップ](../_meta/sitemap.md) (16)
- [sonic-crm YANG](yang/sonic-crm.md) (14)

### [ConsumerStateTable](#term-consumerstatetable)

- [ZMQ ProducerStateTable / ConsumerStateTable 設計](../internals/zmq-producer-consumer-state-table-design.md) (11)
- [ProducerStateTable の view switching（warm reboot 用の差分適用）](../switching/view-switching-in-producerstatetable.md) (4)
- [SWSS docker warm restart（state restore / consistency / sync up）](../system/sonic-swss-docker-warm-restart.md) (4)
- [swss-schema（APPL_DB / STATE_DB の中心スキーマ参照）](../internals/swss-schema.md) (3)
- [設定データフロー](../topics/01-overview/architecture.md) (3)

### [DASH](#term-dash)

- [SmartSwitch HA: HAMgrD（NPU 側 actor 分割と DPU 連携）](../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md) (69)
- [SONiC-DASH（Disaggregated APIs for SONiC Hosts）アーキテクチャ概観](../overlay/sonic-dash-hld.md) (54)
- [NPU-DPU DB と ENI ベース転送の内部構造](../topics/13-dash-smartswitch/internals.md) (46)
- [DPU の IP 割当・gNMI 連携・KVM 検証](../topics/13-dash-smartswitch/setup.md) (43)
- [DASH と SmartSwitch の考え方](../topics/13-dash-smartswitch/concept.md) (38)

### [DHCP Relay](#term-dhcp-relay)

- [サイトマップ](../_meta/sitemap.md) (6)
- [DHCP Relay per-interface counter（dhcpmon マルチスレッド + COUNTERS_DB 永続化）](../routing/dhcp-relay-per-interface-counter.md) (2)
- [NAT / DHCP Relay / Time-DNS Services](../topics/16-nat-dhcp-dns/index.md) (2)
- [変更履歴](../_meta/changelog.md) (1)
- [DHCP DoS 緩和（ポート単位 DHCP レート制限・Linux TC ベース）](../acl-qos/dhcp-dos-mitigation-in-sonic.md) (1)

### [DPU](#term-dpu)

- [HA / PMON / reboot / upgrade の運用](../topics/13-dash-smartswitch/operations.md) (107)
- [SmartSwitch HA: HAMgrD（NPU 側 actor 分割と DPU 連携）](../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md) (84)
- [DASH と SmartSwitch の考え方](../topics/13-dash-smartswitch/concept.md) (69)
- [SmartSwitch HA - DPU-Scope-DPU-Driven 構成](../architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md) (67)
- [DPU の IP 割当・gNMI 連携・KVM 検証](../topics/13-dash-smartswitch/setup.md) (66)

### [DPB](#term-dpb)

- [動的ポートブレイクアウト（DPB）既知問題と YANG モデル](../system/dynamic-port-breakout-known-issues.md) (22)
- [ビルド時間最適化（Dockerfile レイヤ削減 / BuildKit / 並列 dh / sairedis 分離）](../architecture/build-system-improvements.md) (11)
- [BREAKOUT_CFG テーブル](config-db/breakout-cfg.md) (5)
- [pmon 強化（PSU/FAN/syseeprom 周辺データ STATE_DB 集約）](../system/platform-monitor-enhancement-design.md) (3)
- [YANG モデル既知問題と検証](../system/yang-model-issues-and-validation.md) (3)

### [DPDK](#term-dpdk)

- [DASH SONiC KVM（BMv2 ベース仮想 DPU）](../overlay/dash-sonic-kvm.md) (2)

### [DSCP](#term-dscp)

- [Egress Outer DSCP 書換 ACL（UNDERLAY_SET_DSCP / METADATA + EGR_SET_DSCP）](../acl-qos/egress-outer-dscp-change-table.md) (56)
- [トンネルトラフィックの DSCP / TC リマップ（Dual-ToR PFC デッドロック回避）](../overlay/dscp-remapping-for-tunnel-traffic.md) (54)
- [sonic-dscp-tc-map YANG](yang/sonic-dscp-tc-map.md) (21)
- [Packet Trimming（symmetric / asymmetric DSCP / ACL disable）](../architecture/sonic-packet-trimming.md) (18)
- [サイトマップ](../_meta/sitemap.md) (17)

### [DWRR](#term-dwrr)

- [SCHEDULER テーブル](config-db/scheduler.md) (7)
- [サイトマップ](../_meta/sitemap.md) (4)
- [QoS Scheduler / Shaper（SP / WRR / DWRR + min/max bandwidth）](../acl-qos/sonic-qos-scheduler-and-shaping.md) (4)
- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (4)
- [QoS / Buffer の設定](../topics/08-qos-buffer/setup.md) (4)

### [ECMP](#term-ecmp)

- [サイトマップ](../_meta/sitemap.md) (35)
- [Fine Grained ECMP（FG_NHG / fgnhgorch）](../routing/sonic-fine-grained-ecmp.md) (28)
- [ECMP Family](../topics/04-vrf-ecmp/ecmp.md) (28)
- [L3 基盤と VRF](../topics/04-vrf-ecmp/concept.md) (23)
- [VoQ シャーシでの BGP 構成（iBGP フルメッシュ + addpath / multipath-relax）](../routing/bgp-setup-for-voq-chassis.md) (18)

### [ECN](#term-ecn)

- [WRED / ECN 統計（per-queue / per-port、capability ベース）](../acl-qos/wred-and-ecn-statistics.md) (38)
- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (11)
- [頻出 SAI 属性早見表](sai-attributes.md) (7)
- [QoS / Buffer の発展トピック](../topics/08-qos-buffer/advanced.md) (7)
- [QoS / Buffer の運用](../topics/08-qos-buffer/operations.md) (6)

### [ENI](#term-eni)

- [SmartSwitch ENI Based Forwarding（DashEniFwdOrch / ENI_REDIRECT ACL）](../overlay/smartswitch-eni-based-forwarding.md) (41)
- [DASH と SmartSwitch の考え方](../topics/13-dash-smartswitch/concept.md) (35)
- [NPU-DPU DB と ENI ベース転送の内部構造](../topics/13-dash-smartswitch/internals.md) (28)
- [SONiC-DASH（Disaggregated APIs for SONiC Hosts）アーキテクチャ概観](../overlay/sonic-dash-hld.md) (25)
- [sonic-passwh YANG](yang/sonic-passw-hardening.md) (16)

### [ETS](#term-ets)

- [ルータインタフェース (RIF) カウンタ](../routing/router-interface-counters-in-sonic.md) (20)
- [ポート不正パケットドロップ設計（Interface MIB / L3 カウンタ拡張）](../architecture/port-illegal-packets-drop-design.md) (13)
- [バイト/パケットレートとポート使用率（RATES テーブル + EMA）](../internals/byte-packet-rates-port-utilization-in-sonic.md) (10)
- [内部実装](../topics/09-telemetry-snmp/internals.md) (8)
- [WRED / ECN 統計（per-queue / per-port、capability ベース）](../acl-qos/wred-and-ecn-statistics.md) (7)

### [EVPN](#term-evpn)

- [EVPN VXLAN（FRR BGP-EVPN / VTEP / VRF / Type-2/Type-5）](../routing/evpn-vxlan-hld.md) (55)
- [VXLAN / VNET / EVPN の概要](../topics/03-vxlan-evpn/concept.md) (45)
- [EVPN VXLAN Multihoming（ESI / DF election / split-horizon）](../routing/evpn-vxlan-multihoming.md) (38)
- [サイトマップ](../_meta/sitemap.md) (32)
- [Overlay 発展トピック](../topics/03-vxlan-evpn/advanced.md) (23)

### [EVPN-MH](#term-evpn-mh)

- [EVPN VXLAN Multihoming（ESI / DF election / split-horizon）](../routing/evpn-vxlan-multihoming.md) (10)
- [EVPN VXLAN（FRR BGP-EVPN / VTEP / VRF / Type-2/Type-5）](../routing/evpn-vxlan-hld.md) (1)
- [Overlay 発展トピック](../topics/03-vxlan-evpn/advanced.md) (1)
- [内部実装](../topics/06-l2-vlan-lag/internals.md) (1)

### [Fast Reboot](#term-fast-reboot)

- [Warm-Reboot / Fast-Reboot 関連](../categories/reboot.md) (2)
- [Express Reboot（Cisco 8000 向けサブ秒データプレーン断のリブート）](../system/sonic-express-reboot-hld-spec.md) (1)

### [FDB](#term-fdb)

- [内部実装](../topics/06-l2-vlan-lag/internals.md) (37)
- [L2 Forwarding 強化（FDB flush / aging / static MAC / VLAN range）](../switching/layer-2-forwarding-enhancements.md) (32)
- [L2 運用確認](../topics/06-l2-vlan-lag/operations.md) (20)
- [頻出 SAI 属性早見表](sai-attributes.md) (14)
- [L2 のアーキテクチャ](../topics/06-l2-vlan-lag/architecture.md) (11)

### [fdbsyncd](#term-fdbsyncd)

- [内部実装](../topics/06-l2-vlan-lag/internals.md) (5)
- [EVPN VXLAN Multihoming（ESI / DF election / split-horizon）](../routing/evpn-vxlan-multihoming.md) (2)
- [ログレベルの永続化（LOGLEVEL_DB → CONFIG_DB.LOGGER への移行）](../system/persistent-log-level-hld.md) (2)
- [L2 運用確認](../topics/06-l2-vlan-lag/operations.md) (2)
- [内部実装](../topics/20-swss-sai-redis/internals.md) (2)

### [FLEX_COUNTER_DB](#term-flex_counter_db)

- [FEC FLR（Frame Loss Ratio）算出と予測（port_flr.lua / counterpoll port flr-interval-factor）](../platform/fec-flr-support-in-sonic.md) (5)
- [flexcounter の queue/PG map 生成と watermark 有効化の整合](../acl-qos/align-watermark-flow-with-port-configuration-hld.md) (4)
- [counterpoll 種別と watermark / queue / pg-drop マップの整合テストプラン](../acl-qos/test-plan-for-align-watermark-flow-with-port-configuration.md) (3)
- [Trap Flow Counter（Host I/F Trap 単位の Generic Counter 集計）](../architecture/sonic-trap-flow-counter-design.md) (2)
- [複数 Redis インスタンスのユーザ定義（database_config.json で DB を分散）](../internals/support-multiple-user-defined-redis-database-instances.md) (2)

### [FlexCounter](#term-flexcounter)

- [flexcounter の queue/PG map 生成と watermark 有効化の整合](../acl-qos/align-watermark-flow-with-port-configuration-hld.md) (19)
- [FlexCounter リファクタ（CounterContext テンプレート化）](../internals/sonic-flexcounter-refactor.md) (18)
- [sai_query_stats_capability による Counter Capability 一括取得](../platform/query-stats-capability-new-sai-api-indroduction.md) (9)
- [FEC FLR（Frame Loss Ratio）算出と予測（port_flr.lua / counterpoll port flr-interval-factor）](../platform/fec-flr-support-in-sonic.md) (8)
- [内部実装](../topics/09-telemetry-snmp/internals.md) (8)

### [FPGA](#term-fpga)

- [gRPC client（active-active DualToR / ycabled ↔ SoC 連携）](../management/design-doc.md) (3)
- [S3IP sysfs 仕様（platform 情報を /sys_switch/ で公開）](../platform/s3ip-sysfs-specification.md) (2)
- [fwutil（platform component firmware の install / update / show）](../platform/sonic-fw-utility.md) (2)
- [設定](../topics/14-platform-port-optics/setup.md) (2)
- [サイトマップ](../_meta/sitemap.md) (1)

### [FPM](#term-fpm)

- [概要](../topics/02-bgp/concept.md) (16)
- [fpmsyncd NextHop Group 拡張（dplane_fpm_nl / NEXTHOP_GROUP_TABLE）](../routing/fpmsyncd-nexthop-group-enhancement-high-level-design-document.md) (9)
- [内部実装](../topics/02-bgp/internals.md) (8)
- [概念](../topics/17-srv6-mpls/concept.md) (8)
- [経路は RIB にあるが FIB / ASIC に降りない](runbooks/route-not-installed-in-fib.md) (7)

### [fpmsyncd](#term-fpmsyncd)

- [fpmsyncd NextHop Group 拡張（dplane_fpm_nl / NEXTHOP_GROUP_TABLE）](../routing/fpmsyncd-nexthop-group-enhancement-high-level-design-document.md) (20)
- [BGP Route Install Error Handling（ERROR_ROUTE_TABLE / FIB-install pending）](../routing/bgp-route-install-error-handling.md) (15)
- [BGP PIC（Prefix Independent Convergence / NHG 階層）](../routing/bgp-prefix-independent-convergence-architecture-document.md) (14)
- [新 FRR-SONiC 通信チャネル（dplane_fpm_sonic モジュール）](../routing/new-frr-sonic-communication-channel.md) (13)
- [SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB）](../platform/hld-for-handling-sai-failures.md) (12)

### [FRR](#term-frr)

- [概要](../topics/02-bgp/concept.md) (51)
- [FRR-BGP Unified Mgmt Framework（frrcfgd / OpenConfig BGP）](../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md) (36)
- [サイトマップ](../_meta/sitemap.md) (35)
- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (22)
- [SRv6 Static SID/Locator 設定（CONFIG_DB → bgpcfgd → FRR）](../routing/static-configuration-of-srv6-in-sonic-hld.md) (22)

### [gNMI](#term-gnmi)

- [サイトマップ](../_meta/sitemap.md) (66)
- [gNMI / gNOI / OpenConfig 関連](../categories/gnmi-openconfig.md) (28)
- [概要](../topics/10-gnmi-openconfig/concept.md) (23)
- [DPU の IP 割当・gNMI 連携・KVM 検証](../topics/13-dash-smartswitch/setup.md) (23)
- [gNSI（Certz / Authz / Pathz / Credentialz）の Rotate モデル](../management/gnsi-hld.md) (21)

### [GCU](#term-gcu)

- [YANG モデルによる ConfigDB 更新検証（GCU + ConfigDBConnector デコレータ）](../management/sonic-config-update-validation-via-yang.md) (19)
- [Generic Config Update / Rollback（GCU・JSON Patch・checkpoint）](../architecture/sonic-generic-configuration-update-and-rollback.md) (10)
- [サイトマップ](../_meta/sitemap.md) (5)
- [概念と読み始め方](../topics/01-overview/concept.md) (5)
- [gNMI / gNOI / OpenConfig 関連](../categories/gnmi-openconfig.md) (4)

### [gNOI](#term-gnoi)

- [サイトマップ](../_meta/sitemap.md) (28)
- [Wake-on-LAN（wol CLI と SonicWolService gNOI）](../switching/wake-on-lan-in-sonic.md) (18)
- [SmartSwitch reboot 順序（NPU → 各 DPU の gNOI HALT → PCI detach → 個別 reboot）](../system/smart-switch-reboot-high-level-design.md) (18)
- [gNOI / gNSI](../topics/10-gnmi-openconfig/gnoi-gnsi.md) (17)
- [gNMI / gNOI / OpenConfig 関連](../categories/gnmi-openconfig.md) (16)

### [Graceful Restart](#term-graceful-restart)

- [Reboot 運用と障害調査](../topics/11-reboot/operations.md) (5)
- [BGP Graceful Restart のネゴシエーションに失敗する](runbooks/bgp-graceful-restart-failure.md) (4)
- [サイトマップ](../_meta/sitemap.md) (2)
- [Reboot / Upgrade の発展トピック](../topics/11-reboot/advanced.md) (2)
- [Reboot family の選び方](../topics/11-reboot/concept.md) (2)

### [HLD](#term-hld)

- [HLD と実装の乖離 一覧（discrepancy-index）](verification/discrepancy-index.md) (240)
- [サイトマップ](../_meta/sitemap.md) (36)
- [SSD ヘルスチェック（show platform ssdhealth + ssdutil プラグイン）](../architecture/ssdhealth-design.md) (34)
- [L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd / show](../internals/l3-scaling-and-performance-enhancements.md) (34)
- [BGP セッション向け BFD ハードウェアオフロード（bfdsyncd 経路）](../routing/bfd-hw-offload-for-bgp-session.md) (34)

### [Headroom](#term-headroom)

- [ACL & QoS](../acl-qos/index.md) (3)
- [サイトマップ](../_meta/sitemap.md) (2)
- [Dynamic Headroom Calculation（buffer_model = dynamic）](../acl-qos/dynamically-headroom-calculation.md) (2)
- [DEFAULT_LOSSLESS_BUFFER_PARAMETER テーブル](config-db/default-lossless-buffer-parameter.md) (2)
- [QoS / Buffer の発展トピック](../topics/08-qos-buffer/advanced.md) (1)

### [hostcfgd](#term-hostcfgd)

- [TACACS+ passkey 暗号化（key_encrypt + master key /etc/cipher_pass）](../management/tacacs-passkey-encryption.md) (32)
- [FEATURE テーブルによるオプショナル機能の有効/無効制御](../system/sonic-optional-feature-control-enhancement.md) (21)
- [config reload の event-driven 化（FEATURE.delayed + PortInitDone）](../management/config-reload-enhancement.md) (18)
- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (17)
- [SSH サーバ全体設定（SSH_SERVER.POLICIES）](../management/ssh-server-global-config-hld.md) (9)

### [HwSku](#term-hwsku)

- [設定](../topics/21-lab-vs-developer/setup.md) (2)

### [IFA](#term-ifa)

- [config vrf サブコマンド](cli/config-vrf.md) (2)
- [IP インタフェース ループバックアクション（同一 RIF 出戻りの drop/forward）](../architecture/sonic-ip-interface-loopback-action.md) (1)
- [FEC FLR 設定・運用（counterpoll / show interfaces counters fec-stats / portstat -f）](../platform/fec-flr-support-in-sonic-operations.md) (1)
- [FEC FLR（Frame Loss Ratio）算出と予測（port_flr.lua / counterpoll port flr-interval-factor）](../platform/fec-flr-support-in-sonic.md) (1)
- [Port FEC BER（Pre/Post FEC BER の算出と show fec-stat 拡張）](../platform/sonic-port-fec-ber.md) (1)

### [INT](#term-int)

- [sonic-vlan YANG](yang/sonic-vlan.md) (45)
- [IP インタフェース ループバックアクション（同一 RIF 出戻りの drop/forward）](../architecture/sonic-ip-interface-loopback-action.md) (43)
- [sonic-interface YANG](yang/sonic-interface.md) (43)
- [sonic-vlan-sub-interface YANG](yang/sonic-vlan-sub-interface.md) (37)
- [sonic-portchannel YANG](yang/sonic-portchannel.md) (31)

### [intfmgrd](#term-intfmgrd)

- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (9)
- [VRF VS テストプラン（vrfmgrd / intfmgrd / Orchagent → APP_DB / ASIC_DB / kernel）](../routing/vrf-vs-test-plan.md) (5)
- [IP / LAG / MTU の Incremental Update（portmgrd / intfmgrd / teammgrd 分担）](../switching/sonic-ip-lag-incremental-update.md) (5)
- [L3 基盤と VRF](../topics/04-vrf-ecmp/concept.md) (4)
- [サイトマップ](../_meta/sitemap.md) (3)

### [intfsyncd](#term-intfsyncd)

- [SWSS docker warm restart（state restore / consistency / sync up）](../system/sonic-swss-docker-warm-restart.md) (2)
- [swss-schema（APPL_DB / STATE_DB の中心スキーマ参照）](../internals/swss-schema.md) (1)
- [VOQ_INBAND_INTERFACE テーブル](config-db/voq-inband-interface.md) (1)

### [IPinIP](#term-ipinip)

- [Dual-ToR の考え方](../topics/05-dual-tor/concept.md) (9)
- [サイトマップ](../_meta/sitemap.md) (8)
- [VLAN Subnet Decap（Netscan 用 IPinIP MP2MP デカプスル）](../platform/subnet-decapsulation-with-sonic.md) (8)
- [トンネルトラフィックの DSCP / TC リマップ（Dual-ToR PFC デッドロック回避）](../overlay/dscp-remapping-for-tunnel-traffic.md) (7)
- [Active-Standby Dual ToR（y-cable + linkmgrd state machine + IPinIP tunnel）](../overlay/active-standby-dual-tor.md) (5)

### [LOGLEVEL_DB](#term-loglevel_db)

- [ログレベルの永続化（LOGLEVEL_DB → CONFIG_DB.LOGGER への移行）](../system/persistent-log-level-hld.md) (23)
- [サイトマップ](../_meta/sitemap.md) (2)
- [Multi-ASIC 名前空間の Redis（database_global.json と SonicDBConfig）](../internals/support-redis-databases-in-multiple-namespaces.md) (2)
- [複数 Redis インスタンスのユーザ定義（database_config.json で DB を分散）](../internals/support-multiple-user-defined-redis-database-instances.md) (1)
- [swss-common データベース設定（database_config.json）](../internals/swss-common-database-config.md) (1)

### [LACP](#term-lacp)

- [ICCPd 内部構成（MC-LAG / MLACP FSM ファイル別マップ）](../switching/brief-introduction-of-iccp-code.md) (24)
- [サイトマップ](../_meta/sitemap.md) (10)
- [PortChannel メンバーで LACP が確立しない](runbooks/portchannel-lacp-not-established.md) (10)
- [Warm-reboot 中の LACP retry count 拡張（LACP version 0xf1 / 新規 TLV）](../switching/increasing-lacp-pdu-timeout-during-warm-reboot.md) (10)
- [Reboot 運用と障害調査](../topics/11-reboot/operations.md) (9)

### [LAG](#term-lag)

- [分散 VOQ シャシでの LAG（SYSTEM_LAG_TABLE と system_lag_id）](../switching/lag-on-distributed-voq-system.md) (63)
- [sonic-mclag YANG](yang/sonic-mclag.md) (61)
- [サイトマップ](../_meta/sitemap.md) (53)
- [内部実装](../topics/06-l2-vlan-lag/internals.md) (50)
- [MCLAG Enhancements（dynamic config / unique IP / isolation group / static MAC）](../switching/mclag-enhancements.md) (35)

### [linkmgrd](#term-linkmgrd)

- [linkmgrd のデフォルトルート連動（DualToR mux 制御）](../routing/default-route.md) (26)
- [Active-Standby Dual ToR（y-cable + linkmgrd state machine + IPinIP tunnel）](../overlay/active-standby-dual-tor.md) (19)
- [Mux 制御の内部構造](../topics/05-dual-tor/internals.md) (19)
- [Dual-ToR の運用](../topics/05-dual-tor/operations.md) (17)
- [Active-Active Dual ToR（gRPC ベース cable control + prefix-based neighbor）](../overlay/active-active-dual-tor.md) (14)

### [LLDP](#term-lldp)

- [sonic-lldp YANG](yang/sonic-lldp.md) (35)
- [LLDP / LLDP_PORT テーブル](config-db/lldp.md) (21)
- [サイトマップ](../_meta/sitemap.md) (15)
- [LLDP_PORT テーブル](config-db/lldp-port.md) (15)
- [show lldp サブコマンド](cli/show-lldp.md) (7)

### [MPLS](#term-mpls)

- [概念](../topics/17-srv6-mpls/concept.md) (51)
- [MPLS TC → TC map（MPLS パケットの QoS classification）](../routing/mpls-tc-to-tc-map.md) (45)
- [SONiC の MPLS 基盤（per-RIF MPLS / LABEL_ROUTE_TABLE / 静的 LSP）](../routing/mpls-for-sonic-high-level-design-document.md) (37)
- [内部実装](../topics/17-srv6-mpls/internals.md) (25)
- [設定](../topics/17-srv6-mpls/setup.md) (23)

### [MCLAG](#term-mclag)

- [sonic-mclag YANG](yang/sonic-mclag.md) (61)
- [config mclag サブコマンド](cli/config-mclag.md) (28)
- [MCLAG Enhancements（dynamic config / unique IP / isolation group / static MAC）](../switching/mclag-enhancements.md) (27)
- [MCLAG_DOMAIN / MCLAG_INTERFACE / MCLAG_UNIQUE_IP テーブル](config-db/mclag-domain.md) (20)
- [サイトマップ](../_meta/sitemap.md) (13)

### [minigraph.xml](#term-minigraph.xml)

- [CONFIG_DB save / load が反映されない](runbooks/config-save-load.md) (7)
- [minigraph 適用後に reload が完了しない / 起動が固まる](runbooks/minigraph-reload-stuck.md) (7)
- [SYSTEM_DEFAULTS テーブルによる SONiC 既定値の集約](../switching/control-sonic-behaviors-with-system-defaults-table.md) (5)
- [sonic-cfggen コマンド](cli/sonic-cfggen.md) (4)
- [SONiC User Manual の位置づけと SONiC CLI / 運用フローの全体像](../management/sonic-user-manual.md) (3)

### [MMU](#term-mmu)

- [sonic-route-map YANG](yang/sonic-route-map.md) (24)
- [SNMP テーブル](config-db/snmp.md) (11)
- [COMMUNITY_SET テーブル](config-db/community-set.md) (10)
- [SNMP TABLE スキーマ提案（SNMP / SNMP_COMMUNITY / SNMP_USER）](../system/sonic-snmp-table-schema-proposal.md) (10)
- [config snmp / snmpagentaddress / snmptrap サブコマンド](cli/config-snmp.md) (9)

### [MUX](#term-mux)

- [Active-Standby Dual ToR（y-cable + linkmgrd state machine + IPinIP tunnel）](../overlay/active-standby-dual-tor.md) (46)
- [sonic-mux-cable YANG](yang/sonic-mux-cable.md) (31)
- [Active-Standby Dual ToR 設定と運用（CONFIG_DB / CLI / トラブルシューティング）](../overlay/active-standby-dual-tor-operations.md) (22)
- [MUX_LINKMGR テーブル](config-db/mux-linkmgr.md) (21)
- [Dual-ToR の設定](../topics/05-dual-tor/setup.md) (20)

### [NAT](#term-nat)

- [sonic-nat YANG](yang/sonic-nat.md) (85)
- [内部実装](../topics/16-nat-dhcp-dns/internals.md) (58)
- [NAT in SONiC（natsyncd / NatOrch / iptables ↔ SAI）](../architecture/nat-in-sonic.md) (55)
- [NAT_GLOBAL / NAT_POOL テーブル](config-db/nat.md) (53)
- [config nat サブコマンド](cli/config-nat.md) (41)

### [natmgrd / natsyncd](#term-natmgrd-natsyncd)

- [NAT in SONiC（natsyncd / NatOrch / iptables ↔ SAI）](../architecture/nat-in-sonic.md) (1)
- [運用](../topics/16-nat-dhcp-dns/operations.md) (1)

### [neighsyncd](#term-neighsyncd)

- [WARM_RESTART テーブル](config-db/warm-restart.md) (9)
- [ARP / Neighbor エントリが古い IP-MAC を保持し続ける](runbooks/arp-entry-stuck.md) (6)
- [Reboot / warm restart の設定](../topics/11-reboot/setup.md) (6)
- [config warm_restart サブコマンド](cli/config-warm_restart.md) (5)
- [sonic-warm-restart YANG](yang/sonic-warm-restart.md) (5)

### [Netlink](#term-netlink)

- [新 FRR-SONiC 通信チャネル（dplane_fpm_sonic モジュール）](../routing/new-frr-sonic-communication-channel.md) (5)
- [ARP / Neighbor エントリが古い IP-MAC を保持し続ける](runbooks/arp-entry-stuck.md) (2)
- [BGP / EVPN 関連](../categories/bgp-evpn.md) (1)
- [経路は RIB にあるが FIB / ASIC に降りない](runbooks/route-not-installed-in-fib.md) (1)
- [アーキテクチャ](../topics/02-bgp/architecture.md) (1)

### [Next Hop Group](#term-next-hop-group)

- [L3 基盤と VRF](../topics/04-vrf-ecmp/concept.md) (5)
- [P4Orch（PINS の P4Runtime 用 orchagent / 同期書き込み）](../internals/p4-orchagent.md) (1)
- [発展トピックへの橋渡し](../topics/04-vrf-ecmp/advanced.md) (1)

### [NDP](#term-ndp)

- [SRv6 uSID（srv6orch の uN/uA/uDT/uDX 拡張）](../routing/sonic-usid.md) (20)
- [VNET の Local Endpoint Forwarding（DPU 直結 nexthop の最適化）](../overlay/vnet-local-endpoint-forwarding.md) (8)
- [Active-Standby Dual ToR（y-cable + linkmgrd state machine + IPinIP tunnel）](../overlay/active-standby-dual-tor.md) (3)
- [clear (sonic-clear) コマンド](cli/clear.md) (3)
- [Dataplane Telemetry（DTel / INT / Postcard / Drop / Queue Report）](../system/dataplane-telemetry-in-sonic.md) (2)

### [NPU](#term-npu)

- [SmartSwitch reboot 順序（NPU → 各 DPU の gNOI HALT → PCI detach → 個別 reboot）](../system/smart-switch-reboot-high-level-design.md) (45)
- [DASH と SmartSwitch の考え方](../topics/13-dash-smartswitch/concept.md) (38)
- [DPU の IP 割当・gNMI 連携・KVM 検証](../topics/13-dash-smartswitch/setup.md) (24)
- [サイトマップ](../_meta/sitemap.md) (23)
- [NPU-DPU DB と ENI ベース転送の内部構造](../topics/13-dash-smartswitch/internals.md) (22)

### [orchagent](#term-orchagent)

- [SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB）](../platform/hld-for-handling-sai-failures.md) (29)
- [dump utility（モジュール単位で複数 DB から関連 key を集約する debug CLI）](../internals/dump-utility-for-easy-debugging.md) (23)
- [サイトマップ](../_meta/sitemap.md) (22)
- [運用](../topics/20-swss-sai-redis/operations.md) (22)
- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (19)

### [PFC](#term-pfc)

- [サイトマップ](../_meta/sitemap.md) (37)
- [PFC 履歴統計（PFCWD lua スクリプトによる estimate と --history CLI）](../acl-qos/pfc-historical-statistics.md) (36)
- [Asymmetric PFC テストプラン（PTF + sonic-mgmt fixtures）](../acl-qos/asymmetric-pfc-test-plan.md) (31)
- [QoS / Buffer の運用](../topics/08-qos-buffer/operations.md) (31)
- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (26)

### [PFC Watchdog](#term-pfc-watchdog)

- [PFC_WD テーブル](config-db/pfc-wd.md) (2)
- [サイトマップ](../_meta/sitemap.md) (1)
- [Bulk Counter（sai_bulk_object_get_stats / chunk size）](../architecture/sonic-bulk-counter-design.md) (1)
- [ACL_TABLE テーブル](config-db/acl-table.md) (1)
- [PFC で帯域が出ない / Buffer overflow](runbooks/pfc-bandwidth.md) (1)

### [PG (Priority Group)](#term-pg)

- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (1)

### [portmgrd](#term-portmgrd)

- [DHCP DoS 緩和（ポート単位 DHCP レート制限・Linux TC ベース）](../acl-qos/dhcp-dos-mitigation-in-sonic.md) (13)
- [IP / LAG / MTU の Incremental Update（portmgrd / intfmgrd / teammgrd 分担）](../switching/sonic-ip-lag-incremental-update.md) (8)
- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (5)
- [ポートの動的 add / del（zero-port 起動と post-init 操作）](../acl-qos/enhancements-to-add-or-del-ports-dynamically.md) (4)
- [ポート Auto-Negotiation（advertised-speeds / interface-type）](../architecture/sonic-port-auto-negotiation-design.md) (4)

### [portsyncd](#term-portsyncd)

- [ポートの動的 add / del（zero-port 起動と post-init 操作）](../acl-qos/enhancements-to-add-or-del-ports-dynamically.md) (17)
- [動的ポート add/del 概念（zero-port 起動と post-init モデル）](../acl-qos/enhancements-to-add-or-del-ports-dynamically-concepts.md) (8)
- [config reload の event-driven 化（FEATURE.delayed + PortInitDone）](../management/config-reload-enhancement.md) (8)
- [内部実装](../topics/06-l2-vlan-lag/internals.md) (7)
- [動的ポート add/del 制限事項と HLD との乖離（ref counter 未取り込み・race 残存）](../acl-qos/enhancements-to-add-or-del-ports-dynamically-limitations.md) (5)

### [port_config.ini](#term-port-config-ini)

- [port_config.ini パーサ統合（portconfig.py 一元化）](../architecture/sonic-port-configuration-refactor-design.md) (18)
- [SONiC ポート命名規則の変更案（et[sX]pY[abcd]）](../platform/sonic-port-naming-convention-change.md) (16)
- [PMON の Multi-ASIC 対応（global DB と per-ASIC namespace の役割分担）](../system/platform-monitor-design-for-multi-asic-platforms.md) (10)
- [VOQ シャシでの recirculation port サポート（Inb / Rec ポートロール）](../platform/recirculation-port-support-on-voq-chassis.md) (6)
- [概要](../topics/14-platform-port-optics/concept.md) (4)

### [PINS](#term-pins)

- [サイトマップ](../_meta/sitemap.md) (20)
- [設定](../topics/18-p4-pins/setup.md) (17)
- [発展トピック](../topics/18-p4-pins/advanced.md) (16)
- [概念](../topics/18-p4-pins/concept.md) (15)
- [P4 / PINS / Programmable Pipeline](../topics/18-p4-pins/index.md) (8)

### [ProducerStateTable](#term-producerstatetable)

- [ZMQ ProducerStateTable / ConsumerStateTable 設計](../internals/zmq-producer-consumer-state-table-design.md) (11)
- [発展トピック](../topics/20-swss-sai-redis/advanced.md) (10)
- [ProducerStateTable の view switching（warm reboot 用の差分適用）](../switching/view-switching-in-producerstatetable.md) (6)
- [アーキテクチャ](../topics/20-swss-sai-redis/architecture.md) (6)
- [サイトマップ](../_meta/sitemap.md) (5)

### [PortChannel](#term-portchannel)

- [L2 設定パターン](../topics/06-l2-vlan-lag/setup.md) (32)
- [IP / LAG / MTU の Incremental Update（portmgrd / intfmgrd / teammgrd 分担）](../switching/sonic-ip-lag-incremental-update.md) (23)
- [Switchport モード（access / trunk / routed）と VLAN CLI 拡張](../switching/switch-port-modes-and-vlan-cli-enhancement.md) (23)
- [PortChannel (LAG) の OpenConfig YANG サポート（REST / gNMI）](../switching/openconfig-support-for-portchannel-aggregate-interface.md) (21)
- [L2 運用確認](../topics/06-l2-vlan-lag/operations.md) (21)

### [Policer](#term-policer)

- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (5)
- [BUM ストームコントロール（PORT_STORM_CONTROL）](../switching/sonic-bum-storm-control.md) (4)
- [内部実装](../topics/07-acl-copp-mirror/internals.md) (3)
- [POLICER テーブル](config-db/policer.md) (2)
- [PORT_STORM_CONTROL テーブル](config-db/port-storm-control.md) (2)

### [Policing](#term-policing)

- [サイトマップ](../_meta/sitemap.md) (2)
- [COPP_GROUP テーブル](config-db/copp-group.md) (1)
- [sonic-copp YANG](yang/sonic-copp.md) (1)
- [概念](../topics/07-acl-copp-mirror/concept.md) (1)
- [概念](../topics/15-security-aaa/concept.md) (1)

### [QoS](#term-qos)

- [サイトマップ](../_meta/sitemap.md) (33)
- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (14)
- [config qos サブコマンド](cli/config-qos.md) (11)
- [MPLS TC → TC map（MPLS パケットの QoS classification）](../routing/mpls-tc-to-tc-map.md) (9)
- [QoS Scheduler / Shaper（SP / WRR / DWRR + min/max bandwidth）](../acl-qos/sonic-qos-scheduler-and-shaping.md) (8)

### [RoCE](#term-roce)

- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (3)
- [QoS / Buffer の設定](../topics/08-qos-buffer/setup.md) (3)
- [ACL_RULE テーブル](config-db/acl-rule.md) (1)
- [PFC_PRIORITY_TO_PRIORITY_GROUP_MAP テーブル](config-db/pfc-priority-to-priority-group-map.md) (1)
- [PFC で帯域が出ない / Buffer overflow](runbooks/pfc-bandwidth.md) (1)

### [Redis](#term-redis)

- [Redis Client Manager（RCM: connection pool / transactional client）](../management/redis-client-manager-rcm-hld.md) (39)
- [サイトマップ](../_meta/sitemap.md) (28)
- [VOQ カウンタ集約（chassis supervisor からの aggregate 表示）](../internals/aggregate-voq-counters-in-sonic.md) (20)
- [設定](../topics/20-swss-sai-redis/setup.md) (19)
- [ZMQ ProducerStateTable / ConsumerStateTable 設計](../internals/zmq-producer-consumer-state-table-design.md) (15)

### [RIF](#term-rif)

- [ルータインタフェース (RIF) カウンタ](../routing/router-interface-counters-in-sonic.md) (46)
- [バイト/パケットレートとポート使用率（RATES テーブル + EMA）](../internals/byte-packet-rates-port-utilization-in-sonic.md) (34)
- [ポート不正パケットドロップ設計（Interface MIB / L3 カウンタ拡張）](../architecture/port-illegal-packets-drop-design.md) (29)
- [Route / Interface / Counter の確認](../topics/04-vrf-ecmp/operations.md) (20)
- [DIP=SIP PTF 検証テスト](../architecture/dip-sip-ptf-validation-high-level-design.md) (17)

### [ROUTE_TABLE](#term-route_table)

- [BGP Route Install Error Handling（ERROR_ROUTE_TABLE / FIB-install pending）](../routing/bgp-route-install-error-handling.md) (21)
- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../architecture/error-handling-framework-in-sonic.md) (12)
- [内部実装](../topics/04-vrf-ecmp/internals.md) (10)
- [NEXT_HOP_GROUP_TABLE による APP_DB ルートとネクストホップ分離](../routing/routing-and-next-hop-table-enhancement.md) (9)
- [内部実装](../topics/02-bgp/internals.md) (8)

### [SNMP](#term-snmp)

- [sonic-snmp YANG](yang/sonic-snmp.md) (73)
- [SNMP TABLE スキーマ提案（SNMP / SNMP_COMMUNITY / SNMP_USER）](../system/sonic-snmp-table-schema-proposal.md) (65)
- [config snmp / snmpagentaddress / snmptrap サブコマンド](cli/config-snmp.md) (48)
- [サイトマップ](../_meta/sitemap.md) (42)
- [SNMP テーブル](config-db/snmp.md) (36)

### [SRv6](#term-srv6)

- [概念](../topics/17-srv6-mpls/concept.md) (47)
- [発展トピック](../topics/17-srv6-mpls/advanced.md) (46)
- [SRv6 VPN（L3VPN over SRv6 と SRv6 Policy）](../routing/srv6-vpn-hld.md) (31)
- [サイトマップ](../_meta/sitemap.md) (28)
- [SRv6 uSID（srv6orch の uN/uA/uDT/uDX 拡張）](../routing/sonic-usid.md) (20)

### [SAI](#term-sai)

- [頻出 SAI 属性早見表](sai-attributes.md) (241)
- [サイトマップ](../_meta/sitemap.md) (84)
- [SAI API バージョン整合チェック（sai_query_api_version + ビルド時検査）](../platform/sai-api-version-check.md) (65)
- [SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB）](../platform/hld-for-handling-sai-failures.md) (52)
- [内部実装](../topics/20-swss-sai-redis/internals.md) (49)

### [SerDes](#term-serdes)

- [1.6T Ethernet 対応（200G SerDes / SFF-8024 / xcvrd / PortsOrch）](../platform/1-6t-support-in-sonic.md) (6)
- [Media-based Port Settings（media_settings.json による SerDes プロファイル）](../platform/media-based-port-settings-in-sonic.md) (6)
- [サイトマップ](../_meta/sitemap.md) (5)
- [プラットフォーム](../platform/index.md) (2)
- [頻出 SAI 属性早見表](sai-attributes.md) (2)

### [sFlow Agent](#term-sflow-agent)

- [設定](../topics/09-telemetry-snmp/setup.md) (1)

### [sonic-buildimage](#term-sonic-buildimage)

- [Fast-reboot Flow Improvements（finalizer / reconciliation）](../system/fast-reboot-flow-improvements-hld.md) (90)
- [ビルド時間最適化（Dockerfile レイヤ削減 / BuildKit / 並列 dh / sairedis 分離）](../architecture/build-system-improvements.md) (78)
- [FRR-BGP Unified Mgmt Framework（frrcfgd / OpenConfig BGP）](../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md) (52)
- [dump utility（モジュール単位で複数 DB から関連 key を集約する debug CLI）](../internals/dump-utility-for-easy-debugging.md) (51)
- [Critical Resource Monitoring（CRM・SAI 表枯渇のしきい値監視）](../system/critical-resource-monitoring-in-sonic.md) (33)

### [sonic-cfggen](#term-sonic-cfggen)

- [sonic-cfggen コマンド](cli/sonic-cfggen.md) (13)
- [ビルド時間最適化（Dockerfile レイヤ削減 / BuildKit / 並列 dh / sairedis 分離）](../architecture/build-system-improvements.md) (9)
- [show runningconfiguration / startupconfiguration サブコマンド](cli/show-running-config.md) (7)
- [DEVICE_RUNTIME_METADATA テーブル](config-db/device-runtime-metadata.md) (7)
- [SONiC NOS の設定手段一覧（CLI / sonic-cfggen / config_db.json / RESTCONF / gNMI / ZTP](../management/sonic-nos-configuration-methods.md) (6)

### [sonic-mgmt](#term-sonic-mgmt)

- [sonic-mgmt_interface YANG](yang/sonic-mgmt_interface.md) (20)
- [sonic-mgmt_port YANG](yang/sonic-mgmt_port.md) (19)
- [DIP=SIP PTF 検証テスト](../architecture/dip-sip-ptf-validation-high-level-design.md) (18)
- [サイトマップ](../_meta/sitemap.md) (17)
- [sonic-mgmt_vrf YANG](yang/sonic-mgmt_vrf.md) (13)

### [sonic-swss](#term-sonic-swss)

- [ポートの動的 add / del（zero-port 起動と post-init 操作）](../acl-qos/enhancements-to-add-or-del-ports-dynamically.md) (19)
- [swss-schema（APPL_DB / STATE_DB の中心スキーマ参照）](../internals/swss-schema.md) (18)
- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../architecture/error-handling-framework-in-sonic.md) (17)
- [SmartSwitch HA: HAMgrD（NPU 側 actor 分割と DPU 連携）](../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md) (17)
- [サイトマップ](../_meta/sitemap.md) (15)

### [sonic-swss-common](#term-sonic-swss-common)

- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../architecture/error-handling-framework-in-sonic.md) (9)
- [SWSS docker の Warm Restart 実装メモ（開発時リファレンス）](../system/swss-docker-warm-restart-code-reference.md) (8)
- [Debug Framework（コンポーネント dump 登録 / assert 拡張）](../architecture/debug-framework-in-sonic.md) (7)
- [SmartSwitch HA: HAMgrD（NPU 側 actor 分割と DPU 連携）](../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md) (7)
- [Error Handling Framework 制限事項と HLD との乖離（コア機構未実装 / CRM 代替）](../architecture/error-handling-framework-in-sonic-limitations.md) (5)

### [sonic-sairedis](#term-sonic-sairedis)

- [SAI API バージョン整合チェック（sai_query_api_version + ビルド時検査）](../platform/sai-api-version-check.md) (15)
- [NPU MDIO アクセスと gbsyncd 単一 docker 化](../platform/sonic-npu-mdio-access-support-and-gbsyncd-docker-enhancement-hld.md) (8)
- [libsairedis API idempotence（warm restart 用 OID キャッシュと duplicate 抑止）](../system/sonic-libsairedis-api-idempotence-support.md) (8)
- [Bulk Counter（sai_bulk_object_get_stats / chunk size）](../architecture/sonic-bulk-counter-design.md) (7)
- [Warm Reboot 開発フェーズと OID 復元戦略（idempotent libsairedis vs syncd view comparison）](../system/what-are-the-development-phases-and-scope-for-warm-reboot.md) (5)

### [sonic-utilities](#term-sonic-utilities)

- [config bgp サブコマンド](cli/config-bgp.md) (12)
- [FEC FLR（Frame Loss Ratio）算出と予測（port_flr.lua / counterpoll port flr-interval-factor）](../platform/fec-flr-support-in-sonic.md) (11)
- [サイトマップ](../_meta/sitemap.md) (10)
- [TACACS+ passkey 暗号化（key_encrypt + master key /etc/cipher_pass）](../management/tacacs-passkey-encryption.md) (10)
- [Switchport モード（access / trunk / routed）と VLAN CLI 拡張](../switching/switch-port-modes-and-vlan-cli-enhancement.md) (10)

### [Scheduler](#term-scheduler)

- [QoS Scheduler / Shaper（SP / WRR / DWRR + min/max bandwidth）](../acl-qos/sonic-qos-scheduler-and-shaping.md) (5)
- [サイトマップ](../_meta/sitemap.md) (2)
- [ACL & QoS](../acl-qos/index.md) (2)
- [sonic-queue YANG](yang/sonic-queue.md) (2)
- [sonic-scheduler YANG](yang/sonic-scheduler.md) (2)

### [Shaper](#term-shaper)

- [QoS Scheduler / Shaper（SP / WRR / DWRR + min/max bandwidth）](../acl-qos/sonic-qos-scheduler-and-shaping.md) (3)
- [サイトマップ](../_meta/sitemap.md) (2)
- [ACL & QoS](../acl-qos/index.md) (2)

### [Shaping](#term-shaping)

- [QoS Scheduler / Shaper（SP / WRR / DWRR + min/max bandwidth）](../acl-qos/sonic-qos-scheduler-and-shaping.md) (1)
- [WRED / ECN 統計（per-queue / per-port、capability ベース）](../acl-qos/wred-and-ecn-statistics.md) (1)
- [QoS / Buffer の発展トピック](../topics/08-qos-buffer/advanced.md) (1)

### [SmartNIC](#term-smartnic)

- [DASH と SmartSwitch の考え方](../topics/13-dash-smartswitch/concept.md) (4)
- [DASH 関連](../categories/dash.md) (1)
- [横断カテゴリ](../categories/index.md) (1)
- [SmartSwitch 関連](../categories/smartswitch.md) (1)
- [Overlay 設定](../topics/03-vxlan-evpn/setup.md) (1)

### [SmartSwitch](#term-smartswitch)

- [サイトマップ](../_meta/sitemap.md) (43)
- [DASH と SmartSwitch の考え方](../topics/13-dash-smartswitch/concept.md) (22)
- [SmartSwitch 関連](../categories/smartswitch.md) (16)
- [gNOI 連携と他章との境界](../topics/13-dash-smartswitch/advanced.md) (13)
- [HA / PMON / reboot / upgrade の運用](../topics/13-dash-smartswitch/operations.md) (13)

### [STATE_DB](#term-state_db)

- [SmartSwitch gNMI フィードバック（DPU APPL_STATE_DB と version_id）](../management/smart-switch-gnmi-feedback-design-omit-in-toc.md) (27)
- [サイトマップ](../_meta/sitemap.md) (20)
- [液冷漏洩検出（LiquidCoolingBase + thermalctld + system-health gNMI イベント）](../platform/liquid-cooling-leakage-detection-in-sonic.md) (18)
- [P4RT アプリケーション（PINS の gRPC サービス、port 9559）](../management/p4rt-application-hld.md) (17)
- [FIPS 向け MACsec SAI POST（FIPS_MACSEC_POST_TABLE）](../switching/sonic-sai-post-support-for-macsec.md) (17)

### [swssconfig](#term-swssconfig)

- [ACL の基本設計（ACL_TABLE / ACL_RULE スキーマ）](../acl-qos/acl-support-in-sonic.md) (11)
- [VLAN Subnet Decap（Netscan 用 IPinIP MP2MP デカプスル）](../platform/subnet-decapsulation-with-sonic.md) (7)
- [DPU の IP 割当・gNMI 連携・KVM 検証](../topics/13-dash-smartswitch/setup.md) (5)
- [ACL in SONiC（テーブル型 / マッチ・アクション / SWSS パイプライン）](../acl-qos/acl-in-sonic.md) (3)
- [L2 Forwarding 強化（FDB flush / aging / static MAC / VLAN range）](../switching/layer-2-forwarding-enhancements.md) (2)

### [syncd](#term-syncd)

- [運用](../topics/20-swss-sai-redis/operations.md) (43)
- [NPU MDIO アクセスと gbsyncd 単一 docker 化](../platform/sonic-npu-mdio-access-support-and-gbsyncd-docker-enhancement-hld.md) (38)
- [サイトマップ](../_meta/sitemap.md) (36)
- [内部実装](../topics/20-swss-sai-redis/internals.md) (36)
- [SAI 失敗時の dump 取得（syncd_dump.sh / SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP）](../platform/dump-on-sai-failure.md) (28)

### [Syslog](#term-syslog)

- [sonic-syslog YANG](yang/sonic-syslog.md) (5)
- [SYSLOG_SERVER テーブル](config-db/syslog-server.md) (4)
- [サイトマップ](../_meta/sitemap.md) (3)
- [システム](../system/index.md) (2)
- [概念](../topics/09-telemetry-snmp/concept.md) (2)

### [TAM](#term-tam)

- [Path Tracing Midpoint（IPv6 HbH-PT に MCD を追記）](../routing/path-tracing-midpoint.md) (3)
- [内部実装](../topics/17-srv6-mpls/internals.md) (3)
- [運用](../topics/17-srv6-mpls/operations.md) (2)
- [PFC 履歴統計（PFCWD lua スクリプトによる estimate と --history CLI）](../acl-qos/pfc-historical-statistics.md) (1)
- [頻出 SAI 属性早見表](sai-attributes.md) (1)

### [TC (Traffic Class)](#term-tc)

- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (1)

### [TCAM](#term-tcam)

- [ACL in SONiC（テーブル型 / マッチ・アクション / SWSS パイプライン）](../acl-qos/acl-in-sonic.md) (5)
- [発展トピック](../topics/07-acl-copp-mirror/advanced.md) (5)
- [クリティカルリソースモニタリング (CRM) 要件](../system/critical-resource-monitoring.md) (4)
- [概念](../topics/07-acl-copp-mirror/concept.md) (3)
- [発展トピック](../topics/16-nat-dhcp-dns/advanced.md) (3)

### [ToS](#term-tos)

- [SmartSwitch HA - DPU-Scope-DPU-Driven 構成](../architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md) (7)
- [BGP Loading Optimization（fpmsyncd flush / orchagent ring buffer / async sairedis）](../routing/bgp-loading-optimization-for-sonic.md) (3)

### [tunnelmgrd](#term-tunnelmgrd)

- [TUNNEL テーブル](config-db/tunnel.md) (3)
- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (2)
- [PEER_SWITCH テーブル](config-db/peer-switch.md) (1)
- [SUBNET_DECAP テーブル](config-db/subnet-decap.md) (1)
- [TUNNEL_DECAP_TABLE (APPL_DB)](config-db/tunnel-decap-table.md) (1)

### [VOQ](#term-voq)

- [概念](../topics/12-multi-asic-voq/concept.md) (37)
- [サイトマップ](../_meta/sitemap.md) (32)
- [発展トピック](../topics/12-multi-asic-voq/advanced.md) (25)
- [VOQ カウンタ集約（chassis supervisor からの aggregate 表示）](../internals/aggregate-voq-counters-in-sonic.md) (24)
- [VOQ_INBAND_INTERFACE テーブル](config-db/voq-inband-interface.md) (20)

### [VS](#term-vs)

- [内部実装](../topics/21-lab-vs-developer/internals.md) (40)
- [概念](../topics/21-lab-vs-developer/concept.md) (26)
- [発展トピック](../topics/21-lab-vs-developer/advanced.md) (16)
- [運用](../topics/21-lab-vs-developer/operations.md) (16)
- [SONiC-VS のビルドと libvirt 起動手順](../architecture/steps-to-bring-up-sonic-vs.md) (15)

### [VLAN](#term-vlan)

- [sonic-vlan YANG](yang/sonic-vlan.md) (114)
- [Switchport モード（access / trunk / routed）と VLAN CLI 拡張](../switching/switch-port-modes-and-vlan-cli-enhancement.md) (78)
- [サイトマップ](../_meta/sitemap.md) (55)
- [sonic-spanning-tree YANG](yang/sonic-spanning-tree.md) (55)
- [L2 設定パターン](../topics/06-l2-vlan-lag/setup.md) (55)

### [vlanmgrd](#term-vlanmgrd)

- [VLAN メンバーを追加してもタグが付かない](runbooks/vlan-tagging.md) (6)
- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (5)
- [VLAN_MEMBER テーブル](config-db/vlan-member.md) (4)
- [VLAN テーブル](config-db/vlan.md) (4)
- [内部実装](../topics/06-l2-vlan-lag/internals.md) (4)

### [VNET](#term-vnet)

- [sonic-vnet YANG](yang/sonic-vnet.md) (86)
- [VXLAN / VNET / EVPN の概要](../topics/03-vxlan-evpn/concept.md) (47)
- [VNET / VNET_ROUTE テーブル](config-db/vnet.md) (40)
- [VXLAN / VNet 全体設計（VxlanOrch / VnetOrch / VRF mapper）](../overlay/vxlan-sonic.md) (26)
- [config vnet サブコマンド](cli/config-vnet.md) (25)

### [VRF](#term-vrf)

- [L3 基盤と VRF](../topics/04-vrf-ecmp/concept.md) (86)
- [サイトマップ](../_meta/sitemap.md) (51)
- [config vrf サブコマンド](cli/config-vrf.md) (48)
- [VRF Ansible テストプラン（T0 上で BGP/ACL/loopback/warm-reboot 含む E2E 検証）](../routing/vrf-feature-ansible-test-plan-omit-in-toc.md) (45)
- [Management VRF 設計（201911 release / l3mdev + cgroups）](../routing/sonic-management-vrf-design-document-201911-release.md) (42)

### [vrfmgrd](#term-vrfmgrd)

- [VRF VS テストプラン（vrfmgrd / intfmgrd / Orchagent → APP_DB / ASIC_DB / kernel）](../routing/vrf-vs-test-plan.md) (10)
- [VRF サポート（vrfmgrd / vrforch / FRR vrf-aware）](../routing/sonic-vrf-support-design-spec-draft.md) (6)
- [サイトマップ](../_meta/sitemap.md) (5)
- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (5)
- [VRF テーブル](config-db/vrf.md) (5)

### [VXLAN](#term-vxlan)

- [sonic-vxlan YANG](yang/sonic-vxlan.md) (59)
- [VXLAN / VNet 全体設計（VxlanOrch / VnetOrch / VRF mapper）](../overlay/vxlan-sonic.md) (55)
- [EVPN VXLAN（FRR BGP-EVPN / VTEP / VRF / Type-2/Type-5）](../routing/evpn-vxlan-hld.md) (44)
- [サイトマップ](../_meta/sitemap.md) (41)
- [VXLAN / VNET / EVPN の概要](../topics/03-vxlan-evpn/concept.md) (33)

### [vxlanmgrd](#term-vxlanmgrd)

- [CONFIG_DB ↔ orchagent クラス対応表](config-db-orch-map.md) (5)
- [Overlay 運用](../topics/03-vxlan-evpn/operations.md) (4)
- [config vxlan サブコマンド](cli/config-vxlan.md) (3)
- [VXLAN / VNET / EVPN の概要](../topics/03-vxlan-evpn/concept.md) (3)
- [VNET / VNET_ROUTE テーブル](config-db/vnet.md) (2)

### [Warm Reboot](#term-warm-reboot)

- [サイトマップ](../_meta/sitemap.md) (6)
- [Warm-Reboot / Fast-Reboot 関連](../categories/reboot.md) (3)
- [Warm path の内部構造](../topics/11-reboot/architecture.md) (3)
- [システム](../system/index.md) (2)
- [Express Reboot（Cisco 8000 向けサブ秒データプレーン断のリブート）](../system/sonic-express-reboot-hld-spec.md) (2)

### [WRED](#term-wred)

- [WRED / ECN 統計（per-queue / per-port、capability ベース）](../acl-qos/wred-and-ecn-statistics.md) (51)
- [sonic-wred-profile YANG](yang/sonic-wred-profile.md) (47)
- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (20)
- [QUEUE テーブル](config-db/queue.md) (14)
- [sonic-queue YANG](yang/sonic-queue.md) (13)

### [WRR](#term-wrr)

- [SCHEDULER テーブル](config-db/scheduler.md) (15)
- [サイトマップ](../_meta/sitemap.md) (8)
- [QoS Scheduler / Shaper（SP / WRR / DWRR + min/max bandwidth）](../acl-qos/sonic-qos-scheduler-and-shaping.md) (8)
- [ACL & QoS](../acl-qos/index.md) (6)
- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (4)

### [YANG](#term-yang)

- [サイトマップ](../_meta/sitemap.md) (232)
- [gNMI / gNOI / OpenConfig 関連](../categories/gnmi-openconfig.md) (52)
- [概要](../topics/10-gnmi-openconfig/concept.md) (35)
- [OpenConfig Interfaces YANG（Ethernet 設定の REST/gNMI 対応と sonic-mgmt-common transformer）](../management/openconfig-support-for-ethernet-interfaces.md) (27)
- [SONiC YANG モデル記述ガイドライン（ABNF.json → sonic-*.yang）](../management/sonic-yang-model-guidelines.md) (26)

### [zebra](#term-zebra)

- [fpmsyncd NextHop Group 拡張（dplane_fpm_nl / NEXTHOP_GROUP_TABLE）](../routing/fpmsyncd-nexthop-group-enhancement-high-level-design-document.md) (31)
- [debug / undebug コマンド群](cli/debug-group.md) (25)
- [経路は RIB にあるが FIB / ASIC に降りない](runbooks/route-not-installed-in-fib.md) (12)
- [新 FRR-SONiC 通信チャネル（dplane_fpm_sonic モジュール）](../routing/new-frr-sonic-communication-channel.md) (12)
- [BGP Suppress FIB Pending（dplane_fpm_nl + RTM_F_OFFLOAD）](../routing/bgp-suppress-announcements-of-routes-not-installed-in-hw.md) (10)

### [ZTP](#term-ztp)

- [Zero Touch Provisioning（ZTP・DHCP option / plugin / state machine）](../system/zero-touch-provisioning-ztp.md) (23)
- [SONiC NOS の設定手段一覧（CLI / sonic-cfggen / config_db.json / RESTCONF / gNMI / ZTP](../management/sonic-nos-configuration-methods.md) (7)
- [ビルドプロファイル（rules/profiles/*.mk）](../architecture/build-profiles.md) (6)
- [config-setup サービス（first-boot config 生成 / 版間 migration）](../system/sonic-configuration-setup-service.md) (6)
- [サイトマップ](../_meta/sitemap.md) (5)

<!-- /glossary-xref -->
