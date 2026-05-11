---
title: Interface MTU mismatch によるパケットドロップ
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/portsorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-utilities
    path: config/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: [PORT, VLAN, PORTCHANNEL]
  cli: [show interfaces status, config interface mtu]
  yang: [sonic-port]
---

# Runbook: Interface MTU mismatch によるパケットドロップ

!!! danger "実行前提"
    `config interface mtu <if> <N>` は ASIC への即時反映で、当該 port を一瞬 reset する実装になっている SAI ベンダーが多い。L3 隣接 (BGP/OSPF) が flap する。事前に `show interfaces status > /tmp/if.before` を取り、変更後 `show interfaces status` で差分確認。問題発生時は元の MTU に戻して `config save -y`。

## 症状

- 大きい packet (>1500B) のみ落ちる
- `ping -s 1472 -M do` が通り、`ping -s 8000 -M do` が通らない
- BGP UPDATE が大きい場合のみ session reset

## 想定原因（優先度順）

1. **両端 MTU 不一致**: ローカル 9100、対向 1500 等
2. **VLAN / PortChannel の MTU が member より小さい**: 上位論理 IF が L1 を絞る
3. **MPLS / VXLAN encapsulation オーバーヘッド未考慮**: VTEP で +50B 越え
4. **PMTUD ブラックホール**: 中間 ACL が ICMP `frag-needed` を破棄

## 切り分け手順

### 1. 両端 MTU 比較

```bash
show interfaces status | grep -E "Ethernet0|PortChannel"
ip -d link show Ethernet0
```

- 期待: 両端で同値
- SONiC default: 9100

### 2. PMTUD テスト

```bash
ping -M do -s 1472 <peer>
ping -M do -s 8972 <peer>
```

### 3. ASIC_DB 反映

```bash
sonic-db-cli ASIC_DB hgetall "ASIC_STATE:SAI_OBJECT_TYPE_PORT:<oid>" | grep -i mtu
```

### 4. counters

```bash
show interfaces counters errors
portstat -c
```

- `RX_ERR` / `RX_OVR` の増加を確認

## 対処方法

- 両端を揃える: `sudo config interface mtu Ethernet0 9100` を双方で実行
- VLAN / PortChannel: `sudo config interface mtu Vlan100 9100`
- 保存: `sudo config save -y`

## 関連ページ

- [bgp-session-down.md](bgp-session-down.md)
- [../cli/config-interface.md](../cli/config-interface.md)
- [../config-db/port.md](../config-db/port.md)

## 引用元

[^1]: sonic-net/sonic-swss @ 4305596 — portsorch.cpp の MTU 反映
[^2]: sonic-net/sonic-utilities @ 39732bceb — config interface mtu
