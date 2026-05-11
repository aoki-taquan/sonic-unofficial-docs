---
title: BGP route が広告されない
description: "Runbook: BGP route が広告されない — : sonic-net/sonic-frr @ 799f47f — bgpd/bgp_route.c : sonic-net/sonic-swss @ 4305596 — fpmsyncd で zebra → APP_DB 反映"
area: reference
verification: runbook-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-frr
    path: bgpd/bgp_route.c
    ref: 799f47f215e4266063c4ebde0041a0c7dd2d11d0
  - repo: sonic-net/sonic-swss
    path: fpmsyncd/fpmlink.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db: [BGP_NEIGHBOR, ROUTE_MAP, PREFIX_LIST]
  cli: [show ip bgp, vtysh]
  yang: [sonic-route-map]
---

# Runbook: BGP route が広告されない

!!! danger "実行前提"
    `clear ip bgp <peer> soft out` は対向への full advertise を再送する。peer の inbound 処理に瞬間負荷がかかる。`clear ip bgp *` 全 reset は経路断を伴うので避ける。修正前に `vtysh -c "show running-config bgpd" > /tmp/frr.bak` を取得し、悪化時は `vtysh -f /tmp/frr.bak` で書き戻す。

## 症状

- `show ip route` には経路があるが、`show ip bgp neighbors <peer> advertised-routes` に出てこない
- 対向側で受信されない
- 自分の loopback prefix が外に出ない

## 想定原因（優先度順）

1. **`network` / redistribute 文の不足**: [FRR](../../reference/glossary.md#term-frr) で `network 1.1.1.0/24` または `redistribute connected` が無い
2. **outbound route-map で deny**: `route-map RM_OUT permit` の match で外れる
3. **prefix-list で除外**: `ip prefix-list PL_OUT` の sequence で deny
4. **next-hop self / community 設定不適**: iBGP で next-hop が peer から到達不能
5. **best-path にならない**: 同 prefix で他の経路（IGP / static）に負けて Adj-RIB-Out に乗らない

## 切り分け手順

### 1. local RIB と Adj-RIB-Out

```bash
docker exec bgp vtysh -c "show ip bgp 1.1.1.0/24"
docker exec bgp vtysh -c "show ip bgp neighbors <peer> advertised-routes"
docker exec bgp vtysh -c "show ip bgp neighbors <peer> received-routes" # 対向側用
```

- 期待: 該当 prefix が `*>` (best, valid) で、advertised-routes に出る
- 異常: best ではない → 他の同 prefix エントリと比較

### 2. route-map の適用

```bash
docker exec bgp vtysh -c "show running-config bgpd" | grep -A20 "neighbor <peer>"
docker exec bgp vtysh -c "show route-map"
```

### 3. prefix-list の確認

```bash
docker exec bgp vtysh -c "show ip prefix-list"
```

### 4. soft clear で再評価

```bash
docker exec bgp vtysh -c "clear ip bgp <peer> soft out"
```

### 5. CONFIG_DB の ROUTE_MAP

```bash
sonic-db-cli CONFIG_DB keys "ROUTE_MAP|*"
sonic-db-cli CONFIG_DB keys "PREFIX_LIST|*"
```

## 対処方法

- `network` 文追加: `vtysh -c "conf t" -c "router bgp <ASN>" -c "network 1.1.1.0/24"` → [CONFIG_DB](../../reference/glossary.md#term-config_db) 側にも反映
- route-map 修正: `route-map RM_OUT permit 100` を追加、または既存の deny を緩める
- iBGP 経路で next-hop 問題: `neighbor <peer> next-hop-self`

## 関連ページ

- [bgp-session-down.md](bgp-session-down.md)
- [../../topics/02-bgp/operations.md](../../topics/02-bgp/operations.md)
- [../config-db/route-map.md](../config-db/route-map.md)

## 引用元

[^1]: sonic-net/sonic-frr @ 799f47f — bgpd/bgp_route.c
[^2]: sonic-net/[sonic-swss](../../reference/glossary.md#term-sonic-swss) @ 4305596 — [fpmsyncd](../../reference/glossary.md#term-fpmsyncd) で [zebra](../../reference/glossary.md#term-zebra) → APP_DB 反映

<!-- glossary-links-injected: 035b99b8e325 -->
