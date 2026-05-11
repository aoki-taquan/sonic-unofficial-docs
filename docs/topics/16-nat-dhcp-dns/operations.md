---
title: 運用
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/reference/cli/show-nat.md
  - docs/routing/dhcp-relay-per-interface-counter.md
  - docs/acl-qos/dhcp-dos-mitigation-in-sonic.md
  - docs/architecture/dhcpv4-relay-agent.md
  - docs/architecture/dhcpv6-relay-agent.md
---

# 運用

NAT / DHCP relay / DHCP server / DoS 緩和は、CPU 経由のパスと ASIC ハードウェアパスの両方を含むため、調査時はまず「どの daemon が動いているか」「どの counter が増えているか」を切り分けるのが近道です。

## NAT の確認順序

1. `show nat config global` / `show nat config bindings` で feature と設定が CONFIG_DB に入っているか。
2. `show nat translations` で iptables 側（natmgrd / natsyncd 経路）の動的・静的エントリ。
3. `show nat statistics` で hit counter。0 ヒットなら、route lookup と NAT zone の inside / outside 設定を疑います。
4. ASIC オフロードを確認するときは `sai_dump` / `SAI_OBJECT_TYPE_NAT_ENTRY` 数を syncd 側で見ます。
5. natsyncd が conntrack を拾えない場合は `docker-nat` の `natsyncd` ログと kernel `nf_conntrack` の counter を確認します。

CLI は [show nat ページ](../../reference/cli/show-nat.md) に詳細があります。

## DHCP relay の確認順序

1. `show dhcp_relay` / `show vlan brief` で VLAN ごとの upstream server が登録されているか。
2. `show dhcp_relay ipv4 counter Vlan<N>` / `show dhcp_relay ipv6 counters Vlan<N>` で per-interface counter が増えるか。RX/TX、direction、message type で切り分けできます。詳細は [per-interface counter ページ](../../routing/dhcp-relay-per-interface-counter.md) を参照してください。
3. counter が 0 のときは `docker-dhcp-relay` 内の `supervisorctl status` で `dhcrelay-Vlan<N>` / `dhcpmon-Vlan<N>` / `dhcp6relay` が `RUNNING` か確認します。
4. v6 で reply が戻らないときは Option 79 / RFC 6939（`dhcpv6_option|rfc6939_support`）の設定と、dual-ToR の場合は loopback アドレス利用を確認します。
5. リセットは `sonic-clear dhcp_relay ipv4 counter` / `sonic-clear dhcp6relay_counters` です。

## DHCP server の確認順序

1. `FEATURE|dhcp_server` の `state` と `docker-dhcp-server` の起動状態。
2. `show dhcp_server ipv4 ...` で kea に流された設定。
3. `docker exec docker-dhcp-server cat /etc/kea/kea-dhcp4.conf` で `dhcpservd` が生成した実体。
4. `docker logs docker-dhcp-server` で kea / lease_update の動作。
5. 払い出しが届かない場合は relay 側 counter で OFFER が relay まで届いているか、giaddr が primary subnet を指しているかを確認します。

## DHCP DoS 緩和の確認

ポートごとの `dhcp_rate_limit` は CONFIG_DB の `PORT` に書き込まれます。ただし master では portmgrd の tc 投入実装が未取り込みで、`tc qdisc show dev <port>` で確認しても rate limiter は入っていない可能性が高いです。CoPP 側の `dhcp_relay` trap は従来通り残っているため、システム全体での DHCP rate 制限はそちらで効きます。詳細は [DHCP DoS 緩和ページ](../../acl-qos/dhcp-dos-mitigation-in-sonic.md) を参照してください。

## サービス health の見方

- `docker ps` で `docker-nat` / `docker-dhcp-relay` / `docker-dhcp-server` が UP か。`FEATURE` で disabled の container は起動しません。
- `systemctl status nat` / `dhcp_relay` / `dhcp_server` でホスト側 unit の状態。
- `supervisorctl status` を各 container で叩き、subprocess（dhcrelay / dhcpmon / kea / natmgrd / natsyncd）の状態を見ます。
- ログは `/var/log/syslog`、各 container の `/var/log/supervisor*.log`、`/var/log/dhcrelay.log`、kea の `/var/log/kea-dhcp4.log` に分散します。

## 関連ページ

- [show nat](../../reference/cli/show-nat.md)
- [DHCP Relay per-interface counter](../../routing/dhcp-relay-per-interface-counter.md)
- [DHCP DoS 緩和](../../acl-qos/dhcp-dos-mitigation-in-sonic.md)
- [DHCPv4 Relay Agent](../../architecture/dhcpv4-relay-agent.md)
- [DHCPv6 Relay Agent](../../architecture/dhcpv6-relay-agent.md)
