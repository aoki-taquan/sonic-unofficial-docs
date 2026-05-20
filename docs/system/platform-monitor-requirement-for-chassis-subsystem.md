---
title: シャーシサブシステムにおける Platform Monitor 要件（Mandatory + Future）
description: シャーシサブシステムにおける Platform Monitor 要件（Mandatory + Future） — このドキュメントはシャーシ型 SONiC（Supervisor + Linecards + Fabric Cards）における PMON 関連の必須要件と将来要件 を箇条書きで挙げたチェックリスト形式の…
area: system
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/SONiC
  path: doc/pmon/pmon-chassis-requirements.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - CHASSIS_MODULE
  - MID_PLANE_BRIDGE
  - DPU
  cli:
  - show chassis module status
  - show system-health
  - show reboot-cause
  - config qos
  yang:
  - sonic-chassis-module
  - sonic-asic-sensors
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含みます。機能の概念・設定・運用を読み物として読みたい場合は [Topics 14 章: Platform / Port / Optics](../topics/14-platform-port-optics/index.md) を参照。
<!-- /topics-tip -->

!!! info "裏取りステータス: code-verified（要件チェックリスト）"
    `sonic-platform-daemons/sonic-chassisd/scripts/chassisd` master に `CHASSIS_MODULE_TABLE` / `CHASSIS_ASIC_TABLE` の生成と `CHASSIS_MODULE_HOSTNAME_TABLE` (= `CHASSIS_MODULE_TABLE`) の hostname フィールド処理を確認（要件 #21 の hostname 表示拡張）。`sonic-psud` / `sonic-thermalctld` も同 daemon repo に存在。要件で挙がった Mandatory 項目は master 取り込み済み。Future 項目（LED 統一 / sensors 移行 / Generic console）は別途追跡。

# シャーシサブシステムにおける Platform Monitor 要件（Mandatory + Future）

## 概要

