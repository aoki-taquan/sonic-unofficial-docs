---
title: アーキテクチャ
description: アーキテクチャ — gNMI / REST のリクエストが CONFIG_DB に到達するまでの経路は、入口の transport が違っても中間層
  (Translib / Transformer) で合流する。
area: topics
verification: code-verified
last_verified: 2026-06-04
sources:
- repo: sonic-net/sonic-gnmi
  path: proto/sonic.proto
  ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
- repo: sonic-net/sonic-gnmi
  path: sonic_data_client/db_client.go
  ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
- repo: sonic-net/sonic-mgmt-common
  path: translib/subscribe_notify.go
  ref: f71cf829883c36963455cf4d90fe16dae35f0b80
related:
  cli:
  - show gnmi
  - config gnmi
  config_db:
  - TELEMETRY
  - TELEMETRY_CLIENT
  yang:
  - sonic-telemetry
---

# アーキテクチャ

[gNMI](../../reference/glossary.md#term-gnmi) / REST のリクエストが [CONFIG_DB](../../reference/glossary.md#term-config_db) に到達するまでの経路は、入口の transport が違っても中間層 (Translib / Transformer) で合流する。ここでは「どの daemon を通り、どの [YANG](../../reference/glossary.md#term-yang) model がいつ validation するか」を追う。

## 全体フロー

```mermaid
graph TD
  C1[gRPC client] --> G[gNMI server]
  C2[REST client] --> R[REST server]
  C3[CLI / KLISH] --> CL[click commands]
  G --> T[Translib]
  R --> T
  CL --> T
  T --> TF[Transformer]
  TF --> Y[YANG validation]
  Y --> CDB[(CONFIG_DB)]
  CDB --> SWSS[swss / orchagent]
  SWSS --> SAI[syncd / SAI]
  CDB -.config subscribe.-> G
  APPL[(STATE_DB / COUNTERS_DB / APPL_DB)] -.state/telemetry stream.-> G
```

REST と gNMI server は同じ telemetry container で動き、Translib 経由で OpenConfig / [SONiC](../../reference/glossary.md#term-sonic) YANG をどちらも扱う。Subscribe (gNMI streaming) の主な対象は運用状態を持つ [STATE_DB](../../reference/glossary.md#term-state_db) / [COUNTERS_DB](../../reference/glossary.md#term-counters_db) / [APPL_DB](../../reference/glossary.md#term-appl_db) であり、CONFIG_DB は「設定変更そのものを観測したい」ケースで使う補助的な subscribe target という位置付けになる。`sonic-gnmi/proto/sonic.proto` の `Target` enum でも APPL_DB / [ASIC_DB](../../reference/glossary.md#term-asic_db) / COUNTERS_DB / CONFIG_DB / STATE_DB / CHASSIS_STATE_DB が同列に列挙されており、DB を問わず Redis keyspace notification 経由で stream できる構造になっている[^subscribe-targets]。

詳細な server 内部設計は [gNMI server interface design](../../management/sonic-gnmi-server-interface-design.md) と [Management Framework 全体像](../../management/sonic-management-framework.md) を参照する。

## Translib と Transformer の責務

- **Translib**: 上位 API。Get / Set / Subscribe を YANG パス単位で受け付け、リクエストを Transformer に渡して内部表現に直す。OpenConfig パスと SONiC YANG パスの両方を受ける。
- **Transformer**: YANG ノードと CONFIG_DB テーブル/カラムの対応規則を持ち、片方向ではなく Get と Set 両方に効く双方向の写像を行う。複雑な依存 (たとえば [VLAN](../../reference/glossary.md#term-vlan) member と [LAG](../../reference/glossary.md#term-lag) の整合) は Transformer のロジックで吸収する。

OpenConfig replace / delete を CONFIG_DB に正しく落とすために、Transformer は単なるフィールド変換ではなく**モデル意味論を保つ replace / delete** を実装する。挙動の詳細は [Model-based replace/delete in Mgmt Framework Transformer](../../management/model-based-replace-delete-in-mgmt-framework-transformer.md) にまとまっている。

## YANG validation はいつ走るか

YANG validation は 2 段階で走る。

1. **入口時点**: Translib が受け取った時点で構文と単純な制約 (range、enum、leafref の参照先存在) をチェックする。
2. **CONFIG_DB 書き込み前**: 依存関係を含めた制約 (must / when 式、cross-table leafref、機能間整合) を YANG モデルで検証する。

[GCU](../../reference/glossary.md#term-gcu) (Generic Config Update) や JSON patch でも同じ validator を通る設計のため、入口が違っても同じ違反は同じエラーで弾かれる。validator の設計と限界は [SONiC config update validation via YANG](../../management/sonic-config-update-validation-via-yang.md) を参照する。

## Subscribe / Telemetry の経路

Subscribe (ON_CHANGE / SAMPLE / TARGET_DEFINED) は gNMI server が対象 DB の [Redis](../../reference/glossary.md#term-redis) keyspace notification (`__keyspace@N__:TABLE|KEY`) を `PSUBSCRIBE` で購読し、YANG path に変換して streaming する形になる[^psubscribe]。実装上は path から導出された DB を `sonic.proto` の `Target` enum 経由で解決するため、運用状態の subscribe は STATE_DB / COUNTERS_DB / APPL_DB に向かうことが多く、CONFIG_DB subscribe は設定差分を観測したい補助的な用途で使う。COUNTERS_DB のうち per-object key を持たないテーブル (例: `RATES`) は keyspace pattern の delimitor を省略する分岐が入っており、テーブル種別に応じて subscribe pattern が変わる点に注意する[^counters-noseparator]。[FRR](../../reference/glossary.md#term-frr) の経路を YANG で stream する仕組みは [gNMI subscription for YANG data](../../routing/gnmi-subscription-for-yang-data.md) で [BGP](../../reference/glossary.md#term-bgp) RIB を例に説明される。

Dial-out モード (switch から collector へ push する向き) は telemetry container 内の別の経路で動作する。dial-in と dial-out の TLS / 認証境界が違う点に注意する。詳細は [運用](operations.md) と [dial-out mode](../../system/sonic-telemetry-in-dial-out-mode.md) を参照する。

## CLI 自動生成と YANG モデル

KLISH を入口にする SONiC CLI は YANG モデルから生成される。これは「CLI と gNMI の操作整合」を保つだけでなく、SONiC への CLI 追加コストを減らす目的を持つ。生成ツールの構成は [CLI auto-generation tool](../../management/sonic-cli-auto-generation-tool.md) を参照する。

## 関連ページ

- [Management Framework 全体像](../../management/sonic-management-framework.md)
- [gNMI server interface design](../../management/sonic-gnmi-server-interface-design.md)
- [Model-based replace/delete in Transformer](../../management/model-based-replace-delete-in-mgmt-framework-transformer.md)
- [SONiC config update validation via YANG](../../management/sonic-config-update-validation-via-yang.md)
- [SONiC YANG model guidelines](../../management/sonic-yang-model-guidelines.md)
- [SONiC CLI auto-generation tool](../../management/sonic-cli-auto-generation-tool.md)
- [gNMI subscription for YANG data](../../routing/gnmi-subscription-for-yang-data.md)

[^subscribe-targets]: `sonic-gnmi/proto/sonic.proto` (master) L9-L22 で `Target` enum が `APPL_DB / ASIC_DB / COUNTERS_DB / CONFIG_DB / STATE_DB / CHASSIS_STATE_DB` を定義し、DB を問わず gNMI subscribe target になる。
[^psubscribe]: `sonic-gnmi/sonic_data_client/db_client.go` (master) L1419-L1437。`pattern := "__keyspace@" + ... + "__:" + tableName + delimitor + key` を `redisDb.PSubscribe` で購読する実装。
[^counters-noseparator]: 同 L1422-L1426。`tblPath.dbName == "COUNTERS_DB" && !countersDbHasTableKeys(tableName)` のときは delimitor を pattern に付けない分岐がある。

<!-- glossary-links-injected: c22475bfc39e -->
