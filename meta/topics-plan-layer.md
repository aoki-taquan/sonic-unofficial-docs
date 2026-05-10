# 読み物章立て案（階層軸視点）

- 作成日: 2026-05-10
- 対象: `docs/` 配下の non-index Markdown
- 制約: このファイルは Phase B の設計レポートであり、本文ページ、frontmatter、`mkdocs.yml` は変更しない。

## 調査メモ

本来の列挙コマンドは `find docs -name "*.md" -not -name "index.md"` だが、この実行環境には `find` が無い。既存の `meta/restructure-plan.md` と同じ方針で、同等の列挙を `rg --files docs -g '*.md' | rg -v '/index\.md$' | sort` により実施した。

結果は 498 ページ。`meta/restructure-plan.md` は 455 通常ページを対象に area 別一覧を作成しているが、現在の worktree では `reference` が 163 ページあり、加えて `categories` 10、`guides` 4、`_meta` 1 が non-index ページとして存在する。章立て設計では全 498 ページを一次配置し、既存 area と読み物章の関係を明示する。

## 設計方針

既存 area は `routing` / `switching` / `management` のような機能別分類で維持する。新設する `topics` は、SONiC を上から下へ読むための階層別導線として重ねる。

各章は 4-6 ページ程度で構成し、次の共通テンプレートを基本にする。

- 全体像: その階層が SONiC 全体で何を担当するか
- コンポーネント: daemon、Orch、DB、コンテナ、外部 API の役割
- データフロー: CONFIG_DB / APPL_DB / ASIC_DB / STATE_DB / COUNTERS_DB などをまたぐ処理順序。Phase B では Mermaid sequence を置く
- 境界と契約: 上位、下位、隣接層との API、DB schema、SAI、YANG、CLI、gRPC の境界
- 内部メカニズム: 高度な実装、例外系、性能、warm restart、multi-ASIC など
- 既存ページへの導線: HLD、reference、CLI、CONFIG_DB、YANG、test plan へ戻れるリンク

## 提案章一覧

1. SONiC 全体アーキテクチャ
2. Redis DB と設定適用パイプライン
3. Data Plane プログラミング
4. Control Plane とルーティング制御
5. L2 / Overlay / Dual ToR
6. ACL / QoS / Telemetry / Counters
7. Management Plane と OpenConfig
8. Platform 層と PMON
9. Multi-ASIC / VoQ / Smart Switch
10. Build / Image / Packaging
11. Reboot / Resilience / Error Handling
12. 内部実装・開発・検証ガイド

## 章別設計

### 1. SONiC 全体アーキテクチャ

- 役割: `architecture`、`system`、`categories`、`guides` を縦串でつなぎ、SAI / SwSS / syncd / orchagent / Redis / コンテナ群の全体像を最初に掴ませる入口。
- 構成ページ案:
  - 全体像: SONiC を「北側 API、Redis DB、SwSS、syncd、SAI、ASIC、platform services」の層で読む。
  - コンポーネント: docker 群、orchagent、syncd、FRR、PMON、mgmt-framework、telemetry、database コンテナ。
  - データフロー: 設定、ルート、ポート状態、カウンタ、通知が DB を経由して流れる全体 sequence。
  - 境界と契約: container boundary、Redis table contract、SAI boundary、platform API boundary。
  - 内部メカニズム: feature table、system ready、optional feature、namespace、service dependency。
- 統合する既存ページ: `docs/guides/beginner.md`、`docs/guides/developer.md`、`docs/categories/*.md`、`docs/system/sonic-optional-feature-control-enhancement.md`、`docs/system/system-ready-hld.md`。
- 新規執筆の境界: 既存ページは各機能詳細としてリンクし、章では「どの順に読むか」と「DB / コンテナ / SAI の位置関係」を新規に説明する。
- 想定ボリューム: 5 ページ、約 8,000-10,000 字。

### 2. Redis DB と設定適用パイプライン

