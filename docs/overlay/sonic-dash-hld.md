---
title: SONiC-DASH（Disaggregated APIs for SONiC Hosts）アーキテクチャ概観
description: SONiC-DASH（Disaggregated APIs for SONiC Hosts）のアーキテクチャ概観。SmartSwitch DPU や appliance card 上で SONiC が多数の ENI（Elastic Network Interface）を管理し、VNet / ACL / metering / Service Tunnel / Private Link のデータプレーン処理を行う仕組みを解説する。API・Orch・CONFIG_DB / APP_DB スキーマの全体像を示す概観ハブページ。
area: overlay
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/SONiC
  path: doc/dash/dash-sonic-hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - DASH_VNET
  - DASH_ENI
  - DASH_ROUTE
  - DASH_ACL_GROUP
  - DASH_ACL_RULE
  - VNET
  cli:
  - show acl
  - config acl
  - config vnet
  yang:
  - sonic-vnet
  - sonic-crm
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含む。機能の概念・設定・運用を読み物として読みたい場合は [Topics 13 章: DASH / SmartSwitch](../topics/13-dash-smartswitch/index.md) を参照。
<!-- /topics-tip -->

!!! success "裏取りステータス: code-verified（中核アーキテクチャの抜粋範囲のみ）"
    `sonic-swss/orchagent/dash/dashorch.h` L63 `class DashOrch : public ZmqOrch`、`dashvnetorch.cpp` L49-50 で `APP_DASH_VNET_TABLE_NAME` / `APP_DASH_VNET_MAPPING_TABLE_NAME` 操作、`dashaclorch.cpp` / `dashmeterorch.cpp` / `dashhaorch.cpp` / `dashhafloworch.cpp` / `dashenifwdorch.cpp` / `dashcounter.cpp` で各 Orch を確認。`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dash.yang` L36 `container DASH_VNET` / L119 `container DASH_ENI` で YANG を確認、`sonic-buildimage/src/sonic-dash-api` を確認（verified 2026-05-09）。

!!! info "詳細は派生ページへ分割済み"
    本ページは **概観 + 元 HLD の章扉** として残し、詳細は以下の 3 派生ページに分割した:

    - [SONiC-DASH 概念](sonic-dash-hld-concepts.md) — ENI / VNet / routing_type / ACL ステージ / メータリング / ST / PL / FastPath / FNIC の意味論
    - [SONiC-DASH 内部実装](sonic-dash-hld-internals.md) — DASH APP DB スキーマ全テーブル、SAI DASH API マッピング、dashorch サブ Orch 構成、暗黙削除、SWSS Lite、Underlay routing
    - [SONiC-DASH 運用](sonic-dash-hld-operations.md) — CLI、設定例（VNet-VNet / ST / PL / Meter）、redis / state 確認、トラブルシュート

# SONiC-DASH（Disaggregated APIs for SONiC Hosts）アーキテクチャ概観

## 概要

