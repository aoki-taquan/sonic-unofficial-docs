---
title: LLDP / LLDP_PORT テーブル
description: "LLDP / LLDP_PORT テーブル — LLDP テーブルはシステム全体の LLDP 設定 (GLOBAL キー) を、LLDP_PORT テーブルはポート単位の LLDP 有効化 / モードを保持する。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-lldp.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - LLDP
    - LLDP_PORT
    - PORT
  cli:
    - config lldp
  yang:
    - sonic-lldp
---

# LLDP / LLDP_PORT テーブル

## 概要

`LLDP` テーブルはシステム全体の LLDP 設定 (`GLOBAL` キー) を、`LLDP_PORT` テーブルはポート単位の LLDP 有効化 / モードを保持する[^1]。`lldp-syncd` および `docker-lldp` 内の `lldpd` が CONFIG_DB を読み出して動作する。

## key 構造

```
LLDP|GLOBAL
LLDP_PORT|<ifname>
```

`LLDP` テーブルは `GLOBAL` 単一エントリ（YANG では `container GLOBAL` 直下のスカラー leaf 群）。`LLDP_PORT` は `PORT` への leafref をキーに持つリスト。

| キー | 型 | 説明 |
|------|----|------|
| `GLOBAL` | 固定 | システム全体設定 |
| `ifname` | leafref → `PORT.name` | ポート単位設定 |

## フィールド (`LLDP|GLOBAL`)

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `hello_time` | uint8 (5..254) [秒] | 30 | 周期 hello の間隔 |
| `multiplier` | uint8 (1..10) | 4 | `hello_time × multiplier` がネイバー保持時間 |
| `system_name` | string | — | 管理者割当のシステム名 |
| `system_description` | string | — | システム説明 |
| `supp_mgmt_address_tlv` | boolean | false | Management Address TLV 送信抑制 |
| `supp_system_capabilities_tlv` | boolean | false | System Capabilities TLV 送信抑制 |
| `enabled` | boolean (grouping `lldp_mode_config`) | true | LLDP 有効化 |
| `mode` | enum `RECEIVE` / `TRANSMIT` | — | RX/TX モード |

## フィールド (`LLDP_PORT|<ifname>`)

grouping `lldp_mode_config` を `uses`:

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `enabled` | boolean | true | ポート単位の LLDP 有効化 |
| `mode` | enum `RECEIVE` / `TRANSMIT` | — | ポート単位の RX/TX モード |

## 制約

- `hello_time` 5..254 秒、`multiplier` 1..10（hold time = hello × multiplier）
- `LLDP_PORT.ifname` は `PORT` への leafref（VLAN / PortChannel 等は対象外）

## 購読者

- `lldp-syncd` (`docker-lldp`) — `lldpd` 設定生成、STATE_DB への neighbor 反映
- `lldpd` (open-lldp フォーク)

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `PORT`、`DEVICE_NEIGHBOR`、`DEVICE_NEIGHBOR_METADATA`
- 関連 YANG: `sonic-lldp`、`sonic-port`
- 関連 CLI: `config lldp`、`show lldp`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-lldp`](../yang/sonic-lldp.md)
- CLI: `config lldp`

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-lldp.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-lldp.yang>

## 関連ページ
- [CONFIG_DB: DEVICE_NEIGHBOR](device-neighbor.md)
- [CONFIG_DB: PORT](port.md)
