---
title: VLAN_MEMBER テーブル
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-vlan.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - VLAN
    - VLAN_MEMBER
    - PORT
    - PORTCHANNEL
  cli:
    - config vlan member
  yang:
    - sonic-vlan
---

# VLAN_MEMBER テーブル

## 概要

VLAN とポート (PORT または PORTCHANNEL) のメンバ関係、および各メンバが tagged / untagged のいずれで参加するかを保持する。VLAN_MEMBER のエントリ追加で `vlanmgrd` が Linux bridge にメンバを add し、`orchagent` が SAI VLAN member を生成する[^1]。

## key 構造

```
VLAN_MEMBER|<vlan_name>|<port>
```

`<vlan_name>` は `VLAN` テーブルへの leafref、`<port>` は PORT または PORTCHANNEL への leafref（union）。

## フィールド一覧

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `name` (key) | leafref `VLAN.name` | ✅ | - | 親 VLAN |
| `port` (key) | leafref `PORT.name` \| `PORTCHANNEL.name` | ✅ | - | メンバポート / LAG |
| `tagging_mode` | `vlan_tagging_mode` (`tagged`/`untagged`/`priority_tagged`) | ✅ | - | タグ付与モード |

## 制約 (must)

- メンバ port が他の mirror session の `dst_port` であってはならない
- メンバ port が `PORTCHANNEL_MEMBER` のメンバ port になっていてはならない（同一物理ポートの二重所属防止）
- メンバ port が `INTERFACE` (L3) として登録されていてはならない
- 同一 port を `untagged` で登録できる VLAN は最大 1 つ

## 購読者

- `vlanmgrd`: Linux bridge へのメンバ操作
- `orchagent` の `VlanMgr`: SAI VLAN member を生成

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `VLAN`、`PORT`、`PORTCHANNEL`、`PORTCHANNEL_MEMBER`、`INTERFACE`、`MIRROR_SESSION`
- 関連 CLI: `config vlan member add/del`
- 関連 YANG: `sonic-vlan`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-vlan`](../yang/sonic-vlan.md)
- CLI: [`config vlan member`](../cli/config-vlan.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-vlan.yang` 内 `VLAN_MEMBER` コンテナ。<https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-vlan.yang#L273>

## 関連ページ
- [HLD: Switchport モードと VLAN CLI 拡張](../../switching/switch-port-modes-and-vlan-cli-enhancement.md)
- [CLI: config vlan](../cli/config-vlan.md)
- [CONFIG_DB: VLAN](vlan.md)
- [YANG: sonic-vlan](../yang/sonic-vlan.md)
