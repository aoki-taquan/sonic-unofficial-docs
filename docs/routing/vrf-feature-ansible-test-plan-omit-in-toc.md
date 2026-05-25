---
title: VRF Ansible テストプラン（T0 上で BGP/ACL/loopback/warm-reboot 含む E2E 検証）
description: "VRF Ansible テストプラン（T0 上で BGP/ACL/loopback/warm-reboot 含む E2E 検証） — vrf-vs-test-plan が SwSS 内部の DB 反映を見るのに対し、本プランは 実 SONiC スイッチ上で VRF 機能を E2E 検証 する。"
area: routing
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/SONiC
    path: doc/vrf/vrf-ansible-test-plan.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - VRF
    - PORTCHANNEL_INTERFACE
    - VLAN_INTERFACE
    - LOOPBACK_INTERFACE
    - BGP_NEIGHBOR
    - ACL_TABLE
    - ACL_RULE
  cli:
    - config vrf
  yang:
    - sonic-vrf
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含みます。機能の概念・設定・運用を読み物として読みたい場合は [Topics 04 章: VRF / ECMP / 経路選択](../topics/04-vrf-ecmp/index.md) を参照。
<!-- /topics-tip -->

!!! success "裏取りステータス: code-verified"
    本テストプランは sonic-mgmt 上の `test_vrf.py` 設計記述。`config vrf` / `config interface vrf bind` CLI、`frr.conf.j2` の VRF テンプレート、`acl-loader` の `redirect:<ip>@<intf>` action、1000 VRF スケールテストの現行挙動は未裏取り。

# VRF Ansible テストプラン（T0 上で BGP/ACL/loopback/warm-reboot 含む E2E 検証）

## 概要

