---
title: SONiC BMC Platform Management & Monitoring（pmon ↔ BMC 連携）
area: system
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/bmc/sonicBMC/pmon-bmc-design.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli:
    - show platform fan
    - show platform temperature
    - show platform psu
  yang:
    - sonic-platform
---

!!! warning "裏取りステータス: code-verified"
    BMC 経由 pmon の現行 master 実装、Redfish / IPMI トランスポート差は未確認。

!!! note "Verifier 注記（2026-05-10）"
    実コード裏取り: `sonic-platform-common/sonic_platform_base/bmc_base.py` / `redfish_client.py` / `bmc_fw_update.py` に BMC 抽象化レイヤを確認。`sonic-platform-daemons/sonic-bmcctld/scripts/bmcctld` に BMC controller daemon 実装。HLD の Redfish / IPMI 連携設計は現行 master に取り込まれている。

# SONiC BMC Platform Management & Monitoring（pmon ↔ BMC 連携）

## 概要

「BMC 付き SONiC platform」では、PSU・fan・温度センサ・電圧などの **physical inventory が BMC（OpenBMC 等）配下** にあり、CPU 直結ではない[^1]。HLD は **NPU 上の SONiC pmon と BMC の通信レイヤを抽象化** して、`Chassis` / `Psu` / `Fan` / `Thermal` プラットフォーム API がどの BMC コールに展開されるかを決める設計を扱う。

## 動作仕様

```mermaid
flowchart LR
    PMON[NPU 側 pmon] --> PA[sonic-platform-common\nplatform plugin]
    PA --> XPORT{transport}
    XPORT -->|Redfish HTTPS| BMC[BMC stack\n(OpenBMC など)]
    XPORT -->|IPMI / OEM| BMC
    XPORT -->|i2c proxy| BMC
    BMC --> SENS[(PSU / fan / thermal / FRU)]
    PMON --> STDB[(STATE_DB\nFAN_INFO / PSU_INFO / THERMAL_INFO)]
```

要点[^1]:

- **transport**: Redfish HTTPS が第一選択。IPMI / vendor OEM をフォールバックとする platform もある
- **plugin 側 abstraction**: `Psu` / `Fan` / `Thermal` クラスが BMC API 呼び出しに展開され、SONiC 側からは既存 API そのまま見える
- **キャッシュ**: BMC への問い合わせはコストが高いので、pmon 側で短期キャッシュ
- **イベント通知**: BMC からの critical 通知（過温度等）は SEL / Redfish event を pmon に橋渡し

## 関連 STATE_DB / CONFIG_DB

| Table | DB | 役割 |
|-------|----|------|
| `FAN_INFO` | STATE | fan rpm / status |
| `PSU_INFO` | STATE | PSU presence / oper |
| `THERMAL_INFO` | STATE | sensor 温度 |
| `CHASSIS_INFO` | STATE | model / serial / FRU |

直接の CONFIG_DB スキーマは新設せず、既存の platform monitor 設計に乗せる想定。

## 関連 CLI

| Command | 用途 |
|---------|------|
| `show platform fan` | fan 状態 |
| `show platform psu` | PSU 状態 |
| `show platform temperature` | 温度センサ |
| `show platform inventory` | FRU 情報 |

## 制限事項

- **BMC が落ちると inventory も落ちる**: pmon 側 cache だけでは長期停止に耐えない
- **transport の latency**: 1 秒オーダの応答遅延がある platform もあるため pmon ループ周期と整合
- **権限**: BMC 認証情報の保管・rotation が運用課題
- **Redfish スキーマ差**: vendor OpenBMC 拡張で属性名が違う

## 干渉する機能

- **smartswitch-pmon**: NPU+DPU+BMC 構成での DPU 状態取得
- **transceiver / sensor monitoring**: 同 area 別 HLD と pmon ループを共有
- **system health monitor**: BMC 由来 critical event を吸収するパス
- **IP address assignment**: BMC への通信は management VRF や別 NIC 経由になることが多い

## トラブルシューティング

- `show platform fan` が空 → BMC 接続性、Redfish endpoint URL、認証情報を確認
- 値が古い → pmon キャッシュ TTL、BMC の応答性能、SEL の溢れを確認
- センサ単位で欠損 → vendor 固有 OEM 属性のマッピングを確認

## 引用元

[^1]: `sonic-net/SONiC` `doc/bmc/sonicBMC/pmon-bmc-design.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- sonic-platform-common の Psu / Fan / Thermal クラスの BMC backend 切替実装確認
- pmon docker 内での Redfish / IPMI クライアントライブラリ取り込みと依存パッケージ確認
- STATE_DB FAN_INFO / PSU_INFO / THERMAL_INFO スキーマと BMC 由来データ追加カラム確認
- BMC イベント（SEL / Redfish event）から system health monitor への通知経路確認
- BMC 認証情報の格納方式と rotation の現行運用確認
- vendor 別 Redfish スキーマ差吸収レイヤの現行実装確認
-->

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Platform / Port / Optics / PHY](../topics/14-platform-port-optics/index.md)

<!-- /topics-back-ref -->