このドキュメントはシャーシ型 [SONiC](../reference/glossary.md#term-sonic)（Supervisor + Linecards + Fabric Cards）における **PMON 関連の必須要件と将来要件** を箇条書きで挙げたチェックリスト形式の [HLD](../reference/glossary.md#term-hld) である。具体実装は各サブ HLD（chassisd / psud / thermalctld / pcie-monitoring 等）に委ねられる[^1]。

## 動作仕様

### Mandatory 要件（21 項目）

カテゴリ別に整理すると[^1]:

#### 再起動とリンク状態

| # | 要件 |
|---|------|
| 1 | LC の `reboot` は LC 全体を **power-cycle**。Peer ノードはリンクダウンを即検知できること |
| 2 | RP の `reboot` は **システム全体（RP + LC）**を再起動。Peer はリンクダウンを検知 |
| 3 | Supervisor の **ungraceful reboot** で全 LC が再起動。LC は **headless で動かない** |
| 4 | LC の `config shut/unshut` を Chassis-d 設計に従ってサポート |

#### イベント監視・ログ・アラート

| # | 要件 |
|---|------|
| 5 | クリティカルイベント全部に syslog。閾値はドキュメント化して Alert Orchestration に流す |
| 6 | FC [ASIC](../reference/glossary.md#term-asic) / LC ASIC の PCIe 検出失敗を検知して syslog（[pcie-monitoring-services-hld.md](https://github.com/sonic-net/SONiC/blob/master/doc/pcie-mon/pcie-monitoring-services-hld.md) 連動）|
| 7 | HW Watchdog: 既存 SONiC 挙動踏襲（reboot 前に起動、reboot 後に SONiC が明示 disable）|

#### chassisd と Chassis State DB

| # | 要件 |
|---|------|
| 8 | LC / RP 両方で `chassisd` 動作。`CHASSIS_MODULE_TABLE|<key>` の全フィールドを正しく埋める |
| 9 | `CHASSIS_ASIC_TABLE|<key>` も埋める。SUP 上で FABRIC ASIC ready を待って swss/[syncd](../reference/glossary.md#term-syncd) 起動を制御 |
| 12 | Supervisor と LC の両方が `TEMPERATURE_INFO` を **Chassis State DB** に反映。LC [STATE_DB](../reference/glossary.md#term-state_db) にもローカル分が残る |

#### PSU / FAN / 温度（thermalctld 系）

| # | 要件 |
|---|------|
| 10 | Supervisor 上で **psud のパワーアルゴリズム** を実装（chassis 設計文書に従う）|
| 11 | Supervisor の show コマンドに **PSU LED ステータス** |
| 13 | Supervisor 上で **fan speed アルゴリズム** 実装 |
| 14 | Supervisor の show コマンドに **FAN LED ステータス** |

#### reboot-cause / mid-plane / show 系

| # | 要件 |
|---|------|
| 15 | Supervisor / LC 両方で **`reboot-cause` reason と履歴** をサポート |
| 16 | mid-plane switch の show コマンド（chassis 設計文書準拠）|
| 17 | Fabric / LC カードの **RMA 手順** をドキュメント化 |
| 18 | LC ↔ FC fabric link down のハンドリング |
| 19 | `show system-health detail` / `monitor-list` / `summary` を Supervisor / LC で実装 |
| 20 | Supervisor 上で LC reachability の **plat 固有チェック**、syslog 化 |
| 21 | `show chassis module status` で LINECARD1 のような generic name ではなく **linecard hostname** を表示 |

### Future / Enhancement 要件

| # | 要件 |
|---|------|
| 1 | LC の **Generic console**（[Console Switch HLD](https://github.com/Azure/SONiC/blob/master/doc/console/SONiC-Console-Switch-High-Level-Design.md)）|
| 2 | Critical fault 検知時の HW コンポーネント自動 reboot/shutdown |
| 3 | Module / Chassis / Board LED 統一インフラ（led daemon と show 拡張）|
| 4 | 温度測定の **粒度向上** + ポーリング間隔の調整、show での location フィルタ |
| 5 | Voltage / Current センサを sensorsd/libsensors から **PMON / thermalctld 経由** に移行 |
| 6 | Midplane switch の counter 監視と [QoS](../reference/glossary.md#term-qos) 調整（HW midplane 機種向け）|

<!-- evidence:
source: sonic-net/SONiC/doc/pmon/pmon-chassis-requirements.md#L11-L33 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  1. On LC the reboot command should power-cycle the entire LC ...
  3. Ungraceful Reboot of Supervisor should bring all LC's. LC's should not run headless.
  8. chassisd daemon support on both LC and RP with all fields of table CHASSIS_MODULE_TABLE|xxxx correctly populated.
reasoning: 主要な必須要件 (再起動、headless 禁止、chassisd フィールド充足) の根拠。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/SONiC/doc/pmon/pmon-chassis-requirements.md#L11-L33 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)"

    **出典**:

    `sonic-net/SONiC/doc/pmon/pmon-chassis-requirements.md#L11-L33 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)`

    **抜粋**:

    ```text
    1. On LC the reboot command should power-cycle the entire LC ...
    3. Ungraceful Reboot of Supervisor should bring all LC's. LC's should not run headless.
    8. chassisd daemon support on both LC and RP with all fields of table CHASSIS_MODULE_TABLE|xxxx correctly populated.
    ```

    **判断根拠**: 主要な必須要件 (再起動、headless 禁止、chassisd フィールド充足) の根拠。

<!-- evidence-rendered:end -->

## 設定

### 関連する CONFIG_DB / STATE_DB

本 HLD は要件のみで [CONFIG_DB](../reference/glossary.md#term-config_db) スキーマを規定しない。STATE_DB / Chassis State DB 側の主要テーブルとして以下が言及される[^1]:

| Table | 場所 | 用途 |
|-------|------|------|
| `CHASSIS_MODULE_TABLE` | Chassis State DB | モジュール（LC/RP）の状態 |
| `CHASSIS_ASIC_TABLE`   | Chassis State DB | ASIC ready 状態（FABRIC ASIC 起動同期に使用）|
| `TEMPERATURE_INFO`     | Chassis State DB / LC STATE_DB | 温度センサ情報 |

### 関連する CLI

| CLI | 関連要件 |
|-----|---------|
| `show chassis module status` | #21（hostname 表示）|
| `show system-health detail` / `monitor-list` / `summary` | #19 |
| `show reboot-cause` | #15 |
| PSU / FAN LED 表示 | #11, #14 |

## 制限事項

- **要件チェックリストに過ぎない**: 各項目の具体実装は別 HLD / 別文書を当たる必要がある[^1]。
- **Mandatory / Future の境界**: Future 側に「移行・改修系」が多く、現状 SONiC は Mandatory レベル止まりで実装されているケースが多い可能性がある。
- **Sensors の扱いが Future**: Voltage / Current の sensors → PMON 移行は未完了で、当面は Linux `sensorsd` 系が併用されると考えられる[^1]。

## 干渉する機能

- **chassisd**: 多くの Mandatory 要件の中核。`CHASSIS_MODULE_TABLE` / `CHASSIS_ASIC_TABLE` の生成元。
- **psud / thermalctld**: PSU / FAN / 温度のアルゴリズム実装場所。
- **pcie-monitoring（[pcie-monitoring-services-hld](../platform/pcieinfo-design.md) 関連）**: #6 の PCIe 検出失敗 syslog の根拠。
- **Console Switch HLD**: Future #1 の前提となる別 HLD。
- **led daemon**: Future #3 の中心。

## トラブルシューティング

- LC の reboot で peer がリンクダウンを検知しない: 要件 #1（power-cycle）が実機で守られているか。chassisd の reboot ハンドラ実装を確認。
- Supervisor 障害時に LC が headless で残る: 要件 #3 違反。SUP→LC 連動再起動経路（chassisd / heartbeat）を確認。
- `show chassis module status` で LINECARD1 等のままになる: 要件 #21 の hostname 反映が未実装の可能性[^1]。

### コマンド例

chassis subsystem の platform monitor 状態を確認する。

```bash
show platform summary
show platform fan
show platform psustatus
docker exec pmon supervisorctl status
```

## 引用元

[^1]: `sonic-net/SONiC` `doc/pmon/pmon-chassis-requirements.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Multi-ASIC / VOQ Chassis](../topics/12-multi-asic-voq/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: ec18b66e3507 -->