- 役割: `management`、`internals`、`reference/config-db`、各 feature HLD を横断し、CONFIG_DB → APPL_DB → ASIC_DB / STATE_DB / COUNTERS_DB の読み方を教える。
- 構成ページ案:
  - 全体像: SONiC の DB を control plane / data plane / management plane の契約面として読む。
  - コンポーネント: ConfigDBConnector、ProducerStateTable、ConsumerStateTable、Orch、syncd、STATE_DB writer、COUNTERS_DB writer。
  - データフロー: CLI / gNMI / config reload から CONFIG_DB に入り、mgrd / Orch を経由して APPL_DB / ASIC_DB に反映される sequence。
  - 境界と契約: CONFIG_DB schema、APPL_DB schema、YANG validation、Generic Config Updater、Redis namespace。
  - 内部メカニズム: ZMQ ProducerStateTable、multi-namespace DB、user-defined Redis DB、schema drift の扱い。
- 統合する既存ページ: `docs/internals/swss-schema.md`、`docs/internals/zmq-producer-consumer-state-table-design.md`、`docs/internals/support-redis-databases-in-multiple-namespaces.md`、`docs/management/sonic-config-update-validation-via-yang.md`、`docs/reference/config-db/*.md`。
- 新規執筆の境界: CONFIG_DB 個別表の説明は reference に任せ、章では表同士の関係、更新順、競合、rollback、namespace を解説する。
- 想定ボリューム: 6 ページ、約 10,000-12,000 字。

### 3. Data Plane プログラミング

- 役割: `architecture`、`platform`、SAI 関連ページを縦串にし、ASIC へ設定が到達するまでの流れを説明する。
- 構成ページ案:
  - 全体像: APPL_DB / ASIC_DB / SAI / syncd / vendor SDK の責務分担。
  - コンポーネント: orchagent、各 Orch、sairedis、syncd、SAI redis adapter、vendor SAI、ASIC。
  - データフロー: CONFIG_DB → mgrd → APPL_DB → Orch → ASIC_DB → syncd → SAI → ASIC の sequence。
  - 境界と契約: SAI object、OID、SAI attribute、bulk API、capability query、SAI failure handling。
  - 内部メカニズム: warm reboot の view comparison、libsairedis idempotence、bulk counter、hash、port profile init。
- 統合する既存ページ: `docs/architecture/port-profile-init-hld.md`、`docs/architecture/sonic-bulk-counter-design.md`、`docs/platform/sai-api-version-check.md`、`docs/platform/query-stats-capability-new-sai-api-indroduction.md`、`docs/system/sonic-libsairedis-api-idempotence-support.md`。
- 新規執筆の境界: 既存 HLD は機能単位の SAI 利用例として扱い、章では data plane programming の共通パターンを新規に説明する。
- 想定ボリューム: 5 ページ、約 9,000-11,000 字。

### 4. Control Plane とルーティング制御

- 役割: `routing` を中心に、FRR、bgpcfgd、fpmsyncd、routeorch、neighorch、vrforch、teamd 周辺を層として読む。
- 構成ページ案:
  - 全体像: FRR RIB、Linux kernel、APPL_DB、orchagent、ASIC FIB の分担。
  - コンポーネント: FRR、bgpcfgd、fpmsyncd、zebra、BfdOrch、RouteOrch、NeighOrch、VRFOrch。
  - データフロー: BGP route が FRR から fpmsyncd / APPL_DB / orchagent / SAI へ進む sequence。
  - 境界と契約: FRR config、FPM / dplane_fpm_sonic、ROUTE_TABLE、NEXT_HOP_GROUP_TABLE、CONFIG_DB BGP tables。
  - 内部メカニズム: BGP PIC、FG ECMP、WCMP、SRv6、MPLS、FIB pending、route install error handling。
- 統合する既存ページ: `docs/routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md`、`docs/routing/new-frr-sonic-communication-channel.md`、`docs/routing/bgp-loading-optimization-for-sonic.md`、`docs/routing/routing-and-next-hop-table-enhancement.md`、`docs/reference/cli/config-bgp.md`。
- 新規執筆の境界: BGP / VRF / MPLS / SRv6 の詳細は既存ページへ委譲し、章では FRR と SONiC DB / Orch の境界を解説する。
- 想定ボリューム: 6 ページ、約 12,000 字。