`vrf-vs-test-plan` が SwSS 内部の DB 反映を見るのに対し、本プランは **実 [SONiC](../reference/glossary.md#term-sonic) スイッチ上で [VRF](../reference/glossary.md#term-vrf) 機能を E2E 検証** する。`t0` トポロジ前提で、[PortChannel](../reference/glossary.md#term-portchannel) / [VLAN](../reference/glossary.md#term-vlan) を 2 つの VRF (`Vrf1` / `Vrf2`) に分け、neighbor / route 学習、[ACL](../reference/glossary.md#term-acl) redirect、loopback、warm-reboot を網羅する[^1]。

## 動作仕様

### Topology / VRF 配置例[^1]

| VRF | bind 対象 |
|-----|-----------|
| `Vrf1` | `PortChannel0001` / `PortChannel0002` / `Vlan1000` |
| `Vrf2` | `PortChannel0003` / `PortChannel0004` / `Vlan2000` |

`PORTCHANNEL_INTERFACE` の `<pc>\|<addr/prefix>` で v4 / v6 アドレス、`<pc>` キーの `vrf_name` で VRF bind[^1]。

### BGP（FRR）VRF 設定の生成

`/usr/share/sonic/templates/frr.conf.j2` を VRF 対応に拡張。各 VRF に独立した `router bgp 65100 vrf VrfX` ブロックを生成し、IPv4/IPv6 unicast、neighbor、route-map (`set-next-hop-global-v6`、`RM_SET_SRC[6]` 等) を VRF 毎に持つ[^1]:

```text
router bgp 65100 vrf Vrf2
  bgp router-id 10.1.0.32
  neighbor 10.0.0.61 remote-as 64600
  bgp listen range 10.255.0.0/25 peer-group BGPSLBPassive
  ...
```

`BGP_PEER_RANGE` / `BGP_NEIGHBOR` の各 entry にも `vrf_name` または `Vrf<N>|<addr>` キーで VRF を伝える[^1]。

### ACL redirect（VRF 別 nexthop）

VRF 跨ぎリダイレクトでは **outgoing interface も明示** が必要[^1]:

```text
"VRF_ACL_REDIRECT_V4|rule1": {
  "priority": "55",
  "SRC_IP": "10.0.0.1",
  "packet_action": "redirect:<ip1>@<intf1>,<ip2>@<intf2>"
}
```

`<ip>@<intf>` 形式で nexthop の interface を VRF とともに固定する。

### テストケース 10 項目[^1]

| # | 観点 | 主な手順 |
|---|------|---------|
| 1 | VRF 作成 / bind | `config load vrf` → kernel + APP_DB 確認 |
| 2 | neighbor 学習 | DUT から VM へ ping、トラフィックで neighbor 検証 |
| 3 | route 学習 | bgp で各 VM が 6.4K v4 + 6.4K v6 route を広報、トラフィック検証 |
| 4 | VRF 隔離 | 異 VRF で同一 prefix を広報し、neighbor / route が混ざらないこと |
| 5 | ACL redirect | `<ip>@<intf>` リダイレクト先で受信、複数 nexthop の load balance |
| 6 | loopback IF | 異 VRF の loopback、loopback を bgp `update-source` に使い session Established |
| 7 | warm-reboot | system warm + swss warm 中の連続トラフィック無断絶 |
| 8 | 1000 VRF | 1000 VLAN + 1000 VRF を CLI 生成、エラー無し + ping 通る |
| 9 | unbind | VRF unbind 時の neighbor/route 削除と他 IF への波及無し |
| 10 | VRF 削除 | bind 中 IF ごと VRF 削除、IP/neighbor/route が連動削除、他 VRF 不変 |

### PTF traffic 判定

`src_mac` オプションテストでは PTF が L3 forward 後の dst_mac を見て、設定済 VRF `src_mac` と一致した場合のみ forward 判定する[^1]。

## 制限事項

- `t0` トポロジ前提
- TODO（[HLD](../reference/glossary.md#term-hld) 末尾）: `fallback_lookup` 属性、VRF 間 route leak、everflow VRF 対応、ssh 等 application の VRF 対応 は **本プラン範囲外**[^1]
- 1000 VRF テストは生成時間 / メモリの観点で実機制約を受ける可能性あり

## 干渉する機能

- **[FRR](../reference/glossary.md#term-frr) ([zebra](../reference/glossary.md#term-zebra)/bgpd)**: VRF 別ルーティングテーブルの中核
- **ACL redirect**: `redirect:<ip>@<intf>` action の VRF 跨ぎ振る舞い
- **warm-reboot**: system + swss warm の双方で連続トラフィックを保証

## 引用元

[^1]: [sonic-net/SONiC doc/vrf/vrf-ansible-test-plan.md @ 49bab5b](https://github.com/sonic-net/SONiC/blob/49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06/doc/vrf/vrf-ansible-test-plan.md)

## 裏取りメモ (batch 30, 2026-05-11)

本ページは [sonic-mgmt](../reference/glossary.md#term-sonic-mgmt) 配下の Ansible テストプラン記述で、対象実装側 (SONiC NOS) の確認ポイント:

- `sonic-swss/cfgmgr/vrfmgr.cpp:12-26` で `VRF_TABLE_START 1001` / `VRF_TABLE_END 5097` / `MGMT_VRF_TABLE_ID 6000` を持ち、`m_appVrfTableProducer(appDb, APP_VRF_TABLE_NAME)` / `m_appVxlanVrfTableProducer(appDb, APP_VXLAN_VRF_TABLE_NAME)` / `m_stateVrfTable(stateDb, STATE_VRF_TABLE_NAME)` / `m_stateVrfObjectTable(stateDb, STATE_VRF_OBJECT_TABLE_NAME)` を open。テストプランが要求する `config vrf` → [CONFIG_DB](../reference/glossary.md#term-config_db) → [vrfmgrd](../reference/glossary.md#term-vrfmgrd) → [APPL_DB](../reference/glossary.md#term-appl_db) / Linux kernel の流路は cfgmgr に実装済み。
- 4096 VRF（VRF_TABLE_START=1001, END=5097）のレンジが定義されており、HLD/プランの「1000 VRF スケール」記述と整合。

テストプラン自体は記述で、現行 master の vrfmgrd 実装と整合。`code-verified` に昇格。

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Lab / Virtual SONiC / Developer Entry](../topics/21-lab-vs-developer/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 8ba32e5aa69d -->