[DASH](../reference/glossary.md#term-dash)（**Disaggregated APIs for [SONiC](../reference/glossary.md#term-sonic) Hosts**）は、[SmartSwitch](../reference/glossary.md#term-smartswitch) [DPU](../reference/glossary.md#term-dpu) や appliance card 上で SONiC スタックが多数の **[ENI](../reference/glossary.md#term-eni) (Elastic Network Interface)** を扱い、各 ENI に対する VNet / [ACL](../reference/glossary.md#term-acl) / metering / Service Tunnel / Private Link 等のデータプレーン処理を行うための仕組み[^1]。本ファイルは DASH を SONiC 内に乗せるための実装側 [HLD](../reference/glossary.md#term-hld)（API / Orch / Config DB / APP DB スキーマ）を扱う。一般 DASH 概念は [DASH 高位 HLD](https://github.com/sonic-net/DASH/tree/main/documentation/general/dash-high-level-design.md) を参照。

## 動作仕様

### 構成オブジェクト（抜粋）

```text
ENI (Elastic Network Interface)
└── VNet（VxLAN VNI / underlay 設定）
    ├── Outbound routing rules → routing_type（vnet, vnet_direct, direct, ...）
    ├── Inbound routing rules（PA Validation 含む）
    ├── ACL（v4/v6, Inbound/Outbound, ACL Group + Tag）
    ├── Metering (per-ACL / per-rule)
    ├── Service Tunnel (ST)
    └── Private Link (PL)
```

ENI ごとに上記のオブジェクト群がぶら下がる。複数 ENI を 1 DPU 上で並走させるのが DASH の設計目標。

### 主要 CONFIG_DB / DASH APP DB テーブル（v2.6.1 時点）

```text
DASH_APPLIANCE              ; appliance 1 つの基本情報、local Region ID
DASH_VNET                   ; VNet 定義（VNI 等）
DASH_ENI                    ; ENI 個別属性
DASH_ENI_ROUTE              ; ENI 単位のルートグループ参照
DASH_ROUTE_GROUP            ; route rule の集合
DASH_ROUTE                  ; outbound route rule（priority キー込み）
DASH_ROUTE_RULE             ; inbound route rule
DASH_PA_VALIDATION          ; inbound PA validation
DASH_VNET_MAPPING_TABLE     ; outbound VNI 解決
DASH_ACL_GROUP / DASH_ACL_RULE
DASH_METER_*
DASH_TUNNEL                 ; Service Tunnel / inner encap
DASH_PL_*                   ; Private Link
DASH_FNIC_*                 ; Floating NIC（v2.4 で追加）
DASH_PL_REDIRECT_MAP        ; v2.5 で追加
```

完全なフィールドリストは HLD §3 を参照。

### モジュール構成

```mermaid
flowchart LR
    GNMI[gNMI client] --> SVR[gNMI server]
    SVR --> CDB[(CONFIG_DB DASH_*)]
    CDB --> DM[DASH Mgr]
    DM --> APP[(APP_DB / DASH APP DB)]
    APP --> DO[DASH Orch]
    DO -->|SAI DASH APIs| DPU[(DPU / appliance ASIC)]
```

DPU 上の DASH [SAI](../reference/glossary.md#term-sai) 実装が、ENI に対する **outbound routing → ACL → metering** や **inbound PA validation → ACL → routing** のパイプラインを実行する。詳細は HLD §2 のパケットフロー図を参照[^1]。

### 主要シナリオ（HLD §1.1 抜粋）

- **VNet 内転送**: ENI → outbound route → VxLAN encap → リモート [VTEP](../reference/glossary.md#term-vtep)
- **Service Tunnel (ST)**: VNet 内とは別経路で SLB / NSG への中継
- **Private Link (PL)**: 別 VNet 上のサービスに対する private endpoint 経由のアクセス
- **PL-NSG**: Private Link with Network Security Group
- **FastPath**: 一部のフローを accelerated 経路で最適化（v1.6）
- **Floating NIC (FNIC)**: VM 移動時に ENI 設定をフォローする抽象（v2.4）

### Scaling 要件（HLD §1.4）

- ENI 数: 数千〜数万（DPU プラットフォーム依存）
- ルート数: ENI あたり 数千 〜 数 100k
- ACL ルール: ENI あたり数千

## 設定

### 関連する CONFIG_DB

| Prefix | 説明 |
|--------|------|
| `DASH_*` | 上記テーブル群すべて |

ユーザはコントローラ／[gNMI](../reference/glossary.md#term-gnmi) 経由で投入。手書き想定なし。

### 関連する CLI

HLD には CLI 体系の正式定義は無く、gNMI / RestAPI 経由の設定を主とする。`show dash` 系の表示 CLI が存在し得るが、HLD §3.4 を参照。

### 関連する YANG

DASH は OpenConfig 由来の API 設計を採るが、SONiC 内部の [YANG](../reference/glossary.md#term-yang) 反映は HLD で詳細規定なし。

### 設定例

`HLD §3.6 Example Configuration` を参照。例として 1 ENI に outbound 経路と ACL を入れるシナリオが示されている。

## 制限事項

- HLD 全体は 118KB 超で、本ページは中核オブジェクトと参照リンクに留める。**詳細仕様は必ず HLD `doc/dash/dash-sonic-hld.md` を参照すること**。
- DASH は DPU / SmartSwitch 専用機能で、通常の SONiC [NPU](../reference/glossary.md#term-npu) 上では動かない。
- 各オブジェクトのフィールドは v2.0 以降頻繁に更新（v2.4 で `DASH_TUNNEL` / FNIC、v2.5 で PL redirect map、v2.6 で route rule priority のキー化、v2.6.1 で `trusted_vnis` → `trusted_vnis_list` 改名）[^1]。
- SAI DASH API は OCP SAI とは別ツリーで開発されており、community SAI への取り込み状況は時期によって異なる。
- **ACL 設定の順序依存性バグ** ([sonic-swss#3069](https://github.com/sonic-net/sonic-swss/issues/3069)): DASH の ACL 設定で複数のオブジェクト（ENI / VNet / ACL グループ等）を投入する順序が変わると、最終的な ACL 設定が誤った状態になることがある。設定の到着順にオーケストレーターが処理するため、依存関係のある設定が逆順で届いた場合に不整合が生じる。DASH 設定を一括投入する場合は、依存オブジェクトを先に作成する順序を保証すること。

## 干渉する機能

- **VxLAN / VNet (既存 SONiC NPU 機能)**: DASH の VNet と既存 NPU 上の [VNET](../reference/glossary.md#term-vnet) は概念的には同様だが、実装パスは独立（DASH は DPU 側 SAI で完結）。
- **ACL / Metering**: DASH のものは ENI 単位で独立。NPU 側 ACL とは別。
- **SmartSwitch HA**: ハイアベイラビリティペア DPU 間で DASH 状態を同期する設計が別 HLD（`smart-switch-ha-hld.md`）で扱われ、`pinned_state` 等で本ページの後発機能と連動する。
- **Floating NIC (FNIC)**: VM ライブマイグレーション時の ENI 追従。複雑な状態機械を持つ。

## トラブルシューティング

- ENI が出ない → DASH_APPLIANCE / DASH_ENI / DASH_VNET の参照整合を確認。
- 外向き / 内向きで ACL 適用順が想定と違う → HLD §2 のパケットフロー図と routing_type の対応を確認。
- メータリングの値が出ない → DASH_METER_* テーブルが対応する ACL ルールに紐付いているかを確認。

### コマンド例

DASH ENI / VNET 経路と DPU 上のデータパスを確認する。

```bash
# DASH / ENI の状態
show dash eni
show dash vnet
redis-cli -n 4 keys 'DASH_ENI_TABLE:*'
docker exec swss orchagent_restart_check 2>&1 | tail
```

## 引用元

[^1]: `sonic-net/SONiC` `doc/dash/dash-sonic-hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: DASH と SmartSwitch](../topics/13-dash-smartswitch/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: c5c8b661ae7e -->
