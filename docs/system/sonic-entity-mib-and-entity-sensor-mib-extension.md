---
title: Entity MIB / Entity Sensor MIB 拡張（chassis 階層化と sensor / fan / PSU 追加）
description: Entity MIB / Entity Sensor MIB 拡張（chassis 階層化と sensor / fan / PSU 追加）
  — SONiC の SNMP Entity MIB（RFC 2737）実装は当初、entityPhysical グループの transceiver と DOM
  sensor だけ…
area: system
verification: code-verified
last_verified: 2026-05-10
sources:
- repo: sonic-net/SONiC
  path: doc/snmp/extension-to-physical-entity-mib.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - SNMP
  - SNMP_AGENT_ADDRESS_CONFIG
  - CHASSIS_MODULE
  - MID_PLANE_BRIDGE
  - DPU
  - VOQ_INBAND_INTERFACE
  - SNMP_COMMUNITY
  cli:
  - config snmp
  - show snmpagentaddress
  yang:
  - sonic-snmp
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含みます。機能の概念・設定・運用を読み物として読みたい場合は [Topics 09 章: Telemetry / SNMP / ログ](../topics/09-telemetry-snmp/index.md) を参照。
<!-- /topics-tip -->

!!! success "裏取りステータス: code-verified"
    実装裏取り済み（下記コード位置）。rfc2737 (Entity MIB): sonic-snmpagent/src/sonic_ax_impl/mibs/ietf/rfc2737.py:241,672,822,1144 (entPhysicalContainedIn, FAN_INFO map) / rfc3433 (Entity Sensor MIB): rfc3433.py に RFC 3433 link / sub_oid: physical_entity_sub_oid_generator.py で確認。

# Entity MIB / Entity Sensor MIB 拡張（chassis 階層化と sensor / fan / PSU 追加）

## 概要

