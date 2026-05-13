---
title: ACL_RULE テーブル
description: "ACL_RULE テーブル — ACL_TABLE 内の個別ルールを定義する。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/aclorch.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/aclorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db:
    - ACL_RULE
    - ACL_TABLE
    - MIRROR_SESSION
  cli:
    - config acl
  yang: []
---

# ACL_RULE テーブル

## 概要

`ACL_TABLE` 内の個別ルールを定義する。優先度、match 条件 (5-tuple、TCP flags、TC、ICMP、tunnel inner、metadata 等)、action (PACKET_ACTION、REDIRECT、MIRROR、COUNTER、[DSCP](../../reference/glossary.md#term-dscp) 上書き、DTel 等) を持つ[^1]。`AclOrch` が `ACL_TABLE` 配下のルールを [SAI](../../reference/glossary.md#term-sai) [ACL](../../reference/glossary.md#term-acl) entry として展開する。

!!! warning "YANG 未定義"
    `ACL_RULE` テーブルは YANG モジュールで未定義。スキーマの正本は `sonic-swss/orchagent/aclorch.{h,cpp}`。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>ACL_RULE")]
  DM["AclOrch"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_ACL_RULE_TABLE")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_acl_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
ACL_RULE|<table_name>|<rule_name>
```

`<table_name>` は `ACL_TABLE.name` を参照（実装上は名前一致のみで leafref はない）。

## 共通フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `PRIORITY` | uint32 | ルール評価順位。値が大きいほど優先 |
| `PACKET_ACTION` | enum `FORWARD`/`DROP`/`DO_NOT_NAT`/etc | 既定アクション |

## match フィールド (代表)

| 名前 | 値 |
|------|----|
| `IN_PORTS` / `OUT_PORT` / `OUT_PORTS` | カンマ区切り PORT 名 |
| `SRC_IP` / `DST_IP` | IPv4 prefix |
| `SRC_IPV6` / `DST_IPV6` | IPv6 prefix |
| `L4_SRC_PORT` / `L4_DST_PORT` | TCP/UDP ポート |
| `L4_SRC_PORT_RANGE` / `L4_DST_PORT_RANGE` | range `<min>..<max>` |
| `ETHER_TYPE` | uint16（hex 可） |
| `IP_PROTOCOL` / `NEXT_HEADER` | uint8 |
| `VLAN_ID` | uint16 |
| `TCP_FLAGS` | `<flags>/<mask>` |
| `IP_TYPE` | enum (`ANY`/`IP`/`NON_IP`/`IPV4ANY`/`IPV6ANY`/...) |
| `DSCP` / `TC` | [DSCP](../../reference/glossary.md#term-dscp) / TC 値 |
| `ICMP_TYPE` / `ICMP_CODE` / `ICMPV6_TYPE` / `ICMPV6_CODE` | ICMP |
| `TUNNEL_VNI` | VNI |
| `INNER_ETHER_TYPE` / `INNER_IP_PROTOCOL` / `INNER_L4_SRC_PORT` / `INNER_L4_DST_PORT` | inner header |
| `INNER_SRC_MAC` / `INNER_DST_MAC` / `INNER_SRC_IP` | inner header |
| `BTH_OPCODE` / `AETH_SYNDROME` | [RoCE](../../reference/glossary.md#term-roce) 用 |
| `TUNNEL_TERM` | bool |
| `META_DATA` | uint32 |

## action フィールド (代表)

| 名前 | 説明 |
|------|------|
| `PACKET_ACTION` | `FORWARD` / `DROP` 等 |
| `REDIRECT_ACTION` | redirect 先（next-hop / mirror セッション 等） |
| `DO_NOT_NAT_ACTION` | [NAT](../../reference/glossary.md#term-nat) バイパス |
| `DISABLE_TRIM_ACTION` | バッファ trim 無効化 |
| `MIRROR_ACTION` / `MIRROR_INGRESS_ACTION` / `MIRROR_EGRESS_ACTION` | mirror セッション参照 |
| `FLOW_OP` / `INT_SESSION` / `DROP_REPORT_ENABLE` / `TAIL_DROP_REPORT_ENABLE` / `FLOW_SAMPLE_PERCENT` / `REPORT_ALL_PACKETS` | DTel (`DTEL_*`) |
| `COUNTER` | カウンタ装着 |
| `META_DATA_ACTION` | metadata 上書き |
| `DSCP_ACTION` | [DSCP](../../reference/glossary.md#term-dscp) 上書き |
| `INNER_SRC_MAC_REWRITE_ACTION` | inner SRC MAC rewrite |

ユーザ定義型 (`ACL_TABLE_TYPE`) を使う場合、ここで使える match / action は `ACL_TABLE_TYPE.MATCHES` / `.ACTIONS` で許可された集合に限られる。

## 購読者

- `orchagent` `AclOrch`: [SAI](../../reference/glossary.md#term-sai) [ACL](../../reference/glossary.md#term-acl) entry を生成
- `mirrororch`: `MIRROR_*_ACTION` 経由で連動
- `copporch`: `CTRLPLANE` 種別の `ACL_TABLE` 配下のルールに連動

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `ACL_TABLE`、`MIRROR_SESSION`、`POLICER`
- 関連 CLI: [`config acl`](../cli/config-acl.md)
- 関連 [YANG](../../reference/glossary.md#term-yang): なし

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| 条件 | 挙動 |
|------|------|
| key の TABLE_ID が空文字 | WARN ログ後 erase、skip |
| 対応する ACL_TABLE が未作成 | 待機 (`it++`)、テーブル作成後に再試行 |
| コントロールプレーンテーブルのルール | INFO ログ後 erase、skip |
| `AclRule::makeShared` が例外 | ERROR ログ後 erase & 関数 return（処理中断） |
| 未知/不正な属性名 | rule INACTIVE、erase |
| `MATCH_TCP_FLAGS` あり・IP_PROTOCOL 未指定 | IP_PROTOCOL=6 (TCP) を自動付与 |
| IPv4 と IPv6 matchfield 混在（L3V4V6 テーブル） | `bAllAttributesOk=false`、rule INACTIVE |
| SAI リソース枯渇 | retry キャッシュに退避、リソース解放後に再試行 |
| IN_PORTS/OUT_PORTS に非物理 IF | `return false`、rule INACTIVE |
| VLAN ID 範囲外 | `return false`、rule INACTIVE |
| Range 形式不正 | `return false`、rule INACTIVE |

<!-- evidence: sonic-net/sonic-swss/orchagent/aclorch.cpp:5520L -->
<!-- /cdb-exceptions -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `PACKET_ACTION` (enum)

| 値 | SAI マッピング | 効果 | evidence |
|---|---|---|---|
| `FORWARD` | `SAI_PACKET_ACTION_FORWARD` | パケットを通過させる | `aclorch.h:83,145` |
| `DROP` | `SAI_PACKET_ACTION_DROP` | パケットをドロップ | `aclorch.h:84,146` |
| `COPY` | `SAI_PACKET_ACTION_COPY` | パケットを CPU コピー後に続行 | `aclorch.h:85,147` |
| `REDIRECT` | `SAI_PACKET_ACTION_REDIRECT` | 指定 next-hop / port へリダイレクト | `aclorch.h:86` |
| `DO_NOT_NAT` | — | NAT 処理をバイパス | `aclorch.h:87` |
| `DISABLE_TRIM` | — | バッファ trim を無効化 | `aclorch.h:88` |

### `IP_TYPE` (match enum)

| 値 | SAI マッピング | 意味 | evidence |
|---|---|---|---|
| `ANY` | `SAI_ACL_IP_TYPE_ANY` | IP/非IP 問わず全パケット | `aclorch.cpp:503` |
| `IP` | `SAI_ACL_IP_TYPE_IP` | IPv4/IPv6 どちらかのパケット | `aclorch.cpp:504` |
| `NON_IP` | `SAI_ACL_IP_TYPE_NON_IP` | 非 IP パケット | `aclorch.cpp:505` |
| `IPV4ANY` | `SAI_ACL_IP_TYPE_IPV4ANY` | IPv4 パケット | `aclorch.cpp:506` |
| `NON_IPV4` | `SAI_ACL_IP_TYPE_NON_IPV4` | 非 IPv4 パケット | `aclorch.cpp:507` |
| `IPV6ANY` | `SAI_ACL_IP_TYPE_IPV6ANY` | IPv6 パケット | `aclorch.cpp:508` |
| `NON_IPV6` | `SAI_ACL_IP_TYPE_NON_IPV6` | 非 IPv6 パケット | `aclorch.cpp:509` |
| `ARP` | — | ARP パケット | `aclorch.h:105` |
| `ARP_REQUEST` | — | ARP Request | `aclorch.h:106` |
| `ARP_REPLY` | — | ARP Reply | `aclorch.h:107` |

### 複合条件

- `MATCH_TCP_FLAGS` あり、かつ `IP_PROTOCOL` 未指定 → `AclOrch` が自動的に `IP_PROTOCOL=6 (TCP)` を付与 (`aclorch.cpp`)
- `IP_TYPE=IPV4ANY` と `SRC_IPV6` を同一ルールに混在させると `bAllAttributesOk=false`、rule が INACTIVE になる
- `stage=INGRESS` テーブルでは `MIRROR_INGRESS_ACTION` が有効、`stage=EGRESS` テーブルでは `MIRROR_EGRESS_ACTION` のみ有効 (`aclorch.cpp:263-291`)
<!-- /value-behavior -->

<!-- ref-triangle:start -->

## 関連リファレンス

- CLI: [`config acl`](../cli/config-acl.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: match / action のキー名は `sonic-swss/orchagent/aclorch.h` の `MATCH_*` / `ACTION_*` マクロ定義から抽出。<https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/aclorch.h>

## 関連ページ
- [HLD: ACL の基本設計](../../acl-qos/acl-support-in-sonic.md)
- [CLI: config acl](../cli/config-acl.md)
- [CLI: show acl](../cli/show-acl.md)
- [CONFIG_DB: ACL_TABLE](acl-table.md)

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: ACL / CoPP / Mirror / Packet Action](../../topics/07-acl-copp-mirror/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `ACL_RULE|<table-name>|<rule-name>`。
- `priority`: 0..65535（大きいほど優先）。9999 等の値を運用で使う。
- `packet_action`: `FORWARD` / `DROP` / `REDIRECT:<nh>`。
- match: `src_ip` / `dst_ip` / `l4_src_port` / `ip_protocol` 等。

### よくある誤設定

- 同じ `priority` を複数 rule で使うと適用順が ASIC 依存で予測不能。
- `SRC_IP` を V6 テーブルに入れると無視され、rule が hit せず原因不明になる。`SRC_IPV6` を使う。
- `packet_action: REDIRECT:` の nexthop 解決が失敗すると rule が install されない（syslog 確認）。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'ACL_RULE|EVERFLOW|*'
aclshow -a -t EVERFLOW
```
<!-- /ops-hint -->

<!-- glossary-links-injected: b4c5898e0257 -->
