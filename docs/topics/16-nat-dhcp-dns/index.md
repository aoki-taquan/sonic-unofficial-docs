---
title: NAT / DHCP Relay / Time-DNS Services
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/architecture/nat-in-sonic.md
  - docs/architecture/dhcpv4-relay-agent.md
  - docs/architecture/dhcpv6-relay-agent.md
  - docs/routing/dhcp-relay-for-ipv6-hld.md
  - docs/routing/dhcp-relay-per-interface-counter.md
  - docs/management/ipv4-port-based-dhcp-server-in-sonic.md
  - docs/management/dhcp-relay-v4-specify-gaaddr-as-primary-interface-s-gateway-explicitly.md
  - docs/reference/cli/config-nat.md
  - docs/reference/cli/show-nat.md
  - docs/reference/cli/config-dhcp-relay.md
  - docs/reference/config-db/nat.md
  - docs/reference/config-db/dhcpv4-relay.md
  - docs/reference/config-db/dhcp-server-ipv4.md
  - docs/reference/yang/sonic-nat.md
  - docs/reference/yang/sonic-dhcp-server.md
  - docs/acl-qos/dhcp-dos-mitigation-in-sonic.md
  - docs/system/sonic-network-time-protocol-ntp-client-configuration.md
  - docs/system/sonic-migration-to-chrony.md
  - docs/system/static-dns-configuration.md
  - docs/reference/config-db/ntp-global.md
  - docs/reference/config-db/ntp-server.md
  - docs/reference/yang/sonic-ntp.md
  - docs/reference/yang/sonic-dns.md
  - docs/system/twamp-light-hld.md
  - docs/architecture/1-udev-rules-design-for-terminal-server.md
keywords:
  - NAT
  - DHCP Relay
  - DNS
  - NTP
  - Time service
  - dhcrelay
  - natsyncd
  - natmgrd
  - サービス
---

# NAT / DHCP Relay / Time-DNS Services

この章は、SONiC が「edge / management 側で動く付帯サービス」と呼べる機能群、つまり NAT、DHCP relay と DHCP server、NTP / chrony / DNS、そして TWAMP Light や terminal server のような測定・補助サービスをまとめて読むための入口です。これらは BGP や ACL のように data plane の主役ではありませんが、ToR / management スイッチを「使える装置」にするための薄い層であり、container と daemon の境界、management VRF との関係を把握しないと運用で迷います。

NAT は data plane に踏み込むがフローテーブル管理が中心、DHCP relay は L2/L3 broadcast を upstream へ橋渡しする agent、DHCP server は kea を内蔵してポート単位で leases を払い出す機能、time / DNS は OS レイヤ寄りの設定で management VRF 越しに通信する、というように責務がはっきり分かれます。章内のページでは、まずこれらを「どの container / daemon が処理するか」で並べ直します。

## この章で答える質問

- NAT、DHCPv4 relay、DHCPv6 relay、DHCP server は SONiC のどの container / daemon が処理するか。
- DHCPv4 / DHCPv6、per-interface counter、Option 82 / Option 79 はどう設定・監視するか。
- NTP / chrony / static DNS は management VRF とどう関係するか。
- DHCP DoS 緩和、giaddr 固定のような派生機能はどの層に乗っているか。
- TWAMP Light や terminal server はサービス系としてどこに置くか。

## 読み進め方

1. [概念](concept.md): edge service の範囲と、NAT / DHCP relay / DHCP server / time-DNS の責務分担。
2. [アーキテクチャ](architecture.md): `docker-nat`、`docker-dhcp-relay`、`docker-dhcp-server`、kea、chrony と packet flow。
3. [設定](setup.md): NAT、DHCP relay、DHCP server の CONFIG_DB / CLI / YANG リファレンス。
4. [運用](operations.md): counter、DoS 緩和、service health の確認順序。
5. [発展トピック](advanced.md): NTP / chrony 移行、static DNS、TWAMP Light、terminal server udev。

## 関連ページ

- [NAT in SONiC](../../architecture/nat-in-sonic.md)
- [DHCPv4 Relay Agent](../../architecture/dhcpv4-relay-agent.md)
- [DHCPv6 Relay Agent](../../architecture/dhcpv6-relay-agent.md)
- [ポートベース IPv4 DHCP Server](../../management/ipv4-port-based-dhcp-server-in-sonic.md)

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [VRF / ECMP / RIB-FIB パイプライン](../04-vrf-ecmp/index.md)

**派生で読むべき章**

- [Dual-ToR と Mux 制御](../05-dual-tor/index.md)

**補完的に読む章**

- [ACL / CoPP / Mirror / Packet Action](../07-acl-copp-mirror/index.md)
- [L2 / VLAN / LAG / MC-LAG](../06-l2-vlan-lag/index.md)
- [Security / AAA / FIPS / Hardening](../15-security-aaa/index.md)

