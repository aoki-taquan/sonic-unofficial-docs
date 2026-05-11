---
title: 経路は RIB にあるが FIB / ASIC に降りない
description: "Runbook: `show ip route` には出るが ASIC に書き込まれず、転送に使われない経路の切り分け"
area: reference
verification: hld-only
last_verified: 2026-05-11
tags: [runbook, routing, fib, fpm]
sources:
  - repo: sonic-net/sonic-swss
    path: fpmsyncd/fpmsyncd.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/routeorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-frr
    path: zebra/zebra_fpm.c
    ref: 799f47f215e4266063c4ebde0041a0c7dd2d11d0
related:
  config_db: [ROUTE_TABLE, NEXTHOP_GROUP]
  cli: [show ip route, vtysh, sonic-db-cli]
  yang: []
---

# Runbook: 経路は RIB にあるが FIB / ASIC に降りない

!!! warning "HLD-only"
    FRR zebra → FPM → fpmsyncd → APPL_DB → routeorch → ASIC_DB の標準パスに基づく運用ノート。

## 症状

- `vtysh -c "show ip route <prefix>"` に該当経路が出るが `*` (FIB selected) が付かない
- `show ip route <prefix>` (SONiC 側) に出ない、または出るのに traffic は DROP
- `APPL_DB ROUTE_TABLE` に entry が無い

## 切り分けフロー

```mermaid
flowchart TD
    A[RIB にあるが FIB に無い] --> B{zebra で selected?}
    B -- No --> C[admin distance / route-map / nexthop 解決確認]
    B -- Yes --> D{APPL_DB ROUTE_TABLE に出る?}
    D -- No --> E[fpmsyncd / FPM socket 確認]
    D -- Yes --> F{ASIC_DB SAI_ROUTE_ENTRY?}
    F -- No --> G[routeorch / CRM / sai-table-full]
    F -- Yes --> H[forwarding 側を確認: ACL/NAT/MTU]
```

## 確認コマンド

```bash
# FRR (RIB)
docker exec bgp vtysh -c "show ip route <prefix>"
docker exec bgp vtysh -c "show ip route <prefix> json" | python3 -m json.tool | head -40

# zebra の FIB 選択
docker exec bgp vtysh -c "show ip route <prefix>" | grep -E "^[A-Z]\*|^[A-Z] "

# SONiC 側
show ip route <prefix>
sonic-db-cli APPL_DB hgetall "ROUTE_TABLE:<prefix>"
sonic-db-cli ASIC_DB keys "ASIC_STATE:SAI_OBJECT_TYPE_ROUTE_ENTRY:*" | grep "<prefix>"

# fpmsyncd の状態
docker exec swss supervisorctl status fpmsyncd
sudo grep -i fpmsyncd /var/log/syslog | tail -50

# CRM (FIB capacity)
crm show resources route
crm show resources nexthop

# Nexthop 解決
docker exec bgp vtysh -c "show ip nht"
ip neigh | grep <nexthop_ip>
```

## よくある原因

1. **Nexthop が unresolved** — ARP が無く、zebra が FIB に入れない
2. **fpmsyncd と zebra の FPM socket 断** — FRR の FPM が disable / socket reconnect ループ
3. **routeorch の bulk pending** — ASIC への書き込みが queue 滞留中
4. **CRM route / nexthop 枯渇** — `crm show resources` で `used == max`
5. **ASIC FIB table full** — `sai-table-full.md` 参照
6. **同一 prefix を別 source が上書き** — static route と BGP route の admin distance
7. **Blackhole / Null route** — `null0` が選択されていて意図せず DROP

## 関連 reference / topics

- [bgp-route-not-advertised.md](bgp-route-not-advertised.md)
- [sai-table-full.md](sai-table-full.md)
- [crm-threshold-exceeded.md](crm-threshold-exceeded.md)
- [swss-orchagent-busy-loop.md](swss-orchagent-busy-loop.md)
- [arp-entry-stuck.md](arp-entry-stuck.md)
