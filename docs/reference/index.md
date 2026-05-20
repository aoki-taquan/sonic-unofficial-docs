---
title: リファレンス
description: "リファレンス — CLI、CONFIG_DB、YANG を機械抽出ベースで整理する参照章。"
verification: meta
last_verified: 2026-05-11
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# リファレンス

`docs/reference/` は SONiC NOS (community master) を運用 / 検証する際に **辞書として直接引く** 情報を集める章である。Topics 章 (`docs/topics/`) が「読み物」として導線を提供するのに対し、本章は **コマンド名 / テーブル名 / モジュール名 / 症状** から逆引きする使い方を想定している。

各 reference ページは原則 `verification: code-verified` で、`.cache/sonic-sources/` に shallow clone した master の固定 commit を一次情報として持つ。[HLD](../reference/glossary.md#term-hld) 由来の推測は本文に明示する。

## サブセクションの入口

| カテゴリ | 入口 | 役割 |
|---|---|---|
| **CLI** | [cli/index.md](cli/index.md) | `config-*` / `show-*` / `clear` / `debug-*` / `sonic-installer` / `sonic-cfggen` 等の `sonic-utilities` ベースのコマンドツリー |
| **[CONFIG_DB](../reference/glossary.md#term-config_db)** | [config-db/index.md](config-db/index.md) | [Redis](../reference/glossary.md#term-redis) DB 4 (CONFIG_DB) のテーブル定義。[orchagent](../reference/glossary.md#term-orchagent) / *mgrd 各 daemon が subscribe するスキーマ |
| **[YANG](../reference/glossary.md#term-yang)** | [yang/index.md](yang/index.md) | `sonic-yang-models` の native SONiC YANG モジュール。CONFIG_DB の正本 |
| **Runbooks** | [runbooks/index.md](runbooks/index.md) | 症状逆引きの運用ハンドブック ([BGP](../reference/glossary.md#term-bgp) down, [PFC](../reference/glossary.md#term-pfc) bandwidth, warm-reboot 失敗 等) |
| **Verification** | [verification/index.md](verification/index.md) | 裏取り運用方針と [discrepancy-index](verification/discrepancy-index.md) (HLD と実装の乖離一覧) |

### 将来追加予定 (未着手)

| カテゴリ | 状態 |
|---|---|
| `glossary/` (用語集) | 未着手。現状は本文中で都度説明 |
| `sai-attributes/` ([SAI](../reference/glossary.md#term-sai) 属性表) | 未着手。今後 `meta/index/sai.json` から生成予定 |
| `config-db-orch-map/` (テーブル ↔ Orch マッピング) | 未着手。現状は CONFIG_DB ページ本文に分散 |

これらの placeholder は backlog (`meta/backlog/reference/`) で追跡する。

## カバー率 (手動集計, 2026-05-20) {#coverage}

`docs/reference/<sub>/*.md` を直接数えた件数。`verification` 内訳は frontmatter の `verification:` キーから抽出した。本表は `gen_coverage.py` の自動更新スコープ外であり、手動メンテで更新している。

| カテゴリ | 総ページ | code-verified | runbook-verified | stub | hld-only | discrepancy-found | meta |
|---|---:|---:|---:|---:|---:|---:|---:|
| CLI | 72 | 71 | 0 | 0 | 0 | 1 | 1 (index) |
| CONFIG_DB | 293 | 285 | 0 | 1 | 2 | 5 | 1 (index) |
| YANG | 84 | 84 | 0 | 0 | 0 | 0 | 1 (index) |
| Runbooks | 52 | 25 | 27 | 0 | 0 | 0 | 1 (index) |
| Verification | 1 | 0 | 0 | 0 | 0 | 0 | 2 (index + discrepancy-index) |
| **合計** | **502** | **465** | **27** | **1** | **2** | **6** | **6** |

discrepancy-found 自体は reference 内ではなく `docs/topics/` 配下に分布する。全 **46** ページ。[discrepancy-index](verification/discrepancy-index.md) から area 別 / monitor 別に逆引きできる。

### 元リポジトリのカバー率参考値

`meta/index/*.json` で棚卸ししたカウントに対する本プロジェクトの reference ページ数 (網羅率はおおよその目安)。

| カテゴリ | 元リポの総数 | 本プロジェクト | 備考 |
|---|---:|---:|---|
| `sonic-utilities` click グループ | ~85 | 72 | 主要グループは網羅、低使用頻度の dropcounters / vrouter 等が残 |
| `sonic-yang-models` の CONFIG_DB テーブル | ~160 | 121 | 派生・廃止テーブルを除いた主要分は網羅 |
| `sonic-*` native YANG モジュール | ~110 | 84 | smartswitch / [DASH](../reference/glossary.md#term-dash) 系の一部、ベンダー特化モジュールが残 |

未カバー分は `meta/backlog/reference/` で追跡しており、Reference 拡張バッチで段階的に消化する。

## よく引かれる項目 (早見リンク集) {#quickref}

主要機能ごとの CLI / CONFIG_DB / YANG / Runbook を 1 行に並べる。HLD への入口は Topics 章を参照する。

### BGP / Routing

- CLI: [config bgp](cli/config-bgp.md) / [show bgp](cli/show-bgp.md) / [show ip](cli/show-ip.md) / [show route-map](cli/show-route-map.md)
- CONFIG_DB: [BGP_GLOBALS](config-db/bgp-globals.md) / [BGP_NEIGHBOR](config-db/bgp-neighbor.md) / [BGP_PEER_GROUP](config-db/bgp-peer-group.md) / [ROUTE_MAP](config-db/route-map.md) / [PREFIX_SET](config-db/prefix-set.md)
- YANG: [sonic-bgp-global](yang/sonic-bgp-global.md) / [sonic-bgp-neighbor](yang/sonic-bgp-neighbor.md) / [sonic-route-map](yang/sonic-route-map.md)
- Runbook: [bgp-session-down](runbooks/bgp-session-down.md) / [bgp-route-not-advertised](runbooks/bgp-route-not-advertised.md)
- Topic: [02 BGP と FRR 制御プレーン](../topics/02-bgp/index.md)

### VLAN / L2 / LAG / MC-LAG

- CLI: [config vlan](cli/config-vlan.md) / [show vlan](cli/show-vlan.md) / [config portchannel](cli/config-portchannel.md) / [config mclag](cli/config-mclag.md) / [show mclag](cli/show-mclag.md)
- CONFIG_DB: [VLAN](config-db/vlan.md) / [VLAN_MEMBER](config-db/vlan-member.md) / [VLAN_INTERFACE](config-db/vlan-interface.md) / [PORTCHANNEL](config-db/portchannel.md) / [PORTCHANNEL_MEMBER](config-db/portchannel-member.md) / [PEER_SWITCH](config-db/peer-switch.md)
- YANG: [sonic-vlan](yang/sonic-vlan.md) / [sonic-portchannel](yang/sonic-portchannel.md) / [sonic-mclag](yang/sonic-mclag.md)
- Runbook: [vlan-tagging](runbooks/vlan-tagging.md) / [portchannel-lacp-not-established](runbooks/portchannel-lacp-not-established.md) / [mclag-sync-failure](runbooks/mclag-sync-failure.md)
- Topic: [06 L2 / VLAN / LAG / MC-LAG](../topics/06-l2-vlan-lag/index.md)

### VXLAN / EVPN / VNET

- CLI: [config vxlan](cli/config-vxlan.md) / [config vnet](cli/config-vnet.md)
- CONFIG_DB: [VXLAN_TUNNEL](config-db/vxlan-tunnel.md) / [VXLAN_TUNNEL_MAP](config-db/vxlan-tunnel-map.md) / [TUNNEL](config-db/tunnel.md) / [TUNNEL_DECAP_TABLE](config-db/tunnel-decap-table.md)
- YANG: [sonic-vxlan](yang/sonic-vxlan.md)
- Runbook: [evpn-type2-not-advertised](runbooks/evpn-type2-not-advertised.md)
- Topic: [03 VXLAN / EVPN / VNET](../topics/03-vxlan-evpn/index.md)

### VRF / ECMP / RIB-FIB

- CLI: [config vrf](cli/config-vrf.md) / [config route](cli/config-route.md) / [show ip](cli/show-ip.md)
- CONFIG_DB: [VRF](config-db/vrf.md) / [FG_NHG](config-db/fg-nhg.md) / [INTERFACE](config-db/interface.md) / [LOOPBACK_INTERFACE](config-db/loopback-interface.md)
- YANG: [sonic-vrf](yang/sonic-vrf.md) / [sonic-route-common](yang/sonic-route-common.md)
- Runbook: [routing-loop-detected](runbooks/routing-loop-detected.md)
- Topic: [04 VRF / ECMP / RIB-FIB](../topics/04-vrf-ecmp/index.md)

### ACL / CoPP / Mirror

- CLI: [config acl](cli/config-acl.md) / [show acl](cli/show-acl.md) / [config mirror-session](cli/config-mirror-session.md)
- CONFIG_DB: [ACL_TABLE](config-db/acl-table.md) / [ACL_RULE](config-db/acl-rule.md) / [COPP_TRAP](config-db/copp-trap.md) / [COPP_GROUP](config-db/copp-group.md) / [MIRROR_SESSION](config-db/mirror-session.md) / [POLICER](config-db/policer.md)
- YANG: [sonic-copp](yang/sonic-copp.md) / [sonic-mirror-session](yang/sonic-mirror-session.md)
- Runbook: [acl-rule-no-hit](runbooks/acl-rule-no-hit.md) / [rif-acl-counter-zero](runbooks/rif-acl-counter-zero.md)
- Topic: [07 ACL / CoPP / Mirror](../topics/07-acl-copp-mirror/index.md)

### QoS / Buffer / PFC

- CLI: [config qos](cli/config-qos.md) / [config buffer](cli/config-buffer.md) / [show buffer](cli/show-buffer.md) / [config pfcwd](cli/config-pfcwd.md) / [show pfc](cli/show-pfc.md) / [show priority-group](cli/show-priority-group.md) / [show queue](cli/show-queue.md)
- CONFIG_DB: [BUFFER_POOL](config-db/buffer-pool.md) / [BUFFER_PROFILE](config-db/buffer-profile.md) / [BUFFER_PG](config-db/buffer-pg.md) / [BUFFER_QUEUE](config-db/buffer-queue.md) / [QUEUE](config-db/queue.md) / [SCHEDULER](config-db/scheduler.md) / [WRED_PROFILE](config-db/wred-profile.md) / [DSCP_TO_TC_MAP](config-db/dscp-to-tc-map.md) / [TC_TO_QUEUE_MAP](config-db/tc-to-queue-map.md) / [PFC_WD](config-db/pfc-wd.md)
- YANG: [sonic-buffer-pool](yang/sonic-buffer-pool.md) / [sonic-buffer-profile](yang/sonic-buffer-profile.md) / [sonic-buffer-pg](yang/sonic-buffer-pg.md) / [sonic-buffer-queue](yang/sonic-buffer-queue.md) / [sonic-queue](yang/sonic-queue.md) / [sonic-scheduler](yang/sonic-scheduler.md) / [sonic-pfcwd](yang/sonic-pfcwd.md) / [sonic-dscp-tc-map](yang/sonic-dscp-tc-map.md) / [sonic-tc-queue-map](yang/sonic-tc-queue-map.md)
- Runbook: [pfc-bandwidth](runbooks/pfc-bandwidth.md)

### Dual-ToR / Mux

- CLI: [config muxcable](cli/config-muxcable.md) / [show muxcable](cli/show-muxcable.md)
- CONFIG_DB: [MUX_CABLE](config-db/mux-cable.md) / [PEER_SWITCH](config-db/peer-switch.md) / [TUNNEL_DECAP_TABLE](config-db/tunnel-decap-table.md)
- Runbook: [dualtor-mux](runbooks/dualtor-mux.md) / [ycable-firmware-update-failure](runbooks/ycable-firmware-update-failure.md)
- Topic: [05 Dual-ToR / Mux](../topics/05-dual-tor/index.md)

### Platform / Port / Optics

- CLI: [show platform](cli/show-platform.md) / [config platform firmware](cli/config-platform-firmware.md) / [show interfaces](cli/show-interfaces.md) / [show environment](cli/show-environment.md) / [show flowcnt](cli/show-flowcnt.md)
- CONFIG_DB: [PORT](config-db/port.md) / [DEVICE_METADATA](config-db/device-metadata.md) / [DEVICE_NEIGHBOR](config-db/device-neighbor.md)
- YANG: [sonic-port](yang/sonic-port.md) / [sonic-device_metadata](yang/sonic-device_metadata.md) / [sonic-interface](yang/sonic-interface.md)
- Runbook: [asic-link-autoneg-mismatch](runbooks/asic-link-autoneg-mismatch.md) / [fec-errors](runbooks/fec-errors.md) / [link-flapping](runbooks/link-flapping.md) / [interface-mtu-mismatch](runbooks/interface-mtu-mismatch.md) / [platform-fan-psu-anomaly](runbooks/platform-fan-psu-anomaly.md)

### Reboot / Warm-restart / Lifecycle

- CLI: [reboot / fast / warm](cli/reboot-fast-warm.md) / [config warm_restart](cli/config-warm_restart.md) / [config kdump](cli/config-kdump.md) / [sonic-installer](cli/sonic-installer.md) / [sonic-package-manager](cli/sonic-package-manager.md)
- CONFIG_DB: [KDUMP](config-db/kdump.md) / [FEATURE](config-db/feature.md)
- Runbook: [warm-reboot-failure](runbooks/warm-reboot-failure.md) / [container-not-starting](runbooks/container-not-starting.md) / [container-memory-limit-exceeded](runbooks/container-memory-limit-exceeded.md) / [minigraph-reload-stuck](runbooks/minigraph-reload-stuck.md)
- Topic: [11 Reboot / Warm-restart](../topics/11-reboot/index.md)

### SAI / SWSS / ASIC_DB

- CONFIG_DB: [FLEX_COUNTER_TABLE](config-db/flex-counter-table.md) / [DEBUG_COUNTER](config-db/debug-counter.md) / [CRM](config-db/crm.md)
- Runbook: [appdb-asicdb-sync-lag](runbooks/appdb-asicdb-sync-lag.md) / [sai-failure](runbooks/sai-failure.md) / [sai-table-full](runbooks/sai-table-full.md) / [crm-threshold-exceeded](runbooks/crm-threshold-exceeded.md) / [flex-counter-stuck](runbooks/flex-counter-stuck.md) / [interface-counters-reset](runbooks/interface-counters-reset.md)
- Topic: [20 SWSS / SAI / Redis](../topics/20-swss-sai-redis/index.md)

### Management / gNMI / SNMP / Telemetry

- CLI: [config snmp](cli/config-snmp.md) / [show snmpagentaddress](cli/show-snmpagentaddress.md) / [show snmptrap](cli/show-snmptrap.md) / [config sflow](cli/config-sflow.md) / [config syslog](cli/config-syslog.md) / [show techsupport](cli/show-techsupport.md)
- CONFIG_DB: [TELEMETRY](config-db/telemetry.md) / [SFLOW](config-db/sflow.md) / [SYSLOG_SERVER](config-db/syslog-server.md) / [AUTO_TECHSUPPORT](config-db/auto-techsupport.md) / [KUBERNETES_MASTER](config-db/kubernetes-master.md)
- YANG: [sonic-syslog](yang/sonic-syslog.md) / [sonic-system-aaa](yang/sonic-system-aaa.md) / [sonic-feature](yang/sonic-feature.md)
- Runbook: [gnmi-subscribe-disconnect](runbooks/gnmi-subscribe-disconnect.md) / [telemetry-dialout-not-sending](runbooks/telemetry-dialout-not-sending.md) / [snmp-polling-timeout](runbooks/snmp-polling-timeout.md) / [snmpv3-auth-failure](runbooks/snmpv3-auth-failure.md) / [techsupport-size-bloat](runbooks/techsupport-size-bloat.md) / [techsupport-timeout](runbooks/techsupport-timeout.md)
- Topic: [10 gNMI / OpenConfig / YANG](../topics/10-gnmi-openconfig/index.md)

### NAT / DHCP / Time / DNS

- CLI: [config nat](cli/config-nat.md) / [show nat](cli/show-nat.md) / [config dhcp-relay](cli/config-dhcp-relay.md) / [config ntp](cli/config-ntp.md) / [show clock](cli/show-clock.md)
- CONFIG_DB: [DHCPV4_RELAY](config-db/dhcpv4-relay.md) / [DHCP_SERVER_IPV4](config-db/dhcp-server-ipv4.md) / [NTP (global)](config-db/ntp-global.md) / [NTP_SERVER](config-db/ntp-server.md)
- YANG: [sonic-ntp](yang/sonic-ntp.md)
- Runbook: [dhcp-relay](runbooks/dhcp-relay.md) / [nat-translation-miss](runbooks/nat-translation-miss.md)

### Security / AAA

- CLI: [config aaa / tacacs / radius](cli/config-aaa.md) / [show aaa](cli/show-aaa.md) / [config ssh](cli/config-ssh.md)
- CONFIG_DB: [TACPLUS_SERVER](config-db/tacplus-server.md) / [LDAP_SERVER](config-db/ldap-server.md) / [MGMT_INTERFACE](config-db/mgmt-interface.md) / [MGMT_VRF_CONFIG](config-db/mgmt-vrf-config.md)
- YANG: [sonic-system-aaa](yang/sonic-system-aaa.md)
- Runbook: [snmpv3-auth-failure](runbooks/snmpv3-auth-failure.md)

### SmartSwitch / DASH

- Runbook: [dash-eni-down](runbooks/dash-eni-down.md) / [smartswitch-dpu-unresponsive](runbooks/smartswitch-dpu-unresponsive.md) / [smartswitch-dpu-image-install-failure](runbooks/smartswitch-dpu-image-install-failure.md) / [smartswitch-dpu-graceful-shutdown-failure](runbooks/smartswitch-dpu-graceful-shutdown-failure.md)

## reference vs topics の役割分担

| 軸 | `docs/reference/` | `docs/topics/` |
|---|---|---|
| 読み方 | 辞書 (名前から逆引き) | 読み物 (機能から導線) |
| 粒度 | 1 コマンド / 1 テーブル / 1 モジュール = 1 ページ | 1 機能 = `setup / operations / deep-dive` の章 |
| frontmatter | `verification: code-verified` 中心 | `code-verified` / `discrepancy-found` / `hld-only` 混在 |
| 主な参照元 | Topics 章末「関連 reference」と Runbook 内コマンド/テーブル名 | Runbook の「関連ページ」、HLD 由来の設計議論 |

詳細な相互ナビゲーションは [Topics: リファレンス横断索引](../topics/22-reference-index/index.md) を参照。本ページ「よく引かれる項目」が **早見表 (canonical) **、Topics 22 章の `cli-index` / `config-db-index` / `yang-index` は **章構造ごとの詳細表 (canonical) ** として役割を分担する。

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: リファレンス横断索引](../topics/22-reference-index/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 1f7c67d9cefa -->