### 5. L2 / Overlay / Dual ToR

- 役割: `switching`、`overlay`、一部 `routing` を横断し、L2、LAG、VLAN、VXLAN、Dual ToR、MCLAG を data/control の境界で読む。
- 構成ページ案:
  - 全体像: L2 feature が CONFIG_DB、teamd、portsyncd、orchagent、SAI にどう分散するか。
  - コンポーネント: portmgrd、intfmgrd、teammgrd、teamsyncd、VxlanOrch、VnetOrch、MuxOrch、linkmgrd。
  - データフロー: VLAN / LAG / VxLAN / mux state の設定反映 sequence。
  - 境界と契約: PORT / VLAN / PORTCHANNEL / VXLAN_TUNNEL / VNET / MUX_CABLE tables、OpenConfig interfaces。
  - 内部メカニズム: view switching、Dual ToR state machine、EVPN-VXLAN multihoming、MC-LAG。
- 統合する既存ページ: `docs/switching/sonic-ip-lag-incremental-update.md`、`docs/overlay/vxlan-sonic.md`、`docs/overlay/active-active-dual-tor.md`、`docs/overlay/active-standby-dual-tor.md`、`docs/routing/evpn-vxlan-hld.md`。
- 新規執筆の境界: 個別機能の HLD はそのまま残し、章では L2 / overlay の daemon と DB の共通パターンを示す。
- 想定ボリューム: 5 ページ、約 9,000-11,000 字。

### 6. ACL / QoS / Telemetry / Counters

- 役割: `acl-qos`、`system`、`internals`、`reference` を横断し、パケット分類、queue、buffer、counter、telemetry を data plane の横串として読む。
- 構成ページ案:
  - 全体像: ACL/QoS は forwarding behavior と observability の両方にまたがる層であることを説明。
  - コンポーネント: AclOrch、BufferOrch、QosOrch、FlexCounter、counterpoll、watermark、CRM、telemetry agent。
  - データフロー: ACL_RULE / BUFFER_* / QUEUE / WRED_PROFILE が SAI object と counters に展開される sequence。
  - 境界と契約: SAI ACL / queue / scheduler / counter API、COUNTERS_DB、STATE_DB、CONFIG_DB reference。
  - 内部メカニズム: flex counter refactor、counter capability query、watermark、PFCWD、debug counter、DTel。
- 統合する既存ページ: `docs/acl-qos/acl-in-sonic.md`、`docs/acl-qos/sonic-qos-scheduler-and-shaping.md`、`docs/acl-qos/watermark-counters-in-sonic.md`、`docs/internals/sonic-flexcounter-refactor.md`、`docs/system/dataplane-telemetry-in-sonic.md`。
- 新規執筆の境界: CONFIG_DB table reference と feature HLD は詳細資料とし、章では「分類、制御、観測」の 3 観点で整理する。
- 想定ボリューム: 6 ページ、約 11,000-13,000 字。

### 7. Management Plane と OpenConfig

- 役割: `management` と `reference/yang`、`reference/cli` を縦串にし、CLI / REST / gNMI / KLISH / translib / OpenConfig 統合を説明する。
- 構成ページ案:
  - 全体像: 北側 API が CONFIG_DB / STATE_DB / APPL_DB に到達する経路。
  - コンポーネント: sonic-mgmt-framework、REST server、gNMI server、KLISH、Translib、Transformer、sonic-mgmt-common YANG。
  - データフロー: OpenConfig Set / RESTCONF / CLI が transformer を経由して CONFIG_DB に入る sequence。
  - 境界と契約: OpenConfig YANG、SONiC YANG、ABNF、JSON patch、GCU、RBAC / AAA / gNSI。
  - 内部メカニズム: gNMI subscription、master arbitration、save-on-set、model-based replace/delete。
- 統合する既存ページ: `docs/management/sonic-management-framework.md`、`docs/management/sonic-gnmi-server-interface-design.md`、`docs/management/openconfig-support-for-ethernet-interfaces.md`、`docs/management/sonic-cli-auto-generation-tool.md`、`docs/reference/yang/*.md`。
- 新規執筆の境界: API ごとの操作詳細は既存ページに委譲し、章では「同じ設定を複数入口から変更する時の収束点」を解説する。
- 想定ボリューム: 6 ページ、約 12,000 字。

