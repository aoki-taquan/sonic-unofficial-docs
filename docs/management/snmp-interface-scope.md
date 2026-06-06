---
title: SNMP エージェントがサポートするインターフェーススコープ
area: management
tags: [snmp, snmpagent, rfc1213, mib, interface, mgmt, vlan]
description: sonic-snmpagent の RFC1213-MIB ifTable が列挙するインターフェース種別（フロントパネル / LAG / 管理 / VLAN）と、管理インターフェースのカウンタが SNMP では取得できない制約を実装ソースから整理する。
source_issues:
  - https://github.com/sonic-net/sonic-snmpagent/issues/83
sources:
  - repo: sonic-net/sonic-snmpagent
    path: src/sonic_ax_impl/mibs/ietf/rfc1213.py
    ref: 329f1cca300b28cd7297e69db423cadf8c60ddb9
  - repo: sonic-net/sonic-snmpagent
    path: src/sonic_ax_impl/mibs/__init__.py
    ref: 329f1cca300b28cd7297e69db423cadf8c60ddb9
related:
  cli: []
  config_db:
    - MGMT_PORT
    - PORT
    - PORTCHANNEL
    - VLAN
  yang: []
  _no_related_yang: true
  _no_related_cli: true
verification: code-verified
last_verified: 2026-06-06
---

# SNMP エージェントがサポートするインターフェーススコープ

## 概要

`sonic-snmpagent` が実装する RFC1213-MIB の `ifTable` は、次の 4 種を 1 つのインデックス空間 (`if_range`) に統合して列挙する[^if-range]。

