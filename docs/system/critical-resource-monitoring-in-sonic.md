---
title: Critical Resource Monitoring（CRM・SAI 表枯渇のしきい値監視）
area: system
verification: hld-only
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/crm/Critical-Resource-Monitoring-High-Level-Design.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - CRM
  cli:
    - crm config
    - crm show
  yang:
    - sonic-crm
---

!!! warning "裏取りステータス: HLD-only"
    CrmOrch / SAI Object availability API の現行 master 取り込み状況、generic-sai-extension HLD（同 area）との関係は未確認。

# Critical Resource Monitoring（CRM・SAI 表枯渇のしきい値監視）

## 概要

ASIC 側のリソース（route 表エントリ数、neighbor 数、ACL counter 数、FDB 数、NAT 数 等）は **ハードウェアサイズで上限が決まっている**。CRM はそれらの **使用量をポーリングし、しきい値超えで警告/critical を出す** 仕組み[^1]。

主目的:

- ASIC 表の枯渇を **障害発生前に** 通知
- 使用量・上限値を運用者が `crm show` で常時確認できるようにする
- しきい値の dynamic / static、`high` / `low` の区別

## 監視対象

主要な resource 種別（HLD ベース）[^1]:

- L3: `IPV4_ROUTE`, `IPV6_ROUTE`, `IPV4_NEIGHBOR`, `IPV6_NEIGHBOR`, `IPV4_NEXTHOP`, `IPV6_NEXTHOP`
- L3 group: `NEXTHOP_GROUP`, `NEXTHOP_GROUP_MEMBER`
- L2: `FDB_ENTRY`
- ACL: `ACL_TABLE`, `ACL_GROUP`, `ACL_ENTRY`, `ACL_COUNTER`
- DNAT/SNAT: `DNAT_ENTRY`, `SNAT_ENTRY`, `IPMC_ENTRY`
- Tunnel / SRv6 等: 後発で追加

## 動作仕様

```mermaid
flowchart LR
    CFG[CONFIG_DB CRM] --> CO[CrmOrch]
    CO --> SAI[(SAI object availability API)]
    CO --> COUNTERSDB[(COUNTERS_DB CRM)]
    CO --> SYS[syslog\n(WARN / CRITICAL)]
    USR[管理者] --> CLI[crm show]
    CLI --> COUNTERSDB
```

しきい値モード[^1]:

- **percentage**: 上限の % で `high_threshold` / `low_threshold` を設定
- **used**: 絶対使用量
- **free**: 残量

`high` を超えると WARN/CRIT、`low` を下回ると clear、`free` モードはその逆。ポーリング周期は `polling_interval`（既定数秒〜数十秒）。

## 関連 CONFIG_DB

| Key | 説明 |
|-----|------|
| `CRM|Config` | `polling_interval`、各 resource ごとに `<r>_threshold_type`、`<r>_high_threshold`、`<r>_low_threshold` |

## 関連 CLI

| Command | 用途 |
|---------|------|
| `crm config polling interval <n>` | 周期設定 |
| `crm config thresholds <r> type <p|u|f>` | mode |
| `crm config thresholds <r> high <n>` / `low <n>` | しきい値 |
| `crm show resources [all|ipv4 route|...]` | 残量と使用量 |
| `crm show thresholds` | 現行しきい値 |

## 制限事項

- **SAI 実装が availability API を返す必要がある**: vendor 側で未対応の resource は値が出ない
- **フィードバック先**: WARN/CRIT は syslog のみで自動 recovery アクションは無い（運用側で対応）
- **resource ごとのコスト**: 多 resource を高頻度ポーリングすると ASIC SDK が重くなる
- **ACL counter / FDB**: SDK の query が高コストな場合があり推奨 polling 間隔が大きい

## 干渉する機能

- **generic SAI extension CRM (`generic-sai-extension-critical-resource-monitoring-crm`)**: HLD レベルの拡張。新 resource 追加の枠組み（同 area の別 HLD）
- **system health monitor**: critical 通知の集約
- **NAT / mux / SRv6 / multi-asic**: 各機能側で resource 種別を増やす

## トラブルシューティング

- `crm show` で値が `N/A` → SAI vendor の object_availability 実装の有無
- しきい値未通知 → polling_interval、syslog の rate-limit、threshold mode の確認
- counter が振動する → polling 周期と実際の使用量変動の解像度差

## 引用元

[^1]: `sonic-net/SONiC` `doc/crm/Critical-Resource-Monitoring-High-Level-Design.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- CrmOrch の現行 master 実装（CRM resource の追加範囲）の確認
- SAI object availability API（SAI_OBJECT_TYPE_*_AVAILABLE_*) の community SAI 取り込み確認
- CONFIG_DB CRM スキーマの現行 sonic-yang-models 取り込み確認
- crm config / crm show CLI の sonic-utilities 取り込み確認
- generic-sai-extension CRM HLD との実装統合確認
- system health monitor / telemetry dial-out との連携の現行実装確認
-->