### 8. Platform 層と PMON

- 役割: `platform` と `system` の platform monitoring 系を縦串にし、PMON、xcvrd、thermal、PSU/FAN、BMC、SAI bridging を説明する。
- 構成ページ案:
  - 全体像: Platform 層は ASIC 以外のハードウェア抽象化と監視を担うことを説明。
  - コンポーネント: pmon、xcvrd、thermalctld、psud、sensormond、pcied、storagemond、platform API。
  - データフロー: optical module / fan / PSU / thermal / PCIe 状態が STATE_DB / telemetry / CLI に出る sequence。
  - 境界と契約: sonic_platform Python API、platform.json、SAI capability、sysfs、BMC / Redfish。
  - 内部メカニズム: CMIS FSM、media settings、dynamic gearbox tuning、thermal policy、platform capability file。
- 統合する既存ページ: `docs/platform/sonic-sfp-refactoring.md`、`docs/system/platform-monitor-enhancement-design.md`、`docs/platform/sonic-thermal-control-design.md`、`docs/platform/platform-capability-file-enhancement.md`、`docs/system/sonic-bmc-platform-management-monitoring.md`。
- 新規執筆の境界: センサーや optics の個別 HLD はリンク先に任せ、章では platform API と DB 公開の共通構造を説明する。
- 想定ボリューム: 5 ページ、約 9,000-11,000 字。

### 9. Multi-ASIC / VoQ / Smart Switch

- 役割: `platform`、`system`、`architecture`、`overlay`、`acl-qos` に散らばる multi-ASIC、VoQ、Smart Switch、DASH、DPU 統合をまとめる。
- 構成ページ案:
  - 全体像: single ASIC SONiC から namespace / chassis / DPU 連携へ拡張される構造。
  - コンポーネント: per-ASIC Redis、namespace、chassis DB、fabric ASIC、DPU DB、HAMgrD、DASH Orch。
  - データフロー: NPU と DPU、front panel ASIC と fabric ASIC、CHASSIS_APP_DB の連携 sequence。
  - 境界と契約: namespace DB、chassisdb.conf、DPU overlay DB、gNMI feedback、system port / fabric port schema。
  - 内部メカニズム: VoQ system port、recirculation port、SmartSwitch HA、DPU reboot / upgrade / graceful shutdown。
- 統合する既存ページ: `docs/platform/1-sonic-on-multi-asic-platforms.md`、`docs/platform/voq-sonic.md`、`docs/architecture/smart-switch-database-design.md`、`docs/overlay/sonic-dash-hld.md`、`docs/system/independent-dpu-upgrade.md`。
- 新規執筆の境界: SmartSwitch / DASH / VoQ の個別文書を統合せず、章では「どの DB と namespace が誰の責任か」を新規に説明する。
- 想定ボリューム: 6 ページ、約 12,000-14,000 字。

### 10. Build / Image / Packaging

