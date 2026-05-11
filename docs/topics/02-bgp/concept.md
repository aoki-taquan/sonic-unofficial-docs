---
title: 概要
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 概要

「SONiC で BGP を読む」ときに最初にぶつかる困りごとは、BGP プロトコルそのものではなく、**SONiC と FRR の境界がどこにあるか** が見えづらいことです。BGP のプロトコル処理は FRR（オープンソースのルーティング suite）が行い、SONiC は設定の受付と ASIC への反映を担当しますが、両者の橋渡しに複数の daemon と DB が並んでいるため、どこで何が起きているかを掴むのに時間がかかります。

この章は、その境界線をはっきりさせるための入口です。

## SONiC の BGP は何の問題を解決するか

データセンタースイッチでは、BGP は単に AS 間の経路交換ではなく、**EBGP unnumbered で leaf-spine のあらゆる link 上で動かす ECMP fabric の制御面** として使われます。SONiC はこの利用形態を前提に、以下を引き受けます。

- BGP neighbor / policy / route-map を CONFIG_DB / YANG / CLI で受ける。
- FRR の vty / 設定ファイルへ差分反映する。
- FRR から到達した経路を FPM 経由で受け取り、ASIC の FIB に書き込む。
- BGP 由来のイベント（peer down、route flap）を STATE_DB / telemetry に出す。

つまり SONiC の BGP は「FRR をうまく使うための包み」と考えると、HLD を読むときの迷子が減ります。

## SONiC の中での位置

| 軸 | 担当 |
| --- | --- |
| Management plane | `config bgp`, `vtysh`, sonic-cli, gNMI, CONFIG_DB.BGP_* |
| Control plane | FRR bgpd / zebra / staticd、bgpcfgd / frrcfgd、fpmsyncd |
| Data plane | orchagent (RouteOrch / NhgOrch)、syncd、SAI route / next-hop / next-hop-group |

BGP は **management と control の橋渡し** が大半で、data plane 側はほぼ汎用の RouteOrch を使います。BGP 固有のロジックの多くは「CONFIG_DB → FRR」と「FRR → APPL_DB」の 2 つの方向にあります。

## 最初に押さえる用語

| 用語 | 意味 |
| --- | --- |
| FRR | bgpd / zebra / staticd など複数 daemon からなる routing suite。SONiC は patch-fork した FRR を使う |
| bgpcfgd | CONFIG_DB を読み、Jinja テンプレートで FRR 設定ファイルを生成する daemon |
| frrcfgd | OpenConfig BGP 等、Management Framework 経由の設定を FRR vty コマンドへ翻訳する daemon |
| FPM | FRR Forwarding Plane Manager。zebra が学習経路を外部へ出す TCP プロトコル |
| fpmsyncd | FPM を受け取り `APPL_DB.ROUTE_TABLE` に書き込む SONiC 側 daemon |
| dplane_fpm_sonic | FRR 側の SONiC 専用 FPM plugin（オリジナル FPM のフォーク） |
| RIB / FIB | FRR が持つ Routing Information Base / ASIC に入っている Forwarding Information Base |
| `frr_mgmt_framework_config` | bgpcfgd と frrcfgd のどちらを使うかを切り替えるメタデータ |

## まず責務を分ける

| 層 | 主な責務 | 代表コンポーネント |
| --- | --- | --- |
| 設定入力 | CLI、gNMI/REST、CONFIG_DB の受付 | sonic-utilities、Management Framework |
| FRR 設定反映 | CONFIG_DB 差分を FRR 設定へ変換 | bgpcfgd、frrcfgd |
| BGP 制御 | neighbor、policy、best path、RIB | bgpd |
| 経路配布 | FRR RIB から SONiC への FPM 出力 | zebra、dplane_fpm_sonic |
| SONiC 転送面反映 | APPL_DB から ASIC_DB/SAI へ | fpmsyncd、orchagent、syncd |

従来の中心は `bgpcfgd` で、Jinja template と一部の動的反映により FRR 設定を作ります。OpenConfig BGP を Management Framework から扱う構成では `frrcfgd` が CONFIG_DB の差分から FRR vty コマンドを生成します。両者は同時に動かす前提ではなく、`DEVICE_METADATA.localhost.frr_mgmt_framework_config` で切り替える設計です。詳しくは [FRR-BGP Unified Mgmt Framework](../../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md) を参照してください。

## 典型的な使用シーン

### シーン 1: leaf-spine fabric の EBGP unnumbered

