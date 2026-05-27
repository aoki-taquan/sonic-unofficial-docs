---
title: Runbooks (症状逆引き)
description: 'Runbooks (症状逆引き) — 現場で観測される症状から逆引きで切り分け手順に辿り着くことを目的とした実務向けハンドブック集。症状・原因・確認コマンド・対処の 4 要素で統一された構造で記述する。'
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-utilities
    path: show/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
  - repo: sonic-net/sonic-swss
    path: orchagent/orchdaemon.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db: []
  cli: []
  yang: []
  _no_related: true
---

# Runbooks (症状逆引き)

このセクションは「**現場で観測される症状から逆引きで切り分け手順に辿り着く**」ことを目的とした実務向けハンドブック集。各 runbook は次の構造に従う:

- **症状**: 何が起きているか（ユーザ視点）
- **想定原因**: 優先度順に 3〜5 件
- **切り分け手順**: 実行コマンドと期待 / 異常出力
- **対処方法**: 復旧手段
- **関連ページ**: 該当 topic / reference / discrepancy へのリンク

掲載コマンドおよび DB スキーマは `.cache/sonic-sources/` 内の master 実装を根拠としている。[HLD](../../reference/glossary.md#term-hld) 由来の推測は本文中に明示する。

## 一覧

| # | 症状 | Runbook |
|---|------|---------|
| 01 | [BGP](../../reference/glossary.md#term-bgp) セッションが UP しない | [bgp-session-down.md](bgp-session-down.md) |
| 02 | [VLAN](../../reference/glossary.md#term-vlan) メンバー追加してもタグが付かない | [vlan-tagging.md](vlan-tagging.md) |
| 03 | FEC エラーが多発する | [fec-errors.md](fec-errors.md) |
| 04 | [Warm Reboot](../../reference/glossary.md#term-warm-reboot) が失敗する / 通信断が長引く | [warm-reboot-failure.md](warm-reboot-failure.md) |
| 05 | [PFC](../../reference/glossary.md#term-pfc) で帯域が出ない / Buffer overflow | [pfc-bandwidth.md](pfc-bandwidth.md) |
| 06 | [DHCP Relay](../../reference/glossary.md#term-dhcp-relay) で IP が払い出されない | [dhcp-relay.md](dhcp-relay.md) |
| 07 | [Multi-ASIC](../../reference/glossary.md#term-multi-asic) で namespace 間通信できない | [multi-asic-namespace.md](multi-asic-namespace.md) |
| 08 | Dual-ToR mux が切り替わらない | [dualtor-mux.md](dualtor-mux.md) |
| 09 | [SAI](../../reference/glossary.md#term-sai) failure / [syncd](../../reference/glossary.md#term-syncd) リスタート多発 | [sai-failure.md](sai-failure.md) |
| 10 | コンテナが起動しない (FEATURE) | [container-not-starting.md](container-not-starting.md) |
| 11 | show techsupport が timeout する | [techsupport-timeout.md](techsupport-timeout.md) |
| 12 | counter が更新されない (FLEX_COUNTER) | [flex-counter-stuck.md](flex-counter-stuck.md) |
| 13 | [RIF](../../reference/glossary.md#term-rif) / [ACL](../../reference/glossary.md#term-acl) counter が 0 のまま | [rif-acl-counter-zero.md](rif-acl-counter-zero.md) |
| 14 | [CONFIG_DB](../../reference/glossary.md#term-config_db) save / load が反映されない | [config-save-load.md](config-save-load.md) |
| 15 | [SmartSwitch](../../reference/glossary.md#term-smartswitch) [DPU](../../reference/glossary.md#term-dpu) が応答しない | [smartswitch-dpu-unresponsive.md](smartswitch-dpu-unresponsive.md) |
| 16 | Telemetry が送信されない ([gNMI](../../reference/glossary.md#term-gnmi) dial-out) | [telemetry-dialout-not-sending.md](telemetry-dialout-not-sending.md) |
| 17 | [gNMI](../../reference/glossary.md#term-gnmi) Subscribe が頻繁に切れる | [gnmi-subscribe-disconnect.md](gnmi-subscribe-disconnect.md) |
| 18 | Y-cable firmware 更新が失敗する | [ycable-firmware-update-failure.md](ycable-firmware-update-failure.md) |
| 19 | [PINS](../../reference/glossary.md#term-pins) gRPC (P4Runtime) が応答しない | [pins-grpc-unresponsive.md](pins-grpc-unresponsive.md) |
| 20 | [CRM](../../reference/glossary.md#term-crm) threshold 越え (route / nexthop / [FDB](../../reference/glossary.md#term-fdb) / [ACL](../../reference/glossary.md#term-acl)) | [crm-threshold-exceeded.md](crm-threshold-exceeded.md) |
| 21 | [ASIC](../../reference/glossary.md#term-asic) link が UP しない (autoneg / FEC / speed) | [asic-link-autoneg-mismatch.md](asic-link-autoneg-mismatch.md) |
| 22 | [MACsec](../../reference/glossary.md#term-macsec) MKA セッションが確立しない | [macsec-mka-not-established.md](macsec-mka-not-established.md) |
| 23 | [DASH](../../reference/glossary.md#term-dash) [ENI](../../reference/glossary.md#term-eni) が落ちる | [dash-eni-down.md](dash-eni-down.md) |
| 24 | [SmartSwitch](../../reference/glossary.md#term-smartswitch) [DPU](../../reference/glossary.md#term-dpu) graceful shutdown 失敗 | [smartswitch-dpu-graceful-shutdown-failure.md](smartswitch-dpu-graceful-shutdown-failure.md) |
| 25 | APP_DB → [ASIC_DB](../../reference/glossary.md#term-asic_db) の反映遅延 | [appdb-asicdb-sync-lag.md](appdb-asicdb-sync-lag.md) |
| 26 | SNMPv3 user 認証失敗 | [snmpv3-auth-failure.md](snmpv3-auth-failure.md) |
| 27 | [NAT](../../reference/glossary.md#term-nat) translation が漏れる | [nat-translation-miss.md](nat-translation-miss.md) |
| 28 | [EVPN](../../reference/glossary.md#term-evpn) Type-2 route が広告されない | [evpn-type2-not-advertised.md](evpn-type2-not-advertised.md) |
| 29 | [MCLAG](../../reference/glossary.md#term-mclag) sync 不能 | [mclag-sync-failure.md](mclag-sync-failure.md) |
| 30 | show techsupport の size 肥大化対策 | [techsupport-size-bloat.md](techsupport-size-bloat.md) |
| 31 | [PortChannel](../../reference/glossary.md#term-portchannel) メンバーで [LACP](../../reference/glossary.md#term-lacp) が確立しない | [portchannel-lacp-not-established.md](portchannel-lacp-not-established.md) |
| 32 | [SNMP](../../reference/glossary.md#term-snmp) polling が timeout する | [snmp-polling-timeout.md](snmp-polling-timeout.md) |
| 33 | [BGP](../../reference/glossary.md#term-bgp) route が広告されない | [bgp-route-not-advertised.md](bgp-route-not-advertised.md) |
| 34 | [ACL](../../reference/glossary.md#term-acl) ルールが効かない / counter が増えない | [acl-rule-no-hit.md](acl-rule-no-hit.md) |
| 35 | Interface MTU mismatch によるドロップ | [interface-mtu-mismatch.md](interface-mtu-mismatch.md) |
| 36 | Routing loop が発生している | [routing-loop-detected.md](routing-loop-detected.md) |
| 37 | minigraph 適用後に reload が固まる | [minigraph-reload-stuck.md](minigraph-reload-stuck.md) |
| 38 | T0/T1 リンクが flap し続ける | [link-flapping.md](link-flapping.md) |
| 39 | [CONFIG_DB](../../reference/glossary.md#term-config_db) の永続化が失敗する | [config-db-persistence-failure.md](config-db-persistence-failure.md) |
| 40 | コンテナ memory limit 超過 / OOM kill | [container-memory-limit-exceeded.md](container-memory-limit-exceeded.md) |
| 41 | config save 後に予期しない diff が出る | [config-save-diff-unexpected.md](config-save-diff-unexpected.md) |
| 42 | [SAI](../../reference/glossary.md#term-sai) table full (route / nexthop / [FDB](../../reference/glossary.md#term-fdb)) | [sai-table-full.md](sai-table-full.md) |
| 43 | [SmartSwitch](../../reference/glossary.md#term-smartswitch) [DPU](../../reference/glossary.md#term-dpu) image install 失敗 | [smartswitch-dpu-image-install-failure.md](smartswitch-dpu-image-install-failure.md) |
| 44 | show platform fan / psu 異常値 | [platform-fan-psu-anomaly.md](platform-fan-psu-anomaly.md) |
| 45 | show interfaces counters が突然リセット | [interface-counters-reset.md](interface-counters-reset.md) |

## 使い方の前提

- すべてのコマンドは admin ユーザ（sudo 可）で host 側 shell から実行することを想定する
- container 内コマンドの場合は明示的に `docker exec -it <container> bash` 経由で示す
- [Redis](../../reference/glossary.md#term-redis) key の確認は `redis-cli` ではなく **`sonic-db-cli <DB-NAME>`** を推奨（multi-[ASIC](../../reference/glossary.md#term-asic) 環境で namespace を意識せずに済むため）
- 出力例の数値・MAC・IP はマスクされたサンプル

## 引用元

本ページの根拠は引用元 [^1][^2] を参照。

[^1]: sonic-net/[sonic-utilities](../../reference/glossary.md#term-sonic-utilities) @ 39732bceb（`show/`, `scripts/` 配下の各種ツール）
[^2]: sonic-net/[sonic-swss](../../reference/glossary.md#term-sonic-swss) @ 4305596（[orchagent](../../reference/glossary.md#term-orchagent), [syncd](../../reference/glossary.md#term-syncd) 連携）

<!-- glossary-links-injected: b2808d0c2bca -->
