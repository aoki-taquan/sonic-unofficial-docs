---
title: T0/T1 リンクが flap し続ける
description: "Runbook: T0/T1 リンクが flap し続ける — : sonic-net/sonic-swss @ 4305596 — portsorch.cpp port_state notification : sonic-net/sonic-platform-common @ 4305596 — sfp_base…"
area: reference
verification: runbook-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/portsorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-platform-common
    path: sonic_platform_base/sfp_base.py
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db: [PORT]
  cli: [show interfaces status, show transceiver]
  yang: [sonic-port]
---

# Runbook: T0/T1 リンクが flap し続ける

!!! danger "実行前提"
    `config interface shutdown` / `startup` の連打や `config reload` は周辺 BGP / ECMP 経路を巻き込む。flap 中の interface のみ admin down にして安定化させ、ピア側の状態を確認すること。事前に `show interfaces status > /tmp/if.before` と `show interfaces transceiver eeprom -d > /tmp/xcvr.before` を取得。

## 症状

- syslog に `Port <if> oper status changed from up to down` が断続
- `show interfaces counters errors` の `RX_ERR` / `FCS` が増加
- BGP peer が頻繁に flap

## 想定原因（優先度順）

1. **光モジュール (SFP/QSFP) の劣化**: DOM 値が閾値外
2. **FEC mismatch**: 両端 FEC mode 違い → [fec-errors.md](fec-errors.md)
3. **autoneg / speed mismatch**: → [asic-link-autoneg-mismatch.md](asic-link-autoneg-mismatch.md)
4. **ケーブル / patch panel の物理劣化**
5. **対向側 OS の panic / reboot ループ**

## 切り分け手順

### 1. flap 頻度の定量化

```bash
sudo grep "oper status changed" /var/log/syslog | grep Ethernet0 | tail -20
```

### 2. DOM 値

```bash
show interfaces transceiver eeprom -d Ethernet0
show interfaces transceiver lpmode
```

- RX power が `-15dBm` 未満 / TX power が異常 → 物理層の問題

### 3. FEC / counter

```bash
show interfaces counters fec-stats
show interfaces counters errors Ethernet0
```

### 4. ASIC notification

```bash
docker logs syncd 2>&1 | grep -i "port_state_change" | tail -20
```

## 対処方法

- 一時 admin down で安定化: `sudo config interface shutdown Ethernet0`
- SFP 入れ替え / 清掃
- 両端 FEC mode 統一: `sudo config interface fec Ethernet0 rs`
- 暫定で `config interface speed Ethernet0 <lower>` に落とす

## 関連ページ

- [fec-errors.md](fec-errors.md)
- [asic-link-autoneg-mismatch.md](asic-link-autoneg-mismatch.md)

## 引用元

[^1]: sonic-net/sonic-swss @ 4305596 — portsorch.cpp port_state notification
[^2]: sonic-net/sonic-platform-common @ 4305596 — sfp_base DOM
