---
title: 運用
description: 運用 — NAT / DHCP relay / DHCP server / DoS 緩和は、CPU 経由のパスと ASIC ハードウェアパスの両方を含むため、調査時はまず「どの
  daemon が動いているか」「どの counter が増えているか」を切り分けるのが近道です。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/reference/cli/show-nat.md
- docs/routing/dhcp-relay-per-interface-counter.md
- docs/acl-qos/dhcp-dos-mitigation-in-sonic.md
- docs/architecture/dhcpv4-relay-agent.md
- docs/architecture/dhcpv6-relay-agent.md
related:
  cli:
  - show nat
  - clear
  - show feature
  - show vlan
  - config nat
  - show acl
  - config acl
  config_db:
  - NAT
  - VLAN
  - PORT
  - FEATURE
  - COPP_GROUP
  - COPP_TRAP
  - ACL_RULE
  yang:
  - sonic-nat
  - sonic-copp
  - sonic-vlan
  - sonic-vlan-sub-interface
---

# 運用

[NAT](../../reference/glossary.md#term-nat) / DHCP relay / DHCP server / DoS 緩和は、CPU 経由のパスと ASIC ハードウェアパスの両方を含むため、調査時はまず「どの daemon が動いているか」「どの counter が増えているか」を切り分けるのが近道です。

## サービス全体の入口

```bash
admin@sonic:~$ docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'nat|dhcp'
docker-nat               Up 5 days
docker-dhcp-relay        Up 5 days
docker-dhcp-server       Up 2 hours

admin@sonic:~$ show feature status | grep -E 'nat|dhcp'
nat               enabled        enabled         enabled       N/A
dhcp_relay        enabled        enabled         enabled       N/A
dhcp_server       enabled        enabled         enabled       N/A
```

`Status` が `Restarting` を繰り返す container は config 不整合（[CONFIG_DB](../../reference/glossary.md#term-config_db) 側の参照テーブル欠落、テンプレート展開失敗）か、kernel 側の前提モジュール（`nf_conntrack`, `nf_nat`）未ロードの可能性があります。`docker logs --tail 200 docker-nat` を先に見ます。

## NAT の確認順序

1. `show nat config global` / `show nat config bindings` で feature と設定が CONFIG_DB に入っているか。
2. `show nat translations` で iptables 側（[natmgrd](../../reference/glossary.md#term-natmgrd-natsyncd) / natsyncd 経路）の動的・静的エントリ。
3. `show nat statistics` で hit counter。0 ヒットなら、route lookup と NAT zone の inside / outside 設定を疑います。
4. ASIC オフロードを確認するときは `sai_dump` / `SAI_OBJECT_TYPE_NAT_ENTRY` 数を [syncd](../../reference/glossary.md#term-syncd) 側で見ます。
5. natsyncd が conntrack を拾えない場合は `docker-nat` の `natsyncd` ログと kernel `nf_conntrack` の counter を確認します。

CLI は [show nat ページ](../../reference/cli/show-nat.md) に詳細があります。

### NAT の典型 show 出力

```bash
admin@sonic:~$ show nat config global
Admin Mode    : enabled
Global Timeout: 600 secs
TCP Timeout   : 86400 secs
UDP Timeout   : 300 secs

admin@sonic:~$ show nat translations
Static NAT Entries .................. 2
Dynamic NAT Entries ................. 128
Static NAPT Entries ................. 4
Dynamic NAPT Entries ................ 2418

Protocol  Source              Destination       Translated Source     Translated Destination
--------  ------------------  ----------------  --------------------  ----------------------
tcp       10.1.1.5:55321      203.0.113.10:443  192.0.2.5:50001       203.0.113.10:443
udp       10.1.1.6:5060       203.0.113.20:5060 192.0.2.5:50002       203.0.113.20:5060
...

admin@sonic:~$ show nat statistics
Protocol    Source           Destination       Packets       Bytes
--------    ---------------  ----------------  ------------  ------------
tcp         10.1.1.5         203.0.113.10        1,204,500    62,308,000
udp         10.1.1.6         203.0.113.20           58,402    18,945,000

admin@sonic:~$ redis-cli -n 4 hgetall 'NAT_GLOBAL|Values'
1) "admin_mode"
2) "enabled"
3) "nat_tcp_timeout"
4) "86400"
```

`Dynamic NAT Entries=0` で長期間張り付くのは、inside zone がきちんと設定されていない、または route lookup で outside zone に出ていないケースが多いです。`show nat zones` で zone と interface のひも付けを確認します。ASIC オフロード状態は `syncd` 側で `redis-cli -n 1 keys 'ASIC_STATE:SAI_OBJECT_TYPE_NAT_ENTRY:*' | wc -l` で件数を見ます。

## DHCP relay の確認順序

1. `show dhcp_relay` / `show vlan brief` で [VLAN](../../reference/glossary.md#term-vlan) ごとの upstream server が登録されているか。
2. `show dhcp_relay ipv4 counter Vlan<N>` / `show dhcp_relay ipv6 counters Vlan<N>` で per-interface counter が増えるか。RX/TX、direction、message type で切り分けできます。詳細は [per-interface counter ページ](../../routing/dhcp-relay-per-interface-counter.md) を参照してください。
3. counter が 0 のときは `docker-dhcp-relay` 内の `supervisorctl status` で `dhcrelay-Vlan<N>` / `dhcpmon-Vlan<N>` / `dhcp6relay` が `RUNNING` か確認します。
4. v6 で reply が戻らないときは Option 79 / RFC 6939（`dhcpv6_option|rfc6939_support`）の設定と、dual-ToR の場合は loopback アドレス利用を確認します。
5. リセットは `sonic-clear dhcp_relay ipv4 counter` / `sonic-clear dhcp6relay_counters` です。

### DHCP relay の典型 show 出力

```bash
admin@sonic:~$ show dhcp_relay ipv4 helper Vlan1000
-------  -------------
Vlan1000  192.0.2.10
          192.0.2.11
-------  -------------

admin@sonic:~$ show dhcp_relay ipv4 counter Vlan1000
Message Type    Vlan1000(RX)    Vlan1000(TX)
--------------  --------------  --------------
Discover                  4218               0
Offer                        0            4150
Request                   4150               0
ACK                          0            4148
NAK                          0               2
Release                    312               0
Decline                      6               0

admin@sonic:~$ show dhcp_relay ipv6 counters Vlan1000
Message Type   Vlan1000(RX)    Vlan1000(TX)
-------------  --------------  --------------
Solicit                  1840              0
Advertise                   0           1820
Request                  1820              0
Reply                       0           1815
```

`Discover` が RX に来るのに `Offer` が TX で 0 のときは、upstream server まで届いていないか、server からの reply が relay の待ち受けポートに戻っていないかです。`tcpdump -i any port 67 or port 68` で実体を確認します。`dhcrelay-Vlan1000` の supervisor 状態と `/var/log/dhcrelay.log` も併せて見ます。

## DHCP server の確認順序

1. `FEATURE|dhcp_server` の `state` と `docker-dhcp-server` の起動状態。
2. `show dhcp_server ipv4 ...` で kea に流された設定。
3. `docker exec docker-dhcp-server cat /etc/kea/kea-dhcp4.conf` で `dhcpservd` が生成した実体。
4. `docker logs docker-dhcp-server` で kea / lease_update の動作。
5. 払い出しが届かない場合は relay 側 counter で OFFER が relay まで届いているか、giaddr が primary subnet を指しているかを確認します。

### DHCP server (kea) の確認

```bash
admin@sonic:~$ show dhcp_server ipv4
Interface    Mode    Lease    Default Router   Subnet         Pool                          Status
-----------  ------  -------  ---------------  -------------  ----------------------------  --------
Vlan1000     PORT    900      192.168.10.1     192.168.10.0   192.168.10.10-192.168.10.200  enabled

admin@sonic:~$ docker exec docker-dhcp-server kea-shell --host 127.0.0.1 -- lease4-get-all
{ "arguments": { "leases": [ ... ] }, "result": 0 }

admin@sonic:~$ docker logs docker-dhcp-server 2>&1 | tail -10
2026-05-10T03:21:01 INFO  DHCP4_LEASE_ALLOC [hwtype=1 11:22:33:44:55:66], cid=[no info], tid=0x2c8c87b1: lease 192.168.10.42 has been allocated
2026-05-10T03:21:11 ERROR DHCP4_PACKET_RECEIVE_FAIL: error while receiving DHCPv4 packet: ...
```

`lease4-get-all` で結果が空のときは、kea-dhcp4 が起動失敗しているか、設定生成の `dhcpservd` が `CONFIG_DB` を読めていない可能性があります。

## DHCP DoS 緩和の確認

ポートごとの `dhcp_rate_limit` は CONFIG_DB の `PORT` に書き込まれます。ただし master では [portmgrd](../../reference/glossary.md#term-portmgrd) の tc 投入実装が未取り込みで、`tc qdisc show dev <port>` で確認しても rate limiter は入っていない可能性が高いです。[CoPP](../../reference/glossary.md#term-copp) 側の `dhcp_relay` trap は従来通り残っているため、システム全体での DHCP rate 制限はそちらで効きます。詳細は [DHCP DoS 緩和ページ](../../acl-qos/dhcp-dos-mitigation-in-sonic.md) を参照してください。

```bash
admin@sonic:~$ redis-cli -n 4 hget 'PORT|Ethernet0' dhcp_rate_limit
"300"

admin@sonic:~$ tc qdisc show dev Ethernet0
qdisc mq 0: root
qdisc pfifo_fast 0: parent :8 bands 3 priomap 1 2 2 2 1 2 0 0 1 1 1 1 1 1 1 1
（dhcp_rate_limit が ASIC / tc に入っていないため、ここに ingress qdisc は見えない）

admin@sonic:~$ show copp -t dhcp_relay
Trap Name           Trap Group       Trap Action    Trap Priority   Queue       CBS    CIR
-----------------   --------------   -------------  --------------- -------     ----   ----
dhcp                queue1_group3    trap                       3       3      600    600
dhcpv6              queue1_group3    trap                       3       3      600    600
```

`CIR=600` pps の CoPP 上限が DHCP 全体の supervisor 流入 cap です。これを超える DHCP storm は ASIC で drop されます。

## サービス health の見方

- `docker ps` で `docker-nat` / `docker-dhcp-relay` / `docker-dhcp-server` が UP か。`FEATURE` で disabled の container は起動しません。
- `systemctl status nat` / `dhcp_relay` / `dhcp_server` でホスト側 unit の状態。
- `supervisorctl status` を各 container で叩き、subprocess（dhcrelay / dhcpmon / kea / natmgrd / natsyncd）の状態を見ます。
- ログは `/var/log/syslog`、各 container の `/var/log/supervisor*.log`、`/var/log/dhcrelay.log`、kea の `/var/log/kea-dhcp4.log` に分散します。

## 異常検出と典型ログ

| ログ片 | 意味 | 一次対応 |
|---|---|---|
| `natsyncd: failed to receive conntrack event: No buffer space` | conntrack イベント受信オーバーフロー | `nf_conntrack_buckets` 確認、kernel パラメータ調整 |
| `natmgrd: failed to add NAT entry: SAI_STATUS_TABLE_FULL` | ASIC NAT 表枯渇 | NAT pool 縮小、timeout 短縮で entry 自然削減 |
| `dhcrelay: cannot bind socket: Address already in use` | 別 dhcrelay インスタンスが残存 | `pkill dhcrelay` の上、`supervisorctl restart` |
| `dhcrelay: forward_packet: bad bootp packet` | malformed DHCP packet 受信 | source MAC / port を [ACL](../../reference/glossary.md#term-acl) でブロック |
| `dhcp6relay: drop packet: option 79 missing` | LDRA 設定不一致 | RFC 6939 (Option 79) 設定を確認 |
| `kea-dhcp4: CONFIGURATION_FAILED` | 設定生成 / 構文エラー | `dhcpservd` ログと kea config 実体を確認 |
| `kernel: nf_conntrack: table full, dropping packet` | conntrack table 満杯 | hashsize / max を増やす |

## DB / 設定実体の参照表

| 対象 | DB / ファイル | 確認方法 |
|---|---|---|
| NAT global | `CONFIG_DB` `NAT_GLOBAL` | `redis-cli -n 4 hgetall 'NAT_GLOBAL\|Values'` |
| NAT zone | `CONFIG_DB` `NAT_ZONE\|<intf>` | `redis-cli -n 4 keys 'NAT_ZONE*'` |
| 動的 NAT セッション | `APPL_DB` `NAT_TABLE`, kernel conntrack | `conntrack -L` |
| ASIC NAT | `ASIC_DB` `SAI_OBJECT_TYPE_NAT_ENTRY` | `redis-cli -n 1 keys 'ASIC_STATE:SAI_OBJECT_TYPE_NAT_ENTRY:*'` |
| DHCP relay 設定 | `CONFIG_DB` `VLAN\|Vlan<N>` の `dhcp_servers` | `redis-cli -n 4 hgetall 'VLAN\|Vlan1000'` |
| DHCP relay counter | `COUNTERS_DB` `DHCPV4_COUNTER_TABLE` / `DHCPV6_COUNTER_TABLE` | `redis-cli -n 2 keys 'DHCPV4_COUNTER_TABLE*'` |
| DHCP server 設定 | `CONFIG_DB` `DHCP_SERVER_IPV4*` | `redis-cli -n 4 keys 'DHCP_SERVER_IPV4*'` |
| kea 生成 config | `docker-dhcp-server:/etc/kea/kea-dhcp4.conf` | `docker exec docker-dhcp-server cat ...` |
| CoPP trap | `CONFIG_DB` `COPP_TRAP\|dhcp` | `show copp -t dhcp` |

## 復旧コマンドの目安

| 状況 | コマンド | 注意 |
|---|---|---|
| dhcrelay-VlanN のみ再起動 | `docker exec docker-dhcp-relay supervisorctl restart dhcrelay-Vlan1000` | 該当 VLAN で数秒の DHCP 中断 |
| nat container 全体再起動 | `sudo systemctl restart nat` | 既存 NAT セッション全断 |
| NAT counter クリア | `sudo sonic-clear nat statistics` | 集計のみクリア、entry は維持 |
| NAT 動的 entry 全削除 | `sudo sonic-clear nat translations` | アクティブセッション断 |
| DHCP server config 再展開 | `docker exec docker-dhcp-server supervisorctl restart dhcpservd kea-dhcp4` | 払い出し中の lease は維持 |
| conntrack 全 flush | `sudo conntrack -F` | 既存接続全断、最終手段 |

破壊的になりやすいのは `clear nat translations` と `conntrack -F` で、両方ともユーザー通信を切ります。深夜帯または HA 片系で実施するのが定石です。

## 他章への誘導

- DHCP storm の root cause が CoPP / ACL 側のときは [ACL / CoPP / Mirror の運用](../07-acl-copp-mirror/operations.md) を参照。
- VLAN 設計や SVI 経路の問題は [L2 / VLAN / LAG の運用](../06-l2-vlan-lag/operations.md) を参照。
- DHCP server の設計と kea テンプレート展開の詳細は [architecture](./architecture.md)、API 拡張は [advanced](./advanced.md) を参照。

## 関連ページ

- [show nat](../../reference/cli/show-nat.md)
- [DHCP Relay per-interface counter](../../routing/dhcp-relay-per-interface-counter.md)
- [DHCP DoS 緩和](../../acl-qos/dhcp-dos-mitigation-in-sonic.md)
- [DHCPv4 Relay Agent](../../architecture/dhcpv4-relay-agent.md)
- [DHCPv6 Relay Agent](../../architecture/dhcpv6-relay-agent.md)

<!-- glossary-links-injected: 6c3f4b3a3498 -->
