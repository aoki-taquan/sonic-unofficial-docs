---
title: EVPN VXLAN Multihoming 運用（config interface evpn-esi / show vxlan ethernet-segment / 差分）
description: "EVPN VXLAN Multihoming の運用ページ。config interface evpn-esi / config evpn-mh / show vxlan ethernet-segment / show evpn es / show bgp l2vpn evpn es / REST API / FRR debug の使い方と、現行 master との差分・回避策（MC-LAG への退避）をまとめる。"
area: routing
verification: discrepancy-found
monitor: not_implemented
last_verified: 2026-05-11
page_kind: split-child
sources:
  - repo: sonic-net/SONiC
    path: doc/vxlan/EVPN/EVPN_VxLAN_Multihoming.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - EVPN_ETHERNET_SEGMENT
    - EVPN_MH_GLOBAL
    - PORTCHANNEL
  cli:
    - config interface evpn-esi
    - config evpn-mh
    - show vxlan ethernet-segment
    - show evpn es
    - show bgp l2vpn evpn es
  yang:
    - sonic-evpn
---

!!! warning "裏取りステータス: discrepancy-found / 機能未実装"
    **以下の CLI / REST API は HLD 提案ベース**。現行 SONiC master にはコマンド自体が存在しないため、そのまま打っても `Error: No such command "evpn-esi"` 等で失敗する。実機の dual-attach 構成には [MC-LAG enhancements](../switching/mclag-enhancements.md) を使う。差分節は本ページ末尾。

# EVPN VXLAN Multihoming 運用

