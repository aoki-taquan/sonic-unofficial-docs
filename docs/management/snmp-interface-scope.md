---
title: SNMP エージェントがサポートするインターフェーススコープ
area: management
tags: [snmp, snmpagent, rfc1213, mib, interface, mgmt]
description: sonic-snmpagent の RFC1213-MIB ifTable がサポートするインターフェース種別と、管理インターフェース（eth0）が含まれない制約。
source_issues:
  - https://github.com/sonic-net/sonic-snmpagent/issues/83
verification: issue-confirmed
last_verified: 2026-05-20
---

# SNMP エージェントがサポートするインターフェーススコープ

## 概要

`sonic-snmpagent` が実装する RFC1213-MIB の `ifTable` には、**フロントパネルインターフェース**と **[LAG](../reference/glossary.md#term-lag)（ポートチャネル）インターフェース**のみが含まれる。管理インターフェース（eth0）・ループバックインターフェース・[VLAN](../reference/glossary.md#term-vlan) インターフェースは含まれない。

## サポートされるインターフェース

| インターフェース種別 | ifTable に含まれるか |
|---------------------|---------------------|
| フロントパネルポート（Ethernet0, Ethernet4, ...） | **含まれる** |
| LAG / [PortChannel](../reference/glossary.md#term-portchannel)（PortChannel0001, ...） | **含まれる** |
| 管理インターフェース（eth0, Management0） | **含まれない** |
| ループバック（Loopback0, ...） | **含まれない** |
| VLAN（Vlan100, ...） | **含まれない** |

## 背景

RFC1213-MIB（MIB-II）の `ifTable` はネットワーク機器の全インターフェースを列挙する設計だが、`sonic-snmpagent` の実装では主にデータプレーンのインターフェースのみを対象としている。

管理インターフェース（eth0）の扱いについて、標準上の定義が曖昧であること（管理プレーンのインターフェースを含めるべきかどうかの解釈の相違）が、実装を複雑にしている。

## 影響

### 監視ツールでの注意点

[SNMP](../reference/glossary.md#term-snmp) ポーリングで帯域使用量や統計を収集する際：

- `eth0` の IN/OUT バイト数は `ifTable` からは取得できない
- 代替として Linux の `/proc/net/dev` 経由の情報を利用するか、別途 SNMP OID を実装する必要がある

### 回避策

`eth0` の統計を SNMP で取得したい場合、プライベート OID を実装する方法があるが、標準に準拠しないため相互運用性が下がる（Issue #83 でのコメント参照）。

より適切な解決策は、`sonic-snmpagent` に対して管理インターフェースサポートを追加するコントリビューションを行うことである。

## 関連インターフェース情報の取得方法

管理インターフェースの情報は CLI から取得できる。

```bash
# 管理インターフェースの状態確認
show management_interface addresses

# eth0 の詳細確認
ip addr show eth0
ip -s link show eth0

# Redis での確認（MGMT_PORT テーブル）
redis-cli -n 4 hgetall "MGMT_PORT|eth0"
```

## 関連

- GitHub Issue: [sonic-net/sonic-snmpagent#83](https://github.com/sonic-net/sonic-snmpagent/issues/83)

<!-- glossary-links-injected: 1bb2312a6ed4 -->
