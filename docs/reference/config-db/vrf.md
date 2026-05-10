---
title: VRF テーブル
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-vrf.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - VRF
    - INTERFACE
    - VLAN_INTERFACE
    - PORTCHANNEL_INTERFACE
    - LOOPBACK_INTERFACE
    - BGP_GLOBALS
  cli:
    - config vrf
  yang:
    - sonic-vrf
---

# VRF テーブル

## 概要

L3 トラフィック分離のための Virtual Routing and Forwarding インスタンスを定義する[^1]。`vrfmgrd` がこのテーブルを購読し、Linux VRF (`ip vrf` / `cgroup`) を作成する。各種 `*_INTERFACE` テーブルから `vrf_name` で leafref 参照される。EVPN VXLAN では `vni` を介して L3 VNI と紐付く。

## key 構造

```
VRF|<name>
```

`<name>` は `Vrf` プレフィクス + `[a-zA-Z0-9_-]+` のパターン制約あり（例: `Vrf_blue`）。

## フィールド一覧

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `name` (key) | string `Vrf<...>` | ✅ | - | VRF 名 |
| `fallback` | boolean | - | `false` | 指定 VRF からデフォルト経路へフォールバック |
| `vni` | uint32 (0..16777215) | - | `0` | この VRF にマップする L3 VNI |

## 購読者

- `vrfmgrd`: Linux VRF / cgroup を作成・破棄
- `intfmgrd`: 各 `*_INTERFACE` の `vrf_name` 参照を反映
- `bgpcfgd` / `frr-mgmt-framework`: `BGP_GLOBALS|<vrf>` と組合わせて FRR `vrf <name>` 設定生成
- `orchagent` `VRFOrch`: SAI VR (Virtual Router) を生成

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `INTERFACE`、`VLAN_INTERFACE`、`PORTCHANNEL_INTERFACE`、`LOOPBACK_INTERFACE`、`BGP_GLOBALS`、`MGMT_VRF_CONFIG`
- 関連 CLI: `config vrf add/del`
- 関連 YANG: `sonic-vrf`

## 引用元

[^1]: YANG 定義: `sonic-vrf.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-vrf.yang>

## 関連ページ
- [HLD: VRF サポート](../../routing/sonic-vrf-support-design-spec-draft.md)
- [CLI: config vrf](../cli/config-vrf.md)
- [CLI: config interface](../cli/config-interface.md)
- [YANG: sonic-vrf](../yang/sonic-vrf.md)
