---
title: 運用
description: BGP の運用確認は neighbor 状態だけでは足りない。FRR で best path か、APPL_DB / ASIC に届いたか、BMP や SNMP CiscoBgp4MIB の外部監視に出ているかを分けて確認する手順をまとめる。
area: topics
verification: meta
last_verified: 2026-06-06
sources:
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d
  - repo: sonic-net/sonic-snmpagent
    path: src/sonic_ax_impl/mibs/vendor/cisco/bgp4.py
    ref: 329f1cc
  - repo: sonic-net/sonic-swss
    path: fpmsyncd/fpmsyncd.cpp
    ref: 4305596
  - repo: sonic-net/sonic-buildimage
    path: dockers/docker-fpm-frr/TSA
    ref: 799f47f
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-bmpcfgd/bmpcfgd/bmpcfgd.py
    ref: 799f47f
related:
  cli:
  - show bgp
  - show ip
  - clear
  - config bgp
  - show bfd
  - config snmp
  - show acl
  config_db:
  - BMP
  - SNMP
  - VRF
  - CRM
  - BGP_NEIGHBOR
  - SNMP_AGENT_ADDRESS_CONFIG
  - ACL_RULE
  yang:
  - sonic-crm
  - sonic-snmp
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-global
  - sonic-bgp-bbr
---

# 運用

