---
title: VoQ SONiC（distributed VoQ chassis / system-port / fabric）
area: platform
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/voq/voq_hld.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - DEVICE_METADATA
    - SYSTEM_PORT
    - VOQ_INBAND_INTERFACE
    - PORT
    - BGP_NEIGHBOR
  cli:
    - show chassis
    - show fabric
    - show system-port
  yang:
    - sonic-device_metadata
    - sonic-system-port
---

!!! info "裏取りステータス: code-verified（要点裏取り）"
    `DEVICE_METADATA.{switch_type,switch_id,sub_role}` は `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-device_metadata.yang`、SYSTEM_PORT / VOQ_INBAND_INTERFACE / chassis BGP は同 repo の `sonic-system-port.yang` / `sonic-voq-inband-interface.yang` / `sonic-bgp-voq-chassis-neighbor.yang`、CLI は `sonic-utilities/show/{chassis_modules,fabric}.py` および `chassis_modules.py:system_ports`（`voqutil`）で確認済み。distributed VoQ counter / fabric port などの詳細は派生 HLD ページを参照。

# VoQ SONiC（distributed VoQ chassis / system-port / fabric）

## 概要

複数の Network Processing Unit (NPU / line card) を fabric card で繋ぎ、外側からは「1 台のスイッチ」に見える **分散 VoQ chassis** を SONiC で動かす設計[^1]。

要点:

- **Virtual Output Queue (VoQ)**: 入力側 NPU が、出力側 NPU の各 port / class に対する仮想キューを持つ。HoL ブロッキングを避け、輻輳判定を fabric を跨いで行う
- **system-port**: chassis 全体で一意な論理 port 識別子。各 NPU の物理 port は system-port にマップされる
- **distributed control plane**: BGP / FRR は複数 NPU 上で協調する。各 NPU の supervisor / control plane と fabric が連動

## 動作仕様

```mermaid
flowchart LR
    subgraph LineCardA[Line card A]
      NPUA[NPU A]
    end
    subgraph LineCardB[Line card B]
      NPUB[NPU B]
    end
    subgraph FabricCard[Fabric card]
      FAB[(fabric ASIC)]
    end
    NPUA <--> FAB
    NPUB <--> FAB
    NPUA -. system-port view .- NPUB
```

主要な構成要素[^1]:

- **`DEVICE_METADATA|localhost.switch_type=voq`**: chassis-wide で VoQ モードを示す
- **`SYSTEM_PORT`**: chassis 内のすべての port の論理マップ。`switch_id`、`core_index`、`core_port_index`、`speed` 等
- **`VOQ_INBAND_INTERFACE`**: chassis 内 NPU 間制御 plane 通信用 inband interface
- **fabric port**: NPU↔fabric 接続を表す port。CRM / link state / counter は専用扱い
- **chassis-wide BGP**: line card ごとに ASN / loopback を分けず chassis として 1 つの BGP speaker（または multi-speaker 連携）として振る舞う設計

## 設定

### 関連する CONFIG_DB

| Table | 説明 |
|-------|------|
| `DEVICE_METADATA` | `switch_type=voq`、`sub_role`、`switch_id`、`max_cores` |
| `SYSTEM_PORT` | chassis 全 port の論理識別 |
| `VOQ_INBAND_INTERFACE` | NPU 間 control plane の inband |
| `PORT` | 通常の per-NPU port（system-port にも紐づく） |
| `BGP_NEIGHBOR` | chassis-wide で構成 |

### 関連する CLI

| Command | 用途 |
|---------|------|
| `show chassis` | chassis モジュール一覧 |
| `show chassis modules status` | line card / fabric の状態 |
| `show fabric counters` | fabric port の counter |
| `show system-port` | system-port 一覧 |
| `show interfaces counters fabric` | fabric 方向 |

## 制限事項

- **対応 ASIC が限定的**: VoQ アーキテクチャをサポートする NPU / fabric chip でのみ動く
- **single-asic 前提機能との非互換**: 一部の機能（VLAN、特定の ACL）は VoQ 上で挙動が異なるか未対応
- **show コマンドの単位**: 既存 `show interfaces counters` の意味が VoQ では port / system-port / fabric のどれか曖昧になりやすい
- **HLD は包括設計のみ**: バッファ計算、scheduler、warmboot、congestion 詳細は派生 HLD を参照

## 干渉する機能

- **distributed VoQ counter**: 入出力 NPU を跨ぐ統計の集計（同 area の別 HLD）
- **fabric port support**: fabric port 単独の管理（同 area）
- **everflow on VoQ chassis**: mirror の宛先解決が system-port 単位
- **single-asic VoQ fixed system**: VoQ 機能を 1 ASIC platform で適用する派生（同 area 別 HLD）
- **chassis BGP / chassis-wide management**: control-plane 側 HLD 群

## トラブルシューティング

- system-port が出ない → `DEVICE_METADATA.switch_type=voq` と `SYSTEM_PORT` の populate 状態を確認
- fabric link 不安定 → `show fabric counters errors`、cable 状態、neighbor NPU の状態
- 統計が物理 port と合わない → VoQ 集計の単位（system-port vs front-panel）を確認

## 引用元

[^1]: `sonic-net/SONiC` `doc/voq/voq_hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- DEVICE_METADATA.switch_type=voq の現行 sonic-yang-models 取り込み確認
- SYSTEM_PORT / VOQ_INBAND_INTERFACE スキーマの現行値とフィールド差分確認
- show chassis / show fabric / show system-port CLI の sonic-utilities 取り込み確認
- 対応 NPU / fabric platform リストの現行範囲確認
- VoQ chassis-wide BGP（FRR multi-instance / ASN 共有）の現行設計確認
- single-asic VoQ fixed system / fabric port / VoQ counter HLD との実装連携確認
-->
