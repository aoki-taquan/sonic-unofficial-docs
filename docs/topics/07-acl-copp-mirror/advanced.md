---
title: 発展トピック
description: 発展トピック — このページは、ACL / CoPP / mirror の基本線から少し外れるが、同じ「分類、保護、観測、rate limit」の考え方で読める機能への案内です。通常運用の入口は前ページまでで足りることが多く、ここでは境界だけを整理します。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/acl-qos/copp-manager-redesign-test-plan.md
- docs/acl-qos/copp-neighbor-miss-trap-and-enhancements.md
- docs/acl-qos/dash-acl-tags.md
- docs/acl-qos/port-access-control-in-sonic.md
- docs/acl-qos/dhcp-dos-mitigation-in-sonic.md
related:
  cli:
  - show acl
  - show nat
  - config nat
  - config bgp
  - show bgp
  - show arp
  - config aaa
  config_db:
  - COPP_TRAP
  - ACL_RULE
  - VLAN
  - NAT
  - AAA
  - FEATURE
  - ACL_TABLE
  yang:
  - sonic-copp
  - sonic-nat
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-global
  - sonic-bgp-bbr
---

# 発展トピック

このページは、[ACL](../../reference/glossary.md#term-acl) / [CoPP](../../reference/glossary.md#term-copp) / mirror の基本線から少し外れるが、同じ「分類、保護、観測、rate limit」の考え方で読める機能への案内です。通常運用の入口は前ページまでで足りることが多く、ここでは境界だけを整理します。

## CoPP Manager Redesign

CoPP Manager 再設計は、`COPP_TRAP` と `FEATURE` の整合性を見直し、feature が disabled または存在しない場合は trap を install しない、ただし `always_enabled=true` の trap は常に install する、というルールに整理します。

これは ACL rule の priority 問題ではなく、CPU bound trap をいつ hostif trap として作るかの問題です。[BGP](../../reference/glossary.md#term-bgp)、[ARP](../../reference/glossary.md#term-arp)、[LACP](../../reference/glossary.md#term-lacp)、UDLD、IP2ME などの trap が feature 状態とどう連動するかを読むときに参照します。

## CoPP Neighbor Miss と Capability

Neighbor miss trap は、ARP / ND 解決前の IP packet が CPU に集中して他の control plane traffic を巻き込む問題を避けるため、`SAI_HOSTIF_TRAP_TYPE_NEIGHBOR_MISS` を個別 policer に分離する拡張です。同時に、[SAI](../../reference/glossary.md#term-sai) enum capability query でサポート trap 一覧を [STATE_DB](../../reference/glossary.md#term-state_db) に公開し、未対応 trap の install 失敗を可視化します。

CoPP のトラブルシュートでは、`show copp configuration` で trap が hardware に入っているかを見る入口になります。

## DASH ACL Tags

[DASH](../../reference/glossary.md#term-dash) ACL tags は、DASH の ACL rule でサービスを IP prefix 群として扱うための仕組みです。通常 ACL の `ACL_TABLE` / `ACL_RULE` ではなく、`DASH_PREFIX_TAG_TABLE` と `DASH_ACL_RULE_TABLE` の拡張として読みます。

通常 ACL との共通点は、match 対象を抽象化し、rule 生成時に展開することです。違いは、DASH pipeline と APP_DB schema が別系統であり、[SONiC](../../reference/glossary.md#term-sonic) の data plane ACL 設定と同じ運用コマンドでは扱わないことです。

## Port Access Control

PAC は 802.1x / MAB / [RADIUS](../../reference/glossary.md#term-radius) によるポート単位の認証です。認証結果に応じて MAC、[VLAN](../../reference/glossary.md#term-vlan)、learning mode、host trap を制御するため、ACL に似た「許可 / 不許可」の話に見えますが、主体は authentication manager、hostapd、mabd、RADIUS です。

ACL 章では、物理ポート単位の access 制御であり、[LAG](../../reference/glossary.md#term-lag) / VLAN への ACL bind とは別の設計として位置付けます。

## DHCP DoS 緩和

DHCP DoS 緩和は、従来 CoPP のシステム全体 DHCP rate limit では単一ポートの flood が他ポートの正規 DHCP を巻き込む問題を、ポート単位の Linux TC rate limit で局所化する設計です。

ただし既存ページでは discrepancy-found とされており、データ層や CLI は取り込まれている一方、[HLD](../../reference/glossary.md#term-hld) が要求する `portmgrd` の TC 投入ロジックや CoPP 側の完全な置き換えは未確認です。設計参考として扱い、実装判断では現行コードと platform 動作を確認します。

## 関連ページ

- [CoPP Manager 再設計テストプラン](../../acl-qos/copp-manager-redesign-test-plan.md)
- [CoPP Neighbor Miss trap と enum capability query](../../acl-qos/copp-neighbor-miss-trap-and-enhancements.md)
- [DASH ACL タグ](../../acl-qos/dash-acl-tags.md)
- [Port Access Control](../../acl-qos/port-access-control-in-sonic.md)
- [DHCP DoS 緩和](../../acl-qos/dhcp-dos-mitigation-in-sonic.md)

## 発展トピック

- **ERSPAN Type-II / Type-III**: 通常 SPAN/Everflow に加え、GRE 経由で remote collector に届ける ERSPAN は SAI mirror session の `SAI_MIRROR_SESSION_ATTR_TYPE` で表現する。Type-III は timestamp と probabilistic sampling をサポートする。
- **ACL counters の telemetry export**: `COUNTERS_DB` から ACL rule 単位のヒット数を [gNMI](../../reference/glossary.md#term-gnmi) / streaming telemetry で出す構成。Top talker / DoS 検出に直結する。
- **[TCAM](../../reference/glossary.md#term-tcam) 共有 (ACL group sharing)**: 同じ ACL を複数 port に bind するとき、[ASIC](../../reference/glossary.md#term-asic) TCAM を group 共有でケチる。SAI side で `SAI_ACL_TABLE_GROUP` の MULTIPLE binding が要件。
- **Egress ACL の counter visibility**: ingress ACL counter は読みやすいが egress ACL counter は ASIC によって粒度が異なる。`show acl rule` で counter が更新されない場合は SAI 側 attribute サポートを確認する。
- **CoPP trap 別 policer の動的調整**: 障害対応中に特定 trap (例えば LACPDU storm) の policer を一時的に上げる運用がある。`COPP_GROUP` / `COPP_TRAP` で per-feature に切り替える。

## 既知の制約と回避方法

- **ACL update 中の transient match miss**: rule replace 時に一瞬 hit しない瞬間がある。`atomic update` を ASIC がサポートするなら priority 違いで shadow rule を先入れし、後で旧 rule を消す。
- **mirror session の TTL / source MAC**: ERSPAN の outer header はデフォルトで encap した装置の MAC / IP を使う。collector 側 [NAT](../../reference/glossary.md#term-nat) / FW が想定外の send 元を弾く例があるので outer header を明示する。
- **CoPP の Linux 側 hostif との二重バケット**: SAI policer と Linux netdev queue の両方が rate limit を持つ。CPU 到達後にも drop されることがあるので、`ethtool -S Ethernet*` で host queue drop を確認する。
- **DASH ACL tag と data plane ACL の混同**: 名前は似るが pipeline が別。DASH pipeline 上で動くため `iptables` や [CONFIG_DB](../../reference/glossary.md#term-config_db) `ACL_RULE` で代用できない。

## 将来計画 / ロードマップ

- [gNOI](../../reference/glossary.md#term-gnoi) `gnoi.system.SetPackage` や `gnoi.os.Activate` と組み合わせた dynamic ACL push 提案がある (集中 controller からの policy 更新)。
- ACL の P4 表現 ([18 P4/PINS](../18-p4-pins/index.md)) は中長期テーマで、SDN controller が P4 table 経由で ACL を流し込む。
- CoPP の [YANG](../../reference/glossary.md#term-yang) モデル整備 (`sonic-copp.yang`) が進めば、設定検証と `gnmi Set` 経由の運用が安定する。

## 関連 RFC / 仕様書

- [RFC 6035](https://datatracker.ietf.org/doc/html/rfc6035) — sFlow と ACL counter の関係参考
- [RFC 7011](https://datatracker.ietf.org/doc/html/rfc7011) — IPFIX (ACL hit を export する将来形)
- [IEEE 802.1X](https://1.ieee802.org/security/802-1x/) — Port Access Control の基準
- [RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749) — OAuth2 (PAC + RADIUS 連携の将来モデル)
- [RFC 2475](https://datatracker.ietf.org/doc/html/rfc2475) — DiffServ (CoPP の [DSCP](../../reference/glossary.md#term-dscp) マッチで参照)

## upstream 開発の最新動向

- `sonic-swss` の `aclorch` / `coppmgr` / `copporch` で trap capability 公開、policer attribute 動的更新、ACL counter race 修正の PR が継続。
- DASH ACL tags は `sonic-dash-api` (proto) の更新で flow rule 表現が拡張されており、controller 側との binding が変化しやすい。
- 802.1X / MAB 関連は hostapd の SONiC docker 統合と RADIUS attribute 拡張の PR が散発的にあり、[AAA](../../reference/glossary.md#term-aaa) 章 ([15](../15-security-aaa/index.md)) と相互に影響する。

## ハンドオフ

- **概念とアーキテクチャ**は本章の [concept](concept.md) / [internals](internals.md) と、area HLD の [acl-qos/](../../acl-qos/index.md) 配下の ACL / CoPP / Mirror 系ページで完結する。aclorch / coppmgrd / coppmgr / mirror orch の責務分担は internals に集約。
- **設定とリファレンス**は [reference/cli](../../reference/cli/index.md) の `config acl` / `show acl` / `config copp` / `show mirror` 系、`ACL_RULE`, `ACL_TABLE`, `COPP_TRAP`, `COPP_GROUP`, `MIRROR_SESSION` の [CONFIG_DB スキーマ](../../reference/config-db/index.md) で網羅される。
- **本ページ** は ACL counter export、CoPP policer の動的調整、ERSPAN/SPAN の境界、DASH ACL tags、P4 表現といった「ACL/CoPP/Mirror を周辺機能と結合する」発展領域だけを扱う。

## トラブルシュート観点

- ACL rule が ASIC に降りないときは、まず `aclshow -a` で counter の有無、`redis-cli -n 1 keys 'ACL_*'` で [APPL_DB](../../reference/glossary.md#term-appl_db) / [ASIC_DB](../../reference/glossary.md#term-asic_db) の rule 数を確認する。TCAM 不足の場合は `swss` の `syncd` ログに `SAI_STATUS_INSUFFICIENT_RESOURCES` が出る。
- CoPP で control plane を drop しているときは、`docker exec swss coppmgr` の状態と `show copp` の rate/burst を確認する。BGP / LACP / ARP のような protocol trap が `MATCH_DROP` に分類されていると、コンソール経由でも疎通しない事象が起きる。
- mirror session が動作しないときは、`show mirror_session` で session の active/inactive、`MIRROR_SESSION` テーブルの GRE/ERSPAN 設定、宛先 next-hop の到達性を点検する。[VXLAN](../../reference/glossary.md#term-vxlan) 経由 mirror は dst [VTEP](../../reference/glossary.md#term-vtep) の MAC 解決失敗で停止しやすい。

## 検証パスとラボ要件

- ACL scale 検証は `sonic-mgmt` の `acl/test_acl.py` を baseline に、4k〜16k rule を投入して TCAM 使用率と [orchagent](../../reference/glossary.md#term-orchagent) レイテンシを計測する。ASIC capability (TCAM 段数、stateful 数) を事前に `saictl query` で取得しておく。
- CoPP 検証は `iperf3` や `hping3` で各 trap rate の限界を計測する。target rate は `COPP_GROUP` の `cir/cbs` 設定通りに収まるべきで、超過時は `policer drop counter` が増えることを確認。
- Mirror session の throughput / drop は `ostinato` / `pktgen` で帯域を上げ、`show mirror_session` の active 状態と GRE encap オーバーヘッドを考慮した宛先側受信量を比較する。

## 関連ページ (追補)

- [ACL in SONiC](../../acl-qos/acl-in-sonic.md)
- [ACL support in SONiC](../../acl-qos/acl-support-in-sonic.md)
- [Everflow test plan](../../acl-qos/everflow-test-plan.md)
- [SONiC port mirroring HLD](../../acl-qos/sonic-port-mirroring-hld.md)
- [CoPP manager redesign test plan](../../acl-qos/copp-manager-redesign-test-plan.md)
- [DASH ACL tags](../../acl-qos/dash-acl-tags.md)
- [02 BGP: CoPP の BGP trap rate チューニング](../02-bgp/index.md)
- [13 DASH / SmartSwitch: DPU 上の ACL flow rule](../13-dash-smartswitch/index.md)
- [15 Security / AAA: 802.1X / MAB / RADIUS の境界](../15-security-aaa/index.md)
- [18 P4 / PINS: P4 表現での ACL](../18-p4-pins/index.md)

<!-- glossary-links-injected: be22a36d6598 -->
