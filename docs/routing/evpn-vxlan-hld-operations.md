---
title: EVPN VXLAN 設定・運用（vtysh / show evpn / show bgp l2vpn）
description: EVPN VXLAN の CLI 設定例とトラブルシュート。config vxlan / config vrf / FRR vtysh の address-family l2vpn evpn 設定、show vxlan / show evpn / show bgp l2vpn evpn の読み方と典型的な障害切り分け手順。
area: routing
verification: code-verified
last_verified: 2026-05-26
page_kind: split-child
sources:
  - repo: sonic-net/SONiC
    path: doc/vxlan/EVPN/EVPN_VXLAN_HLD.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - VXLAN_TUNNEL
    - VXLAN_TUNNEL_MAP
    - VXLAN_EVPN_NVO
    - VRF
    - VLAN
  cli:
    - config vxlan
    - config vrf
    - config neigh-suppress
    - show vxlan
    - show evpn
    - show bgp l2vpn evpn
  yang:
    - sonic-vxlan
---

# EVPN VXLAN 設定・運用（vtysh / show evpn / show bgp l2vpn）

このページは [EVPN VXLAN HLD（概要ハブ）](evpn-vxlan-hld.md) の派生ページで、**設定 CLI と運用・トラブルシュート手順** に絞って整理する。概念は [evpn-vxlan-hld-concepts.md](evpn-vxlan-hld-concepts.md)、内部実装は [evpn-vxlan-hld-internals.md](evpn-vxlan-hld-internals.md) を参照。

## 1. 設定の全体像

EVPN VXLAN を最小構成で動かすには **SONiC CLI 側と FRR vtysh 側の両方** に設定を入れる必要がある[^1]。

| 設定対象 | 入れる場所 |
|---------|------------|
| VXLAN tunnel (VTEP loopback) | SONiC CLI (`config vxlan ...`) |
| EVPN NVO instance | SONiC CLI |
| VLAN ↔ L2VNI mapping | SONiC CLI |
| VRF ↔ L3VNI mapping | SONiC CLI + FRR vtysh |
| BGP-EVPN session + `address-family l2vpn evpn` | FRR vtysh (or `frr.conf` template) |
| ARP/ND suppression (per VLAN) | SONiC CLI |

## 2. SONiC CLI 設定例

### 2.1 VTEP loopback とトンネル

```bash
# Loopback に VTEP source IP を持たせる
config interface ip add Loopback0 1.1.1.1/32

# VXLAN tunnel object（SIP only）
config vxlan add vtep1 1.1.1.1

# EVPN NVO instance を紐づけ
config vxlan evpn_nvo add nvo1 vtep1
```

CONFIG_DB 上は以下のようになる[^1]:

```json
"VXLAN_TUNNEL": { "vtep1": { "src_ip": "1.1.1.1" } }
"VXLAN_EVPN_NVO": { "nvo1": { "source_vtep": "vtep1" } }
```

!!! warning "HLD 表記との差"
    HLD では `EVPN_NVO` テーブルと記載されるが、実装・yang 上は `VXLAN_EVPN_NVO` が正。詳細は [概要ハブの「実装との乖離」セクション](evpn-vxlan-hld.md) を参照。

### 2.2 L2 VXLAN (VLAN ↔ L2VNI)

```bash
# VLAN を作成
config vlan add 100
config vlan member add 100 Ethernet0

# VLAN 100 を L2VNI 10100 にマップ
config vxlan map add vtep1 100 10100

# 範囲指定（複数 VLAN を連番 VNI にマップ）
config vxlan map_range add vtep1 200 209 10200
```

### 2.3 L3 VXLAN (VRF ↔ L3VNI) + Symmetric IRB

```bash
# VRF とそれに bind する L3VNI
config vrf add Vrf-Red
config vrf add_vrf_vni_map Vrf-Red 5000

# VLAN interface を VRF に attach（anycast gateway IP は別途）
config vlan add 1000
config interface vrf bind Vlan1000 Vrf-Red
config interface ip add Vlan1000 10.1.0.1/24

# L3VNI を VTEP に map（L3VNI と紐づく中継 VLAN を別途作る運用が一般的）
config vxlan map add vtep1 1000 5000
```