[BGP](../../reference/glossary.md#term-bgp) の運用確認は、neighbor の状態確認だけでは足りない。route が [FRR](../../reference/glossary.md#term-frr) で選ばれているか、[SONiC](../../reference/glossary.md#term-sonic) に渡っているか、[ASIC](../../reference/glossary.md#term-asic) に入ったか、外部監視に見えているかを分けて確認する。

## 状態確認の入口

| 見たいもの | 入口 |
| --- | --- |
| neighbor、RIB、AF ごとの BGP 状態 | [CLI: show bgp](../../reference/cli/show-bgp.md) |
| policy の適用元 | [CLI: show route-map](../../reference/cli/show-route-map.md) |
| BGP monitor protocol による外部収集 | [BMP](../../routing/bmp-for-monitoring-sonic-bgp-info.md) |
| [SNMP](../../reference/glossary.md#term-snmp) CiscoBgp4MIB | [CiscoBgp4MIB の STATE_DB 経由化](../../routing/ciscobgp4mib-implementation-changes.md) |

`show bgp` は FRR 側の BGP 状態を見る。route がそこで best でも、ASIC への install 成功までは保証しない。転送面まで疑う場合は [APPL_DB](../../reference/glossary.md#term-appl_db)/[ASIC_DB](../../reference/glossary.md#term-asic_db)、[orchagent](../../reference/glossary.md#term-orchagent) ログ、[syncd](../../reference/glossary.md#term-syncd)/[SAI](../../reference/glossary.md#term-sai) のエラーも見る。

## FIB に入らないときの切り分け

FIB 未導入時は次の順に狭める。

1. `show bgp ...` で peer から route を受け、best path になっているかを見る。
2. [zebra](../../reference/glossary.md#term-zebra)/[FPM](../../reference/glossary.md#term-fpm) から [fpmsyncd](../../reference/glossary.md#term-fpmsyncd) へ route が流れているかを確認する。
3. APPL_DB の `ROUTE_TABLE` と `NEXTHOP_GROUP_TABLE` に期待する entry があるかを見る。
4. orchagent が route/nexthop group を処理し、SAI エラーを出していないかを見る。
5. Suppress FIB Pending が有効な構成では、offload 完了まで advertise が抑止されていないか確認する。

<!-- evidence:
source: sonic-net/sonic-swss/fpmsyncd/fpmsyncd.cpp#L110-L115 (sha: 4305596)
excerpt: |
  deviceMetadataTable.hget("localhost", "suppress-fib-pending", suppressionEnabledStr);
  if (suppressionEnabledStr == "enabled")
reasoning: fpmsyncd は DEVICE_METADATA の suppress-fib-pending フラグを読み、enable 時のみ FIB pending 検出フローを起動する。
-->


歴史的な Route Install Error Handling [HLD](../../reference/glossary.md#term-hld) は `ERROR_ROUTE_TABLE` と `FIB-install pending` 表示を提案しているが、現行 master の orchagent / fpmsyncd にはこの table 名のコードは存在せず、後発の Suppress FIB Pending（fpmsyncd の `suppress-fib-pending` フラグ + zebra `bgp suppress-fib-pending` 連携）で部分的に置換されている扱いになっている。

<!-- evidence:
source: sonic-net/sonic-swss/fpmsyncd/fpmsyncd.cpp#L110-L300 (sha: 4305596)
excerpt: |
  // fpmsyncd では suppress-fib-pending のハンドリングのみが存在し、
  // ERROR_ROUTE_TABLE / fib-install pending という旧 HLD の table 名は存在しない。
reasoning: Route Install Error Handling HLD は現行 master では別経路（suppress-fib-pending）に置き換わっており、HLD と実装に乖離がある旨を裏取り。
-->
実運用では [BGP Suppress FIB Pending](../../routing/bgp-suppress-announcements-of-routes-not-installed-in-hw.md) と組み合わせて読む。

## BMP は何を見る機能か

BMP は BGP の Adj-RIB-In/Out や peer state を外部 collector に送るための監視機構である。SONiC では `BMP_STATE_DB`（`sonic-swss-common/common/schema.h` で database id 20 として定義）と、`bmpcfgd` が `BGP_NEIGHBOR` / `BGP_RIB_IN_TABLE` / `BGP_RIB_OUT_TABLE` を書く構成、および FRR 側の BMP 有効化が関わる。

<!-- evidence:
source: sonic-net/sonic-swss-common/common/schema.h#L33-L33 (sha: 158de8d)
excerpt: |
  #define BMP_STATE_DB        20
reasoning: BMP_STATE_DB が swss-common 側で database id 20 として正式に定義されている裏取り。
-->
<!-- evidence:
source: sonic-net/sonic-buildimage/src/sonic-bmpcfgd/bmpcfgd/bmpcfgd.py#L21-L76 (sha: 799f47f)
excerpt: |
  BMP_STATE_DB = "BMP_STATE_DB"
  self.state_db_conn.delete_all_by_pattern(BMP_STATE_DB, 'BGP_NEIGHBOR*')
  self.state_db_conn.delete_all_by_pattern(BMP_STATE_DB, 'BGP_RIB_IN_TABLE*')
  self.state_db_conn.delete_all_by_pattern(BMP_STATE_DB, 'BGP_RIB_OUT_TABLE*')
reasoning: bmpcfgd が BMP_STATE_DB 上の BGP_NEIGHBOR / BGP_RIB_IN_TABLE / BGP_RIB_OUT_TABLE を管理しており、Adj-RIB-In/Out が DB に出る構造が確認できる。
-->
[Multi-ASIC](../../reference/glossary.md#term-multi-asic) や [gNMI](../../reference/glossary.md#term-gnmi) Streaming との接点もあるため、単なる `show bgp` の置き換えではなく、継続監視用の出口として読む。

## CiscoBgp4MIB はなぜ STATE_DB 経由か

CiscoBgp4MIB は SNMP から BGP neighbor 情報を見せるための互換面である。旧設計のように SNMP 実装が FRR の VTY socket に直接依存すると、daemon 間結合が強い。[STATE_DB](../../reference/glossary.md#term-state_db) 経由化では `bgpmon` が FRR から情報を収集し、`NEIGH_STATE_TABLE` に書き、SNMP 側は DB を読む。運用上は、SNMP に出ない場合に FRR、bgpmon、STATE_DB、snmp_ax_impl のどこで止まっているかを分けて確認できる。

<!-- evidence:
source: sonic-net/sonic-snmpagent/src/sonic_ax_impl/mibs/vendor/cisco/bgp4.py#L29-L40 (sha: 329f1cc)
excerpt: |
  self.neigh_state_map = Namespace.dbs_keys_namespace(self.db_conn, mibs.STATE_DB, "NEIGH_STATE_TABLE|*")
  ...
  neigh_info = self.db_conn[db_index].get_all(mibs.STATE_DB, neigh_key, blocking=False)
  state = neigh_info['state']
reasoning: CiscoBgp4MIB の実装が FRR VTY ではなく STATE_DB の NEIGH_STATE_TABLE から neighbor state を読み出していることを確認。
-->


## show bgp summary の出力サンプル

`show ip bgp summary` は FRR の `show bgp ipv4 unicast summary` を整形したものである。代表的な T1 ToR の構成では次のように 24 neighbor が並ぶ。

```text
IPv4 Unicast Summary:
BGP router identifier 10.1.0.32, local AS number 65100 vrf-id 0
BGP table version 12811
RIB entries 12817, using 2358328 bytes of memory
Peers 24, using 502080 KiB of memory
Peer groups 4, using 256 bytes of memory


Neighbor       V     AS    MsgRcvd    MsgSent    TblVer    InQ    OutQ  Up/Down    State/PfxRcd    NeighborName
-----------  ---  -----  ---------  ---------  --------  -----  ------  ---------  --------------  --------------
10.0.0.1       4  65200       5919       2717         0      0       0  1d21h11m   6402            ARISTA01T2
10.0.0.5       4  65200       5916       2714         0      0       0  1d21h10m   6402            ARISTA03T2
10.0.0.33      4  64001          0          0         0      0       0  never      Active          ARISTA01T0
10.0.0.35      4  64002          0          0         0      0       0  never      Active          ARISTA02T0
...
Total number of neighbors 24
```

[VRF](../../reference/glossary.md#term-vrf) 指定時（`show ip bgp summary vrf Vrf_red` 等）は `vrf-id` が 0 ではなく VRF の数値 ID になり、neighbor 集合も VRF スコープに限定される。

カラムの読み方:

- `State/PfxRcd` は数値なら受信プレフィクス数で Established 相当、`Active` / `Idle` / `Connect` / `OpenSent` / `OpenConfirm` は未確立。`Active` が続くなら TCP 接続失敗、`OpenSent` で止まるなら capability 不一致を疑う。
- `Up/Down` の `never` は一度も Established していない印。physical link / TCP / [ACL](../../reference/glossary.md#term-acl) / source IP / password を最初に疑う。
- `MsgRcvd` / `MsgSent` が時間と比べて極端に偏っているなら片方向 update が偏在している。policy で deny されている可能性がある。

## 異常検出パターン

| 観測 | 疑う状態 | 一次切り分け |
|---|---|---|
| `State=Active` が継続 | TCP SYN が通っていない、source-address 不一致 | `ss -tnp \| grep 179`、ACL、`bgpcfgd` のログ |
| `State=OpenSent` で停滞 | AS 不一致、capability mismatch、MD5 password 不一致 | `vtysh -c "show bgp neighbor X.X.X.X"` の `Last reset reason` |
| `Up/Down` が短い周期 | hold-timer expiry、underlay packet loss、CPU overload | `show bgp neighbor X` の `Hold time` と `Dropped` |
| `PfxRcd=0` だが Up | 対向 advertise なし、自分側 in-policy で deny | route-map、prefix-list、対向 `show bgp adj-out` |
| FRR では RIB にあるが `show ip route` の `>` 印が無い | RIB-to-FIB 移行で失敗 | zebra ログ、fpmsyncd、APPL_DB:[ROUTE_TABLE](../../reference/glossary.md#term-route_table) |
| APPL_DB に route あるが ASIC 未投入 | orchagent SAI error、resource 枯渇 | `/var/log/swss/sairedis.rec`、orchagent log |
| Suppress FIB pending 有効で advertise が出ない | FIB install 未完了の prefix が抑止対象 | `show bgp ipv4 unicast suppress-fib-pending` |

## 典型的な FRR / SWSS ログサンプル

FRR / bgpd の `Last reset reason` 系メッセージは syslog にも出る。

```text
bgpd[28]: %ADJCHANGE: neighbor 10.0.0.1(ARISTA01T2) in vrf default Up
bgpd[28]: %NOTIFICATION: sent to neighbor 10.0.0.1 4/0 (Hold Timer Expired) 0 bytes
bgpd[28]: %ADJCHANGE: neighbor 10.0.0.1(ARISTA01T2) in vrf default Down BGP Notification send
zebra[18]: client 5 disconnected
fpmsyncd[15]: Received route update for prefix 10.1.0.32/32 nexthop 10.0.0.0 (RTM_NEWROUTE)
```

orchagent / syncd 側の典型エラー（route programming 失敗時）:

```text
orchagent: :- create: Failed to create next hop 10.0.0.1 on Ethernet0, rv:-2
orchagent: :- doTask: Failed to remove still referenced next hop 10.0.0.1 on Ethernet0
syncd: :- processQuadEvent: api SAI_API_ROUTE failed in syncd mode: SAI_STATUS_ITEM_ALREADY_EXISTS
```

`SAI_STATUS_INSUFFICIENT_RESOURCES` が出る場合は LPM / NextHop / NHG のいずれかが枯渇している。`crm` を確認する。

## 対応コマンド早見表

| 目的 | コマンド |
|---|---|
| 一覧 summary | `show ip bgp summary` / `show ipv6 bgp summary` |
| neighbor 詳細 | `show ip bgp neighbor <ip>` |
| neighbor の受信 prefix | `show ip bgp neighbor <ip> received-routes` |
| neighbor の送信 prefix | `show ip bgp neighbor <ip> advertised-routes` |
| VRF 指定 | `show ip bgp vrf <vrf> [summary\|neighbor <ip>]` |
| route-map | `show route-map [<name>]` |
| route flush | `vtysh -c "clear ip bgp <ip> [soft]"` |
| FRR 直接 | `vtysh -c "show bgp ipv4 unicast"` |
| FIB | `show ip route`（zebra）、APPL_DB の `ROUTE_TABLE` |
| Suppress FIB | `show bgp ipv4 unicast suppress-fib-pending` |
| BMP 状態 | `vtysh -c "show bmp"` |
| [CRM](../../reference/glossary.md#term-crm) 残量 | `crm show resources all`、`crm show summary` |

## 関連 CONFIG_DB / STATE_DB / counter

- `CONFIG_DB:BGP_NEIGHBOR|<ip>` — `asn`、`local_addr`、`name`、`admin_status`、`holdtime`、`keepalive` 等。
- `CONFIG_DB:BGP_PEER_RANGE|<range>` — dynamic peering の prefix と peer group。
- `APPL_DB:ROUTE_TABLE:<prefix>` — fpmsyncd が書く install 対象 route。`nexthop`、`ifname`、`weight`。
- `APPL_DB:NEXTHOP_GROUP_TABLE:<id>` — [ECMP](../../reference/glossary.md#term-ecmp) nexthop group。member 数と weight。
- `STATE_DB:NEIGH_STATE_TABLE|<ip>` — `bgpmon` が書く CiscoBgp4MIB 用の neighbor state。
- `STATE_DB:BFD_SESSION_TABLE|...` — BGP に紐づく [BFD](../../reference/glossary.md#term-bfd) session 状態。
- `COUNTERS_DB:CRM_*` — LPM、neighbor、nexthop、ACL の使用量。`crm show summary` で参照。
- `BMP_STATE_DB` — BMP collector に出している Adj-RIB-In/Out の snapshot。

## 横断参照

- BGP service が起動しない: [運用入口](../01-overview/operations.md) の feature / [hostcfgd](../../reference/glossary.md#term-hostcfgd) 確認。
- VRF 内 BGP の route 検証: [VRF / ECMP 章 運用](../04-vrf-ecmp/operations.md)。
- [EVPN](../../reference/glossary.md#term-evpn) underlay: [Overlay 章 運用](../03-vxlan-evpn/operations.md) の BGP-EVPN session 観察。
- Dual-ToR 上流 BGP の BFD offload: [Dual-ToR 章 運用](../05-dual-tor/operations.md)。

## 追加の show 出力例

`show ip bgp neighbor 10.0.0.1` の主要部抜粋である。Established 確認時はまず `BGP state` と `Last reset` を見る。

```text
BGP neighbor is 10.0.0.1, remote AS 65200, local AS 65100, external link
  Description: ARISTA01T2
  BGP version 4, remote router ID 10.1.0.1
  BGP state = Established, up for 1d21h11m
  Last read 00:00:01, Last write 00:00:00
  Hold time is 180, keepalive interval is 60 seconds
  Neighbor capabilities:
    4 Byte AS: advertised and received
    Route refresh: advertised and received(old & new)
    Graceful Restart Capability: advertised and received
      Remote Restart timer is 120 seconds
  Graceful restart information:
    End-of-RIB send: IPv4 Unicast
    End-of-RIB received: IPv4 Unicast
  Message statistics:
                         Sent       Rcvd
    Opens:                  1          1
    Notifications:          0          0
    Updates:              641       3204
    Keepalives:          2074       2713
```

`Last reset` 行が無いケースは初回 Established 維持中である。`Dropped` カウンタが増えている場合は session が一度落ちてから再確立されている。

## 典型的な運用シナリオ

1. **新規 peer 追加** — `config bgp ...` または [GCU](../../reference/glossary.md#term-gcu) patch で `BGP_NEIGHBOR` を追加し、`show ip bgp summary` で `Up/Down` が `never` から時刻に切り替わるかを観察する。`Active` のまま停滞するなら ACL / source IP / MD5 を疑う。
2. **メンテナンスモード移行** — `sudo TSA`（Traffic Shift Away）で外部 neighbor 向け route-map を `bgpd/tsa/bgpd.tsa.isolate.conf.j2` テンプレートから生成して `vtysh -f` で適用し、AS-path prepend や community 操作で上流から traffic を引き寄せないようにしてから、debug や upgrade を行う。復旧は `sudo TSB`（unisolate）。スクリプト本体は docker-fpm-frr コンテナの `/usr/bin/TSA`、`/usr/bin/TSB` にある。

<!-- evidence:
source: sonic-net/sonic-buildimage/dockers/docker-fpm-frr/TSA#L1-L40 (sha: 799f47f)
excerpt: |
  source /usr/bin/TS
  ...
  sonic-cfggen ... -t /usr/share/sonic/templates/bgpd/tsa/bgpd.tsa.isolate.conf.j2 > "$TSA_FILE"
  vtysh -f "$TSA_FILE"
  echo "System Mode: Normal -> Maintenance"
reasoning: TSA が community ではなく vtysh + tsa isolate テンプレートで route-map を差し替える形を取っており、本文の「community-based route policy 切り替え + 低 LOCAL_PREF 広告」という表現を「外部 neighbor 向け route-map を tsa テンプレートで差し替え + AS-path prepend / community 操作」に補正。
-->

3. **peer flap の調査** — `show ip bgp neighbor X` の `Dropped` と `Last reset reason` を見て、hold-timer expired か NOTIFICATION 受信か、TCP RST かを切り分ける。`bgpd` syslog の `%ADJCHANGE` の連続を時系列で並べると周期が見える。
4. **policy 変更後の収束確認** — `vtysh -c "clear ip bgp <ip> soft"` で再 advertise を促し、`received-routes` / `advertised-routes` 数の変化を見る。`clear ip bgp *` は全 peer に影響するので避ける。
5. **route leak 疑い** — VRF 内 BGP の `show ip bgp vrf <vrf>` と `show ip route vrf <vrf>` を突き合わせ、想定外の prefix がどの peer / route-map / import から来たかを調べる。`show bgp ipv4 unicast <prefix> bestpath` で attribute も確認する。

## 関連ページ

- [CLI: show bgp](../../reference/cli/show-bgp.md)
- [CLI: show route-map](../../reference/cli/show-route-map.md)
- [BMP](../../routing/bmp-for-monitoring-sonic-bgp-info.md)
- [CiscoBgp4MIB の STATE_DB 経由化](../../routing/ciscobgp4mib-implementation-changes.md)
- [BGP Route Install Error Handling](../../routing/bgp-route-install-error-handling.md)
- [BGP Suppress FIB Pending](../../routing/bgp-suppress-announcements-of-routes-not-installed-in-hw.md)

<!-- glossary-links-injected: 5c9b3765d470 -->