[SONiC](../reference/glossary.md#term-sonic) の [SNMP](../reference/glossary.md#term-snmp) Entity MIB（RFC 2737）実装は当初、`entityPhysical` グループの **transceiver と DOM sensor** だけが対象で、`entPhysicalContainedIn` も埋まっておらず物理階層を取れなかった[^1]。本 [HLD](../reference/glossary.md#term-hld) はこれを拡張して:

1. **`entityPhysical` の MIB object を全部** 実装する
2. **thermal sensor / fan / fan tachometer / PSU / PSU fan / PSU 内 sensor** を物理エンティティとして追加
3. **`entPhysicalContainedIn`** を埋めて chassis 階層を SNMP から取れるようにする
4. **Entity Sensor MIB**（RFC 3433）も同時に拡張

## 動作仕様

### `entPhysicalTable` の全フィールド対応

既存実装は次のサブセットのみだった[^1]:

```text
entPhysicalDescr / Class / Name /
  HardwareRev / FirmwareRev / SoftwareRev /
  SerialNum / MfgName / ModelName
```

本拡張で `entPhysicalIndex / VendorType / ContainedIn / ParentRelPos / Alias / AssetID / IsFRU` も追加する[^1]。特に `ContainedIn` と `ParentRelPos` の追加が重要で、これでツリー構造が表現できる。

### Chassis hierarchy（HLD で示される構造）

```text
Chassis
├── MGMT (Chassis)
│   ├── CPU package Sensor/T(x)            (Temperature sensor)
│   ├── CPU Core Sensor/T(x)               (Temperature sensor)
│   ├── Board AMB temp/T(x)                (Temperature sensor)
│   ├── Ports AMB temp/T(x)                (Temperature sensor)
│   └── ASIC                                (Switch device)
│        └── ASIC/T(x)                     (Temperature sensor)
├── FAN(x)                                 (Fan)
│    └── FAN/F(y)                          (Fan sensor / tachometer)
├── PS(x)                                  (Power supply)
│    ├── FAN/F(y)                          (PSU FAN)
│    ├── power-mon/T(y)                    (Temperature sensor)
│    └── power-mon/VOLTAGE                 (Voltage sensor)
└── Ethernet x/y ... cable                 (Port module)
     ├── DOM Temperature Sensor for Ethernet(x)
     ├── DOM Voltage Sensor for Ethernet(x)
     ├── DOM RX Power Sensor for Ethernet(x)/(y)
     ├── DOM TX Bias Sensor for Ethernet(x)/(y)
     └── DOM TX Power Sensor for Ethernet(x)/(y)
```

それぞれが `entPhysicalContainedIn = <親 entPhysicalIndex>` を持つ[^1]。

### データソース

`sonic-snmpagent` (`sonic_ax_impl`) は [Redis](../reference/glossary.md#term-redis) を直接読む実装。各 sensor / module 情報は [STATE_DB](../reference/glossary.md#term-state_db) のテーブルに依存:

| MIB object 群 | DB ソース |
|---------------|-----------|
| Transceiver / DOM sensor | `STATE_DB:TRANSCEIVER_INFO`, `TRANSCEIVER_DOM_SENSOR` |
| Fan / Fan sensor | `STATE_DB:FAN_INFO` |
| Temperature sensor | `STATE_DB:TEMPERATURE_INFO` |
| PSU / PSU fan | `STATE_DB:PSU_INFO`, `FAN_INFO` |
| Voltage / current sensor (将来 SensorMon) | `STATE_DB:VOLTAGE_INFO`, `CURRENT_INFO` |

(本 HLD は完全な対応表を固定していないので、sonic-snmpagent 側のコードに従って読む)

### Entity Sensor MIB の対応

Entity MIB に追加した sensor 系エンティティそれぞれに、**Entity Sensor MIB**（RFC 3433）の `entPhySensorTable` エントリ（`Type / Scale / Precision / Value / OperStatus / UnitsDisplay` 等）を生やす[^1]。

```text
SNMPv2-SMI::mib-2.99.1.1.1.4.<idx> = INTEGER: <value>
SNMPv2-SMI::mib-2.99.1.1.1.5.<idx> = INTEGER: <oper-status>
```

### snmpwalk 例

既存実装で見える DOM sensor:

```text
mib-2.47.1.1.1.1.2.1000 = "SFP/SFP+/SFP28 for Ethernet0"
mib-2.47.1.1.1.1.2.1001 = "DOM Temperature Sensor for Ethernet0"
mib-2.47.1.1.1.1.2.1011 = "DOM RX Power Sensor for Ethernet0/1"
...
```

本拡張で chassis / FAN / PSU が同テーブルに追加される。

<!-- evidence:
source: sonic-net/SONiC/doc/snmp/extension-to-physical-entity-mib.md#L72-L96 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  This extension aims to implement all the objects in the entityPhysical group.
  Also plan to add more physical entities such as thermal sensors, fan, and its tachometers; PSU, PSU fan, and some sensors contained in PSU.
  Another thing need to highlight is that in the current implementation, "entPhysicalContainedIn" object is not implemented, so there is no way to reflect the physical location
reasoning: 拡張対象の MIB object 一覧と階層化要件の根拠。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/SONiC/doc/snmp/extension-to-physical-entity-mib.md#L72-L96 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)"

    **出典**:

    `sonic-net/SONiC/doc/snmp/extension-to-physical-entity-mib.md#L72-L96 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)`

    **抜粋**:

    ```text
    This extension aims to implement all the objects in the entityPhysical group.
    Also plan to add more physical entities such as thermal sensors, fan, and its tachometers; PSU, PSU fan, and some sensors contained in PSU.
    Another thing need to highlight is that in the current implementation, "entPhysicalContainedIn" object is not implemented, so there is no way to reflect the physical location
    ```

    **判断根拠**: 拡張対象の MIB object 一覧と階層化要件の根拠。

<!-- evidence-rendered:end -->

## 設定

### 関連する CONFIG_DB

該当なし。SNMP コミュニティ等の設定は別 HLD（`SNMP_*` テーブル）の管轄。

### 関連する CLI

該当なし。`snmpwalk` / `snmpget` が直接の参照手段。

### 設定例

```bash
# Entity MIB walk
snmpwalk -v2c -c <comm> <DUT> 1.3.6.1.2.1.47.1.1.1.1.2 | head -30

# 階層関係（containedIn）を見る
snmpwalk -v2c -c <comm> <DUT> 1.3.6.1.2.1.47.1.1.1.1.4

# Entity Sensor MIB
snmpwalk -v2c -c <comm> <DUT> 1.3.6.1.2.1.99.1.1.1.4
```

## 制限事項

- HLD は `entityPhysical` グループのみ対象。`entityLogical` 等は将来課題[^1]
- HLD Rev 0.3、日付欄空欄。実装範囲は実コードで個別確認が必要
- `entPhysicalContainedIn` の親 index 番号付け規約は HLD で完全には固定されていない
- Voltage / Current sensor 連携は SensorMon HLD と整合する必要があり、両 HLD の合成で初めて機能する

## 干渉する機能

- **xcvrd**: TRANSCEIVER_DOM_SENSOR / INFO のソース
- **thermalctld**: TEMPERATURE_INFO / FAN_INFO のソース
- **psud**: PSU_INFO のソース
- **SensorMon**（別 HLD）: VOLTAGE_INFO / CURRENT_INFO の追加経路
- **SNMP transceiver monitoring testbed test plan**: 本拡張のテスト

## トラブルシューティング

```bash
# entPhysicalContainedIn が埋まっているか
snmpwalk -v2c -c <comm> <DUT> 1.3.6.1.2.1.47.1.1.1.1.4 | head

# 親が 0 ではない（chassis 直下を示す）べき index を抜き出す
snmpwalk -v2c -c <comm> <DUT> 1.3.6.1.2.1.47.1.1.1.1.4 | awk '$NF != "INTEGER: 0"'

# DB ソース
redis-cli -n 6 KEYS "TEMPERATURE_INFO|*"
redis-cli -n 6 KEYS "PSU_INFO|*"
redis-cli -n 6 KEYS "FAN_INFO|*"
```

## 引用元

[^1]: `sonic-net/SONiC` `doc/snmp/extension-to-physical-entity-mib.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Telemetry / SNMP / Observability](../topics/09-telemetry-snmp/index.md)
- [Topics: Multi-ASIC / VOQ Chassis](../topics/12-multi-asic-voq/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 8ba32e5aa69d -->
