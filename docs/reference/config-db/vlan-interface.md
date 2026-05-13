---
title: VLAN_INTERFACE テーブル
description: "VLAN_INTERFACE テーブル — VLAN を L3 IF (SVI) として扱う設定を保持する。VRF / VNET binding、IP アサイン、NAT zone、MPLS、IPv6 link-local、grat ARP / proxy ARP、loopback action、MAC を持つ。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-vlan.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - VLAN_INTERFACE
    - VLAN
    - VRF
  cli:
    - config interface
  yang:
    - sonic-vlan
---

# VLAN_INTERFACE テーブル

## 概要

[VLAN](../../reference/glossary.md#term-vlan) を L3 IF (SVI) として扱う設定を保持する。[VRF](../../reference/glossary.md#term-vrf) / [VNET](../../reference/glossary.md#term-vnet) binding、IP アサイン、[NAT](../../reference/glossary.md#term-nat) zone、[MPLS](../../reference/glossary.md#term-mpls)、IPv6 link-local、grat [ARP](../../reference/glossary.md#term-arp) / proxy [ARP](../../reference/glossary.md#term-arp)、loopback action、MAC を持つ[^1]。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>VLAN_INTERFACE")]
  DM["intfmgrd"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_INTF_TABLE")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_router_intf_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
VLAN_INTERFACE|<name>                       # 属性ロウ
VLAN_INTERFACE|<name>|<ip_prefix>           # IP プレフィクス
```

`<name>` は `VLAN.name` への leafref（例: `Vlan100`）。

## 属性ロウのフィールド一覧

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `name` (key) | leafref `VLAN.name` | ✅ | - | [VLAN](../../reference/glossary.md#term-vlan) 名 |
| `vrf_name` | leafref `VRF.name` | - | - | バインドする [VRF](../../reference/glossary.md#term-vrf) |
| `vnet_name` | leafref `VNET.name` | - | - | バインドする [VNET](../../reference/glossary.md#term-vnet) |
| `nat_zone` | uint8 (0..3) | - | `0` | [NAT](../../reference/glossary.md#term-nat) zone |
| `mpls` | enum `enable`/`disable` | - | - | [MPLS](../../reference/glossary.md#term-mpls) routing |
| `grat_arp` | string `enabled`/`disabled` | - | - | gratuitous [ARP](../../reference/glossary.md#term-arp) |
| `proxy_arp` | string `enabled`/`disabled` | - | - | proxy ARP |
| `ipv6_use_link_local_only` | `mode-status` | - | `disable` | IPv6 link-local のみ |
| `mac_addr` | mac-address | - | - | 管理者指定 MAC |
| `loopback_action` | `loopback_action` | - | - | ingress→same-IF routing 動作 |

## IP プレフィクスロウ

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `name` (key) | leafref `VLAN.name` | ✅ | [VLAN](../../reference/glossary.md#term-vlan) 名（`VLAN_INTERFACE_LIST` に存在することを `must` で要求） |
| `ip-prefix` (key) | union (v4/v6 prefix) | ✅ | IP/プレフィクス |
| `scope` | enum `global`/`local` | - | アドレススコープ |
| `family` | `ip-family` | - | family。`ip-prefix` と整合する `must` |
| `secondary` | boolean | - | secondary subnet フラグ |

## 購読者

- `intfmgrd`: [VRF](../../reference/glossary.md#term-vrf) / MAC / [MPLS](../../reference/glossary.md#term-mpls) / IPv6 LL / proxy_arp / grat_arp を Linux に反映
- `orchagent` `IntfsOrch`: [SAI](../../reference/glossary.md#term-sai) ルータインタフェースを生成
- `arpresponder` 等: proxy ARP / grat ARP を扱う

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `VLAN`、`VLAN_MEMBER`、`VRF`、`VNET`
- 関連 CLI: `config interface ip add/remove Vlan<id>`、`config vlan proxy_arp`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-vlan`

<!-- value-behavior -->
## 値依存挙動マトリクス

| フィールド | 値 | 実挙動 |
|-----------|-----|--------|
| `mpls` | `enable` | `sysctl -w net.mpls.conf.<IF>.input=1` (intfmgr.cpp) |
| `mpls` | `disable` または空 | `sysctl -w net.mpls.conf.<IF>.input=0` |
| `proxy_arp` | `enabled` | `/proc/sys/net/ipv4/conf/<IF>/proxy_arp` / `proxy_arp_pvlan` に `1` |
| `proxy_arp` | `disabled` | 同ファイルに `0` |
| `proxy_arp` | その他 | `SWSS_LOG_ERROR("Proxy ARP state is invalid")` で処理中断 |
| `grat_arp` | `enabled` | `/proc/sys/net/ipv4/conf/<IF>/arp_accept` に `1` |
| `grat_arp` | `disabled` | 同ファイルに `0` |
| `grat_arp` | その他 | `SWSS_LOG_ERROR("GARP state is invalid")` で処理中断 |
| `ipv6_use_link_local_only` | `enable` | IPv6 link-local アドレスのみ付与。グローバル IPv6 アドレス付与不可 |
| `ipv6_use_link_local_only` | `disable` | 通常の IPv6 アドレス割当（デフォルト） |
| `loopback_action` | `drop` | 同一 IF に ingress/egress するパケットをドロップ |
| `loopback_action` | `forward` | 同一 IF に ingress/egress するパケットを転送 |
| `nat_zone` | `0` | [NAT](../../reference/glossary.md#term-nat) zone なし（デフォルト） |
| `nat_zone` | `1`〜`3` | 該当 NAT zone へのバインド |
| `vrf_name` | 変更 (既存 IF) | `isIntfChangeVrf()` で検出しエラー。削除後再 add が必要 |

<!-- /value-behavior -->

## 例外条件・特殊挙動 <!-- cdb-exceptions -->

<!-- evidence: sonic-swss/cfgmgr/intfmgr.cpp; sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang -->

- **VRF 変更禁止**: `intfmgrd` は既存 IF の VRF 変更を `isIntfChangeVrf()` で検出し `SWSS_LOG_ERROR("%s can not change to %s directly, skipping")` を記録してエントリを破棄する[^exc1]。
- **インタフェース未 ready**: `isIntfStateOk()` が false の場合リトライ待ち（"Interface is not ready, skipping"）[^exc1]。
- **VRF 未 ready**: VRF が [STATE_DB](../../reference/glossary.md#term-state_db) に未登録の場合もリトライ待ち[^exc1]。
- **`proxy_arp` / `grat_arp` / `mpls` 不正値**: 不正値の場合 `SWSS_LOG_ERROR("... state is invalid")` を記録して処理を中断[^exc1]。
- **デフォルト補完**: `admin_status` 省略時は `"up"` が補完される[^exc1]。YANG では `nat_zone` のデフォルト `0`、`ipv6_use_link_local_only` のデフォルト `disable`[^exc2]。

[^exc1]: `sonic-swss/cfgmgr/intfmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/intfmgr.cpp>
[^exc2]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang` <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vlan.yang>

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-vlan`](../yang/sonic-vlan.md)
- CLI: [`config interface`](../cli/config-interface.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-vlan.yang` 内 `VLAN_INTERFACE`。<https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-vlan.yang#L71>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: L2 / VLAN / LAG / MC-LAG](../../topics/06-l2-vlan-lag/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `VLAN_INTERFACE|Vlan100` (L3 enable 行) と `VLAN_INTERFACE|Vlan100|10.0.0.1/24` (IP 行) の 2 段。
- `vrf_name`: `Vrfdefault` または `Vrf<name>`。

### よくある誤設定

- L3 enable 行を作らずに IP 行だけ投入すると IntfMgr が IP を作らない。
- `vrf_name` を後から変更しても既存 IP は古い VRF に残る。一旦 del してから再 add。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'VLAN_INTERFACE|*'
show ip interfaces
```
<!-- /ops-hint -->

<!-- glossary-links-injected: b8bde3f9637a -->