### 2.4 ARP / ND suppression

```bash
# VLAN 100 で ARP / ND の VXLAN flood を抑制
config neigh-suppress vlan 100 on
```

!!! warning "ARP/ND suppression は実装未完"
    HLD 記載の機能だが、現行 master では [sonic-swss #2181](https://github.com/sonic-net/sonic-swss/issues/2181) が long-open。設定 CLI は受け付けるが期待通り動かないケースがある。

## 3. FRR vtysh 設定例（BGP-EVPN）

SONiC CLI だけでは BGP-EVPN session は張れない。`bgp` container 内の `vtysh` で `address-family l2vpn evpn` を有効化する必要がある[^1]。

```bash
docker exec -it bgp vtysh

configure terminal
router bgp 65001
 bgp router-id 1.1.1.1
 neighbor 192.0.2.2 remote-as 65000
 neighbor 192.0.2.2 ebgp-multihop 3
 !
 address-family ipv4 unicast
  network 1.1.1.1/32
 exit-address-family
 !
 address-family l2vpn evpn
  neighbor 192.0.2.2 activate
  advertise-all-vni
  advertise ipv4 unicast
 exit-address-family
!
! VRF と L3VNI の bind（Symmetric IRB の中継）
router bgp 65001 vrf Vrf-Red
 address-family ipv4 unicast
  redistribute connected
 exit-address-family
 address-family l2vpn evpn
  advertise ipv4 unicast
 exit-address-family
!
vrf Vrf-Red
 vni 5000
exit-vrf
end
write memory
```

恒久化は `bgp` container の `frr.conf` テンプレート (`sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/bgpd.main.conf.j2`) を編集する。

## 4. 状態確認コマンド

### 4.1 SONiC 側

```bash
# VXLAN tunnel / VTEP の状態
show vxlan tunnel
show vxlan interface
show vxlan remotevtep        # 動的に discover された remote VTEP

# VLAN ↔ VNI mapping
show vxlan vlanvnimap
show vxlan vrfvnimap

# Type-2 で学習した remote MAC
show vxlan remote_mac all
show vxlan remote_vni all

# tunnel counters
show vxlan counters
```

### 4.2 FRR vtysh 側

```bash
docker exec bgp vtysh -c 'show bgp l2vpn evpn summary'
docker exec bgp vtysh -c 'show bgp l2vpn evpn'
docker exec bgp vtysh -c 'show bgp l2vpn evpn route type macip'    # Type-2 のみ
docker exec bgp vtysh -c 'show bgp l2vpn evpn route type prefix'   # Type-5 のみ
docker exec bgp vtysh -c 'show bgp l2vpn evpn route type multicast' # Type-3 (IMET)

docker exec bgp vtysh -c 'show evpn vni'
docker exec bgp vtysh -c 'show evpn vni detail'
docker exec bgp vtysh -c 'show evpn mac vni all'
docker exec bgp vtysh -c 'show evpn arp-cache vni all'
```

### 4.3 DB 直読み（深掘り）

```bash
# CONFIG_DB
sonic-db-cli CONFIG_DB KEYS 'VXLAN_TUNNEL*'
sonic-db-cli CONFIG_DB KEYS 'VXLAN_EVPN_NVO*'    # ※ HLD の "EVPN_NVO*" ではない

# APPL_DB
sonic-db-cli APPL_DB KEYS 'VXLAN_FDB_TABLE:*'
sonic-db-cli APPL_DB KEYS 'VXLAN_REMOTE_VNI_TABLE:*'
sonic-db-cli APPL_DB KEYS 'ROUTE_TABLE:*' | head

# STATE_DB
sonic-db-cli STATE_DB KEYS 'STATE_VXLAN_TUNNEL_TABLE|*'

# ASIC_DB
sonic-db-cli ASIC_DB KEYS 'ASIC_STATE:SAI_OBJECT_TYPE_TUNNEL*'
sonic-db-cli ASIC_DB KEYS 'ASIC_STATE:SAI_OBJECT_TYPE_TUNNEL_MAP*'
```

## 5. トラブルシュート

### 5.1 対向 VTEP に届かない

1. **underlay reachability** を確認: `ping -I Loopback0 <remote-vtep-loopback>`
2. **tunnel object** が SAI に作られているか: `show vxlan tunnel` の operstatus、ASIC_DB の `SAI_OBJECT_TYPE_TUNNEL` 件数
3. **MTU**: VXLAN ヘッダ 50 byte 増。fragmention 不可なら underlay の MTU を 50+ 上乗せ

### 5.2 MAC が学習されない (Type-2 受信問題)

1. **BGP-EVPN session の状態**: `show bgp l2vpn evpn summary` で peer が `Established` か
2. **対向の `advertise-all-vni` 設定**: 入っていないと Type-2 を送らない
3. **fdbsyncd 動作**: `show vxlan remote_mac all` に何も出ない場合は `docker logs swss | grep -i fdbsync`
4. **VXLAN_FDB_TABLE が空**: `sonic-db-cli APPL_DB KEYS 'VXLAN_FDB_TABLE:*'` で確認

### 5.3 Type-5 ルートが入らない

1. **L3VNI ↔ VRF mapping**: `show vxlan vrfvnimap` と FRR 側 `show evpn vni detail` で L3VNI が同じ値か
2. **VRF が SAI に作られているか**: `sonic-db-cli ASIC_DB KEYS 'ASIC_STATE:SAI_OBJECT_TYPE_VIRTUAL_ROUTER*'`
3. **APPL_DB の VRF_ROUTE_TABLE**: `vni_label` / `router_mac` フィールドが入っているか
4. 既知 issue: [sonic-swss #3384 NEIGH_TABLE not populated with VXLAN routes](https://github.com/sonic-net/sonic-swss/issues/3384)

### 5.4 IMET (Type-3) が交換されない

- `show bgp l2vpn evpn route type multicast` で双方の IMET が見えるか
- VLAN-VNI map が設定された **後** に vni netdev が kernel に作られ、それを trigger に IMET が origin される[^1]。順序が逆だと出ない

## 6. 制限事項（運用視点）

- **下位 ASIC 依存**: VXLAN encap/decap、tunnel termination の SAI 実装が必須
- **MTU**: VXLAN ヘッダ 50 byte 分の余裕を underlay に持たせる。不足は黙ってドロップしがち
- **multihoming**: 別 HLD ([evpn-vxlan-multihoming.md](evpn-vxlan-multihoming.md))
- **BUM**: ingress replication のみ。multicast underlay は範囲外
- **ARP/ND suppression**: 実装未完（[#2181](https://github.com/sonic-net/sonic-swss/issues/2181)）

## 7. 次に読む

- 概念 / Route Type / IRB: [evpn-vxlan-hld-concepts.md](evpn-vxlan-hld-concepts.md)
- 内部実装 / Orch クラス / DB フロー: [evpn-vxlan-hld-internals.md](evpn-vxlan-hld-internals.md)
- multihoming: [evpn-vxlan-multihoming.md](evpn-vxlan-multihoming.md)
- 参照: [CONFIG_DB VXLAN_TUNNEL](../reference/config-db/vxlan-tunnel.md), [VXLAN_TUNNEL_MAP](../reference/config-db/vxlan-tunnel-map.md), [VRF](../reference/config-db/vrf.md)

## 引用元

[^1]: `sonic-net/SONiC` `doc/vxlan/EVPN/EVPN_VXLAN_HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: VXLAN / EVPN / VNET オーバーレイ — 運用](../topics/03-vxlan-evpn/operations.md)
- [Topics: VXLAN / EVPN / VNET オーバーレイ — 構築](../topics/03-vxlan-evpn/setup.md)

<!-- /topics-back-ref -->
