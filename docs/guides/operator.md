---
title: 運用者向けガイド
description: 運用者向けガイド — 既に SONiC を運用している読者を想定しています。日々の確認、設定変更、障害調査、CONFIG_DB の意味確認、show
  techsupport やログ・ヘルスチェックの使い方を素早く引くための導線です。
area: guides
verification: meta
last_verified: 2026-05-10
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# 運用者向けガイド

## 想定シナリオ

既に SONiC を運用している読者を想定しています。日々の確認、設定変更、障害調査、[CONFIG_DB](../reference/glossary.md#term-config_db) の意味確認、show techsupport やログ・ヘルスチェックの使い方を素早く引くための導線です。

## 推奨 reading path

1. [CLI リファレンス](../reference/cli/index.md)
2. [show interfaces](../reference/cli/show-interfaces.md)
3. [show ip](../reference/cli/show-ip.md)
4. [show bgp](../reference/cli/show-bgp.md)
5. [show platform](../reference/cli/show-platform.md)
6. [show system-health](../reference/cli/show-system-health.md)
7. [show techsupport](../reference/cli/show-techsupport.md)
8. [config interface](../reference/cli/config-interface.md)
9. [config bgp](../reference/cli/config-bgp.md)
10. [config vlan](../reference/cli/config-vlan.md)
11. [CONFIG_DB リファレンス](../reference/config-db/index.md)
12. [PORT テーブル](../reference/config-db/port.md)
13. [INTERFACE テーブル](../reference/config-db/interface.md)
14. [BGP_NEIGHBOR テーブル](../reference/config-db/bgp-neighbor.md)
15. [VLAN テーブル](../reference/config-db/vlan.md)
16. [show techsupport 設計](../system/show-techsupport.md)
17. [System Health Monitor](../system/sonic-system-health-monitor-high-level-design.md)
18. [Syslog source IP](../system/sonic-syslog-source-ip.md)
19. [NTP client configuration](../system/sonic-network-time-protocol-ntp-client-configuration.md)
20. [Static DNS configuration](../system/static-dns-configuration.md)

## 不足コンテンツ注記

- 障害別の逆引き導線が不足しています。例: 「[BGP](../reference/glossary.md#term-bgp) が上がらない」「ポートが down」「[VLAN](../reference/glossary.md#term-vlan) に疎通しない」「CPU / memory / disk を見たい」から CLI、CONFIG_DB、関連 [HLD](../reference/glossary.md#term-hld) に飛ぶページが必要です。
- CLI と CONFIG_DB の相互参照は各リファレンスで整備されつつありますが、運用手順として「確認、変更、保存、rollback、再起動影響」をまとめた runbook 形式のページがありません。
- `show techsupport`、system health、ログ、カウンタ、platform health をまとめたトラブルシュート入口が必要です。

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: SONiC 全体像と設定基盤](../topics/01-overview/index.md)
- [Topics: 再起動とアップグレード](../topics/11-reboot/index.md)
- [Topics: テレメトリと SNMP](../topics/09-telemetry-snmp/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 12f8ddbcfb3b -->