- フロントパネルポート（`Ethernet*` / Backplane / IB / Recirc）
- [LAG](../reference/glossary.md#term-lag)（`PortChannel*`）
- 管理インターフェース（`Management0` / `eth0` 等、`CONFIG_DB.MGMT_PORT` 由来）
- [VLAN](../reference/glossary.md#term-vlan) インターフェース（`Vlan*`）

ループバック（`Loopback*`）は ifTable には含まれない。また、管理インターフェースはエントリこそ列挙されるが、[SNMP](../reference/glossary.md#term-snmp) 経由のトラフィックカウンタは常に 0 が返る（未実装）[^mgmt-counter]。

この振る舞いは [Issue #83](https://github.com/sonic-net/sonic-snmpagent/issues/83) で取り上げられた「管理インターフェースが ifTable に出てこない」という当初の挙動から進化しており、現在の master では `mgmt_oid_name_map` / `vlan_oid_name_map` を `if_range` に取り込んで返している[^if-range]。

## ifTable 列挙対象

| インターフェース種別 | ifTable に含まれるか | カウンタ取得 | 備考 |
|---------------------|---------------------|------------|------|
| フロントパネルポート（`Ethernet*` 等） | 含まれる | 可（[COUNTERS_DB](../reference/glossary.md#term-counters_db)） | `init_sync_d_interface_tables`[^init-port] |
| LAG / [PortChannel](../reference/glossary.md#term-portchannel) | 含まれる | 可（メンバ加算 + [RIF](../reference/glossary.md#term-rif)）| `init_sync_d_lag_tables` 経由、メンバの値を合算しさらに必要なら router-interface カウンタを足す[^lag-counter] |
| 管理インターフェース（`Management0` / `eth0`） | 含まれる | **不可（常に 0）** | `init_mgmt_interface_tables`[^init-mgmt]。COUNTERS_DB に generic Linux インターフェース用カウンタが無いため `_get_counter` は 0 を返す[^mgmt-counter] |
| VLAN（`Vlan*`） | 含まれる | 可（COUNTERS_DB の RIF カウンタ） | `init_sync_d_vlan_tables`[^init-vlan] |
| ループバック（`Loopback*`） | 含まれない | — | ifTable 構築側で取り込み処理が存在しない |

`if_range` は上記 4 マップのキー（OID インデックス）を `sorted()` で連結したものとして `update_data` 内で再構築される[^if-range]。

## 管理インターフェースの扱い

管理インターフェースは ifTable に **エントリは現れる** が、以下の差異がある。

- 設定情報（admin status / 説明など）は `CONFIG_DB` の `MGMT_PORT|<name>` から、oper status は `STATE_DB` の対応エントリから読む[^mgmt-entry]
- 帯域 / パケットカウンタは取得経路自体が未実装で、`_get_counter` は管理インターフェース OID に対し早期 return で 0 を返す[^mgmt-counter]
- ソース注釈にも `# TODO: mgmt counters not available through SNMP right now` / `# COUNTERS DB does not have support for generic linux (mgmt) interface counters` と明記されている[^mgmt-counter]

したがって、管理プレーンの帯域使用量を SNMP ポーリングで取得しようとしても、ifTable 上では値が 0 のまま伸びない。

## 監視ツール側での回避策

`eth0` の統計を取りたい場合、現状の代替は以下のいずれか:

- ノード上で `/proc/net/dev` や `ip -s link show eth0` を直接読む（SNMP 経由でなく out-of-band 監視で取り扱う）
- 別途 net-snmp 等の汎用 SNMP エージェントを併走させ、Linux インターフェースのカウンタを公開する
- `sonic-snmpagent` 側で COUNTERS_DB に mgmt インターフェース用エントリを追加するコントリビューションを行う（Issue #83 で議論されている方向）

プライベート OID で独自実装する選択肢もあるが、相互運用性が下がるため通常は避けるべきである。

## 関連 CLI から状態を確認する

管理インターフェースそのものの設定は CLI / [Redis](../reference/glossary.md#term-redis) から確認できる。

```bash
# 管理インターフェースの IP 設定確認
show management_interface address

# eth0 の状態とカウンタ（Linux 側）
ip addr show eth0
ip -s link show eth0

# Redis での CONFIG_DB MGMT_PORT 確認
sonic-db-cli CONFIG_DB hgetall "MGMT_PORT|eth0"
```

## 関連

- GitHub Issue: [sonic-net/sonic-snmpagent#83](https://github.com/sonic-net/sonic-snmpagent/issues/83) — 管理インターフェースの ifTable 露出と counter 不在に関する議論

[^if-range]: <!-- evidence: sonic-snmpagent/src/sonic_ax_impl/mibs/ietf/rfc1213.py L253-L268 --> `InterfacesUpdater.update_data` は `oid_name_map`（フロントパネル）/ `oid_lag_name_map`（LAG）/ `mgmt_oid_name_map`（管理）/ `vlan_oid_name_map`（VLAN）の OID を結合して `if_range` を構築する。
[^mgmt-counter]: <!-- evidence: sonic-snmpagent/src/sonic_ax_impl/mibs/ietf/rfc1213.py L397-L400 --> `_get_if_counter` 内で `if oid in self.mgmt_oid_name_map: return 0` と早期 return しており、`# TODO: mgmt counters not available through SNMP right now` / `# COUNTERS DB does not have support for generic linux (mgmt) interface counters` のコメントが付いている。
[^init-port]: <!-- evidence: sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py L276-L295 --> `init_sync_d_interface_tables` がフロントパネル系 (`SONIC_ETHERNET_RE_PATTERN` 等) を `if_name_map` に取り込む。
[^lag-counter]: <!-- evidence: sonic-snmpagent/src/sonic_ax_impl/mibs/ietf/rfc1213.py L401-L442 --> LAG OID のカウンタはメンバの `_get_counter` を合算し、`lag_sai_map` → `port_rif_map` → `rif_counters` 経由で router-interface 側のドロップ系も足し込む。
[^init-mgmt]: <!-- evidence: sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py L246-L274 --> `init_mgmt_interface_tables` が `CONFIG_DB.MGMT_PORT|*` を読み、`mgmt_oid_name_map` と `mgmt_alias_map` を構築する。
[^init-vlan]: <!-- evidence: sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py L349 --> `init_sync_d_vlan_tables` が `vlan_name_map` / `vlan_oid_sai_map` / `vlan_oid_name_map` を構築し、`update_data` 経由で `if_range` に統合される。
[^mgmt-entry]: <!-- evidence: sonic-snmpagent/src/sonic_ax_impl/mibs/ietf/rfc1213.py L465-L496 --> `_get_if_entry` は mgmt OID なら `CONFIG_DB` の `mgmt_if_entry_table` を、`_get_if_entry_state_db` は `STATE_DB` の同テーブル相当を読む。

<!-- glossary-links-injected: 686c7b94339a -->
