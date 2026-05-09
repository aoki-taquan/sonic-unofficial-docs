---
title: SONiC Basic L2 モードテストプラン（FDB / VLAN / SNMP の最小機能検証）
area: switching
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/test-plans/Sonic Basic L2 Mode Test plan.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli:
    - sonic-cfggen --preset l2
  yang: []
---

!!! warning "裏取りステータス: HLD-only"
    `sonic-cfggen -H -p -k <HWSKU> --preset l2` の現行サポート、sonic-mgmt 配下の sanity_check / fdb / vlan / snmp テストの現行カバレッジは未裏取り。

# SONiC Basic L2 モードテストプラン（FDB / VLAN / SNMP の最小機能検証）

## 概要

SONiC を **basic L2 switch** として構成した場合の最小機能を T0 トポロジで検証する[^1]。範囲は意図的に絞られており、L3 / BGP / ACL は対象外。L2 モードの構成手順は [SONiC wiki: L2-Switch-mode](https://github.com/sonic-net/SONiC/wiki/L2-Switch-mode#3-generate-a-configuration-for-l2-switch-mode) に従う。

## 動作仕様

### 設定生成

```bash
sonic-cfggen -H -p -k $HWSKU --preset l2
```

- `-H` で MAC を埋め込み、`-k`/`-p` で port_config.ini を渡す[^1]
- 全ポートが admin-up + Vlan 1000 の untagged member になる構成

### テストケース[^1]

| # | 項目 | sonic-mgmt パス | 期待 |
|---|------|------|------|
| 1 | sanity | `tests/common/sanity_check.py` | orchagent / syncd 起動、リンク Up |
| 2 | FDB | `tests/fdb/test_fdb.py` | 全ポートで MAC 学習 |
| 3 | VLAN + ARP + PING | `tests/vlan/test_vlan.py`（一部要修正: PortChannel 想定箇所） | Vlan IF への IP 設定後、ARP / ping 成立 |
| 4 | SNMP | `tests/snmp/test_snmp_interfaces.py` / `test_snmp_cpu.py` / `test_snmp_psu.py` | Walk 成功（MAC / IF / CPU / PSU 取得） |

サニティチェックは **各テストの前後** で走らせる[^1]。

## 制限事項

- 既存 `vlan_configure` は PortChannel 前提箇所があり、basic L2 mode では修正必要[^1]
- L3 / BGP / ACL / DHCP relay 等は本テストの範囲外

## 干渉する機能

- **VLAN テストフレームワーク**: PortChannel 前提箇所の修正が必要
- **SNMP**: `public` community 設定（[How-to-Check-SNMP-Configuration](https://github.com/sonic-net/SONiC/wiki/How-to-Check-SNMP-Configuration)）

## 引用元

[^1]: [sonic-net/SONiC doc/test-plans/Sonic Basic L2 Mode Test plan.md @ 49bab5b](https://github.com/sonic-net/SONiC/blob/49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06/doc/test-plans/Sonic%20Basic%20L2%20Mode%20Test%20plan.md)
