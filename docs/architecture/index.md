---
title: アーキテクチャ
verification: stub
---

# アーキテクチャ

SONiC 全体の構成と、各サブシステムの役割を解説する章。

!!! info "準備中"
    このセクションは現在準備中です。

## 予定している内容

- 全体構成図（コンテナ・データベース・SAI・ASIC）
- Redis を中心とした状態管理（CONFIG_DB / APPL_DB / STATE_DB / ASIC_DB / COUNTERS_DB）
- SwSS（Switch State Service）と orchagent の役割
- syncd と SAI の関係
- 各 docker コンテナ（bgp, lldp, snmp, dhcp_relay, pmon, teamd など）の役割
- 設定の流れ（ユーザー入力 → CONFIG_DB → orchagent → APPL_DB → syncd → ASIC）
