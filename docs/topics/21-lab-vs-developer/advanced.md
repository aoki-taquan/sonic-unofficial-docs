---
title: 発展トピック
description: 発展トピック — 評価・初学を超えて、CI / 大規模 lab / DPU 検証まで踏み込むときに開く話題を集めます。基本的にはここのリンク先
  HLD を直接読むのが早く、本ページは「どれを開くか」のしおりです。
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
related:
  cli:
  - show acl
  - config acl
  - show pfc
  - config vxlan
  config_db:
  - ACL_RULE
  - ACL_TABLE
  - PFC_WD
  - VXLAN_TUNNEL
  - VXLAN_EVPN_NVO
  - CHASSIS_MODULE
  - MID_PLANE_BRIDGE
  yang:
  - sonic-vxlan
  - sonic-pfc-priority-queue-map
  - sonic-pfc-priority-priority-group-map
  - sonic-srv6
  - sonic-pfcwd
  - sonic-buffer-pool
  - sonic-buffer-profile
---

# 発展トピック

評価・初学を超えて、CI / 大規模 lab / [DPU](../../reference/glossary.md#term-dpu) 検証まで踏み込むときに開く話題を集めます。基本的にはここのリンク先 [HLD](../../reference/glossary.md#term-hld) を直接読むのが早く、本ページは「どれを開くか」のしおりです。

## DASH SONiC KVM

[DASH](../../reference/glossary.md#term-dash)（Disaggregated API for [SONiC](../../reference/glossary.md#term-sonic) Hosts）の DPU 検証を実機 [SmartSwitch](../../reference/glossary.md#term-smartswitch) なしで行うための環境です。データプレーンは BMv2、control plane は SONiC 側、というハイブリッド構成で、[ENI](../../reference/glossary.md#term-eni) / [ACL](../../reference/glossary.md#term-acl) / metering といった DASH HLD の核を仮想で踏むことができます。詳細は [DASH SONiC KVM](../../overlay/dash-sonic-kvm.md) を参照します。

DASH 章本文の機能仕様と組で読むのが前提で、DPU の HW 機能（offload 性能、PPS など）はこの環境では測れません。

## ALViS / KNE と CI 連携

ALViS / KNE は、多数ノードを軽量にデプロイしたい場合の選択肢です。CI で `n` 台の SONiC を立てる、KNE で他 NOS と混在 topology を組む、Pod 単位で個別 reload するなどの運用が想定されています。設計と制約は [Alpine 仮想 SONiC](../../architecture/alpine-high-level-design.md) を読みます。

実装は本家 SONiC-VS と一致しない部分があるため、機能完全性が必要なテストは SONiC-VS で、ノード数が必要なテストは ALViS で、と棲み分けます。

## 仮想で再現しづらい依存

章本文を読むときに「これは VS では確かめられない」と分けるべき要素を、まとめておきます。

| 領域 | VS で困る理由 | 実機 / 別環境が要る |
| --- | --- | --- |
| optics / PHY / CMIS | 物理 transceiver がない | 実機 + 対象 optics |
| buffer / [PFC](../../reference/glossary.md#term-pfc) / watermark / queue | [SAI](../../reference/glossary.md#term-sai) VS の capability 範囲外 | [ASIC](../../reference/glossary.md#term-asic) 実機、または ASIC simulator |
| thermal / PSU / fan / BMC / PCIe | platform docker が dummy | 実機 platform |
| HW offload を伴う mux / [EVPN](../../reference/glossary.md#term-evpn) encap / DASH 高速 path | data plane が Linux / BMv2 | 対応 ASIC / DPU |
| 微小遅延・micro-burst・線速 drop | Linux datapath 性能 | 専用テスト機材 |
| reboot 高速化検証（fast / warm / express） | platform 依存と timing 依存 | 実機 + telemetry。[Reboot / Upgrade / Lifecycle 章](../11-reboot/index.md) も参照 |

これらは仮想 lab の欠点ではなく、対象範囲が違うだけです。HLD を読むときに「VS の試験で十分」「実機が要る」を区別すると、章本文の限界も自然に見えてきます。

## CI で test plan をどう束ねるか

機能ごとの test plan は HLD と並行して存在しますが、CI 側で実際に回る集合は test plan の一部に絞られます。読み手が「この章は CI でどこまで担保されているか」を知りたいときに参照する順序は次のとおりです。

1. 機能章本文（仕様）
2. 該当 test plan（検証境界）
3. test plan で要求される topology / PTF（[DIP=SIP PTF validation HLD](../../architecture/dip-sip-ptf-validation-high-level-design.md) など共通設計）

CI 構成自体（GitHub Actions、Azure Pipelines）は本リポジトリの非公式ドキュメントの対象外です。upstream SONiC repo の `.github` と `azure-pipelines.yml` が一次資料になります。

## 発展トピック

- **Multi-DUT topology in [sonic-mgmt](../../reference/glossary.md#term-sonic-mgmt)**: 複数 DUT を仮想で組み、Dual-ToR / MC-[LAG](../../reference/glossary.md#term-lag) / Chassis シナリオを CI で回す。ansible inventory と PTF docker を組合せる。
- **kvm 仮想 SONiC chassis**: 仮想 supervisor + 仮想 line card 構成を kvm 上で動かす。chassis_db の挙動を VS で検証できる。
- **ptf-py3 と scapy 拡張**: data plane 検証で複雑 packet を生成。Path Tracing、[SRv6](../../reference/glossary.md#term-srv6)、[VXLAN](../../reference/glossary.md#term-vxlan)、EVPN などで重宝。
- **Code coverage と gcov**: SONiC binary を gcov-enabled で build し、CI 経路で coverage を集計する取り組み。orch の race condition 検出に役立つ。
- **fuzz testing**: [gNMI](../../reference/glossary.md#term-gnmi) / [gNOI](../../reference/glossary.md#term-gnoi) server や CLI parser に対する fuzz テスト。security 章 ([15](../15-security-aaa/index.md)) と相互参照。

## 既知の制約と回避方法

- **VS と実機の SAI 差**: SAI VS は CPU 実装で、ASIC 固有の制約 ([TCAM](../../reference/glossary.md#term-tcam) / buffer / pipeline depth) を再現しない。機能合格 ≠ 実機合格。
- **CI 時間と並列化**: 全 test plan を回すと CI が長い。差分テスト (changed area のみ) と nightly full の二段運用が現実的。
- **PTF environment dependency**: PTF docker のバージョンと test plan の整合が崩れると失敗する。pin versioning を CI で固定する。
- **DASH KVM の性能限界**: BMv2 ベースなので scale / throughput は限定的。機能テスト専用と割り切る。

## 将来計画 / ロードマップ

- multi-DUT / multi-ASIC topology の CI 標準化拡大。
- KNE / ALViS と SONiC-VS の機能ギャップ整理と互換 layer 整備。
- Code coverage / mutation testing の標準化。
- DASH KVM の HLD 完成と community 投入。

## virtual SONiC でのトポロジ自動化

実機 lab を持たないチームが CI / 教育 / RFE 試作で再現性を出すための主要パスは三つある。

- **`sonic-mgmt` 標準 topology**: `ansible/vars/topo_*.yaml` で `t0`、`t1-lag`、`ptf32`、`dualtor` などの canonical topology を宣言する。`testbed.csv` と `inventory` を組み合わせると、virtual chassis / Dual-ToR / Multi-DUT も同じテンプレで起動できる。
- **KNE / kne-topologies**: Kubernetes 上に SONiC-VS pod を並べる。SONiC を他 NOS (Arista cEOS、Juniper cRPD 等) と mix した topology が必要なときに採用しやすい。`kne create topology.pb.txt` で立ち上げ、CNI 経由で link を張る。
- **containerlab**: `clab` の `kind: sonic-vs` ノードで軽量に複数 DUT を並べる。CI runner のローカル dev loop に近く、`docker compose` 感覚で扱える。

いずれも image は `target/sonic-vs.img.gz` が起点で、`docker-sonic-vs` を直接 docker run する経路と、kvm に load する経路の二択になる。CI で何百並列も起動するなら docker 直走、kernel datapath 検証が要るなら kvm を選ぶ。

## kvm-vs-physical の差分

virtual / 物理間で動作が乖離する代表領域は次のとおり。

| 領域 | virtual (VS / kvm) | 物理 |
| --- | --- | --- |
| Forwarding plane | SAI VS = CPU 実装 | ASIC pipeline |
| Counters / [WRED](../../reference/glossary.md#term-wred) / queue depth | dummy 値 / 近似 | 実時間 telemetry |
| Link timing (carrier up/down) | ms 単位の Linux event | optics / PHY の物理遅延 |
| MAC learning / flooding | bridge based 簡略 | ASIC [FDB](../../reference/glossary.md#term-fdb) hashing |
| LAG hashing | Linux team driver | SAI hash + UDF |
| [BFD](../../reference/glossary.md#term-bfd) micro / sub-ms timer | jiffies 制約 | HW BFD offload |

機能 path の論理確認は VS で十分だが、性能 / timing / counter は実機が前提。test plan には `vs_supported: yes/no` メタを置き、CI 側で skip 判定する運用が一般的。

## debug build と diagnostics image

`make` には debug 用のフラグ群がいくつかある。Issue 再現用に常備しておくと便利。

- `SONIC_DEBUGGING_ON=y`: `-O0 -g` / strip 抑止で symbol 付き docker を生成。`gdb` / `perf` / `bcc-tools` 連携が前提。
- `ENABLE_PY_DEBUG=y`: python パッケージを debug build。
- `INCLUDE_KERNEL_DEBUG_TOOLS=y` / `INSTALL_DEBUG_TOOLS=y`: image に `strace` / `tcpdump` / `bpftrace` を含める。
- `DEFAULT_USERNAME` / `DEFAULT_PASSWORD` 変更: lab image で SSH 鍵管理を簡素化。

`sonic-installer` には `binary` / `firmware` の他に `coredump` 経路があるため、debug build は coredump enable と SCP destination 設定を [ZTP](../../reference/glossary.md#term-ztp) 段で済ませておくとデバッグサイクルが速い。

## 関連 RFC / 仕様書

- [P4 Behavioral Model (BMv2)](https://github.com/p4lang/behavioral-model) — DASH KVM の data plane
- [KNE (Kubernetes Network Emulation)](https://github.com/openconfig/kne) — topology orchestration
- [RFC 2544](https://datatracker.ietf.org/doc/html/rfc2544) — benchmark methodology (実機テスト参考)
- [RFC 6815](https://datatracker.ietf.org/doc/html/rfc6815) — IETF テスト共通フォーマット

## upstream 開発の最新動向

- `sonic-mgmt` で multi-DUT topology、PTF docker、test plan の拡張 PR が継続。
- `sonic-buildimage` で VS 構成と DASH KVM の整備 PR が散発的。
- KNE / ALViS 系の community 連携で SONiC-VS イメージ整備と config template 提供が議題化。
- CI の Azure Pipelines / GitHub Actions 共通化議論が継続している。

<!-- glossary-links-injected: ec18b66e3507 -->
