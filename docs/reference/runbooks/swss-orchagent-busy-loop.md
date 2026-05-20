---
title: orchagent が CPU 100% で詰まる
description: 'Runbook: swss/orchagent が busy loop に陥り、新規設定変更が反映されなくなる場合の切り分け'
area: reference
verification: runbook-verified
last_verified: 2026-05-11
tags:
- runbook
- swss
- orchagent
- performance
sources:
- repo: sonic-net/sonic-swss
  path: orchagent/orchdaemon.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-swss
  path: orchagent/orch.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-swss-common
  path: common/consumerstatetable.cpp
  ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
related:
  config_db:
  - CRM
  - BGP_NEIGHBOR
  - BGP_GLOBALS
  - ACL_RULE
  - ACL_TABLE
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_NETWORK
  cli:
  - show processes cpu
  - show logging
  - config bgp
  - show bgp
  - show acl
  - config acl
  yang:
  - sonic-bgp-global
  - sonic-bgp-neighbor
  - sonic-crm
  - sonic-bgp-peergroup
  - sonic-bgp-aggregate-address
  - sonic-bgp-sentinel
  - sonic-bgp-peerrange
---

# Runbook: orchagent が CPU 100% で詰まる

!!! danger "実行前提"
    `docker restart swss` は ASIC 構成を再 sync するため数十秒〜数分の中断が発生し、warm-restart 未設定時は転送断となる。本番では計画 maintenance window で行う。

## 症状

- `top` で `orchagent` プロセスが 1 コアを使い切ったまま
- `config` / `show` の応答が極端に遅く、新規設定が反映されない
- `/var/log/swss/sairedis.rec` の更新が止まる、または逆に膨張
- syslog に `doTask` ループの繰り返し WARN が大量出力

## 切り分けフロー

```mermaid
flowchart TD
    A[orchagent CPU 100%] --> B{特定 Orch でループ?}
    B -- routeorch --> C[大量 route churn / BGP flap]
    B -- aclorch --> D[ACL rule 大量 add / ASIC table full]
    B -- neighorch --> E[ARP storm / SAI 失敗の retry]
    B -- 不明 --> F[gdb / perf で stack 取得]
    F --> G[サポート / コミュニティ向け bug report]
```

## 確認コマンド

```bash
# CPU 使用率
docker exec swss top -b -n 1 | head -20
ps -eLo pid,tid,pcpu,comm | grep orchagent | sort -k3 -n -r | head

# 直近のループメッセージ
sudo grep -E "doTask|retry" /var/log/swss/swss.rec 2>/dev/null | tail -40
sudo grep -i orchagent /var/log/syslog | tail -100

# SAI 操作の頻度
sudo tail -n 200 /var/log/swss/sairedis.rec
sudo wc -l /var/log/swss/sairedis.rec.*

# どの Orch が busy か (perf)
sudo perf top -p $(pgrep -f orchagent) -d 5  # Ctrl-C で抜ける

# Redis 側 queue 滞留
sonic-db-cli APPL_DB info | grep -E "db|keys"
sonic-db-cli COUNTERS_DB dbsize
```

## よくある原因

1. **[BGP](../../reference/glossary.md#term-bgp) flap による大量 route churn** — routeorch が `SAI_STATUS_ITEM_NOT_FOUND` retry でループ
2. **[ACL](../../reference/glossary.md#term-acl) rule 大量挿入で ASIC table full** — aclorch が同一エラーを retry し続ける（`sai-table-full.md` 参照）
3. **[CRM](../../reference/glossary.md#term-crm) / sai resource 枯渇** — `crm-threshold-exceeded.md` 参照
4. **依存関係解決の循環** — port / vlan / neigh の add 順序が逆で `SAI_STATUS_OBJECT_IN_USE`
5. **[syncd](../../reference/glossary.md#term-syncd) レスポンス遅延** — [orchagent](../../reference/glossary.md#term-orchagent) は応答待ちで spin（厳密にはブロックだが top では busy に見える）
6. **flex-counter の polling 頻度過剰** — `flex-counter-stuck.md` 参照

## 対処

- 一時的に **`config bgp shutdown all`** で route churn を止め、[orchagent](../../reference/glossary.md#term-orchagent) が収束するか確認
- [ACL](../../reference/glossary.md#term-acl) / route の bulk delete を試す前に `config save -y` で backup
- 最終手段として `docker restart swss`（中断発生）→ warm-restart 設定がある場合のみ無瞬断に近い

`Orch::doTask` は [ConsumerStateTable](../../reference/glossary.md#term-consumerstatetable) から取り出した変更を 1 件ずつ ASIC へ適用し、[SAI](../../reference/glossary.md#term-sai) が失敗を返したエントリは `m_toSync` に残して次回ループで再試行する設計のため、解消不能なエラーが入ると CPU を使い切る[^1]。

[^1]: `sonic-net/sonic-swss` `orchagent/orch.cpp::Orch::doTask` および `orchagent/orchdaemon.cpp` のメインループ実装。`SAI_STATUS_*` エラーは consumer 側で再キューイングされ、根本原因が解決するまで指数バックオフ無しで retry される。

## 関連 reference / topics

- [sai-table-full.md](sai-table-full.md)
- [crm-threshold-exceeded.md](crm-threshold-exceeded.md)
- [flex-counter-stuck.md](flex-counter-stuck.md)
- [appdb-asicdb-sync-lag.md](appdb-asicdb-sync-lag.md)

<!-- glossary-links-injected: 76c8c3f52726 -->
