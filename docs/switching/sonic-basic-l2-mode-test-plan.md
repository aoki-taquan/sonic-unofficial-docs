---
title: SONiC Basic L2 モードテストプラン（FDB / VLAN / SNMP の最小機能検証）
description: SONiC Basic L2 モードテストプラン（FDB / VLAN / SNMP の最小機能検証） — SONiC を basic L2
  switch として構成した場合の最小機能を T0 トポロジで検証する。
area: switching
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/SONiC
  path: doc/test-plans/Sonic Basic L2 Mode Test plan.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - VLAN
  - SNMP
  - VLAN_INTERFACE
  - VLAN_MEMBER
  - SNMP_AGENT_ADDRESS_CONFIG
  - BGP_NEIGHBOR
  - BGP_GLOBALS
  cli:
  - sonic-cfggen --preset l2
  - config vlan
  - show arp
  - show vlan
  - config snmp
  - config bgp
  - show bgp
  yang:
  - sonic-vlan
  - sonic-snmp
  - sonic-bgp-global
  - sonic-bgp-neighbor
  - sonic-portchannel
  - sonic-vlan-sub-interface
  - sonic-bgp-peergroup
---

!!! note "裏取りステータス: code-verified（preset l2 部分）"
    `sonic-buildimage/src/sonic-config-engine/sonic-cfggen` (l.354) で `--preset` 引数が `get_available_config()`（`config_samples` モジュール）の choices として取り込まれ、l.551 で `generate_sample_config(data, args.preset)` が呼ばれる。`data/l2switch.j2` テンプレートが同梱。`tests/test_j2files.py` で `--preset l2` 引数のテストもあり。sonic-mgmt 側 fdb / vlan / snmp テストは別 repo（本 cache 対象外）のためカバレッジは未裏取り。

# SONiC Basic L2 モードテストプラン（FDB / VLAN / SNMP の最小機能検証）

## 概要

[SONiC](../reference/glossary.md#term-sonic) を **basic L2 switch** として構成した場合の最小機能を T0 トポロジで検証する[^1]。範囲は意図的に絞られており、L3 / [BGP](../reference/glossary.md#term-bgp) / [ACL](../reference/glossary.md#term-acl) は対象外。L2 モードの構成手順は [SONiC wiki: L2-Switch-mode](https://github.com/sonic-net/SONiC/wiki/L2-Switch-mode#3-generate-a-configuration-for-l2-switch-mode) に従う。

## 動作仕様

### 設定生成

```bash
sonic-cfggen -H -p -k $HWSKU --preset l2
```

- `-H` で MAC を埋め込み、`-k`/`-p` で [port_config.ini](../reference/glossary.md#term-port-config-ini) を渡す[^1]
- 全ポートが admin-up + Vlan 1000 の untagged member になる構成

### テストケース[^1]

| # | 項目 | [sonic-mgmt](../reference/glossary.md#term-sonic-mgmt) パス | 期待 |
|---|------|------|------|
| 1 | sanity | `tests/common/sanity_check.py` | [orchagent](../reference/glossary.md#term-orchagent) / [syncd](../reference/glossary.md#term-syncd) 起動、リンク Up |
| 2 | [FDB](../reference/glossary.md#term-fdb) | `tests/fdb/test_fdb.py` | 全ポートで MAC 学習 |
| 3 | [VLAN](../reference/glossary.md#term-vlan) + [ARP](../reference/glossary.md#term-arp) + PING | `tests/vlan/test_vlan.py`（一部要修正: [PortChannel](../reference/glossary.md#term-portchannel) 想定箇所） | Vlan IF への IP 設定後、ARP / ping 成立 |
| 4 | [SNMP](../reference/glossary.md#term-snmp) | `tests/snmp/test_snmp_interfaces.py` / `test_snmp_cpu.py` / `test_snmp_psu.py` | Walk 成功（MAC / IF / CPU / PSU 取得） |

サニティチェックは **各テストの前後** で走らせる[^1]。

## 制限事項

- 既存 `vlan_configure` は PortChannel 前提箇所があり、basic L2 mode では修正必要[^1]
- L3 / BGP / ACL / DHCP relay 等は本テストの範囲外

## 干渉する機能

- **VLAN テストフレームワーク**: PortChannel 前提箇所の修正が必要
- **SNMP**: `public` community 設定（[How-to-Check-SNMP-Configuration](https://github.com/sonic-net/SONiC/wiki/How-to-Check-SNMP-Configuration)）

## 引用元

[^1]: [sonic-net/SONiC doc/test-plans/Sonic Basic L2 Mode Test plan.md @ 49bab5b](https://github.com/sonic-net/SONiC/blob/49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06/doc/test-plans/Sonic%20Basic%20L2%20Mode%20Test%20plan.md)

<!-- evidence (verifier-batch-19):
- sonic-buildimage `src/sonic-config-engine/sonic-cfggen` l.354 `--preset` 引数（choices=`get_available_config()`）と l.551 `generate_sample_config(data, args.preset)`
- 同 `src/sonic-config-engine/data/l2switch.j2` テンプレート存在
- 同 `tests/test_j2files.py` l.308, 379 で `--preset l2` 引数のテスト
- sonic-mgmt fdb / vlan / snmp テストカバレッジは別 repo (本 cache 未取得) で未裏取り
-->

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: L2 / VLAN / LAG / MC-LAG](../topics/06-l2-vlan-lag/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 8ba32e5aa69d -->