本ページは [EVPN VXLAN Multihoming（概要ハブ）](evpn-vxlan-multihoming.md) の派生で、[HLD](../reference/glossary.md#term-hld) §3.5 を中心に **CLI / show / REST API / 差分・回避策** を整理する[^1]。概念は [concepts](evpn-vxlan-multihoming-concepts.md)、実装内部は [internals](evpn-vxlan-multihoming-internals.md) を参照。

## 1. 設定 CLI

### 1.1 Ethernet Segment 設定

ESI を [PortChannel](../reference/glossary.md#term-portchannel) に割り当てる。Type-3（system-mac ベース、推奨）の例:

```bash
# system-mac は同一 ES を共有する全 VTEP で一致させる
sudo config interface sys-mac add PortChannel1 00:00:00:0a:00:01

# Type-3: ESI を auto 生成（system-mac + PortChannel 番号 + 0x03）
sudo config interface evpn-esi add PortChannel1 auto-system-mac

# DF 優先度（1..65535、default 32767）
sudo config interface evpn-df-pref add PortChannel1 200
```

Type-0（運用者指定 10 byte ESI）の例:

```bash
sudo config interface sys-mac add PortChannel1 00:00:00:0a:00:01
sudo config interface evpn-esi add PortChannel1 00:00:00:00:00:00:00:0a:00:01
```

削除:

```bash
sudo config interface evpn-esi del PortChannel1
sudo config interface evpn-df-pref del PortChannel1
sudo config interface sys-mac del PortChannel1 00:00:00:0a:00:01
```

`auto-lacp`（[LACP](../reference/glossary.md#term-lacp) system ID から生成）も HLD には記載されているが、[SONiC](../reference/glossary.md#term-sonic) 採用は `auto-system-mac` / 直値が主[^1]。

### 1.2 EVPN-MH global 設定

```bash
# 起動直後の MH ES hold 時間 (0..3600 sec, default 300, 0=disabled)
sudo config evpn-mh startup-delay 180

# Proxy advertisement の MAC 保持時間 (0..86400 sec, default 1080, 0=disabled)
sudo config evpn-mh mac-holdtime 1080

# Proxy advertisement の ARP/ND 保持時間 (0..86400 sec, default 1080)
sudo config evpn-mh neigh-holdtime 1080
```

**[MCLAG](../reference/glossary.md#term-mclag) が設定されていると上記は reject される**（[concepts](evpn-vxlan-multihoming-concepts.md) の MCLAG 相互排他節を参照）。

### 1.3 AD-per-EVI 無効化（FRR vtysh）

scale 試験などで AD-per-EVI を抑制したい場合:

```
sonic(config)# router bgp 65000
sonic(config-router-bgp)# address-family l2vpn evpn
sonic(config-router-bgp-af)# disable-ead-evi-rx
sonic(config-router-bgp-af)# disable-ead-evi-tx
```

## 2. show コマンド（SONiC click）

### 2.1 show vxlan ethernet-segment

ES 単位の DF 状態 / peer [VTEP](../reference/glossary.md#term-vtep) / NHG ID を一覧:

```
admin@sonic$ show vxlan ethernet-segment
+--------------+----------+-----+---------+-----+
| Interface    | VLAN     | DF  | Peers   | NHG |
+==============+==========+=====+=========+=====+
| PortChannel5 | Vlan200  | NDF | 2.2.2.2 | 10  |
|              |          |     | 4.5.6.7 |     |
+--------------+----------+-----+---------+-----+
| PortChannel0 | Vlan300  | DF  | 1.1.1.1 | 20  |
|              |          |     | 3.3.3.3 |     |
+--------------+----------+-----+---------+-----+
```

APP_DB の `EVPN_DF_TABLE` / `EVPN_SPLIT_HORIZON_TABLE` / `EVPN_ES_BACKUP_NHG_TABLE` を joined して表示[^1]。

### 2.2 show vxlan l2-nexthop-group

L2 NHG とメンバの一覧:

```
admin@sonic$ show vxlan l2-nexthop-group
+-------+-----------+----------------+
|   NHG | Tunnels   | LocalMembers   |
+=======+===========+================+
|    10 |           | 20,30,40       |
+-------+-----------+----------------+
|    20 | 2.3.4.5   | PortChannel5   |
+-------+-----------+----------------+
```

NHG 10 が group（child = 20/30/40）、NHG 20/30/40 が single-path の recursive 構造。

### 2.3 show vxlan remotemac

既存コマンドだが、**Tunnel カラムが複数行になる**（複数 VTEP の [ECMP](../reference/glossary.md#term-ecmp) メンバを列挙）:

```
admin@sonic$ show vxlan remotemac
+---------+-------------------+----------------+-------+---------+
| VLAN    | MAC               | RemoteTunnel   |   VNI | Type    |
+=========+===================+================+=======+=========+
| Vlan100 | 00:02:00:00:47:ab | 2.3.4.5        |  1000 | dynamic |
|         |                   | 2.3.4.6        |       |         |
|         |                   | 2.3.4.7        |       |         |
+---------+-------------------+----------------+-------+---------+
```

## 3. show コマンド（FRR vtysh）

### 3.1 show evpn es / es-evi / l2-nh / global

ES の詳細（DF 状態 / preference / NHG / VTEP リスト）:

```
sonic# show evpn es detail
ESI: 03:00:00:00:11:22:33:00:00:01
 Type: Local,Remote
 Interface: PortChannel1
 State: up
 Bridge port: yes
 Ready for BGP: yes
 VNI Count: 2
 MAC Count: 1
 DF status: df
 DF preference: 32767
 Nexthop group: 536870913
 VTEPs:
     4.4.4.4 df_alg: preference df_pref: 32767 nh: 268435458
```

特定 ESI を指定:

```
sonic# show evpn es 03:00:00:00:11:22:33:00:00:02
```

ES と EVI の紐付け:

```
sonic# show evpn es-evi detail
sonic# show evpn es-evi 100
```

[EVPN](../reference/glossary.md#term-evpn) L2 next-hop の一覧:

```
sonic# show evpn l2-nh
VTEP          NH id      #ES
1.1.1.1       268435462  1
2.2.2.2       268435461  1
```

EVPN グローバル状態（MH timer の現在値・start-delay 残時間など）:

```
sonic# show evpn
...
EVPN MH:
  mac-holdtime: 1080s, neigh-holdtime: 1080s
  startup-delay: 180s, start-delay-timer: --:--:--
  uplink-cfg-cnt: 0, uplink-active-cnt: 0
```

### 3.2 show bgp l2vpn evpn es / es-evi / es-vrf / next-hop

[BGP](../reference/glossary.md#term-bgp) テーブル視点での ES（RD / Originator-IP / VTEP 群 / DF preference）:

```
sonic# show bgp l2vpn evpn es detail
ESI: 03:00:00:00:11:22:33:00:00:01
 Type: LR
 RD: 1.1.1.1:3
 Originator-IP: 1.1.1.1
 Local ES DF preference: 32767
 VNI Count: 2
 VTEPs:
  4.4.4.4 flags: EA df_alg: preference df_pref: 32767
```

EVI 単位（`E` = EAD-per-ES、`V` = EAD-per-EVI を flag で表示）:

```
sonic# show bgp l2vpn evpn es-evi vni 100
Flags: L local, R remote, I inconsistent
VTEP-Flags: E EAD-per-ES, V EAD-per-EVI
VNI      ESI                            Flags VTEPs
100      03:00:00:11:22:33:03:00:00:03  LR    2.1.1.1(EV),3.1.1.1(EV),4.1.1.1(EV)
```

ES-[VRF](../reference/glossary.md#term-vrf)（IRB next-hop group の参照確認）:

```
sonic# show bgp l2vpn evpn es-vrf detail
```

L3 EVPN next-hop と RMAC:

```
sonic# show bgp l2vpn evpn next-hops
```

## 4. デバッグコマンド

[FRR](../reference/glossary.md#term-frr) / Zebra 側のデバッグログを有効化:

```
sonic(config)# log syslog debugging
sonic(config)# debug bgp evpn mh
  es     Ethernet Segment debugging
  route  Route debugging
sonic(config)# debug bgp zebra
sonic(config)# debug zebra evpn mh
  es     Ethernet Segment Debugging
  mac    MAC Debugging
  neigh  Neigh Debugging
  nh     Nexthop Debugging
sonic(config)# debug zebra vxlan
sonic(config)# debug zebra kernel
sonic(config)# debug zebra dplane
sonic(config)# debug zebra fpm
```

## 5. REST API（OpenConfig EVPN）

### 5.1 Ethernet-segment 設定

```bash
curl -X PATCH "https://SWITCH_IP:9090/restconf/data/openconfig-network-instance:network-instances/network-instance=default/evpn/ethernet-segments/ethernet-segment=PortChannel17" \
  -H "accept: */*" -H "Content-Type: application/yang-data+json" \
  -d '{
    "openconfig-network-instance:ethernet-segment":[
      {"name":"PortChannel17",
       "config":{"esi-type":"TYPE_0_OPERATOR_CONFIGURED","esi":"0017000000000000000a"},
       "df-election":{"config":{"preference":201}}}
    ]}'
```

### 5.2 EVPN-MH global 設定

```bash
curl -X PATCH "https://SWITCH_IP:9090/restconf/data/openconfig-network-instance:network-instances/network-instance=default/evpn/evpn-mh/config" \
  -H "accept: */*" -H "Content-Type: application/yang-data+json" \
  -d '{"openconfig-network-instance:config":{"startup-delay":150,"mac-holdtime":200,"neigh-holdtime":250}}'
```

## 6. トラブルシューティング

| 症状 | 確認ポイント | 対応 |
|------|------------|------|
| BUM が host に重複到達 | `show evpn es detail` で DF/NDF を確認、`show vxlan ethernet-segment` の DF が両側で `DF` になっていないか | DF election timer (3s) の起動直後を疑う。`startup-delay` で待つ |
| BUM がループする / 別 leaf 経由で戻ってくる | `EVPN_SPLIT_HORIZON_TABLE` の `vteps` が peer を含むか、[ASIC](../reference/glossary.md#term-asic) の isolation group member が正しいか | ShlOrch ログ、[SAI](../reference/glossary.md#term-sai) isolation group dump |
| MH host 向け unicast の load-balance が偏る | Type-1 (per-ES) の受信、L2 NHG member 数、ECMP hash seed | `show evpn l2-nh`、`show bgp l2vpn evpn es-evi` |
| MAC が片側でしか見えない | proxy advertisement / holdtime 不整合 | `mac_holdtime` を peer 全 box で揃える、`debug zebra evpn mh mac` |
| ES link down 後にしばらく drop | backup NHG / protection NHG 未設定 | `EVPN_ES_BACKUP_NHG_TABLE` 存在確認、SAI `PROTECTION_NEXT_HOP_GROUP_ID` |
| `config evpn-mh ...` が reject される | MCLAG ドメインの存在 | `show mclag brief` で確認、MCLAG を撤去してから再投入 |

### 6.1 確認コマンド片

```bash
# APP_DB（HLD どおりなら）
sonic-db-cli APPL_DB keys 'EVPN_DF_TABLE:*'
sonic-db-cli APPL_DB keys 'EVPN_SPLIT_HORIZON_TABLE:*'
sonic-db-cli APPL_DB keys 'L2_NEXTHOP_GROUP_TABLE:*'

# kernel L2 NHG
ip nexthop show | grep fdb
bridge fdb show | grep nhid

# FRR
docker exec bgp vtysh -c 'show evpn es detail'
docker exec bgp vtysh -c 'show evpn es-evi detail'
docker exec bgp vtysh -c 'show bgp l2vpn evpn route type 4'
docker exec bgp vtysh -c 'show bgp l2vpn evpn route type 1'
```

## 7. HLD と実装の差分

<!-- diff-admonition -->
!!! diff "HLD と実装の差分"
    2026-05-10 時点の現行 master を裏取り。**EVPN Multihoming 機能は SONiC メインリポジトリには取り込まれていない**。

    ### 1. `EVPN_ETHERNET_SEGMENT` テーブル / orch が未実装

    - **HLD 記述**: [CONFIG_DB](../reference/glossary.md#term-config_db) に `EVPN_ETHERNET_SEGMENT` / `EVPN_MH_GLOBAL` テーブルを置き、`EvpnMhOrch` / `L2nhgOrch` / `ShlOrch` が SAI へ反映。
    - **実装位置**: `sonic-swss/`、`sonic-buildimage/src/sonic-yang-models/yang-models/`、`sonic-utilities/` のいずれにも `EVPN_ETHERNET_SEGMENT` / `EvpnMhOrch` / `L2nhgOrch` / `ShlOrch` / `ESI` 関連のシンボルは見つからない（grep ヒット 0）。`sonic-evpn-mh.yang` のような派生 module も存在しない。
    - **差分の中身**: テーブル定義 / orch クラス / yang model / CLI のいずれも欠落。HLD は提案段階。
    - **読者への影響**: `config interface evpn-esi add ...` 等のコマンドが click 側に登録されていないため即エラー。CONFIG_DB に直接書いても consumer がいないため何も起こらない。
    - **回避策**:
      - dual-attach 構成が必要なら **MC-LAG**（[../switching/mclag-enhancements.md](../switching/mclag-enhancements.md)）を使う
      - どうしても EVPN MH が必要なら、ベンダー版 SONiC（一部ベンダーが独自実装）または upstream FRR の EVPN-MH（FRR 7.5+）+ 独自 SAI 連携の自前実装が必要

    ### 2. FRR EVPN-MH 側のみ動かしても SONiC 連携が無い

    - **HLD 記述**: FRR の BGP-EVPN MH（Type-1 EAD、Type-4 ES route）が SONiC [orchagent](../reference/glossary.md#term-orchagent) に EAD-per-ES / EAD-per-EVI / ES import-RT を渡し、SAI ESI label / split-horizon を設定。
    - **実装位置**: SONiC 側受け取り経路（`fpmsyncd` の MH 拡張、`EvpnMhOrch` への Type-1/Type-4 ハンドラ、`fdbsyncd` の L2 NHG netlink 対応）は確認できず。
    - **読者への影響**: FRR で `evpn mh es-id ...` を有効化しても SONiC 側で DF election・ESI split-horizon・aliasing が ASIC レベルで効かない。pcap で BGP 4 route は見えても forwarding plane に降りない。
    - **回避策**: 上記のとおり MC-LAG を使うか、独自 patch を入れる。

    ### 3. SAI L2 ECMP bridge port / protection NHG 拡張も未確認

    - **HLD 記述**: SAI 側に `SAI_BRIDGE_PORT_TYPE_BRIDGE_PORT_NEXT_HOP_GROUP` / `SAI_NEXT_HOP_GROUP_TYPE_BRIDGE_PORT` / `SAI_BRIDGE_PORT_ATTR_BRIDGE_PORT_PROTECTION_NEXT_HOP_GROUP_ID` / `SAI_BRIDGE_PORT_ATTR_BRIDGE_PORT_SET_SWITCHOVER` / `SAI_BRIDGE_PORT_ATTR_TUNNEL_TERM_BUM_TX_DROP` の追加を要求。
    - **実装位置**: `sonic-sairedis` の SAI header に上記列挙値・属性は確認できない。SAI コミュニティでも [SAI PR 2084](https://github.com/opencomputeproject/SAI/pull/2084) を含む関連 PR が未 merge の状態。
    - **読者への影響**: たとえ orch を自前実装しても、ベンダー SAI が L2 ECMP bridge port / protection NHG を受け付けない。
    - **回避策**: ASIC ベンダーに ESI / L2 ECMP bridge port サポートの SAI 拡張対応を問い合わせ。現状はコミュニティ master では非対応と認識する。

    ### 結論

    **本機能は現行 master では利用できない**。dual-attached host を扱う実運用構成では MC-LAG を選択する。本 HLD は将来的な機能ロードマップとして参考に留める。

    #### 関連 GitHub Issue / PR

    - [sonic-swss #4262: \[EVPN-MH\] Add EVPN VXLAN Multihoming feature support (open)](https://github.com/sonic-net/sonic-swss/pull/4262) — EVPN MH 機能の本体取り込み大型 PR
    - [sonic-swss #4206: Add support for EVPN MH protocol field (open)](https://github.com/sonic-net/sonic-swss/pull/4206) — MH プロトコルフィールド追加 PR
    - [sonic-swss #4039: Fdbsyncd changes for EVPN MH feature (open)](https://github.com/sonic-net/sonic-swss/pull/4039) — MH 向け [fdbsyncd](../reference/glossary.md#term-fdbsyncd) 改修 PR
    - [SAI PR 2084](https://github.com/opencomputeproject/SAI/pull/2084) — Bridge port protection NHG / SET_SWITCHOVER
    - いずれも 2026-05 時点で open。
<!-- /diff-admonition -->

## 8. 引用元

[^1]: `sonic-net/SONiC` `doc/vxlan/EVPN/EVPN_VxLAN_Multihoming.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- next-action -->
## このページを読んだ後の次アクション

!!! tip "読み手向け"
    - **本機能を実運用で使う場合**: 実装が無いため不可。MC-LAG（[../switching/mclag-enhancements.md](../switching/mclag-enhancements.md)）で代替
    - **upstream 動向を追う場合**: 上記 sonic-swss PR を watch
    - **代替手段（dual-attached host を現行 master で動かす）**:
        1. MC-LAG で代替: `sudo config mclag add 1 10.0.0.1 10.0.0.2` + `sudo config mclag member add 1 PortChannel1`
        2. EVPN VXLAN は single-home で運用: `sudo config vxlan add vtep0 10.1.0.1` + `sudo config vxlan map add vtep0 Vlan100 1000`
        3. upstream 追従: `git -C .cache/sonic-sources/sonic-swss log --oneline --grep="EVPN MH"` で PR #4262 / #4206 / #4039 の取り込みを定期確認
    - **概念・実装の前提**: [concepts](evpn-vxlan-multihoming-concepts.md) / [internals](evpn-vxlan-multihoming-internals.md)
    - **関連 reference**: [CONFIG_DB: PORTCHANNEL](../reference/config-db/portchannel.md) / [CONFIG_DB: VXLAN_TUNNEL](../reference/config-db/vxlan-tunnel.md)

!!! note "本ドキュメントの追跡"
    - monitor: `not_implemented` / last_verified: `2026-05-11`
    - 次回再裏取りトリガ: quarterly + sonic-swss #4262 merge。一覧は [discrepancy-index](../reference/verification/discrepancy-index.md) を参照（運用詳細は repo の `meta/discrepancy-operations.md`）
<!-- /next-action -->

<!-- glossary-links-injected: 771af53c8382 -->