- 役割: `architecture`、`system`、`management`、`reference` を横断し、sonic-buildimage、Makefile.work、docker layer、ARM、SPM、SONIC_PACKAGES_LOCAL を説明する。
- 構成ページ案:
  - 全体像: SONiC image が Debian base、docker image、platform package、local packages から構成されることを説明。
  - コンポーネント: sonic-buildimage、Makefile.work、rules/*.mk、dockers、target/debs、sonic-package-manager。
  - データフロー: source → Debian package → docker image → SONiC image → upgrade / installer の sequence。
  - 境界と契約: platform build、SONIC_PACKAGES_LOCAL、build profile、RFS split、ARM cross / qemu-static。
  - 内部メカニズム: docker layer optimization、Debian upgrade cadence、container hardening、secure boot / secure upgrade との関係。
- 統合する既存ページ: `docs/architecture/build-system-improvements.md`、`docs/architecture/rfs-split-build-improvements-hld.md`、`docs/architecture/sonic-arm-architecture-support.md`、`docs/system/sonic-debian-upgrade-cadence.md`、`docs/management/sonic-application-extension-guide.md`。
- 新規執筆の境界: build 手順の羅列ではなく、成果物と依存関係の地図を新規に作る。詳細手順は既存 HLD / reference に委譲する。
- 想定ボリューム: 4 ページ、約 7,000-9,000 字。

### 11. Reboot / Resilience / Error Handling

- 役割: `system`、`switching`、`platform`、`architecture` の warm reboot、fast reboot、error handling、debug / techsupport を一つの信頼性章にまとめる。
- 構成ページ案:
  - 全体像: SONiC が reboot、service restart、SAI failure、resource exhaustion をどう扱うか。
  - コンポーネント: warmboot manager、orchagent restart check、syncd warm shutdown、ERROR_DB、CRM、system health、techsupport。
  - データフロー: warm reboot shutdown / restore / view comparison / reconciliation の sequence。
  - 境界と契約: WARM_RESTART tables、STATE_DB backup、SAI expected state、ERROR_DB、service readiness。
  - 内部メカニズム: libsairedis idempotence、ProducerStateTable view switching、multi-ASIC warm reboot、dump-on-SAI-failure。
- 統合する既存ページ: `docs/system/sonic-warm-reboot.md`、`docs/system/system-wide-warmboot.md`、`docs/system/swss-docker-warm-restart-code-reference.md`、`docs/switching/view-switching-in-producerstatetable.md`、`docs/architecture/error-handling-framework-in-sonic.md`。
- 新規執筆の境界: reboot 種別や CLI reference は既存ページへ委譲し、章では「状態を失わずに再開するための契約」を説明する。
- 想定ボリューム: 6 ページ、約 12,000 字。

### 12. 内部実装・開発・検証ガイド

- 役割: `internals`、`architecture`、`routing` の test plan / VS / GNS3 / PTF / PR test plan を縦串にし、開発者がコードと検証へ入る導線を作る。
- 構成ページ案:
  - 全体像: 読み物章から実装調査・検証へ進むための入口。
  - コンポーネント: orchagent 各 Orch、syncd、sairedis、flex counter、dump utility、sonic-vs、GNS3、PTF、sonic-mgmt。
  - データフロー: PR で設計変更を入れ、VS / PTF / sonic-mgmt / CI で検証する sequence。
  - 境界と契約: Orch の責務、syncd と SAI の境界、Redis schema、ZMQ ProducerStateTable、test plan の期待値。
  - 内部メカニズム: P4Orch、L3 scaling、counter initialization、dump utility、health-check。
- 統合する既存ページ: `docs/internals/p4-orchagent.md`、`docs/internals/l3-scaling-and-performance-enhancements.md`、`docs/architecture/sonic-on-gns3-vm.md`、`docs/architecture/steps-to-bring-up-sonic-vs.md`、`docs/routing/vrf-vs-test-plan.md`。
- 新規執筆の境界: 実装詳細の再掲は避け、どの subsystem をどの test bed で検証するかを整理する。
- 想定ボリューム: 5 ページ、約 9,000-11,000 字。

## 横断マトリクス

一次配置ベースで全 498 non-index ページを重複なく割り当てた。`reference` は CLI / CONFIG_DB / YANG の性質に応じて該当章へ振り分けている。`categories`、`guides`、`_meta` は `meta/restructure-plan.md` の 455 通常ページには含まれないが、現行 tree の non-index ページとして matrix に含める。

| 章 | architecture | routing | switching | overlay | acl-qos | system | management | platform | internals | reference | categories | guides | _meta | 計 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SONiC 全体アーキテクチャ | 10 | 0 | 0 | 0 | 0 | 14 | 0 | 0 | 0 | 0 | 10 | 4 | 1 | 39 |
| Redis DB と設定適用パイプライン | 2 | 3 | 2 | 1 | 4 | 3 | 10 | 0 | 3 | 55 | 0 | 0 | 0 | 83 |
| Data Plane プログラミング | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 15 |
| Control Plane とルーティング制御 | 0 | 39 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 21 | 0 | 0 | 0 | 60 |
| L2 / Overlay / Dual ToR | 0 | 5 | 13 | 5 | 0 | 0 | 0 | 0 | 0 | 29 | 0 | 0 | 0 | 52 |
| ACL / QoS / Telemetry / Counters | 0 | 0 | 0 | 0 | 27 | 0 | 0 | 0 | 0 | 22 | 0 | 0 | 0 | 49 |
| Management Plane と OpenConfig | 7 | 1 | 2 | 0 | 0 | 5 | 33 | 0 | 0 | 21 | 0 | 0 | 0 | 69 |
| Platform 層と PMON | 0 | 0 | 0 | 0 | 0 | 11 | 0 | 26 | 0 | 2 | 0 | 0 | 0 | 39 |
| Multi-ASIC / VoQ / Smart Switch | 3 | 0 | 0 | 3 | 0 | 2 | 0 | 11 | 0 | 0 | 0 | 0 | 0 | 19 |
| Build / Image / Packaging | 5 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 12 |
| Reboot / Resilience / Error Handling | 0 | 0 | 2 | 0 | 0 | 31 | 0 | 0 | 0 | 11 | 0 | 0 | 0 | 44 |
| 内部実装・開発・検証ガイド | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 0 | 0 | 0 | 0 | 17 |
| 合計 | 41 | 51 | 19 | 9 | 31 | 71 | 43 | 43 | 12 | 163 | 10 | 4 | 1 | 498 |

## 既存 area との関係

- `architecture`: 全体像、data plane、build、multi-ASIC、internals に分散する。既存 area のままでは「SONiC の階層」を読み始めにくいため、新章側では導入と cross-link を厚くする。
- `routing`: Control Plane 章が主担当。ただし EVPN / VXLAN / Dual ToR は L2 / Overlay 章、VRF / CONFIG_DB / gNMI は DB / Management 章にも二次参照する。
- `switching`: L2 / Overlay 章が主担当。ProducerStateTable view switching、OpenConfig VLAN / PortChannel は Reboot / Management にも二次参照する。
- `overlay`: L2 / Overlay 章と Multi-ASIC / Smart Switch 章に分かれる。DASH / DPU は platform ではなく distributed architecture として読む。
- `acl-qos`: ACL / QoS 章が主担当。counter / telemetry / CRM / SAI capability は Data Plane と Resilience にも接続する。
- `system`: Reboot / Platform / Management / Build / Overview に強く分散する。既存 area の横断性が高いため topics で最も導線改善効果が大きい。
- `management`: Management Plane 章が主担当。CONFIG_DB / YANG / GCU の話は DB 章と強く重なる。
- `platform`: Platform 章と Multi-ASIC 章に分かれる。SAI failure / capability は Data Plane / Resilience 章にも接続する。
- `internals`: 内部実装章が主担当。ただし Redis schema と ZMQ は DB 章、FlexCounter は ACL / QoS 章に移動しないリンクとして扱う。
- `reference`: 各章の末尾に「参照する CLI / CONFIG_DB / YANG」として紐付ける。reference は読み物本文へ統合せず、契約仕様として使う。

## Phase B の推奨着手順

1. Redis DB と設定適用パイプライン
2. SONiC 全体アーキテクチャ
3. Data Plane プログラミング
4. Control Plane とルーティング制御
5. Management Plane と OpenConfig
6. Reboot / Resilience / Error Handling
7. L2 / Overlay / Dual ToR
8. Platform 層と PMON
9. ACL / QoS / Telemetry / Counters
10. Multi-ASIC / VoQ / Smart Switch
11. Build / Image / Packaging
12. 内部実装・開発・検証ガイド

理由は、DB 章が全章の共通語彙を作り、全体アーキテクチャ章が読者の入口になるため。Data Plane、Control Plane、Management Plane を先に作ると、以後の feature 章で同じ説明を繰り返さずに済む。

## マッピング率

- 現行 tree の non-index Markdown: 498 ページ
- 本計画で一次配置したページ: 498 ページ
- マッピング率: 100%
- `meta/restructure-plan.md` の 455 通常ページに対するマッピング率: 100%。追加の `reference` 差分、`categories`、`guides`、`_meta` も補助導線として同時に配置済み。
