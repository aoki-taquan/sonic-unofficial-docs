---
title: BGP Graceful Restart のネゴシエーションに失敗する
description: "Runbook: BGP Graceful Restart (GR) capability が対向と合致せず restart 時に経路断が発生する場合の切り分け"
area: reference
verification: hld-only
last_verified: 2026-05-11
tags: [runbook, bgp, frr]
sources:
  - repo: sonic-net/sonic-frr
    path: bgpd/bgp_open.c
    ref: 799f47f215e4266063c4ebde0041a0c7dd2d11d0
  - repo: sonic-net/sonic-utilities
    path: show/bgp_common.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: [BGP_GLOBALS, BGP_NEIGHBOR]
  cli: [show ip bgp neighbor, vtysh, show bgp summary]
  yang: [sonic-bgp-global, sonic-bgp-neighbor]
---

# Runbook: BGP Graceful Restart のネゴシエーションに失敗する

!!! warning "HLD-only"
    本ページは HLD と FRR の一般動作から再構成した運用ノートで、実コード追跡は一部に留まる。SHA は参考。

!!! danger "実行前提"
    `clear ip bgp *` / `systemctl restart bgp` は全 neighbor を一旦切る。GR の検証時は片方向ずつ行い、ECMP の他経路で fail-over できることを確認してから実行する。

## 症状

- `bgp` container を `systemctl restart bgp` で再起動した瞬間に traffic が落ちる（GR が効いていない）
- `show bgp neighbor <peer>` で `Graceful Restart Capability: none` または対向が `Restart Time: 0`
- syslog に `bgpd: ... End-of-RIB ... not received` が出て、stale path が消えてしまう

## 切り分けフロー

```mermaid
flowchart TD
    A[GR が効いていない] --> B{自分側の GR 有効?}
    B -- No --> C[bgp graceful-restart を有効化]
    B -- Yes --> D{対向が GR capability を送るか}
    D -- No --> E[対向側設定を確認 / vendor 制限]
    D -- Yes --> F{Restart Time / Stale Path Time 一致?}
    F -- No --> G[両端の timer を揃える]
    F -- Yes --> H{End-of-RIB を受信できているか}
    H -- No --> I[control plane の負荷 / TCP MSS / MD5 を確認]
```

## 確認コマンド

```bash
# GR capability の現状
docker exec bgp vtysh -c "show bgp neighbor <peer_ip>" | grep -A20 "Graceful Restart"

# 設定値
docker exec bgp vtysh -c "show running-config" | grep -E "graceful-restart|restart-time|stalepath-time"

# CONFIG_DB 側
sonic-db-cli CONFIG_DB hgetall "BGP_GLOBALS|default" | grep -i graceful

# Restart 直後の stale path
docker exec bgp vtysh -c "show bgp ipv4 unicast" | grep -i stale | head
```

## よくある原因

1. **片側でしか graceful-restart が有効化されていない** — `bgp graceful-restart` が router bgp 配下に無い
2. **Restart Time が短すぎる** — bgpd 再起動が完了する前に対向が stale path を破棄
3. **GR-Notification capability の非互換** — RFC 8538 対応版とそれ以前で挙動が異なる
4. **[BFD](../../reference/glossary.md#term-bfd) と併用時の即 down** — [BFD](../../reference/glossary.md#term-bfd) が即 session down を通知するため GR をスキップする
5. **TCP セッションが MD5 / MSS で再確立できない** — control plane の再ハンドシェイクが失敗

GR capability の交換は [BGP](../../reference/glossary.md#term-bgp) OPEN メッセージ中の Capability Optional Parameter で行われ、[FRR](../../reference/glossary.md#term-frr) は `bgpd/bgp_open.c` でエンコード/デコードする[^1]。

[^1]: `sonic-net/sonic-frr` `bgpd/bgp_open.c` における [Graceful Restart](../../reference/glossary.md#term-graceful-restart) capability (Type 64) のパース。Restart Time / Flags / AFI-SAFI の対称性が両端で合っていなければ GR は片側だけ "advertised" 表示となり実際には機能しない。

## 関連 reference / topics

- [bgp-session-down.md](bgp-session-down.md)
- [bgp-route-not-advertised.md](bgp-route-not-advertised.md)
- [../../topics/02-bgp/operations.md](../../topics/02-bgp/operations.md)
- [../cli/show-bgp.md](../cli/show-bgp.md)

<!-- glossary-links-injected: c40fdca68bfe -->
