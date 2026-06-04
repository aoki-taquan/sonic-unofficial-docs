---
title: 運用者向けガイド
description: 運用者向けガイド — 既に SONiC を運用している読者を想定した入口。日々の確認、設定変更、障害調査、CONFIG_DB
  の意味確認、show techsupport やログ・ヘルスチェックの使い方に加え、症状別の逆引き表をインラインで提供します。
area: guides
verification: meta
last_verified: 2026-06-04
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# 運用者向けガイド

## 想定シナリオ

既に [SONiC](../reference/glossary.md#term-sonic) を運用している読者を想定しています。日々の確認、設定変更、障害調査、[CONFIG_DB](../reference/glossary.md#term-config_db) の意味確認、show techsupport やログ・ヘルスチェックの使い方を素早く引くための導線です。

## 症状別の逆引き表

現場で頻出する症状から、まず叩く CLI、確認すべき CONFIG_DB テーブル、関連 [HLD](../reference/glossary.md#term-hld) を引くための入口を以下に並べます。各エントリは「最初の 1 コマンド + 一次情報の場所」までを目安にしており、深掘りはリンク先の各リファレンスで行ってください。

| 症状 | まず叩く CLI | 関連 CONFIG_DB | 関連リファレンス / HLD |
|------|-------------|----------------|----------------------|
| [BGP](../reference/glossary.md#term-bgp) セッションが上がらない | `show ip bgp summary` / `show ip bgp neighbors <peer>` | [`BGP_NEIGHBOR`](../reference/config-db/bgp-neighbor.md) / [`BGP_PEER_RANGE`](../reference/config-db/bgp-peer-range.md) | [show bgp](../reference/cli/show-bgp.md) / [config bgp](../reference/cli/config-bgp.md) |
| 物理ポートが down のまま | `show interfaces status` / `show interfaces counters` | [`PORT`](../reference/config-db/port.md) / [`INTERFACE`](../reference/config-db/interface.md) | [show interfaces](../reference/cli/show-interfaces.md) / [config interface](../reference/cli/config-interface.md) |
| [VLAN](../reference/glossary.md#term-vlan) 内で疎通しない | `show vlan brief` / `show mac` | [`VLAN`](../reference/config-db/vlan.md) / [`VLAN_MEMBER`](../reference/config-db/vlan-member.md) / [`VLAN_INTERFACE`](../reference/config-db/vlan-interface.md) | [config vlan](../reference/cli/config-vlan.md) |
| ルーティングが期待どおりでない | `show ip route` / `show ip route <prefix>` | [`INTERFACE`](../reference/config-db/interface.md) / [`STATIC_ROUTE`](../reference/config-db/index.md) | [show ip](../reference/cli/show-ip.md) |
| ハードウェア状態を見たい | `show platform summary` / `show platform syseeprom` | （platform 依存） | [show platform](../reference/cli/show-platform.md) |
| CPU / メモリ / ディスク等の health | `show system-health summary` / `show system-health detail` | [`SYSTEM_HEALTH_INFO`](../reference/config-db/index.md) | [show system-health](../reference/cli/show-system-health.md) / [System Health Monitor 設計](../system/sonic-system-health-monitor-high-level-design.md) |
| サポート依頼用の dump 取得 | `show techsupport` | [`AUTO_TECHSUPPORT`](../reference/config-db/auto-techsupport.md) / [`AUTO_TECHSUPPORT_FEATURE`](../reference/config-db/auto-techsupport-feature.md) | [show techsupport](../reference/cli/show-techsupport.md) / [show techsupport 設計](../system/show-techsupport.md) |
| [FRR](../reference/glossary.md#term-frr) / BGP ログを直接読みたい | `show logging` / `docker exec -it bgp vtysh -c 'show bgp summary'` | — | [show bgp](../reference/cli/show-bgp.md) |

BGP セッション関連の状態は CONFIG_DB の `BGP_NEIGHBOR` テーブルに格納され、`bgpcfgd` (`BGPPeerMgrBase`) が `swsscommon.CFG_BGP_NEIGHBOR_TABLE_NAME` を購読して FRR (`vtysh`) 設定へ反映します<!-- evidence: sonic-net/sonic-buildimage src/sonic-bgpcfgd/bgpcfgd/main.py L87 -->。`show ip bgp summary` の実装本体は `sonic-utilities` の `show/bgp_frr_v4.py` (`summary` サブコマンド) にあり、内部で FRR の summary を全 BGP インスタンスから集約して表示します<!-- evidence: sonic-net/sonic-utilities show/bgp_frr_v4.py L36-L44 -->。CONFIG_DB に neighbor が居るのに `show ip bgp summary` に出てこない場合、`bgpcfgd` が動作していない（`systemctl status bgp`）か、FRR コンテナが落ちている疑いがあります。

## 推奨 reading path

逆引き表で当たりが付いた後、面で押さえたい場合の読み順です。フラットに 20 項目並べると入口で迷うため、まず **最初に押さえる 5 件** で導線の骨格をつかみ、その後は用途（BGP / interface・VLAN / health & support / 内部設計）でグルーピングしています。

### まず最初に押さえる 5 件

SONiC を一度も触ったことが無い読者でも、この 5 ページで「CLI と CONFIG_DB が両輪である」ことと、最頻出の障害切り分け入口がわかります。

1. [CLI リファレンス](../reference/cli/index.md) — `show` / `config` の全体像
2. [CONFIG_DB リファレンス](../reference/config-db/index.md) — 設定の正規表現は CLI ではなくこちら
3. [show interfaces](../reference/cli/show-interfaces.md) — 物理層の最初の 1 コマンド
4. [show ip](../reference/cli/show-ip.md) — L3 経路確認の入口
5. [show techsupport](../reference/cli/show-techsupport.md) — 詰まったときの dump

### BGP / ルーティング深掘り

逆引き表の「BGP セッションが上がらない」「ルーティングが期待どおりでない」を起点に追加で読む順です。

- [show bgp](../reference/cli/show-bgp.md)
- [config bgp](../reference/cli/config-bgp.md)
- [BGP_NEIGHBOR テーブル](../reference/config-db/bgp-neighbor.md)

### interface / VLAN 深掘り

物理ポート down や VLAN 内疎通不可を起点に追加で読む順です。

- [config interface](../reference/cli/config-interface.md)
- [config vlan](../reference/cli/config-vlan.md)
- [PORT テーブル](../reference/config-db/port.md)
- [INTERFACE テーブル](../reference/config-db/interface.md)
- [VLAN テーブル](../reference/config-db/vlan.md)

### health / platform / support

ハードウェア状態とサポート依頼まわりです。

- [show platform](../reference/cli/show-platform.md)
- [show system-health](../reference/cli/show-system-health.md)
- [System Health Monitor 設計](../system/sonic-system-health-monitor-high-level-design.md)
- [show techsupport 設計](../system/show-techsupport.md)

### 周辺機能 (NTP / syslog / DNS)

逆引き表に直接は無いが、運用導入直後によく問い合わせが入る周辺機能の HLD です。

- [Syslog source IP](../system/sonic-syslog-source-ip.md)
- [NTP client configuration](../system/sonic-network-time-protocol-ntp-client-configuration.md)
- [Static DNS configuration](../system/static-dns-configuration.md)

## 設定変更時の確認 / 保存 / rollback

逆引き表の対処で設定を変えた場合、最低限の運用フローは以下です。詳細手順は本ガイドの範囲を超えるため、各 CLI ページの「保存」「config reload」セクションを参照してください。

- 変更前: `show runningconfiguration all` で現状の running を控える
- 適用: `config <subcommand>` で適用（即時反映、CONFIG_DB に書かれる）
- 確認: 対応する `show` コマンドと、必要なら `redis-cli -n 4 hgetall '<TABLE>|<key>'` で CONFIG_DB を直接覗く
- 保存: `config save -y`（`/etc/sonic/config_db.json` に永続化、再起動後も保持）
- rollback: 直前の `config_db.json` バックアップに対して `config reload -y <file>`

保存忘れによる再起動後の設定消失と、`config save` 後の意図しない state（過去の暫定設定の永続化）は運用上の頻出事故です。`config save` の前に `show runningconfiguration all` で意図したものか目視する習慣を推奨します。

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: SONiC 全体像と設定基盤](../topics/01-overview/index.md)
- [Topics: Lab / Virtual SONiC / Developer Entry](../topics/21-lab-vs-developer/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: eda153721dca -->
