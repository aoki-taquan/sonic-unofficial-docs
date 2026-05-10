---
title: gNMI Subscription for YANG Data（ON_CHANGE / SAMPLE / TARGET_DEFINED）
area: routing
verification: hld-only
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/mgmt/gnmi/gNMI_Subscription_for_YangData.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli:
    - gnmi_cli
  yang:
    - openconfig-*
    - sonic-*
---

!!! warning "裏取りステータス: HLD-only"
    本 HLD は `area=routing` の backlog だが内容は telemetry 全般に関わる。location は backlog 由来のまま。

# gNMI Subscription for YANG Data（ON_CHANGE / SAMPLE / TARGET_DEFINED）

## 概要

gNMI Subscribe は YANG path に紐づくデータを **stream / poll / once** モードでクライアントに push する仕組み[^1]。SONiC は `sonic-mgmt-framework` の Translib + STATE_DB / COUNTERS_DB / APPL_DB の表購読を組合せ、openconfig YANG パスでのサブスクリプションを実現する。

サポートする SubscriptionMode（per-path）:

- **ON_CHANGE**: 値が変化したときのみ送る（例: link state、neighbor state）
- **SAMPLE**: 一定間隔で送る（例: counters）
- **TARGET_DEFINED**: server が path 種別から適切なモードを選ぶ

## 動作仕様

```mermaid
flowchart LR
    CLI[gnmi_cli\n(client)] --gNMI Subscribe--> SRV[gNMI server\n(mgmt-framework)]
    SRV --> TL[Translib]
    TL --> XLATE[Transformer / xpath → DB key]
    XLATE --> SUBSC[subscribe (Redis keyspace + table notif)]
    SUBSC --> STDB[(STATE_DB / COUNTERS_DB / APPL_DB)]
    STDB -- changes --> SUBSC
    SUBSC --> SRV
    SRV -- gNMI Notification --> CLI
```

主要な仕組み[^1]:

- **Sync 期 → Stream 期**: 最初に現在値の snapshot（sync_response）を送り、以後 update を流す
- **ON_CHANGE が成立する path**: STATE_DB のキー単位（`PORT_TABLE` 等）。Redis keyspace notification と組合せ
- **SAMPLE の interval**: subscribe 時に client が指定。下限は server 設定で抑える
- **wildcards**: `interfaces/interface[name=*]/state/oper-status` のように expand してから subscribe
- **TARGET_DEFINED の選択**: counter 系 → SAMPLE、state 系 → ON_CHANGE が一般的

### Heartbeat / suppress-redundant

ON_CHANGE で長時間更新がない時、`heartbeat-interval` で生存通知を出す。`suppress-redundant` で値が変わらない SAMPLE を抑制可能。

## 関連 CLI

| Command | 用途 |
|---------|------|
| `gnmi_cli -a host:port -insecure -client_types gnmi -q '<path>' -qt s -sm o` | ON_CHANGE 購読 |
| `gnmi_cli ... -sm s -i 5` | 5s SAMPLE |

## 制限事項

- **YANG 定義が無い path は購読不可**: openconfig / sonic-* どちらかで定義されていること
- **大量 wildcard 展開**: 全 port の counters wildcard で server 負荷が高くなる
- **ON_CHANGE 対応の限界**: COUNTERS_DB の数値変化は ON_CHANGE 対象として実用的でない（毎 poll 変わる）
- **TLS / 認証**: gNMI は TLS + cert 認証が前提。証明書管理は `gnsi` / `gNOI` 等と統合

## 干渉する機能

- **management framework**: Translib / Transformer の同居機構
- **gNMI Master Arbitration**: 複数クライアントの集中制御で先行ロックを取る HLD（management area）
- **dial-in / dial-out telemetry**: dial-out では subscribe をサーバ側起動で行う
- **STATE_DB schema**: ON_CHANGE 効率は STATE_DB スキーマ設計に依存

## トラブルシューティング

- subscription が来ない → path が YANG schema 上 valid か、subscribe mode の対応可否
- update が遅い → SAMPLE interval、Redis keyspace notification 設定（`notify-keyspace-events`）
- TLS エラー → mgmt-framework の cert 設定、`gnmi_cli -insecure` で切り分け

## 引用元

[^1]: `sonic-net/SONiC` `doc/mgmt/gnmi/gNMI_Subscription_for_YangData.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- gnmi server 実装（sonic-gnmi）の現行 master 取り込みと subscribe ハンドラ確認
- Redis keyspace notification (notify-keyspace-events) の有効化と STATE_DB / COUNTERS_DB 連携確認
- ON_CHANGE 対応 path の実装範囲（openconfig 各モジュール）の現行実装確認
- TARGET_DEFINED の選択ロジック（path → mode）が現行実装でどう決まっているか確認
- TLS / cert 認証と gNSI / gNOI 統合の現行実装確認
- gNMI Master Arbitration / dial-out telemetry との実装関係確認
-->