```mermaid
flowchart LR
  S1[Spine 1<br/>AS 65001] ---|EBGP unnumbered| L1[Leaf 1<br/>AS 65101]
  S2[Spine 2<br/>AS 65001] ---|EBGP unnumbered| L1
  S1 ---|EBGP unnumbered| L2[Leaf 2<br/>AS 65102]
  S2 ---|EBGP unnumbered| L2
  L1 --- H1[Host]
  L2 --- H2[Host]
```

Spine と Leaf の各リンクで EBGP を張り、IPv6 link-local + RFC 5549 で IPv4 prefix を運ぶのが典型です。SONiC では `BGP_NEIGHBOR` ではなく `BGP_PEER_RANGE` / unnumbered 用の templates が使われることが多く、router-id の決まり方が hostname / loopback / metadata に依存する点が落とし穴になりがちです。

### シーン 2: BGP-EVPN を被せた VXLAN overlay

VXLAN / EVPN を被せる場合は、同じ BGP セッションの上に `l2vpn evpn` AFI が乗ります。BGP 自体の設定パスは同じですが、経路を受け取る先が `VXLAN_*` / `EVPN_*` テーブルや FRR の EVPN モジュールに広がります。詳細は [03 章 VXLAN / EVPN](../03-vxlan-evpn/concept.md) を併せて読みます。

## router-id はどこで決まるか

BGP router-id は、明示設定がない場合に既存ロジックで決まります。明示したい場合は `DEVICE_METADATA.localhost.bgp_router_id` を使う設計があります。これは FRR 側だけの設定ではなく、SONiC の起動時設定生成に関わるため、どの値が最終的に FRR に入るかを確認する必要があります。詳細は [BGP router-id を明示的に設定する](../../routing/bgp-router-id-explicitly-configured.md) にまとまっています。

## FRR upgrade は何に影響するか

FRR upgrade は単なるパッケージ更新ではありません。SONiC では FRR fork、patch、docker image、起動テンプレート、FPM plugin、Management Framework との接点が絡みます。BGP 機能を読むときは、HLD が前提にする FRR version と現在の SONiC 実装が一致するかを確認してください。upgrade 手順と patch 管理の観点は [SONiC における FRR upgrade](../../routing/detailed-steps-to-upgrade-frr-in-sonic.md) を参照します。

## 似た機能との違い

| 比較対象 | 違い |
| --- | --- |
| Static route | CONFIG_DB.STATIC_ROUTE → FRR staticd 経由で同じく FPM → ASIC へ。BGP のような peer 状態管理がない |
| OSPF (FRR ospfd) | SONiC のサポート範囲が薄い。bgpcfgd / frrcfgd の翻訳テンプレートが BGP 中心 |
| EVPN | BGP の AFI として動く。data plane が VXLAN / VNI 側に伸びる |
| OpenConfig network-instance/protocols/bgp | gNMI から触る経路。frrcfgd 経路を有効にしているときに使う |

## counter / show の入口

| 見たいもの | 主な入口 |
| --- | --- |
| neighbor の up/down | `show bgp summary`, FRR の `vtysh -c "show ip bgp summary"`, STATE_DB.NEIGH_STATE_TABLE |
| 受信 / 送信経路数 | `show ip bgp summary`, `show bgp neighbor <peer>` |
| ASIC FIB に入った経路 | `show ip route`, `redis-cli -n 1 keys 'ROUTE_TABLE:*'`, ASIC_DB |
| FPM 反映の停滞 | fpmsyncd ログ、APPL_DB ROUTE_TABLE pending |

`show ip route` は FRR 側を見ているのか SONiC 側を見ているのかが混ざりやすい点に注意します。確実な切り分けは「FRR の vty」と「Redis の APPL_DB / ASIC_DB」を別個に確認することです。

## この章での読み方

BGP の設定問題は [設定](setup.md) へ進みます。経路が ASIC に入らない、advertise が遅れる問題は [アーキテクチャ](architecture.md) と [運用](operations.md) を先に読みます。大量経路、障害収束、FIB pending、dynamic peer のように実装差分が大きい機能は [内部実装](internals.md) で比較します。

## 読み終わったあとにできるようになること

- 「BGP の問題」を、CONFIG_DB / FRR / FPM / APPL_DB / ASIC_DB のどこで起きているか切り分けられる。
- `bgpcfgd` と `frrcfgd` の使い分けと、それを決める metadata を把握できる。
- 同じ `show ip route` でも、FRR と SONiC のどちらを見るべきかが選べる。
- HLD を読むとき、その記述が FRR version 依存か SONiC patch 依存かに当たりを付けられる。

## 関連ページ

- [BGP router-id を明示的に設定する](../../routing/bgp-router-id-explicitly-configured.md)
- [FRR-BGP Unified Mgmt Framework](../../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md)
- [SONiC における FRR upgrade](../../routing/detailed-steps-to-upgrade-frr-in-sonic.md)
