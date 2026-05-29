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
- **関連**: [QoS](#term-qos)、[Buffer Pool](#term-buffer-pool)

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
- **関連**: [NPU](#term-npu)

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
- **関連**: [Buffer Pool](#term-buffer-pool)、[Buffer Model](#term-buffer-model)

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
- **関連**: [port_config.ini](#term-port-config-ini)

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

### Scheduler {#term-scheduler}

- **略称**: Scheduler
- **日本語訳**: スケジューラ
- **説明**: 各 Egress Queue から送出するパケットの順序とレートを決定するアルゴリズム実体。SONiC では `SCHEDULER` テーブル (`type` = `STRICT` / `DWRR` / `WRR`、`weight`、`meter_type`、`pir`/`cir`) で定義し、`QUEUE` テーブルから参照する。`qosorch` が SAI Scheduler オブジェクトに変換する。
- **関連**: [Strict Priority](#term-strict-priority)、[DWRR](#term-dwrr)、[WRR](#term-wrr)、[Shaper](#term-shaper)

### Shaper {#term-shaper}

- **略称**: Shaper
- **日本語訳**: シェイパー
- **説明**: 送信レートに上限を設けて超過分をキューイングし、均された速度で送出する QoS 機構。SONiC では `SCHEDULER` テーブルの `pir` / `meter_type` で表現し、SAI Scheduler の `max_bandwidth_*` 属性として実装される。
- **関連**: [Shaping](#term-shaping)、[Scheduler](#term-scheduler)

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
- **関連**: [DPU](#term-dpu)、[MUX](#term-mux)

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
- **説明**: Linux ベースのオープンソース NOS。本ドキュメントが対象とするコミュニティ版 master ブランチ。詳細は [プロジェクトトップ](../index.md) を参照。


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
- **関連**: [ACL](#term-acl)、[CRM](#term-crm)

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
- **関連**: [Policer](#term-policer)、[Shaper](#term-shaper)

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
- **関連**: [sonic-mgmt](#term-sonic-mgmt)

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

- [AAA テーブル](config-db/aaa.md) (50)
- [sonic-system-aaa YANG](yang/sonic-system-aaa.md) (24)
- [AAA Improvements（PAM / NSS / D-Bus / RBAC 多重ロール）](../management/aaa-improvements.md) (23)
- [TACPLUS_SERVER テーブル](config-db/tacplus-server.md) (22)
- [RADIUS テーブル](config-db/radius.md) (20)

### [ACL](#term-acl)

- [APPL_DB ACL テーブル群](config-db/appl-acl.md) (249)
- [ACL_TABLE テーブル](config-db/acl-table.md) (246)
- [ACL_RULE テーブル](config-db/acl-rule.md) (226)
- [ACL_TABLE_TYPE テーブル](config-db/acl-table-type.md) (168)
- [ACL orchagent STATE_DB テーブル](config-db/aclorch-state.md) (159)

### [AQM](#term-aqm)

- [QoS / Buffer の発展トピック](../topics/08-qos-buffer/advanced.md) (1)
- [発展トピック](../topics/12-multi-asic-voq/advanced.md) (1)

### [APPL_DB](#term-appl_db)

- [APPL_DB PORT_TABLE](config-db/appl-port-table.md) (76)
- [APPL_DB ACL テーブル群](config-db/appl-acl.md) (73)
- [APPL_DB LAG_TABLE (portchannel ステータス)](config-db/portchannel-status.md) (66)
- [サイトマップ](../_meta/sitemap.md) (59)
- [FABRIC_MONITOR テーブル](config-db/fabric-monitor.md) (54)

### [ARP](#term-arp)

- [L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd / show](../internals/l3-scaling-and-performance-enhancements.md) (35)
- [ACL_RULE テーブル](config-db/acl-rule.md) (16)
- [NEIGH テーブル](config-db/neigh.md) (15)
- [Active-Standby Dual ToR（y-cable + linkmgrd state machine + IPinIP tunnel）](../overlay/active-standby-dual-tor.md) (13)
- [VLAN_INTERFACE テーブル](config-db/vlan-interface.md) (13)

### [ASIC_DB](#term-asic_db)

- [DSCP_TO_PG_MAP テーブル（非実在）](config-db/dscp-to-pg-map.md) (15)
- [APPL_DB BFD_SESSION_TABLE (bfdorch)](config-db/bfd-orch.md) (13)
- [BFD_SESSION_TABLE (STATE_DB)](config-db/bfd-state.md) (13)
- [ERROR_DB テーブル (ERROR_ROUTE_TABLE / ERROR_NEIGH_TABLE)](config-db/errordb.md) (13)
- [VRRP テーブル](config-db/vrrp.md) (13)

### [ASIC SDK](#term-asic-sdk)

- [FDB Aging Time (SWITCH_TABLE.fdb_aging_time)](config-db/fdb-aging.md) (3)
- [DEVICE_METADATA テーブル](config-db/device-metadata.md) (2)
- [SUPPRESS_ASIC_SDK_HEALTH_EVENT テーブル](config-db/suppress-asic-sdk-health-event.md) (2)
- [L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd / show](../internals/l3-scaling-and-performance-enhancements.md) (1)
- [P4Runtime PacketIO（generic netlink + send_to_ingress）](../management/packetio.md) (1)

### [AsterNOS](#term-asternos)

- [このドキュメントについて](../about.md) (2)
- [SAG（Static Anycast Gateway）for SONiC](../architecture/sag-high-level-design-for-sonic.md) (1)
- [ALARM テーブル (EVENT_DB)](config-db/alarm-table.md) (1)

### [ASIC](#term-asic)

- [SUPPRESS_ASIC_SDK_HEALTH_EVENT テーブル](config-db/suppress-asic-sdk-health-event.md) (112)
- [サイトマップ](../_meta/sitemap.md) (99)
- [CHASSIS_STATE_DB テーブル群](config-db/chassis-state.md) (65)
- [概念](../topics/12-multi-asic-voq/concept.md) (63)
- [DEVICE_METADATA テーブル](config-db/device-metadata.md) (54)

### [BFD](#term-bfd)

- [BFD_SESSION_TABLE (STATE_DB)](config-db/bfd-state.md) (164)
- [APPL_DB BFD_SESSION_TABLE (bfdorch)](config-db/bfd-orch.md) (155)
- [BFD_SESSION テーブル](config-db/bfd-session.md) (155)
- [BGP セッション向け BFD ハードウェアオフロード（bfdsyncd 経路）](../routing/bfd-hw-offload-for-bgp-session.md) (77)
- [BFD ハードウェアオフロード（BfdOrch / BFD_SESSION）](../routing/bfd-hw-offload.md) (75)

### [BGP](#term-bgp)

- [sonic-bgp-neighbor YANG](yang/sonic-bgp-neighbor.md) (245)
- [sonic-bgp-peergroup YANG](yang/sonic-bgp-peergroup.md) (233)
- [sonic-bgp-global YANG](yang/sonic-bgp-global.md) (216)
- [STATE_DB BGP 関連テーブル](config-db/state-bgp.md) (169)
- [BGP_PEER_GROUP テーブル](config-db/bgp-peer-group.md) (139)

### [bgpcfgd](#term-bgpcfgd)

- [DEVICE_METADATA テーブル](config-db/device-metadata.md) (83)
- [BGP_AGGREGATE_ADDRESS テーブル](config-db/bgp-aggregate-address.md) (74)
- [BGP_NEIGHBOR テーブル](config-db/bgp-neighbor.md) (67)
- [STATIC_ROUTE テーブル](config-db/static-route.md) (60)
- [BGP_ALLOWED_PREFIXES テーブル](config-db/bgp-allowed-prefixes.md) (52)

### [Buffer Model](#term-buffer-model)

- [COUNTERS_DB バッファ / ウォーターマーク カウンタ](config-db/counter-buffer.md) (2)

### [Buffer Pool](#term-buffer-pool)

- [COUNTERS_DB バッファ / ウォーターマーク カウンタ](config-db/counter-buffer.md) (25)
- [sonic-buffer-pool YANG](yang/sonic-buffer-pool.md) (6)
- [sai_query_stats_capability による Counter Capability 一括取得](../platform/query-stats-capability-new-sai-api-indroduction.md) (2)
- [ポートバッファドロップカウンタ（PORT_BUFFER_DROP FC group）](../acl-qos/port-buffer-drop-counters-in-sonic.md) (1)
- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (1)

### [Buffer Profile](#term-buffer-profile)

- [COUNTERS_DB バッファ / ウォーターマーク カウンタ](config-db/counter-buffer.md) (2)
- [sonic-buffer-pg YANG](yang/sonic-buffer-pg.md) (1)
- [sonic-buffer-profile YANG](yang/sonic-buffer-profile.md) (1)
- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (1)

### [BUFFER_PG](#term-buffer-pg)

- [BUFFER_PG テーブル](config-db/buffer-pg.md) (60)
- [FLEX_COUNTER_TABLE — PG_WATERMARK エントリ](config-db/pg-watermark.md) (29)
- [APPL_DB BUFFER_* テーブル群](config-db/appl-buffer.md) (26)
- [CABLE_LENGTH テーブル](config-db/cable-length.md) (21)
- [sonic-buffer-pg YANG](yang/sonic-buffer-pg.md) (16)

### [CONFIG_DB](#term-config_db)

- [サイトマップ](../_meta/sitemap.md) (129)
- [APPL_DB FIXED_MIRROR_SESSION_TABLE (P4RT)](config-db/appl-mirror.md) (58)
- [IPv6 Link-local モード](config-db/ipv6-link-local.md) (54)
- [APPL_DB PORT_TABLE](config-db/appl-port-table.md) (50)
- [PASS_THROUGH_ROUTE_TABLE テーブル（ChassisOrch）](config-db/chassis-orch.md) (50)

### [config_db.json](#term-config_db.json)

- [CONFIG_DB の永続化が失敗する](runbooks/config-db-persistence-failure.md) (12)
- [gNOI File.Remove と FactoryReset.Start（gNMI/UMF + DBUS host service）](../management/gnoi-hld-for-file-and-factory-reset-apis.md) (11)
- [multi-ASIC 用 Golden Config 単一 JSON フォーマット（localhost / asic0 / asic1 ...）](../platform/db-design-for-multi-asic-scenarios.md) (11)
- [reset-factory（keep-basic / keep-all-config / only-config）](../architecture/reset-factory-design.md) (9)
- [SONiC NOS の設定手段一覧（CLI / sonic-cfggen / config_db.json / RESTCONF / gNMI / ZTP](../management/sonic-nos-configuration-methods.md) (8)

### [config-setup](#term-config-setup)

- [config-setup サービス（first-boot config 生成 / 版間 migration）](../system/sonic-configuration-setup-service.md) (39)
- [reset-factory（keep-basic / keep-all-config / only-config）](../architecture/reset-factory-design.md) (25)
- [FEATURE テーブル](config-db/feature.md) (11)
- [BANNER_MESSAGE テーブル](config-db/banner-message.md) (8)
- [内部実装](../topics/01-overview/internals.md) (5)

### [COUNTERS_DB](#term-counters_db)

- [COUNTERS_DB NAT カウンタテーブル群](config-db/nat-counters.md) (45)
- [COUNTERS_DB QUEUE カウンタ](config-db/queue-counter.md) (41)
- [PFC_WD 状態フィールド (COUNTERS_DB)](config-db/pfcwd-state.md) (38)
- [COUNTERS_DB RIF カウンタ](config-db/counters-rif.md) (37)
- [COUNTERS_DB PORT カウンタ](config-db/counters-port.md) (35)

### [CoPP](#term-copp)

- [概念](../topics/07-acl-copp-mirror/concept.md) (21)
- [発展トピック](../topics/07-acl-copp-mirror/advanced.md) (20)
- [サイトマップ](../_meta/sitemap.md) (19)
- [DHCP DoS 緩和（ポート単位 DHCP レート制限・Linux TC ベース）](../acl-qos/dhcp-dos-mitigation-in-sonic.md) (15)
- [L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd / show](../internals/l3-scaling-and-performance-enhancements.md) (12)

### [CRM](#term-crm)

- [CRM テーブル](config-db/crm.md) (150)
- [Generic SAI Extension テーブルの CRM（CRM_EXT_TABLE）](../system/generic-sai-extension-critical-resource-monitoring-crm.md) (43)
- [クリティカルリソースモニタリング (CRM) 要件](../system/critical-resource-monitoring.md) (35)
- [ROUTE_TABLE (APPL_DB)](config-db/app-route.md) (29)
- [DASH_ACL_* テーブル](config-db/dash-acl.md) (25)

### [ConsumerStateTable](#term-consumerstatetable)

- [ZMQ 関連 CONFIG_DB フィールド (DEVICE_METADATA / DPU)](config-db/zmq.md) (16)
- [DPU Orchagent 設定 (DEVICE_METADATA — DPU 固有フィールド)](config-db/dpu-orch.md) (13)
- [ZMQ ProducerStateTable / ConsumerStateTable 設計](../internals/zmq-producer-consumer-state-table-design.md) (11)
- [APPL_DB BUFFER_* テーブル群](config-db/appl-buffer.md) (10)
- [LABEL_ROUTE_TABLE (APPL_DB)](config-db/appl-mpls-route.md) (10)

### [CBF](#term-cbf)

- [NEXTHOP_GROUP_TABLE / CLASS_BASED_NEXT_HOP_GROUP_TABLE](config-db/nhg-table.md) (37)
- [CLASS_BASED_NEXT_HOP_GROUP テーブル](config-db/cbf-nhg.md) (33)
- [NEXTHOP_GROUP / CBF_NHG / NHG_MAP テーブル](config-db/nhg-orch.md) (16)
- [クラスベース転送 (CBF) — DSCP/EXP→FC マップと CLASS_BASED_NEXT_HOP_GROUP](../routing/class-based-forwarding-enhancement.md) (11)
- [EXP_TO_FC_MAP テーブル](config-db/exp-to-fc-map.md) (7)

### [DASH](#term-dash)

- [DASH_ROUTING_* テーブル](config-db/dash-routing.md) (164)
- [DASH_ROUTE_* テーブル](config-db/dash-routing-table.md) (149)
- [DASH_VNET テーブル](config-db/dash-vnet.md) (143)
- [DASH_ACL_* テーブル](config-db/dash-acl.md) (127)
- [DASH_ENI_TABLE テーブル](config-db/dash-eni.md) (116)

### [DHCP Relay](#term-dhcp-relay)

- [サイトマップ](../_meta/sitemap.md) (6)
- [DHCPv4 Relay Agent（dhcpmon / dhcrelay / option-82 / circuit-id）](../architecture/dhcpv4-relay-agent.md) (2)
- [DHCP Relay per-interface counter（dhcpmon マルチスレッド + COUNTERS_DB 永続化）](../routing/dhcp-relay-per-interface-counter.md) (2)
- [Security / AAA / FIPS / Hardening](../topics/15-security-aaa/index.md) (2)
- [NAT / DHCP Relay / Time-DNS Services](../topics/16-nat-dhcp-dns/index.md) (2)

### [DPU](#term-dpu)

- [DPU / ENI / VDPU / REMOTE_DPU テーブル](config-db/dpu-eni.md) (193)
- [SmartSwitch DPU テーブル群](config-db/smart-switch-dpu.md) (186)
- [DPU テーブル](config-db/dpu.md) (174)
- [HA / PMON / reboot / upgrade の運用](../topics/13-dash-smartswitch/operations.md) (107)
- [サイトマップ](../_meta/sitemap.md) (94)

### [DPB](#term-dpb)

- [動的ポートブレイクアウト（DPB）既知問題と YANG モデル](../system/dynamic-port-breakout-known-issues.md) (22)
- [BREAKOUT_CFG テーブル](config-db/breakout-cfg.md) (20)
- [BREAKOUT_CFG テーブル (DPB)](config-db/dpb.md) (14)
- [ビルド時間最適化（Dockerfile レイヤ削減 / BuildKit / 並列 dh / sairedis 分離）](../architecture/build-system-improvements.md) (8)
- [サイトマップ](../_meta/sitemap.md) (5)

### [DPDK](#term-dpdk)

- [DASH SONiC KVM（BMv2 ベース仮想 DPU）](../overlay/dash-sonic-kvm.md) (2)

### [DSCP](#term-dscp)

- [TC_TO_DSCP_MAP テーブル](config-db/tc-to-dscp-map.md) (99)
- [DSCP_TO_PG_MAP テーブル（非実在）](config-db/dscp-to-pg-map.md) (92)
- [DSCP_TO_TC_MAP テーブル](config-db/dscp-to-tc-map.md) (86)
- [DSCP_TO_FC_MAP テーブル](config-db/dscp-to-fc-map.md) (63)
- [SWITCH_TRIMMING テーブル](config-db/switch-trimming.md) (59)

### [DWRR](#term-dwrr)

- [SCHEDULER テーブル](config-db/scheduler.md) (19)
- [SCHEDULER — QosOrch SchedulerOrch コード由来デフォルト詳解](config-db/scheduler-orch.md) (11)
- [サイトマップ](../_meta/sitemap.md) (4)
- [QoS Scheduler / Shaper（SP / WRR / DWRR + min/max bandwidth）](../acl-qos/sonic-qos-scheduler-and-shaping.md) (4)
- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (4)

### [DEVICE_METADATA](#term-device_metadata)

- [sonic-device_metadata YANG](yang/sonic-device_metadata.md) (63)
- [DEVICE_METADATA テーブル](config-db/device-metadata.md) (62)
- [cluster フィールド (DEVICE_METADATA / DEVICE_NEIGHBOR_METADATA)](config-db/cluster.md) (37)
- [BGP_INTERNAL_NEIGHBOR テーブル](config-db/bgp-internal-neighbor.md) (29)
- [ZMQ 関連 CONFIG_DB フィールド (DEVICE_METADATA / DPU)](config-db/zmq.md) (28)

### [dot1x](#term-dot1x)

- [DOT1X / PAC テーブル](config-db/dot1x.md) (36)
- [Port Access Control（PAC: 802.1x / MAB / RADIUS）](../acl-qos/port-access-control-in-sonic.md) (6)
- [変更履歴](../_meta/changelog.md) (1)
- [サイトマップ](../_meta/sitemap.md) (1)

### [ECMP](#term-ecmp)

- [SWITCH_HASH テーブル](config-db/switch-hash.md) (39)
- [サイトマップ](../_meta/sitemap.md) (37)
- [NEXTHOP_GROUP_TABLE (APPL_DB)](config-db/nhg.md) (37)
- [ROUTE_TABLE (APPL_DB)](config-db/app-route.md) (34)
- [NEXTHOP_GROUP_TABLE / CLASS_BASED_NEXT_HOP_GROUP_TABLE](config-db/nhg-table.md) (34)

### [ECN](#term-ecn)

- [QUEUE_COUNTER_CAPABILITIES (STATE_DB)](config-db/queue-state.md) (77)
- [WRED_PROFILE テーブル](config-db/wred-profile.md) (50)
- [WRED / ECN 統計（per-queue / per-port、capability ベース）](../acl-qos/wred-and-ecn-statistics.md) (38)
- [COUNTERS_DB QUEUE カウンタ](config-db/queue-counter.md) (34)
- [STATE_DB カウンタ能力テーブル](config-db/counters-state.md) (33)

### [ENI](#term-eni)

- [DASH_ENI_TABLE テーブル](config-db/dash-eni.md) (158)
- [[COUNTERS_DB] DPU カウンタ (ENI / DASH_METER) テーブル](config-db/dpu-counter.md) (151)
- [DPU / ENI / VDPU / REMOTE_DPU テーブル](config-db/dpu-eni.md) (107)
- [DASH_ROUTING_* テーブル](config-db/dash-routing.md) (51)
- [SmartSwitch ENI Based Forwarding（DashEniFwdOrch / ENI_REDIRECT ACL）](../overlay/smartswitch-eni-based-forwarding.md) (41)

### [ETS](#term-ets)

- [COUNTERS_DB PORT カウンタ](config-db/counters-port.md) (44)
- [COUNTERS_DB キュー / PG カウンタテーブル群](config-db/counters-queue.md) (36)
- [[COUNTERS_DB] FLEX_COUNTER 個別カウンタフィールド](config-db/counters-flex.md) (29)
- [COUNTERS_DB QUEUE カウンタ](config-db/queue-counter.md) (20)
- [ルータインタフェース (RIF) カウンタ](../routing/router-interface-counters-in-sonic.md) (20)

### [EVPN](#term-evpn)

- [EVPN DIP トンネル (動的生成)](config-db/vxlan-evpn-tunnel.md) (95)
- [VXLAN_EVPN_NVO テーブル](config-db/vxlan-evpn-nvo.md) (66)
- [EVPN VXLAN（FRR BGP-EVPN / VTEP / VRF / Type-2/Type-5）](../routing/evpn-vxlan-hld.md) (58)
- [VXLAN トンネルポート (Port::TUNNEL)](config-db/tunnel-port.md) (56)
- [サイトマップ](../_meta/sitemap.md) (50)

### [EVPN-MH](#term-evpn-mh)

- [EVPN VXLAN Multihoming 概念（ESI / DF election / Split-horizon / Aliasing）](../routing/evpn-vxlan-multihoming-concepts.md) (11)
- [EVPN VXLAN Multihoming 運用（config interface evpn-esi / show vxlan ethernet-segment / 差分）](../routing/evpn-vxlan-multihoming-operations.md) (5)
- [EVPN VXLAN Multihoming（概要ハブ）](../routing/evpn-vxlan-multihoming.md) (3)
- [HLD と実装の乖離 一覧（discrepancy-index）](verification/discrepancy-index.md) (2)
- [EVPN VXLAN（FRR BGP-EVPN / VTEP / VRF / Type-2/Type-5）](../routing/evpn-vxlan-hld.md) (1)

### [EXP](#term-exp)

- [EXP_TO_FC_MAP テーブル](config-db/exp-to-fc-map.md) (84)
- [Express Reboot（Cisco 8000 向けサブ秒データプレーン断のリブート）](../system/sonic-express-reboot-hld-spec.md) (14)
- [COMMUNITY_SET テーブル](config-db/community-set.md) (10)
- [MPLS TC → TC map（MPLS パケットの QoS classification）](../routing/mpls-tc-to-tc-map.md) (9)
- [DSCP_TO_FC_MAP テーブル](config-db/dscp-to-fc-map.md) (8)

### [Fast Reboot](#term-fast-reboot)

- [Warm-Reboot / Fast-Reboot 関連](../categories/reboot.md) (2)
- [Express Reboot（Cisco 8000 向けサブ秒データプレーン断のリブート）](../system/sonic-express-reboot-hld-spec.md) (1)

### [FDB](#term-fdb)

- [APPL_DB FDB_TABLE](config-db/appl-fdb.md) (170)
- [FDB テーブル](config-db/fdb.md) (147)
- [VXLAN_FDB_TABLE テーブル](config-db/vxlan-fdb.md) (110)
- [STATE_DB orchagent 共通テーブル](config-db/orchagent-state.md) (54)
- [内部実装](../topics/06-l2-vlan-lag/internals.md) (38)

### [fdbsyncd](#term-fdbsyncd)

- [VXLAN_FDB_TABLE テーブル](config-db/vxlan-fdb.md) (38)
- [EVPN DIP トンネル (動的生成)](config-db/vxlan-evpn-tunnel.md) (10)
- [APPL_DB FDB_TABLE](config-db/appl-fdb.md) (8)
- [EVPN VXLAN 内部実装（FRR → fpmsyncd → APPL_DB → orchagent → SAI）](../routing/evpn-vxlan-hld-internals.md) (6)
- [EVPN VXLAN Multihoming 実装内部（EvpnMhOrch / L2nhgOrch / ShlOrch / SAI L2 NHG）](../routing/evpn-vxlan-multihoming-internals.md) (6)

### [FLEX_COUNTER_DB](#term-flex_counter_db)

- [FLEX_COUNTER_DB — ランタイム状態フィールド](config-db/state-flex-counter.md) (49)
- [[COUNTERS_DB] FLEX_COUNTER 個別カウンタフィールド](config-db/counters-flex.md) (40)
- [[COUNTERS_DB] DPU カウンタ (ENI / DASH_METER) テーブル](config-db/dpu-counter.md) (28)
- [COUNTERS_DB PortChannel/LAG カウンタ](config-db/counters-portchannel.md) (19)
- [COUNTERS_DB QUEUE カウンタ](config-db/queue-counter.md) (17)

### [FlexCounter](#term-flexcounter)

- [FLEX_COUNTER_DB — ランタイム状態フィールド](config-db/state-flex-counter.md) (90)
- [COUNTERS_DB RIF カウンタ](config-db/counters-rif.md) (73)
- [COUNTERS_DB PortChannel/LAG カウンタ](config-db/counters-portchannel.md) (65)
- [COUNTERS_DB QUEUE カウンタ](config-db/queue-counter.md) (59)
- [COUNTERS_DB キュー / PG カウンタテーブル群](config-db/counters-queue.md) (57)

### [FPGA](#term-fpga)

- [gRPC client（active-active DualToR / ycabled ↔ SoC 連携）](../management/design-doc.md) (3)
- [S3IP sysfs 仕様（platform 情報を /sys_switch/ で公開）](../platform/s3ip-sysfs-specification.md) (2)
- [fwutil（platform component firmware の install / update / show）](../platform/sonic-fw-utility.md) (2)
- [設定](../topics/14-platform-port-optics/setup.md) (2)
- [サイトマップ](../_meta/sitemap.md) (1)

### [FPM](#term-fpm)

- [ROUTE_TABLE handler 分岐 (fpmsyncd / RouteSync)](config-db/route-handler.md) (35)
- [概要](../topics/02-bgp/concept.md) (16)
- [fpmsyncd NextHop Group 拡張（dplane_fpm_nl / NEXTHOP_GROUP_TABLE）](../routing/fpmsyncd-nexthop-group-enhancement-high-level-design-document.md) (9)
- [内部実装](../topics/02-bgp/internals.md) (8)
- [概念](../topics/17-srv6-mpls/concept.md) (8)

### [fpmsyncd](#term-fpmsyncd)

- [APPL_STATE_DB ROUTE_TABLE (route offload cache)](config-db/route-cache.md) (87)
- [ROUTE_TABLE handler 分岐 (fpmsyncd / RouteSync)](config-db/route-handler.md) (78)
- [DEVICE_METADATA テーブル](config-db/device-metadata.md) (57)
- [STATE_DB BGP 関連テーブル](config-db/state-bgp.md) (41)
- [ROUTE_TABLE (STATE_DB / APPL_STATE_DB)](config-db/route-state.md) (37)

### [FRR](#term-frr)

- [COMMUNITY_SET テーブル](config-db/community-set.md) (87)
- [BGP_GLOBALS_AF テーブル](config-db/bgp-globals-af.md) (65)
- [ROUTE_MAP テーブル](config-db/route-map.md) (63)
- [BGP_AGGREGATE_ADDRESS テーブル](config-db/bgp-aggregate-address.md) (58)
- [PREFIX_SET テーブル](config-db/prefix-set.md) (58)

### [Forwarding Database](#term-forwarding-database)

- [サイトマップ](../_meta/sitemap.md) (2)
- [show mac サブコマンド](cli/show-mac.md) (1)
- [FDB Aging Time (SWITCH_TABLE.fdb_aging_time)](config-db/fdb-aging.md) (1)

### [gNMI](#term-gnmi)

- [サイトマップ](../_meta/sitemap.md) (74)
- [gNMI / gNOI / OpenConfig 関連](../categories/gnmi-openconfig.md) (28)
- [GNMI / GNMI_CLIENT_CERT テーブル](config-db/gnmi.md) (24)
- [TELEMETRY テーブル](config-db/telemetry.md) (23)
- [概要](../topics/10-gnmi-openconfig/concept.md) (23)

### [GCU](#term-gcu)

- [YANG モデルによる ConfigDB 更新検証（GCU + ConfigDBConnector デコレータ）](../management/sonic-config-update-validation-via-yang.md) (19)
- [Generic Config Update / Rollback（GCU・JSON Patch・checkpoint）](../architecture/sonic-generic-configuration-update-and-rollback.md) (8)
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

- [BGP Graceful Restart のネゴシエーションに失敗する](runbooks/bgp-graceful-restart-failure.md) (4)
- [Reboot 運用と障害調査](../topics/11-reboot/operations.md) (4)
- [サイトマップ](../_meta/sitemap.md) (2)
- [Reboot / Upgrade の発展トピック](../topics/11-reboot/advanced.md) (2)
- [Reboot family の選び方](../topics/11-reboot/concept.md) (2)

### [HLD](#term-hld)

- [HLD と実装の乖離 一覧（discrepancy-index）](verification/discrepancy-index.md) (318)
- [ERROR_DB テーブル (ERROR_ROUTE_TABLE / ERROR_NEIGH_TABLE)](config-db/errordb.md) (88)
- [SAG テーブル](config-db/sag.md) (43)
- [VRRP テーブル](config-db/vrrp.md) (41)
- [イベント/アラーム拡張監視設定 (extended-monitor)](config-db/extended-monitor.md) (39)

### [Headroom](#term-headroom)

- [DEFAULT_LOSSLESS_BUFFER_PARAMETER テーブル](config-db/default-lossless-buffer-parameter.md) (29)
- [LOSSLESS_TRAFFIC_PATTERN テーブル](config-db/lossless-traffic-pattern.md) (11)
- [CABLE_LENGTH テーブル](config-db/cable-length.md) (6)
- [BUFFER_POOL テーブル](config-db/buffer-pool.md) (5)
- [ACL & QoS](../acl-qos/index.md) (3)

### [hostcfgd](#term-hostcfgd)

- [RADIUS テーブル](config-db/radius.md) (131)
- [AAA テーブル](config-db/aaa.md) (121)
- [RADIUS_SERVER テーブル](config-db/radius-server.md) (113)
- [SERIAL_CONSOLE / SSH_SERVER テーブル](config-db/cli-config.md) (109)
- [LDAP_SERVER テーブル](config-db/ldap-server.md) (93)

### [HwSku](#term-hwsku)

- [[COUNTERS_DB] gNMI 内部リクエストカウンタ](config-db/gnmi-counter.md) (7)
- [MGMT_PORT テーブル](config-db/mgmt-port.md) (5)
- [LLDP / LLDP_PORT テーブル](config-db/lldp.md) (3)
- [BGP_DEVICE_GLOBAL テーブル](config-db/bgp-device-global.md) (2)
- [設定](../topics/21-lab-vs-developer/setup.md) (2)

### [IFA](#term-ifa)

- [TAM テーブル](config-db/tam.md) (64)
- [サイトマップ](../_meta/sitemap.md) (2)
- [config vrf サブコマンド](cli/config-vrf.md) (2)
- [IP インタフェース ループバックアクション（同一 RIF 出戻りの drop/forward）](../architecture/sonic-ip-interface-loopback-action.md) (1)
- [FEC FLR 設定・運用（counterpoll / show interfaces counters fec-stats / portstat -f）](../platform/fec-flr-support-in-sonic-operations.md) (1)

### [INT](#term-int)

- [VLAN_SUB_INTERFACE テーブル](config-db/vlan-sub-interface.md) (164)
- [VLAN_INTERFACE テーブル](config-db/vlan-interface.md) (146)
- [PORTCHANNEL_INTERFACE テーブル](config-db/portchannel-interface.md) (138)
- [INTERFACE テーブル](config-db/interface.md) (101)
- [MCLAG_INTERFACE テーブル](config-db/mclag-interface.md) (88)

### [intfmgrd](#term-intfmgrd)

- [VLAN_SUB_INTERFACE テーブル](config-db/vlan-sub-interface.md) (48)
- [INTERFACE テーブル](config-db/interface.md) (32)
- [IPv6 Link-local モード](config-db/ipv6-link-local.md) (31)
- [PORTCHANNEL_INTERFACE テーブル](config-db/portchannel-interface.md) (31)
- [VLAN_INTERFACE テーブル](config-db/vlan-interface.md) (31)

### [intfsyncd](#term-intfsyncd)

- [SWSS docker warm restart（state restore / consistency / sync up）](../system/sonic-swss-docker-warm-restart.md) (2)
- [swss-schema（APPL_DB / STATE_DB の中心スキーマ参照）](../internals/swss-schema.md) (1)
- [VOQ_INBAND_INTERFACE テーブル](config-db/voq-inband-interface.md) (1)

### [IPinIP](#term-ipinip)

- [Srv6Orch — APP_DB SRV6 テーブル](config-db/srv6-orch.md) (14)
- [SRV6_MY_SIDS テーブル](config-db/srv6-my-sids.md) (11)
- [Dual-ToR の考え方](../topics/05-dual-tor/concept.md) (9)
- [サイトマップ](../_meta/sitemap.md) (8)
- [VLAN Subnet Decap（Netscan 用 IPinIP MP2MP デカプスル）](../platform/subnet-decapsulation-with-sonic.md) (8)

### [intfsorch](#term-intfsorch)

- [COUNTERS_DB RIF カウンタ](config-db/counters-rif.md) (81)
- [VLAN_INTERFACE テーブル](config-db/vlan-interface.md) (55)
- [VLAN_SUB_INTERFACE テーブル](config-db/vlan-sub-interface.md) (55)
- [COUNTERS_DB PortChannel/LAG カウンタ](config-db/counters-portchannel.md) (45)
- [PORTCHANNEL_INTERFACE テーブル](config-db/portchannel-interface.md) (42)

### [LOGLEVEL_DB](#term-loglevel_db)

- [ログレベルの永続化（LOGLEVEL_DB → CONFIG_DB.LOGGER への移行）](../system/persistent-log-level-hld.md) (23)
- [Redis DB 設定 (database_config.json)](config-db/redis-db-config.md) (3)
- [サイトマップ](../_meta/sitemap.md) (2)
- [Multi-ASIC 名前空間の Redis（database_global.json と SonicDBConfig）](../internals/support-redis-databases-in-multiple-namespaces.md) (2)
- [APPL_DB VRF_TABLE テーブル](config-db/appl-vrf.md) (2)

### [LACP](#term-lacp)

- [ICCPd 内部構成（MC-LAG / MLACP FSM ファイル別マップ）](../switching/brief-introduction-of-iccp-code.md) (24)
- [PORTCHANNEL テーブル](config-db/portchannel.md) (21)
- [STATE_DB LAG_TABLE (PortChannel 状態)](config-db/portchannel-state.md) (12)
- [サイトマップ](../_meta/sitemap.md) (10)
- [STP / ICCP 連携 — コード由来デフォルト詳細](config-db/stp-iccp.md) (10)

### [LAG](#term-lag)

- [APPL_DB MCLAG/ICCP 関連テーブル](config-db/appl-mclag.md) (159)
- [MCLAG_INTERFACE テーブル](config-db/mclag-interface.md) (155)
- [MCLAG_DOMAIN / MCLAG_INTERFACE / MCLAG_UNIQUE_IP テーブル](config-db/mclag-domain.md) (154)
- [APPL_DB LAG_TABLE (portchannel ステータス)](config-db/portchannel-status.md) (141)
- [PORTCHANNEL テーブル](config-db/portchannel.md) (140)

### [linkmgrd](#term-linkmgrd)

- [MUX_LINKMGR テーブル](config-db/mux-linkmgr.md) (85)
- [MUX_CABLE テーブル（per-port フィールド詳細）](config-db/mux-cable-port.md) (52)
- [MUX_CABLE テーブル](config-db/mux-cable.md) (30)
- [linkmgrd のデフォルトルート連動（DualToR mux 制御）](../routing/default-route.md) (27)
- [Active-Standby Dual ToR（y-cable + linkmgrd state machine + IPinIP tunnel）](../overlay/active-standby-dual-tor.md) (19)

### [LLDP](#term-lldp)

- [[APPL_DB] LLDP_ENTRY_TABLE / LLDP_LOC_CHASSIS テーブル](config-db/lldp-state.md) (118)
- [LLDP / LLDP_PORT テーブル](config-db/lldp.md) (94)
- [LLDP_PORT テーブル](config-db/lldp-port.md) (86)
- [sonic-lldp YANG](yang/sonic-lldp.md) (46)
- [サイトマップ](../_meta/sitemap.md) (22)

### [MPLS](#term-mpls)

- [LABEL_ROUTE_TABLE (APPL_DB)](config-db/appl-mpls-route.md) (87)
- [概念](../topics/17-srv6-mpls/concept.md) (51)
- [MPLS TC → TC map（MPLS パケットの QoS classification）](../routing/mpls-tc-to-tc-map.md) (45)
- [SONiC の MPLS 基盤（per-RIF MPLS / LABEL_ROUTE_TABLE / 静的 LSP）](../routing/mpls-for-sonic-high-level-design-document.md) (37)
- [内部実装](../topics/17-srv6-mpls/internals.md) (25)

### [MCLAG](#term-mclag)

- [MCLAG_INTERFACE テーブル](config-db/mclag-interface.md) (139)
- [APPL_DB MCLAG/ICCP 関連テーブル](config-db/appl-mclag.md) (133)
- [MCLAG_DOMAIN / MCLAG_INTERFACE / MCLAG_UNIQUE_IP テーブル](config-db/mclag-domain.md) (121)
- [MCLAG_UNIQUE_IP テーブル](config-db/mclag-unique-ip.md) (113)
- [STP / ICCP 連携 — コード由来デフォルト詳細](config-db/stp-iccp.md) (68)

### [minigraph.xml](#term-minigraph.xml)

- [DEVICE_NEIGHBOR テーブル](config-db/device-neighbor.md) (10)
- [CONFIG_DB save / load が反映されない](runbooks/config-save-load.md) (7)
- [minigraph 適用後に reload が完了しない / 起動が固まる](runbooks/minigraph-reload-stuck.md) (7)
- [DEVICE_NEIGHBOR_METADATA テーブル](config-db/device-neighbor-metadata.md) (5)
- [SYSTEM_DEFAULTS テーブルによる SONiC 既定値の集約](../switching/control-sonic-behaviors-with-system-defaults-table.md) (5)

### [MMU](#term-mmu)

- [COMMUNITY_SET テーブル](config-db/community-set.md) (67)
- [SNMP_COMMUNITY テーブル](config-db/community-list.md) (56)
- [SNMP テーブル](config-db/snmp.md) (32)
- [sonic-route-map YANG](yang/sonic-route-map.md) (24)
- [BGP_ALLOWED_PREFIXES テーブル](config-db/bgp-allowed-prefixes.md) (19)

### [MUX](#term-mux)

- [MUX_CABLE_TABLE / HW_MUX_CABLE_TABLE (STATE_DB)](config-db/mux-cable-state.md) (145)
- [MUX_CABLE テーブル（per-port フィールド詳細）](config-db/mux-cable-port.md) (126)
- [MUX_LINKMGR テーブル](config-db/mux-linkmgr.md) (120)
- [MUX_CABLE テーブル](config-db/mux-cable.md) (117)
- [PEER_SWITCH テーブル](config-db/peer-switch.md) (53)

### [MAC](#term-mac)

- [PORT (macsec フィールド)](config-db/macsec-port.md) (186)
- [MACSEC_PROFILE テーブル](config-db/macsec-profile.md) (159)
- [FIPS 向け MACsec SAI POST（FIPS_MACSEC_POST_TABLE）](../switching/sonic-sai-post-support-for-macsec.md) (83)
- [SAG テーブル](config-db/sag.md) (76)
- [STATE_DB orchagent 共通テーブル](config-db/orchagent-state.md) (59)

### [MACsec](#term-macsec)

- [PORT (macsec フィールド)](config-db/macsec-port.md) (126)
- [MACSEC_PROFILE テーブル](config-db/macsec-profile.md) (85)
- [FIPS 向け MACsec SAI POST（FIPS_MACSEC_POST_TABLE）](../switching/sonic-sai-post-support-for-macsec.md) (35)
- [Gearbox PHY ごとの MACsec backend 決定（macsec_supported）](../switching/sonic-hld-deterministic-macsec-backend-selection-for-gearbox-ports.md) (27)
- [MACsec on SONiC（wpa_supplicant + MACsec Mgr/Orch + SAI）](../switching/macsec-sonic-high-level-design-document.md) (25)

### [Multi-ASIC](#term-multi-asic)

- [サイトマップ](../_meta/sitemap.md) (25)
- [概念](../topics/12-multi-asic-voq/concept.md) (19)
- [Multi-ASIC / VOQ chassis 関連](../categories/multi-asic.md) (16)
- [Multi-ASIC / VOQ Chassis](../topics/12-multi-asic-voq/index.md) (11)
- [設定](../topics/20-swss-sai-redis/setup.md) (10)

### [muxorch](#term-muxorch)

- [MUX_CABLE テーブル](config-db/mux-cable.md) (74)
- [MUX_CABLE_TABLE / HW_MUX_CABLE_TABLE (STATE_DB)](config-db/mux-cable-state.md) (67)
- [PEER_SWITCH テーブル](config-db/peer-switch.md) (44)
- [MUX_CABLE テーブル（per-port フィールド詳細）](config-db/mux-cable-port.md) (43)
- [SYSTEM_DEFAULTS テーブル](config-db/system-defaults.md) (34)

### [NAT](#term-nat)

- [NAT_BINDINGS テーブル](config-db/nat-bindings.md) (331)
- [NAT_GLOBAL / NAT_POOL テーブル](config-db/nat.md) (320)
- [NAT_RESTORE_TABLE / COUNTERS_NAT テーブル](config-db/nat-state.md) (301)
- [COUNTERS_DB NAT カウンタテーブル群](config-db/nat-counters.md) (282)
- [NAT_POOL テーブル](config-db/nat-pool.md) (248)

### [natmgrd / natsyncd](#term-natmgrd-natsyncd)

- [NAT in SONiC（natsyncd / NatOrch / iptables ↔ SAI）](../architecture/nat-in-sonic.md) (1)
- [運用](../topics/16-nat-dhcp-dns/operations.md) (1)

### [neighsyncd](#term-neighsyncd)

- [IPv6 Link-local モード](config-db/ipv6-link-local.md) (28)
- [WARM_RESTART テーブル](config-db/warm-restart.md) (28)
- [NEIGH テーブル](config-db/neigh.md) (11)
- [ARP / Neighbor エントリが古い IP-MAC を保持し続ける](runbooks/arp-entry-stuck.md) (6)
- [Reboot / warm restart の設定](../topics/11-reboot/setup.md) (6)

### [Netlink](#term-netlink)

- [NEIGH テーブル](config-db/neigh.md) (15)
- [NEXTHOP_GROUP_TABLE / CLASS_BASED_NEXT_HOP_GROUP_TABLE](config-db/nhg-table.md) (5)
- [新 FRR-SONiC 通信チャネル（dplane_fpm_sonic モジュール）](../routing/new-frr-sonic-communication-channel.md) (5)
- [STATIC_ROUTE テーブル](config-db/static-route.md) (3)
- [EVPN DIP トンネル (動的生成)](config-db/vxlan-evpn-tunnel.md) (2)

### [Next Hop Group](#term-next-hop-group)

- [L3 基盤と VRF](../topics/04-vrf-ecmp/concept.md) (5)
- [P4Orch（PINS の P4Runtime 用 orchagent / 同期書き込み）](../internals/p4-orchagent.md) (1)
- [VNET_ROUTE / VNET_ROUTE_TUNNEL テーブル](config-db/vnet-route.md) (1)
- [VNET テーブル](config-db/vnet.md) (1)
- [EVPN VXLAN Multihoming 概念（ESI / DF election / Split-horizon / Aliasing）](../routing/evpn-vxlan-multihoming-concepts.md) (1)

### [NDP](#term-ndp)

- [Srv6Orch — APP_DB SRV6 テーブル](config-db/srv6-orch.md) (28)
- [SRv6 uSID（srv6orch の uN/uA/uDT/uDX 拡張）](../routing/sonic-usid.md) (20)
- [APPL_DB SRV6テーブル (SRV6_MY_SID_TABLE / SRV6_SID_LIST_TABLE)](config-db/srv6-applb.md) (19)
- [VNET の Local Endpoint Forwarding（DPU 直結 nexthop の最適化）](../overlay/vnet-local-endpoint-forwarding.md) (8)
- [NEIGH テーブル](config-db/neigh.md) (6)

### [NPU](#term-npu)

- [SmartSwitch reboot 順序（NPU → 各 DPU の gNOI HALT → PCI detach → 個別 reboot）](../system/smart-switch-reboot-high-level-design.md) (45)
- [DASH と SmartSwitch の考え方](../topics/13-dash-smartswitch/concept.md) (38)
- [サイトマップ](../_meta/sitemap.md) (27)
- [ACL_TABLE (CTRLPLANE) テーブル](config-db/control-plane-acl.md) (27)
- [DPU の IP 割当・gNMI 連携・KVM 検証](../topics/13-dash-smartswitch/setup.md) (24)

### [orchagent](#term-orchagent)

- [DEVICE_METADATA テーブル](config-db/device-metadata.md) (218)
- [ZMQ 関連 CONFIG_DB フィールド (DEVICE_METADATA / DPU)](config-db/zmq.md) (97)
- [COUNTERS_DB RIF カウンタ](config-db/counters-rif.md) (68)
- [DPU Orchagent 設定 (DEVICE_METADATA — DPU 固有フィールド)](config-db/dpu-orch.md) (65)
- [APPL_DB PORT_TABLE](config-db/appl-port-table.md) (62)

### [PFC](#term-pfc)

- [PFC_WD テーブル](config-db/pfc-wd.md) (170)
- [PFC_WD 状態フィールド (COUNTERS_DB)](config-db/pfcwd-state.md) (138)
- [MAP_PFC_PRIORITY_TO_QUEUE テーブル](config-db/map-pfc-priority-to-queue.md) (76)
- [PFC_PRIORITY_TO_PRIORITY_GROUP_MAP テーブル](config-db/pfc-priority-to-priority-group-map.md) (62)
- [サイトマップ](../_meta/sitemap.md) (41)

### [PFC Watchdog](#term-pfc-watchdog)

- [PFC_WD テーブル](config-db/pfc-wd.md) (11)
- [PFC_WD 状態フィールド (COUNTERS_DB)](config-db/pfcwd-state.md) (5)
- [サイトマップ](../_meta/sitemap.md) (3)
- [DEVICE_NEIGHBOR テーブル](config-db/device-neighbor.md) (3)
- [[STATE_DB] DEVICE_NEIGHBOR 動作状態（device op state）](config-db/deviceop-state.md) (3)

### [PG (Priority Group)](#term-pg)

- [BUFFER_PG テーブル](config-db/buffer-pg.md) (1)
- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (1)

### [portmgrd](#term-portmgrd)

- [PORT テーブル](config-db/port.md) (25)
- [APPL_DB PORT_TABLE](config-db/appl-port-table.md) (22)
- [PORT_TABLE ステータスフィールド（STATE_DB）](config-db/ports-status.md) (19)
- [BREAKOUT_CFG テーブル (DPB)](config-db/dpb.md) (16)
- [DHCP DoS 緩和（ポート単位 DHCP レート制限・Linux TC ベース）](../acl-qos/dhcp-dos-mitigation-in-sonic.md) (13)

### [portsyncd](#term-portsyncd)

- [APPL_DB PORT_TABLE](config-db/appl-port-table.md) (42)
- [PORT_TABLE ステータスフィールド（STATE_DB）](config-db/ports-status.md) (24)
- [STATE_DB PORT_TABLE（ポート状態テーブル）](config-db/state-db-port.md) (24)
- [ポートの動的 add / del（zero-port 起動と post-init 操作）](../acl-qos/enhancements-to-add-or-del-ports-dynamically.md) (17)
- [BREAKOUT_CFG テーブル](config-db/breakout-cfg.md) (14)

### [port_config.ini](#term-port-config-ini)

- [port_config.ini パーサ統合（portconfig.py 一元化）](../architecture/sonic-port-configuration-refactor-design.md) (18)
- [SONiC ポート命名規則の変更案（et[sX]pY[abcd]）](../platform/sonic-port-naming-convention-change.md) (16)
- [DEVICE_RUNTIME_METADATA テーブル](config-db/device-runtime-metadata.md) (16)
- [DEVICE_NEIGHBOR テーブル](config-db/device-neighbor.md) (12)
- [PORT テーブル](config-db/port.md) (10)

### [PINS](#term-pins)

- [サイトマップ](../_meta/sitemap.md) (23)
- [設定](../topics/18-p4-pins/setup.md) (17)
- [発展トピック](../topics/18-p4-pins/advanced.md) (16)
- [概念](../topics/18-p4-pins/concept.md) (15)
- [P4 / PINS / Programmable Pipeline](../topics/18-p4-pins/index.md) (9)

### [ProducerStateTable](#term-producerstatetable)

- [ROUTE_TABLE handler 分岐 (fpmsyncd / RouteSync)](config-db/route-handler.md) (15)
- [DPU / ENI / VDPU / REMOTE_DPU テーブル](config-db/dpu-eni.md) (13)
- [ZMQ 関連 CONFIG_DB フィールド (DEVICE_METADATA / DPU)](config-db/zmq.md) (13)
- [ZMQ ProducerStateTable / ConsumerStateTable 設計](../internals/zmq-producer-consumer-state-table-design.md) (11)
- [発展トピック](../topics/20-swss-sai-redis/advanced.md) (10)

### [PortChannel](#term-portchannel)

- [MCLAG_INTERFACE テーブル](config-db/mclag-interface.md) (33)
- [L2 設定パターン](../topics/06-l2-vlan-lag/setup.md) (32)
- [PORTCHANNEL_INTERFACE テーブル](config-db/portchannel-interface.md) (29)
- [IP / LAG / MTU の Incremental Update（portmgrd / intfmgrd / teammgrd 分担）](../switching/sonic-ip-lag-incremental-update.md) (23)
- [Switchport モード（access / trunk / routed）と VLAN CLI 拡張](../switching/switch-port-modes-and-vlan-cli-enhancement.md) (23)

### [Policer](#term-policer)

- [PORT_STORM_CONTROL テーブル — 暗黙デフォルト詳細](config-db/storm-control.md) (43)
- [POLICER テーブル](config-db/policer.md) (42)
- [PORT_STORM_CONTROL テーブル](config-db/port-storm-control.md) (26)
- [APPL_DB FIXED_MIRROR_SESSION_TABLE (P4RT)](config-db/appl-mirror.md) (9)
- [MIRROR_SESSION (ERSPAN 種別)](config-db/erspan.md) (9)

### [Policing](#term-policing)

- [サイトマップ](../_meta/sitemap.md) (3)
- [COPP_GROUP テーブル](config-db/copp-group.md) (1)
- [sonic-copp YANG](yang/sonic-copp.md) (1)
- [概念](../topics/07-acl-copp-mirror/concept.md) (1)
- [概念](../topics/15-security-aaa/concept.md) (1)

### [P4RT](#term-p4rt)

- [APPL_DB FIXED_MIRROR_SESSION_TABLE (P4RT)](config-db/appl-mirror.md) (84)
- [P4RT テーブル (PINS p4rt 設定)](config-db/pin-config.md) (66)
- [P4RT アプリケーション（PINS の gRPC サービス、port 9559）](../management/p4rt-application-hld.md) (54)
- [IP マルチキャストルート (P4RT)](config-db/ip-mcast-route.md) (40)
- [TUNNEL_ENCAP_TABLE (P4RT FIXED_TUNNEL_TABLE)](config-db/tunnel-encap-table.md) (33)

### [portsorch](#term-portsorch)

- [APPL_DB PORT_TABLE](config-db/appl-port-table.md) (124)
- [PORT テーブル](config-db/port.md) (106)
- [APPL_DB VLAN_TABLE / VLAN_MEMBER_TABLE テーブル](config-db/appl-vlan.md) (95)
- [FABRIC_PORT テーブル](config-db/fabric-port.md) (82)
- [COUNTERS_DB QUEUE カウンタ](config-db/queue-counter.md) (80)

### [Priority Group](#term-priority-group)

- [サイトマップ](../_meta/sitemap.md) (6)
- [COUNTERS_DB バッファ / ウォーターマーク カウンタ](config-db/counter-buffer.md) (4)
- [DOT1P_TO_PG_MAP テーブル（非実在）](config-db/dot1p-to-pg-map.md) (4)
- [DSCP_TO_PG_MAP テーブル（非実在）](config-db/dscp-to-pg-map.md) (4)
- [TC_TO_PRIORITY_GROUP_MAP テーブル](config-db/tc-to-priority-group-map.md) (3)

### [QoS](#term-qos)

- [サイトマップ](../_meta/sitemap.md) (34)
- [PORT_QOS_MAP テーブル](config-db/port-qos-map.md) (17)
- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (14)
- [EXP_TO_FC_MAP テーブル](config-db/exp-to-fc-map.md) (12)
- [TUNNEL テーブル](config-db/tunnel.md) (12)

### [RoCE](#term-roce)

- [WRED_PROFILE テーブル](config-db/wred-profile.md) (4)
- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (3)
- [QoS / Buffer の設定](../topics/08-qos-buffer/setup.md) (3)
- [ACL_RULE テーブル](config-db/acl-rule.md) (2)
- [PFC_PRIORITY_TO_PRIORITY_GROUP_MAP テーブル](config-db/pfc-priority-to-priority-group-map.md) (2)

### [Redis](#term-redis)

- [TELEMETRY_CONNECTIONS テーブル (STATE_DB)](config-db/gnmi-state.md) (75)
- [Redis Client Manager（RCM: connection pool / transactional client）](../management/redis-client-manager-rcm-hld.md) (44)
- [サイトマップ](../_meta/sitemap.md) (30)
- [Redis DB 設定 (database_config.json)](config-db/redis-db-config.md) (24)
- [ZMQ 関連 CONFIG_DB フィールド (DEVICE_METADATA / DPU)](config-db/zmq.md) (22)

### [RIF](#term-rif)

- [COUNTERS_DB PortChannel/LAG カウンタ](config-db/counters-portchannel.md) (128)
- [COUNTERS_DB RIF カウンタ](config-db/counters-rif.md) (122)
- [ルータインタフェース (RIF) カウンタ](../routing/router-interface-counters-in-sonic.md) (46)
- [VLAN_SUB_INTERFACE テーブル](config-db/vlan-sub-interface.md) (42)
- [バイト/パケットレートとポート使用率（RATES テーブル + EMA）](../internals/byte-packet-rates-port-utilization-in-sonic.md) (34)

### [ROUTE_TABLE](#term-route_table)

- [APPL_STATE_DB ROUTE_TABLE (route offload cache)](config-db/route-cache.md) (71)
- [ROUTE_TABLE (STATE_DB / APPL_STATE_DB)](config-db/route-state.md) (63)
- [RouteOrch event / notification (ResponsePublisher + NextHopObserver)](config-db/route-orch-event.md) (55)
- [ROUTE_TABLE handler 分岐 (fpmsyncd / RouteSync)](config-db/route-handler.md) (53)
- [DASH_ROUTE_* テーブル](config-db/dash-routing-table.md) (50)

### [RADIUS](#term-radius)

- [RADIUS テーブル](config-db/radius.md) (152)
- [RADIUS_SERVER テーブル](config-db/radius-server.md) (104)
- [sonic-system-radius YANG](yang/sonic-system-radius.md) (50)
- [RADIUS 管理 user 認証（PAM / NSS / nss-mapper / 多サーバ priority）](../management/radius-management-user-authentication.md) (44)
- [AAA テーブル](config-db/aaa.md) (43)

### [ROUTE_MAP](#term-route_map)

- [sonic-route-map YANG](yang/sonic-route-map.md) (106)
- [ROUTE_MAP_SET テーブル](config-db/route-map-set.md) (75)
- [ROUTE_MAP テーブル](config-db/route-map.md) (65)
- [sonic-bgp-global YANG](yang/sonic-bgp-global.md) (24)
- [sonic-bgp-neighbor YANG](yang/sonic-bgp-neighbor.md) (24)

### [SNMP](#term-snmp)

- [SNMP テーブル](config-db/snmp.md) (160)
- [SNMP_AGENT_ADDRESS_CONFIG / SNMP_USER テーブル (デフォルト詳細)](config-db/snmp-agent.md) (139)
- [SNMP_COMMUNITY テーブル](config-db/community-list.md) (86)
- [sonic-snmp YANG](yang/sonic-snmp.md) (73)
- [SNMP_AGENT_ADDRESS_CONFIG テーブル](config-db/snmp-agent-address-config.md) (72)

### [SRv6](#term-srv6)

- [概念](../topics/17-srv6-mpls/concept.md) (47)
- [発展トピック](../topics/17-srv6-mpls/advanced.md) (46)
- [Srv6Orch — APP_DB SRV6 テーブル](config-db/srv6-orch.md) (42)
- [サイトマップ](../_meta/sitemap.md) (34)
- [SRv6 VPN（L3VPN over SRv6 と SRv6 Policy）](../routing/srv6-vpn-hld.md) (30)

### [SAI](#term-sai)

- [頻出 SAI 属性早見表](sai-attributes.md) (241)
- [WRED_PROFILE テーブル](config-db/wred-profile.md) (162)
- [ACL_RULE テーブル](config-db/acl-rule.md) (141)
- [POLICER テーブル](config-db/policer.md) (134)
- [COUNTERS_DB PORT カウンタ](config-db/counters-port.md) (131)

### [SerDes](#term-serdes)

- [1.6T Ethernet 対応（200G SerDes / SFF-8024 / xcvrd / PortsOrch）](../platform/1-6t-support-in-sonic.md) (6)
- [Media-based Port Settings（media_settings.json による SerDes プロファイル）](../platform/media-based-port-settings-in-sonic.md) (6)
- [サイトマップ](../_meta/sitemap.md) (5)
- [PORT テーブル](config-db/port.md) (4)
- [プラットフォーム](../platform/index.md) (2)

### [sFlow Agent](#term-sflow-agent)

- [設定](../topics/09-telemetry-snmp/setup.md) (1)

### [sFlow Collector](#term-sflow-collector)

- [SFLOW_COLLECTOR テーブル](config-db/sflow-collector.md) (1)

### [sonic-buildimage](#term-sonic-buildimage)

- [DEVICE_METADATA テーブル](config-db/device-metadata.md) (130)
- [Fast-reboot Flow Improvements（finalizer / reconciliation）](../system/fast-reboot-flow-improvements-hld.md) (78)
- [ビルド時間最適化（Dockerfile レイヤ削減 / BuildKit / 並列 dh / sairedis 分離）](../architecture/build-system-improvements.md) (63)
- [FRR-BGP Unified Mgmt Framework（frrcfgd / OpenConfig BGP）](../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md) (49)
- [BGP_AGGREGATE_ADDRESS テーブル](config-db/bgp-aggregate-address.md) (31)

### [sonic-cfggen](#term-sonic-cfggen)

- [DEVICE_RUNTIME_METADATA テーブル](config-db/device-runtime-metadata.md) (19)
- [DEVICE_METADATA テーブル](config-db/device-metadata.md) (18)
- [RESTAPI テーブル](config-db/restapi.md) (17)
- [DEVICE_NEIGHBOR_METADATA テーブル](config-db/device-neighbor-metadata.md) (16)
- [cluster フィールド (DEVICE_METADATA / DEVICE_NEIGHBOR_METADATA)](config-db/cluster.md) (15)

### [sonic-mgmt](#term-sonic-mgmt)

- [MGMT_PORT テーブル](config-db/mgmt-port.md) (21)
- [HARDWARE テーブル](config-db/hardware.md) (20)
- [sonic-mgmt_interface YANG](yang/sonic-mgmt_interface.md) (20)
- [sonic-mgmt_port YANG](yang/sonic-mgmt_port.md) (19)
- [DIP=SIP PTF 検証テスト](../architecture/dip-sip-ptf-validation-high-level-design.md) (18)

### [sonic-swss](#term-sonic-swss)

- [DEVICE_METADATA テーブル](config-db/device-metadata.md) (87)
- [COUNTERS_DB RIF カウンタ](config-db/counters-rif.md) (56)
- [VLAN_SUB_INTERFACE テーブル](config-db/vlan-sub-interface.md) (45)
- [COUNTERS_DB バッファ / ウォーターマーク カウンタ](config-db/counter-buffer.md) (44)
- [ACL_RULE テーブル](config-db/acl-rule.md) (38)

### [sonic-swss-common](#term-sonic-swss-common)

- [LOGGER テーブル](config-db/log-config.md) (14)
- [ERROR_DB テーブル (ERROR_ROUTE_TABLE / ERROR_NEIGH_TABLE)](config-db/errordb.md) (13)
- [WARM_RESTART テーブル](config-db/warm-restart.md) (12)
- [ALARM テーブル (EVENT_DB)](config-db/alarm-table.md) (10)
- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../architecture/error-handling-framework-in-sonic.md) (9)

### [sonic-sairedis](#term-sonic-sairedis)

- [SAI API バージョン整合チェック（sai_query_api_version + ビルド時検査）](../platform/sai-api-version-check.md) (16)
- [NPU MDIO アクセスと gbsyncd 単一 docker 化](../platform/sonic-npu-mdio-access-support-and-gbsyncd-docker-enhancement-hld.md) (8)
- [libsairedis API idempotence（warm restart 用 OID キャッシュと duplicate 抑止）](../system/sonic-libsairedis-api-idempotence-support.md) (8)
- [Bulk Counter（sai_bulk_object_get_stats / chunk size）](../architecture/sonic-bulk-counter-design.md) (7)
- [DEVICE_METADATA テーブル](config-db/device-metadata.md) (5)

### [sonic-utilities](#term-sonic-utilities)

- [AUTO_TECHSUPPORT_FEATURE テーブル](config-db/auto-techsupport-feature.md) (37)
- [BREAKOUT_CFG テーブル](config-db/breakout-cfg.md) (14)
- [[STATE_DB] DEVICE_NEIGHBOR 動作状態（device op state）](config-db/deviceop-state.md) (13)
- [config bgp サブコマンド](cli/config-bgp.md) (12)
- [DEVICE_METADATA テーブル](config-db/device-metadata.md) (12)

### [Scheduler](#term-scheduler)

- [SCHEDULER テーブル](config-db/scheduler.md) (37)
- [SCHEDULER — QosOrch SchedulerOrch コード由来デフォルト詳解](config-db/scheduler-orch.md) (25)
- [QUEUE テーブル](config-db/queue.md) (16)
- [QoS Scheduler / Shaper（SP / WRR / DWRR + min/max bandwidth）](../acl-qos/sonic-qos-scheduler-and-shaping.md) (5)
- [サイトマップ](../_meta/sitemap.md) (4)

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

- [CHASSIS_MODULE テーブル](config-db/chassis-module.md) (78)
- [サイトマップ](../_meta/sitemap.md) (60)
- [SmartSwitch 関連テーブル (MID_PLANE_BRIDGE / DHCP_SERVER_IPV4_PORT)](config-db/smart-switch.md) (51)
- [NTP テーブル群](config-db/ntp.md) (35)
- [CHASSIS_STATE_DB テーブル群](config-db/chassis-state.md) (32)

### [Strict Priority](#term-strict-priority)

- [SCHEDULER — QosOrch SchedulerOrch コード由来デフォルト詳解](config-db/scheduler-orch.md) (1)

### [STATE_DB](#term-state_db)

- [BFD_SESSION_TABLE (STATE_DB)](config-db/bfd-state.md) (107)
- [ROUTE_TABLE (STATE_DB / APPL_STATE_DB)](config-db/route-state.md) (101)
- [FEATURE (STATE_DB)](config-db/feature-state.md) (91)
- [APPL_STATE_DB ROUTE_TABLE (route offload cache)](config-db/route-cache.md) (85)
- [サイトマップ](../_meta/sitemap.md) (80)

### [swssconfig](#term-swssconfig)

- [FDB Aging Time (SWITCH_TABLE.fdb_aging_time)](config-db/fdb-aging.md) (28)
- [FDB テーブル](config-db/fdb.md) (14)
- [ACL の基本設計（ACL_TABLE / ACL_RULE スキーマ）](../acl-qos/acl-support-in-sonic.md) (11)
- [APPL_DB FDB_TABLE](config-db/appl-fdb.md) (11)
- [VLAN Subnet Decap（Netscan 用 IPinIP MP2MP デカプスル）](../platform/subnet-decapsulation-with-sonic.md) (7)

### [syncd](#term-syncd)

- [APPL_STATE_DB ROUTE_TABLE (route offload cache)](config-db/route-cache.md) (87)
- [APPL_DB MCLAG/ICCP 関連テーブル](config-db/appl-mclag.md) (83)
- [WARM_RESTART テーブル](config-db/warm-restart.md) (82)
- [MCLAG_INTERFACE テーブル](config-db/mclag-interface.md) (79)
- [DEVICE_METADATA テーブル](config-db/device-metadata.md) (78)

### [Syslog](#term-syslog)

- [SYSLOG_CONFIG テーブル](config-db/syslog-config.md) (20)
- [SYSLOG_SERVER テーブル](config-db/syslog-server.md) (20)
- [SYSLOG_CONFIG_FEATURE テーブル](config-db/syslog-config-feature.md) (19)
- [sonic-syslog YANG](yang/sonic-syslog.md) (5)
- [サイトマップ](../_meta/sitemap.md) (3)

### [SONiC](#term-sonic)

- [サイトマップ](../_meta/sitemap.md) (354)
- [HLD と実装の乖離 一覧（discrepancy-index）](verification/discrepancy-index.md) (31)
- [概要](../topics/10-gnmi-openconfig/concept.md) (28)
- [概要](../topics/02-bgp/concept.md) (27)
- [アーキテクチャ](../topics/21-lab-vs-developer/architecture.md) (26)

### [TAM](#term-tam)

- [TAM テーブル](config-db/tam.md) (177)
- [変更履歴](../_meta/changelog.md) (7)
- [Path Tracing Midpoint（IPv6 HbH-PT に MCD を追記）](../routing/path-tracing-midpoint.md) (3)
- [内部実装](../topics/17-srv6-mpls/internals.md) (3)
- [サイトマップ](../_meta/sitemap.md) (2)

### [TC (Traffic Class)](#term-tc)

- [MIRROR_SESSION (ERSPAN 種別)](config-db/erspan.md) (1)
- [QoS / Buffer の概念地図](../topics/08-qos-buffer/concept.md) (1)

### [TCAM](#term-tcam)

- [HARDWARE テーブル](config-db/hardware.md) (22)
- [ACL in SONiC（テーブル型 / マッチ・アクション / SWSS パイプライン）](../acl-qos/acl-in-sonic.md) (5)
- [発展トピック](../topics/07-acl-copp-mirror/advanced.md) (5)
- [クリティカルリソースモニタリング (CRM) 要件](../system/critical-resource-monitoring.md) (4)
- [概念](../topics/07-acl-copp-mirror/concept.md) (3)

### [ToS](#term-tos)

- [APPL_DB STP Orchagent テーブル — フィールドとコード由来デフォルト](config-db/stp-orch.md) (20)
- [SmartSwitch HA DPU-Scope-DPU-Driven 内部実装（状態遷移と再同期）](../architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup-internals.md) (7)
- [SmartSwitch HA - DPU-Scope-DPU-Driven 構成](../architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md) (7)
- [FEC ステート（STATE_DB PORT_TABLE FEC フィールド）](config-db/fec-state.md) (6)
- [DASH_ACL_* テーブル](config-db/dash-acl.md) (3)

### [tunnelmgrd](#term-tunnelmgrd)

- [TUNNEL テーブル](config-db/tunnel.md) (29)
- [SUBNET_DECAP テーブル](config-db/subnet-decap.md) (13)
- [TUNNEL_DECAP_TERM_TABLE (APPL_DB)](config-db/tunnel-decap-term.md) (12)
- [TUNNEL_DECAP_TABLE (APPL_DB)](config-db/tunnel-decap-table.md) (8)
- [PEER_SWITCH テーブル](config-db/peer-switch.md) (5)

### [ToR](#term-tor)

- [サイトマップ](../_meta/sitemap.md) (78)
- [Dual-ToR の考え方](../topics/05-dual-tor/concept.md) (65)
- [DEVICE_METADATA テーブル](config-db/device-metadata.md) (59)
- [Active-Standby Dual ToR（y-cable + linkmgrd state machine + IPinIP tunnel）](../overlay/active-standby-dual-tor.md) (40)
- [Dual-ToR の発展トピック](../topics/05-dual-tor/advanced.md) (36)

### [VOQ](#term-voq)

- [VOQ_INBAND_INTERFACE テーブル](config-db/voq-inband-interface.md) (76)
- [BUFFER_QUEUE テーブル](config-db/buffer-queue.md) (47)
- [概念](../topics/12-multi-asic-voq/concept.md) (37)
- [サイトマップ](../_meta/sitemap.md) (32)
- [QUEUE テーブル](config-db/queue.md) (29)

### [VS](#term-vs)

- [STP / STP_VLAN / STP_PORT テーブル — 暗黙デフォルト詳細](config-db/stp.md) (66)
- [STP_PORT テーブル — 暗黙デフォルト詳細](config-db/stp-port.md) (43)
- [STP_VLAN / STP_VLAN_PORT テーブル](config-db/stp-vlan.md) (40)
- [内部実装](../topics/21-lab-vs-developer/internals.md) (40)
- [概念](../topics/21-lab-vs-developer/concept.md) (26)

### [VLAN](#term-vlan)

- [STP_VLAN / STP_VLAN_PORT テーブル](config-db/stp-vlan.md) (251)
- [APPL_DB VLAN_TABLE / VLAN_MEMBER_TABLE テーブル](config-db/appl-vlan.md) (219)
- [VLAN テーブル](config-db/vlan.md) (182)
- [VLAN_MEMBER テーブル](config-db/vlan-member.md) (164)
- [STATE_DB VLAN_TABLE（VLAN 状態テーブル）](config-db/vlan-state.md) (146)

### [vlanmgrd](#term-vlanmgrd)

- [VLAN テーブル](config-db/vlan.md) (36)
- [VLAN_MEMBER テーブル](config-db/vlan-member.md) (34)
- [STATE_DB VLAN_TABLE（VLAN 状態テーブル）](config-db/vlan-state.md) (34)
- [APPL_DB VLAN_TABLE / VLAN_MEMBER_TABLE テーブル](config-db/appl-vlan.md) (31)
- [VRRP テーブル](config-db/vrrp.md) (27)

### [VNET](#term-vnet)

- [VNET_ROUTE / VNET_ROUTE_TUNNEL テーブル](config-db/vnet-route.md) (183)
- [VNET テーブル](config-db/vnet.md) (177)
- [DASH_VNET テーブル](config-db/dash-vnet.md) (119)
- [sonic-vnet YANG](yang/sonic-vnet.md) (87)
- [VXLAN / VNET / EVPN の概要](../topics/03-vxlan-evpn/concept.md) (47)

### [VRF](#term-vrf)

- [VRF テーブル](config-db/vrf.md) (267)
- [VRF ステートテーブル（STATE_DB）](config-db/state-vrf.md) (252)
- [APPL_DB VRF_TABLE (VRFOrch)](config-db/vrf-orch.md) (224)
- [APPL_DB VRF_TABLE テーブル](config-db/appl-vrf.md) (167)
- [MGMT_VRF_CONFIG テーブル](config-db/mgmt-vrf-config.md) (143)

### [vrfmgrd](#term-vrfmgrd)

- [VRF テーブル](config-db/vrf.md) (54)
- [VRF ステートテーブル（STATE_DB）](config-db/state-vrf.md) (51)
- [APPL_DB VRF_TABLE (VRFOrch)](config-db/vrf-orch.md) (47)
- [APPL_DB VRF_TABLE テーブル](config-db/appl-vrf.md) (30)
- [MGMT_VRF_CONFIG テーブル](config-db/mgmt-vrf-config.md) (17)

### [VXLAN](#term-vxlan)

- [VXLAN_FDB_TABLE テーブル](config-db/vxlan-fdb.md) (114)
- [VXLAN_TUNNEL テーブル](config-db/vxlan-tunnel.md) (94)
- [VxlanTunnelOrch — encap 処理詳細](config-db/tunnel-encap-orch.md) (68)
- [VXLAN_EVPN_NVO テーブル](config-db/vxlan-evpn-nvo.md) (67)
- [サイトマップ](../_meta/sitemap.md) (62)

### [vxlanmgrd](#term-vxlanmgrd)

- [VNET テーブル](config-db/vnet.md) (19)
- [VXLAN_TUNNEL テーブル](config-db/vxlan-tunnel.md) (17)
- [VXLAN_TUNNEL_MAP テーブル](config-db/vxlan-tunnel-map.md) (14)
- [VXLAN_EVPN_NVO テーブル](config-db/vxlan-evpn-nvo.md) (10)
- [STATE_DB VLAN_TABLE（VLAN 状態テーブル）](config-db/vlan-state.md) (9)

### [VRRP](#term-vrrp)

- [VRRP テーブル](config-db/vrrp.md) (194)
- [VRRP_TRACK テーブル](config-db/vrrp-track.md) (124)
- [VRRP（FRR vrrpd 連携 / VRRPv2/v3 / uplink tracking）](../routing/virtual-router-redundancy-protocol-adaptation-hld.md) (36)
- [config interface サブコマンド](cli/config-interface.md) (14)
- [サイトマップ](../_meta/sitemap.md) (13)

### [VTEP](#term-vtep)

- [EVPN DIP トンネル (動的生成)](config-db/vxlan-evpn-tunnel.md) (38)
- [VXLAN トンネルポート (Port::TUNNEL)](config-db/tunnel-port.md) (35)
- [VXLAN_EVPN_NVO テーブル](config-db/vxlan-evpn-nvo.md) (34)
- [EVPN VXLAN 概念（Route Type 2/3/5 / L2VNI / L3VNI / IRB）](../routing/evpn-vxlan-hld-concepts.md) (26)
- [VXLAN_TUNNEL テーブル](config-db/vxlan-tunnel.md) (22)

### [vtysh](#term-vtysh)

- [BGP_GLOBALS_AF_AGGREGATE_ADDR テーブル](config-db/bgp-globals-af-aggregate-addr.md) (34)
- [PIM_GLOBALS / PIM_INTERFACE テーブル](config-db/pim.md) (31)
- [AS_PATH_SET テーブル](config-db/as-path-set.md) (27)
- [BGP_NEIGHBOR_AF テーブル](config-db/bgp-neighbor-af.md) (27)
- [ROUTE_REDISTRIBUTE テーブル](config-db/route-redistribute.md) (26)

### [Warm Reboot](#term-warm-reboot)

- [サイトマップ](../_meta/sitemap.md) (6)
- [Warm-Reboot / Fast-Reboot 関連](../categories/reboot.md) (3)
- [Warm path の内部構造](../topics/11-reboot/architecture.md) (3)
- [システム](../system/index.md) (2)
- [Express Reboot（Cisco 8000 向けサブ秒データプレーン断のリブート）](../system/sonic-express-reboot-hld-spec.md) (2)

### [WRED](#term-wred)

- [WRED_PROFILE テーブル](config-db/wred-profile.md) (144)
- [QUEUE_COUNTER_CAPABILITIES (STATE_DB)](config-db/queue-state.md) (100)
- [STATE_DB カウンタ能力テーブル](config-db/counters-state.md) (84)
- [QUEUE テーブル](config-db/queue.md) (66)
- [COUNTERS_DB QUEUE カウンタ](config-db/queue-counter.md) (61)

### [WRR](#term-wrr)

- [SCHEDULER テーブル](config-db/scheduler.md) (37)
- [SCHEDULER — QosOrch SchedulerOrch コード由来デフォルト詳解](config-db/scheduler-orch.md) (23)
- [サイトマップ](../_meta/sitemap.md) (8)
- [QoS Scheduler / Shaper（SP / WRR / DWRR + min/max bandwidth）](../acl-qos/sonic-qos-scheduler-and-shaping.md) (8)
- [ACL & QoS](../acl-qos/index.md) (6)

### [YANG](#term-yang)

- [サイトマップ](../_meta/sitemap.md) (245)
- [gNMI / gNOI / OpenConfig 関連](../categories/gnmi-openconfig.md) (52)
- [SmartSwitch 関連テーブル (MID_PLANE_BRIDGE / DHCP_SERVER_IPV4_PORT)](config-db/smart-switch.md) (40)
- [NTP_SERVER テーブル](config-db/ntp-server.md) (39)
- [MCLAG_DOMAIN / MCLAG_INTERFACE / MCLAG_UNIQUE_IP テーブル](config-db/mclag-domain.md) (35)

### [zebra](#term-zebra)

- [DEVICE_METADATA テーブル](config-db/device-metadata.md) (42)
- [fpmsyncd NextHop Group 拡張（dplane_fpm_nl / NEXTHOP_GROUP_TABLE）](../routing/fpmsyncd-nexthop-group-enhancement-high-level-design-document.md) (31)
- [debug / undebug コマンド群](cli/debug-group.md) (25)
- [APPL_STATE_DB ROUTE_TABLE (route offload cache)](config-db/route-cache.md) (24)
- [ROUTE_TABLE handler 分岐 (fpmsyncd / RouteSync)](config-db/route-handler.md) (23)

### [ZTP](#term-ztp)

- [Zero Touch Provisioning（ZTP・DHCP option / plugin / state machine）](../system/zero-touch-provisioning-ztp.md) (23)
- [SONiC NOS の設定手段一覧（CLI / sonic-cfggen / config_db.json / RESTCONF / gNMI / ZTP](../management/sonic-nos-configuration-methods.md) (7)
- [ビルドプロファイル（rules/profiles/*.mk）](../architecture/build-profiles.md) (6)
- [config-setup サービス（first-boot config 生成 / 版間 migration）](../system/sonic-configuration-setup-service.md) (6)
- [サイトマップ](../_meta/sitemap.md) (5)

<!-- /glossary-xref -->
