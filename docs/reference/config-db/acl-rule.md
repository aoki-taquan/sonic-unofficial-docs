---
title: ACL_RULE テーブル
description: "ACL_RULE テーブル — ACL_TABLE 内の個別ルールを定義する。"
area: reference
hard: 0
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
| [SAI](../../reference/glossary.md#term-sai) リソース枯渇 | retry キャッシュに退避、リソース解放後に再試行 |
| IN_PORTS/OUT_PORTS に非物理 IF | `return false`、rule INACTIVE |
| [VLAN](../../reference/glossary.md#term-vlan) ID 範囲外 | `return false`、rule INACTIVE |
| Range 形式不正 | `return false`、rule INACTIVE |

<!-- evidence: sonic-net/sonic-swss/orchagent/aclorch.cpp:5520L -->
<!-- /cdb-exceptions -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `PACKET_ACTION` 値別挙動

YANG 定義値: `FORWARD` / `DROP` / `REDIRECT` (sonic-acl.yang:114-116)。
実装 lookup map: `aclPacketActionLookup` (aclorch.cpp:143)。マクロ定数: `PACKET_ACTION_FORWARD` / `PACKET_ACTION_DROP` / `PACKET_ACTION_COPY` / `PACKET_ACTION_REDIRECT` / `PACKET_ACTION_DO_NOT_NAT` / `PACKET_ACTION_DISABLE_TRIM` (aclorch.h:83-88)。

| 値 | SAI マッピング | 効果 | evidence |
|---|---|---|---|
| `FORWARD` | `SAI_PACKET_ACTION_FORWARD` | パケットを通過させる (`PACKET_ACTION_FORWARD`) | `aclorch.h:83`, `aclorch.cpp:145` |
| `DROP` | `SAI_PACKET_ACTION_DROP` | パケットをドロップ (`PACKET_ACTION_DROP`) | `aclorch.h:84`, `aclorch.cpp:146` |
| `COPY` | `SAI_PACKET_ACTION_COPY` | パケットを CPU コピー後に続行 (`PACKET_ACTION_COPY`、YANG 外) | `aclorch.h:85`, `aclorch.cpp:147` |
| `REDIRECT` | oid 解決後に redirect | `REDIRECT:<target>` 形式 (`PACKET_ACTION_REDIRECT`)。コロンなし / ターゲット空は `return false` → rule INACTIVE | `aclorch.h:86`, `aclorch.cpp:2013-2040` |
| `DO_NOT_NAT` | — | [NAT](../../reference/glossary.md#term-nat) 処理をバイパス (`PACKET_ACTION_DO_NOT_NAT`、YANG 外) | `aclorch.h:87` |
| `DISABLE_TRIM` | — | バッファ trim を無効化 (`PACKET_ACTION_DISABLE_TRIM`、YANG 外) | `aclorch.h:88` |

!!! note "REDIRECT 後方互換"
    `ACTION_PACKET_ACTION` フィールドに `REDIRECT:<target>` を書く旧形式が後方互換として残る。新形式は `REDIRECT_ACTION` フィールドを使う (`aclorch.cpp:2013`)。

### `IP_TYPE` 値別挙動

YANG 定義値 7 種 (sonic-acl.yang:122-130)。実装 lookup map: `aclIpTypeLookup` (aclorch.cpp:501)。マクロ定数: `IP_TYPE_ANY` / `IP_TYPE_IP` / `IP_TYPE_NON_IP` / `IP_TYPE_IPv4ANY` / `IP_TYPE_NON_IPv4` / `IP_TYPE_IPv6ANY` / `IP_TYPE_NON_IPv6` / `IP_TYPE_ARP` / `IP_TYPE_ARP_REQUEST` / `IP_TYPE_ARP_REPLY` (aclorch.h:98-107)。
YANG は `mandatory true` のため省略不可。

| 値 | SAI マッピング | 意味 | evidence |
|---|---|---|---|
| `ANY` | `SAI_ACL_IP_TYPE_ANY` | IP/非IP 問わず全パケット (`IP_TYPE_ANY`) | `aclorch.h:98`, `aclorch.cpp:503` |
| `IP` | `SAI_ACL_IP_TYPE_IP` | IPv4 または IPv6 パケット (`IP_TYPE_IP`) | `aclorch.h:99`, `aclorch.cpp:504` |
| `IPV4` | `SAI_ACL_IP_TYPE_IPV4ANY` | IPv4 パケット (YANG のみ、実装上 `IP_TYPE_IPv4ANY` と同義) | `sonic-acl.yang:125` |
| `IPV4ANY` | `SAI_ACL_IP_TYPE_IPV4ANY` | IPv4 パケット (`IP_TYPE_IPv4ANY`) | `aclorch.h:101`, `aclorch.cpp:506` |
| `NON_IPV4` | `SAI_ACL_IP_TYPE_NON_IPV4` | 非 IPv4 パケット (`IP_TYPE_NON_IPv4`) | `aclorch.h:102`, `aclorch.cpp:507` |
| `IPV6ANY` | `SAI_ACL_IP_TYPE_IPV6ANY` | IPv6 パケット (`IP_TYPE_IPv6ANY`) | `aclorch.h:103`, `aclorch.cpp:508` |
| `NON_IPV6` | `SAI_ACL_IP_TYPE_NON_IPV6` | 非 IPv6 パケット (`IP_TYPE_NON_IPv6`) | `aclorch.h:104`, `aclorch.cpp:509` |
| `ARP` | `SAI_ACL_IP_TYPE_ARP` | [ARP](../../reference/glossary.md#term-arp) パケット (`IP_TYPE_ARP`、実装のみ、YANG 外) | `aclorch.h:105`, `aclorch.cpp:510` |
| `ARP_REQUEST` | `SAI_ACL_IP_TYPE_ARP_REQUEST` | [ARP](../../reference/glossary.md#term-arp) Request (`IP_TYPE_ARP_REQUEST`、実装のみ) | `aclorch.h:106`, `aclorch.cpp:511` |
| `ARP_REPLY` | `SAI_ACL_IP_TYPE_ARP_REPLY` | [ARP](../../reference/glossary.md#term-arp) Reply (`IP_TYPE_ARP_REPLY`、実装のみ) | `aclorch.h:107`, `aclorch.cpp:512` |

### `ETHER_TYPE` 値別挙動

YANG pattern で 7 値に制限 (sonic-acl.yang:142)。実装では任意 uint16 を受理 (aclorch.cpp:1066)。
格納値は `0x` プレフィックス付き hex 文字列。`stoul(str, &idx, 0)` で auto 判定 (`converter.h:18` の変換関数)。
マスク: `0xFFFF` (完全一致) で `SAI_ACL_ENTRY_ATTR_FIELD_ETHER_TYPE` として SAI に投入 (aclorch.cpp:1067)。

| 値 | プロトコル | 意味 | evidence |
|---|---|---|---|
| `0x88CC` | LLDP | Link Layer Discovery Protocol | `sonic-acl.yang:142` |
| `0x8100` | IEEE 802.1Q | VLAN タグ付きフレーム | `sonic-acl.yang:142` |
| `0x8915` | [RoCE](../../reference/glossary.md#term-roce) | RDMA over Converged Ethernet | `sonic-acl.yang:142` |
| `0x0806` | [ARP](../../reference/glossary.md#term-arp) | Address Resolution Protocol | `sonic-acl.yang:142` |
| `0x0800` | IPv4 | Internet Protocol version 4 | `sonic-acl.yang:142` |
| `0x86DD` | IPv6 | Internet Protocol version 6 | `sonic-acl.yang:142` |
| `0x8847` | [MPLS](../../reference/glossary.md#term-mpls) | MPLS ユニキャスト | `sonic-acl.yang:142` |

### `stage` 値別挙動 (ACL_TABLE から継承)

ACL_RULE 自体に `stage` フィールドはないが、所属 ACL_TABLE の stage により使用可能な action が変わる。

| 値 | SAI stage | MIRROR action | evidence |
|---|---|---|---|
| `INGRESS` (既定) | `SAI_ACL_STAGE_INGRESS` | `MIRROR_INGRESS_ACTION` 有効 | `aclorch.cpp:166,173,263-266` |
| `EGRESS` | `SAI_ACL_STAGE_EGRESS` | `MIRROR_EGRESS_ACTION` のみ有効 | `aclorch.cpp:167,185,270-272` |

### `type` 値別挙動 (ACL_TABLE から継承)

ACL_RULE で使用可能な match / action は ACL_TABLE の `type` によって決まる。

| 値 | 使用可能な主 action | 備考 | evidence |
|---|---|---|---|
| `L3` | `PACKET_ACTION`, `REDIRECT_ACTION` | 通常 IPv4 ACL | `acltable.h:26`, `aclorch.cpp:200,454` |
| `L3V6` | `PACKET_ACTION`, `REDIRECT_ACTION` | IPv6 ACL。`IP_PROTOCOL` は非推奨 | `acltable.h:27`, `aclorch.cpp:220,1231` |
| `MIRROR` | `MIRROR_INGRESS_ACTION` | ASIC capability 必須 | `acltable.h:29`, `aclorch.cpp:260,3502` |
| `MIRRORV6` | `MIRROR_INGRESS_ACTION` / `MIRROR_EGRESS_ACTION` | ASIC capability 照会、一部統合 | `acltable.h:30`, `aclorch.cpp:279,3503,5811` |

### 値別 grep カバレッジ

| フィールド | 値数 | 0 hit | 証跡ファイル |
|---|---|---|---|
| `PACKET_ACTION` | 3 (YANG) / 6 (実装) | 0 | aclorch.h, aclorch.cpp |
| `IP_TYPE` | 7 (YANG) / 10 (実装) | 0 | aclorch.h, aclorch.cpp, sonic-acl.yang |
| `ETHER_TYPE` | 7 | 0 | sonic-acl.yang, aclorch.cpp |
| `stage` (継承) | 2 | 0 | aclorch.cpp |
| `type` (継承) | 4 (YANG) | 0 | acltable.h, aclorch.cpp |

### 複合条件

1. `MATCH_TCP_FLAGS` あり + `IP_PROTOCOL` 未指定 → `IP_PROTOCOL=6 (TCP)` 自動付与 (`aclorch.cpp:5640-5660`)
2. `IP_TYPE=IPV4ANY` / `IPV4` + `SRC_IPV6` 同一ルール混在 → `bAllAttributesOk=false` → rule INACTIVE (`aclorch.cpp:5636-5658`)
3. YANG `choice ip_src_dst` — `IP_TYPE` が IPv4 系なら `SRC_IP`/`DST_IP` のみ有効、IPv6 系なら `SRC_IPV6`/`DST_IPV6` のみ有効 (`sonic-acl.yang:150-168`)
4. `type=MIRROR`/`MIRRORV6` + stage=EGRESS → `MIRROR_EGRESS_ACTION` のみ有効 (`aclorch.cpp:270-272`)
5. `PACKET_ACTION=REDIRECT:` のコロン後ターゲット欠如 → `return false` → rule INACTIVE (`aclorch.cpp:2020-2028`)
<!-- /value-behavior -->

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

YANG 未定義テーブルのため、全デフォルトはコード実装が正本。

### field × 種別 一覧

| フィールド / 属性 | 種別 | 暗黙デフォルト値 | ソース |
|---|---|---|---|
| `PRIORITY` (C++) | `__init__` 属性 literal | `m_priority = 0` (コンストラクタ初期値) | `aclorch.cpp:905` |
| `PRIORITY` min/max | SAI 動的取得 | `SAI_SWITCH_ATTR_ACL_ENTRY_MINIMUM/MAXIMUM_PRIORITY` を起動時に問合せ | `aclorch.cpp:3689-3696` |
| `PRIORITY` (acl_loader) | Python literal | `max_priority - sequence_id`; `max_priority = 10000` | `acl_loader/main.py:93,772` |
| `PRIORITY` (acl_app.go) | Go literal | `MAX_PRIORITY - seqId`; `MAX_PRIORITY = 65536` | `acl_app.go:56,1153` |
| `TCP_FLAGS` mask | C++ fallback (`else` branch) | マスク省略時 `0x3F` (6bit フルマスク) | `aclorch.cpp:1061` |
| `DSCP` match mask | C++ fallback (`else` branch) | マスク省略時 `0x3F` (6bit フルマスク) | `aclorch.cpp:1090-1093` |
| `ETHER_TYPE` / `L4_SRC_PORT` / `L4_DST_PORT` mask | C++ 固定 | 常に `0xFFFF` | `aclorch.cpp:1067` |
| `VLAN_ID` mask | C++ 固定 | 常に `0xFFF` (12bit) | `aclorch.cpp:1072` |
| `IP_PROTOCOL` / `NEXT_HEADER` / `TC` / `ICMP_*` mask | C++ 固定 | 常に `0xFF` | `aclorch.cpp:1099,1151,1156` |
| `IP_TYPE` mask | C++ 固定 | 常に `0xFFFFFFFF` | `aclorch.cpp:1046` |
| `TUNNEL_VNI` / `META_DATA` mask | C++ 固定 | 常に `0xFFFFFFFF` | `aclorch.cpp:1163,1208` |
| `INNER_ETHER_TYPE` / `INNER_L4_*PORT` mask | C++ 固定 | 常に `0xFFFF` | `aclorch.cpp:1167` |
| `INNER_IP_PROTOCOL` mask | C++ 固定 | 常に `0xFF` | `aclorch.cpp:1172` |
| `INNER_SRC_MAC` / `INNER_DST_MAC` mask | C++ 固定 | 常に `ff:ff:ff:ff:ff:ff` (完全一致) | `aclorch.cpp:957` |
| `IP_PROTOCOL` / `NEXT_HEADER` | C++ 自動付与 | `TCP_FLAGS` あり + `IP_PROTOCOL` 未指定 → `6` (TCP) | `aclorch.cpp:5633-5648` |
| `SAI_ACL_ENTRY_ATTR_ADMIN_STATE` | C++ 固定 (非 CONFIG_DB) | 常に `true` を SAI に送出 | `aclorch.cpp:1293-1295` |
| `MIRROR_ACTION` → ingress | C++ fallback (後方互換) | 旧 `MIRROR_ACTION` フィールドは `MIRROR_INGRESS_ACTION` として処理 | `aclorch.cpp:2268-2271` |
| `IP_TYPE` (acl_loader・L3) | Python 自動付与 | `ETHER_TYPE = 0x0800` (IPv4) を付与 | `acl_loader/main.py:789` |
| `IP_TYPE` (acl_loader・L3V6) | Python 自動付与 | `IP_TYPE = "IPV6ANY"` を付与 | `acl_loader/main.py:787` |
| `IP_TYPE` (acl_app.go・IPv4) | Go 自動付与 | `IP_TYPE = "IPV4ANY"` を常に付与 | `acl_app.go:1219` |
| `IP_TYPE` (acl_app.go・IPv6) | Go 自動付与 | `IP_TYPE = "IPV6ANY"` を常に付与 | `acl_app.go:1251` |

### YANG default との関係

`ACL_RULE` は YANG 未定義のため YANG default は存在しない。全デフォルトはコードレベルのみ。

### 乖離・注意点

1. **PRIORITY の最大値が経路依存**: `acl_loader` は `max_priority=10000`、`acl_app.go` (REST/gNMI) は `MAX_PRIORITY=65536` を使用。同一 sequence_id でも経路によって格納される PRIORITY 値が異なる。
2. **DEFAULT_RULE の IP_TYPE**: `acl_loader` はテーブル種別に応じて `ETHER_TYPE` または `IP_TYPE` を設定するが、`acl_app.go` は常に `IP_TYPE=ANY` を設定 (`acl_app.go:1148`)。
3. **mask は CONFIG_DB に格納されない**: 全 mask デフォルトは C++ 内部でのみ付与され、CONFIG_DB には書かれない。DB には値 (data) のみが格納される。
4. **COUNTER フィールド**: `AclRuleMirror` はデフォルトでカウンタを作成しない (`createCounter=false`)。`AclRulePacket` は `createCounter=true`。

### 該当なしフィールド (追加デフォルトなし)

以下のフィールドは省略時に自動設定は一切行われず、ルールに含まれなければ単に match 条件が適用されない:
`SRC_IP`, `DST_IP`, `SRC_IPV6`, `DST_IPV6`, `IN_PORTS`, `OUT_PORT`, `OUT_PORTS`, `REDIRECT_ACTION`, `MIRROR_INGRESS_ACTION`, `MIRROR_EGRESS_ACTION`, `FLOW_OP`, `INT_SESSION`, `DROP_REPORT_ENABLE`, `TAIL_DROP_REPORT_ENABLE`, `FLOW_SAMPLE_PERCENT`, `REPORT_ALL_PACKETS`, `INNER_SRC_IP`, `BTH_OPCODE`, `AETH_SYNDROME`, `TUNNEL_TERM`, `DO_NOT_NAT_ACTION`, `DISABLE_TRIM_ACTION`, `META_DATA_ACTION`, `DSCP_ACTION`, `INNER_SRC_MAC_REWRITE_ACTION`。

### LSP トレース証跡

- 訪問ファイル数: 3 (`aclorch.cpp`, `acl_loader/main.py`, `acl_app.go`)
- 訪問関数数: 17
- 検出 fallback: 21 件 (mask 系 9 件 + 自動付与 7 件 + 初期値 3 件 + 後方互換 1 件 + SAI 固定 1 件)
- 中間トレース: `meta/_intermediate/cdb-flow/acl-rule-defaults.md`

<!-- /defaults -->

<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

| 派生先フィールド | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| `IP_PROTOCOL` / `NEXT_HEADER` | `MATCH_TCP_FLAGS` あり + `IP_PROTOCOL` 未指定 | `6` (TCP) | `aclorch.cpp:5632-5660` |
| `stage` (ACL_TABLE 継承) | 所属 `ACL_TABLE.stage` | `INGRESS` → `MIRROR_INGRESS_ACTION` 有効 / `EGRESS` → `MIRROR_EGRESS_ACTION` のみ | `aclorch.cpp:263-272` |
| `type` (ACL_TABLE 継承) | 所属 `ACL_TABLE.type` | `L3` / `L3V6` / `MIRROR` 等によって使用可能な match / action が決まる | `aclorch.cpp:200,220,260` |

**minigraph.py 由来の自動設定** (`minigraph.py:1103-1228`):

- XML `InAcl` タグ → `stage=ingress`、`OutAcl` タグ → `stage=egress`
- AttachTo に `erspan` prefix → `type=MIRROR`、`erspanv6` → `type=MIRRORV6`、`erspan_dscp` → `type=MIRROR_DSCP`
- ports なし (CTRLPLANE) → `type=CTRLPLANE`、`stage` 設定あり
- それ以外: ACL 名に `v6` を含む → `type=L3V6`、含まない → `type=L3`

### Phase 7: 条件付き登録

| 条件 | 影響 | ソース |
|---|---|---|
| `AclOrch` は常時登録 (platform 非依存) | ACL_TABLE / ACL_RULE 購読は無条件 | `orchdaemon.cpp:533,569` |
| `DTelOrch` は `platform==BFN\|VS` かつ capability あり のみ生成 | DTelOrch なし → DTEL 系 action (`FLOW_OP`, `INT_SESSION` 等) が機能しない | `orchdaemon.cpp:502-530` |
| `type=MIRROR`/`MIRRORV6` + ASIC capability なし | 起動時 SAI capability query 失敗 → ACL_TABLE 作成 reject | `aclorch.cpp:3500-3541` |
| `type=L3V4V6` + ASIC 未サポート | `isAclL3V4V6TableSupported()` → false → reject | `aclorch.cpp:2737-2739` |
| `META_DATA` 系 action + capability なし | `sai_query_attribute_capability()` で確認後に有効化 | `aclorch.cpp:3590-3659` |

### グレップカバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| TCP 自動付与 (`bHasTCPFlag` + `TCP_PROTOCOL_NUM`) | 3 | `aclorch.cpp:54,5633-5648` |
| minigraph.py `type` 派生 | 6 | `minigraph.py:1218-1228` |
| DTelOrch 条件起動 | 2 | `orchdaemon.cpp:522,527-530` |
| MIRROR capability check | 4 | `aclorch.cpp:3500-3541,5198-5199` |

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

ACL_RULE は `AclOrch::doAclRuleTask()` が処理する。同メソッド内で ACL_TABLE の `type` / `stage` フィールド値を読み取り、ルールの処理方法を分岐する。

| Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `AclOrch` | `doAclRuleTask()` | `table_id.empty()` | 早期 WARN + erase（TABLE_ID 欠如はルール無効） | `sonic-swss/orchagent/aclorch.cpp:5536-5540` |
| `AclOrch` | `doAclRuleTask()` | `table_oid == SAI_NULL_OBJECT_ID` かつ `m_ctrlAclTables.find(table_id) != end` | INFO ログ + erase（コントロールプレーンルールをスキップ）| `sonic-swss/orchagent/aclorch.cpp:5556-5561` |
| `AclOrch` | `doAclRuleTask()` | `table_oid == SAI_NULL_OBJECT_ID` かつ ACL_TABLE 未作成 | `it++`（テーブル作成まで待機） | `sonic-swss/orchagent/aclorch.cpp:5563-5565` |
| `AclOrch` | `doAclRuleTask()` | `type IN [TABLE_TYPE_MIRROR, TABLE_TYPE_MIRRORV6]` | `table_id == m_mirrorTableId[stage]` により MIRROR / MIRRORV6 を再判定 | `sonic-swss/orchagent/aclorch.cpp:5570-5573` |
| `AclOrch` | `doAclRuleTask()` | `bHasTCPFlag && !bHasIPProtocol` かつ `type IN [MIRRORV6, L3V6]` | `IP_PROTOCOL` 自動付与: `MATCH_NEXT_HEADER=6` (IPv6) | `sonic-swss/orchagent/aclorch.cpp:5636-5638` |
| `AclOrch` | `doAclRuleTask()` | `bHasTCPFlag && !bHasIPProtocol` かつ `type` が上記以外 | `IP_PROTOCOL` 自動付与: `MATCH_IP_PROTOCOL=6` (IPv4) | `sonic-swss/orchagent/aclorch.cpp:5640-5643` |
| `AclOrch` | `doAclRuleTask()` | `bHasIPV4 && bHasIPV6 && type == TABLE_TYPE_L3V4V6` | ERROR + `bAllAttributesOk=false` → rule INACTIVE（v4/v6 混在不可） | `sonic-swss/orchagent/aclorch.cpp:5656-5663` |

> **スキャン証跡**: `doAclRuleTask()` L5520-5700 を全行読了、7 件分岐抽出。`type` / `stage` は ACL_RULE 自体のフィールドではなく ACL_TABLE から継承した値を参照。Phase 6/7 derivation ブロックの evidence 再確認: TCP 自動付与・minigraph 派生・DTelOrch 条件起動は実ソースと整合（`aclorch.cpp:5632-5660`、`minigraph.py:1218-1228`、`orchdaemon.cpp:502-530`）— 誤読なし。

<!-- /handler-branching -->

<!-- platform -->
## プラットフォーム差 (Phase H)

ACL_RULE の処理は `AclOrch::init()` が起動時に環境変数 `platform` / `sub_platform` を読み取り、以下の capability を静的に決定する。MIRROR V6 / L3V4V6 / isCombinedMirrorV6 はすべて env var の **静的比較** で確定。META_DATA 系のみ SAI 動的照会 (`sai_query_attribute_capability`) を使う。

### プラットフォーム識別文字列 (orch.h:40-50)

| 定数 | 値 | プラットフォーム例 |
|------|----|--------------------|
| `BRCM_PLATFORM_SUBSTRING` | `"broadcom"` | Broadcom XGS (non-DNX) |
| `BRCM_DNX_PLATFORM_SUBSTRING` | `"broadcom-dnx"` | Broadcom DNX/Jericho (sub_platform) |
| `MLNX_PLATFORM_SUBSTRING` | `"mellanox"` | Mellanox Spectrum |
| `BFN_PLATFORM_SUBSTRING` | `"barefoot"` | Intel Tofino (Barefoot) |
| `VS_PLATFORM_SUBSTRING` | `"vs"` | Virtual Switch (テスト用) |
| `NPS_PLATFORM_SUBSTRING` | `"nephos"` | Nephos |
| `CISCO_8000_PLATFORM_SUBSTRING` | `"cisco-8000"` | Cisco Silicon One |
| `XS_PLATFORM_SUBSTRING` | `"xsight"` | xsight |
| `CLX_PLATFORM_SUBSTRING` | `"clounix"` | Clounix |
| `MRVL_PRST_PLATFORM_SUBSTRING` | `"marvell-prestera"` | Marvell Prestera |
| `MRVL_TL_PLATFORM_SUBSTRING` | `"marvell-teralynx"` | Marvell Teralynx |

### capability 差異一覧

| capability | 有効プラットフォーム | 無効/制限プラットフォーム | 効果 | evidence |
|---|---|---|---|---|
| **MIRROR V6** (`isAclMirrorV6Supported`) | broadcom / cisco-8000 / mellanox / barefoot / marvell-prestera / marvell-teralynx / nephos / xsight / clounix / vs | それ以外（未知） | false → `type=MIRRORV6` の ACL_TABLE 作成を reject → IPv6 mirror ルール不可 | `aclorch.cpp:3489-3513` |
| **isCombinedMirrorV6Table** | broadcom (非 DNX) / barefoot / marvell-teralynx / nephos / vs / その他 | mellanox / cisco-8000 / marvell-prestera / xsight / clounix / broadcom-dnx | true (統合) → `MIRROR` テーブル 1 枚で V4/V6 両対応。false (分離) → `MIRROR` と `MIRRORV6` を別々に作成必須 | `aclorch.cpp:3546-3560` |
| **L3V4V6 テーブル** (`isAclL3V4V6TableSupported`) | marvell-prestera / marvell-teralynx / vs | それ以外 | false → `type=L3V4V6` の ACL_TABLE 作成を reject → IPv4/IPv6 混在 match ルール不可 | `aclorch.cpp:3515-3533, 2739-2742` |
| **ACL range 上限** | — | mellanox: 16 / clounix: 16 | 上限超過時 `return NULL` (ERROR ログ) → range match ルールが INACTIVE | `aclorch.cpp:3373-3377, aclorch.h:109-110` |
| **META_DATA / META_DATA_ACTION** | SAI 動的照会で全 3 属性が実装済みの場合 | SAI が未実装と返した場合 | false → META_DATA match / META_DATA_ACTION は無視 / rule INACTIVE | `aclorch.cpp:3563-3664, 5258-5267` |
| **PFCWD OUT_PORT match** | broadcom-dnx (sub_platform) | それ以外 | DNX のみ PFCWD テーブルが `SAI_ACL_BIND_POINT_TYPE_SWITCH` + `OUT_PORT` match 対応 | `aclorch.cpp:3811-3830` |
| **Egress range フィールド** | それ以外 (Egress で range 付加) | broadcom 非 DNX Egress | broadcom 非 DNX の Egress ACL テーブルは range フィールドを強制付加しない → Egress で L4 range match 不可 | `aclorch.cpp:2608-2628` |
| **DTel 系 action** (`FLOW_OP` / `INT_SESSION` 等) | barefoot / vs | それ以外 | `DTelOrch` 非起動 → DTel action SAI 反映なし | `orchdaemon.cpp:502-530` |

### プラットフォーム別サマリ

| プラットフォーム | MIRROR V6 | Combined Mirror | L3V4V6 | DTel |
|----------------|-----------|----------------|--------|------|
| broadcom (非 DNX) | yes | yes (統合) | no | no |
| broadcom-dnx | yes | no (分離) | no | no |
| mellanox | yes | no (分離) | no | no |
| barefoot | yes | yes (統合) | no | **yes** |
| cisco-8000 | yes | no (分離) | no | no |
| marvell-prestera | yes | no (分離) | **yes** | no |
| marvell-teralynx | yes | yes (統合) | **yes** | no |
| nephos | yes | yes (統合) | no | no |
| xsight | yes | no (分離) | no | no |
| clounix | yes | no (分離) | no | no |
| vs (virtual) | yes | yes (統合) | **yes** | **yes** |
| 未知 | **no** | yes (統合) | no | no |

!!! note "isCombinedMirrorV6Table の運用上の注意"
    `isCombinedMirrorV6Table=false` (mellanox / cisco-8000 / marvell-prestera 等) の環境では、
    IPv6 パケット対象の mirror ルールを適用するには `type=MIRRORV6` の ACL_TABLE を **別途** 作成すること。
    `MIRROR` テーブルのみを作成した場合、IPv6 mirror ルールが有効にならない (`aclorch.cpp:5811`)。

!!! warning "L3V4V6 制限"
    `type=L3V4V6` テーブルは marvell-prestera / marvell-teralynx / vs のみ有効。
    それ以外の環境で ACL_TABLE に `type=L3V4V6` を設定すると、
    テーブル作成時点で `isAclL3V4V6TableSupported()` が false → reject されルールも一切適用されない (`aclorch.cpp:2739-2742`)。

!!! warning "DTel action の前提"
    `FLOW_OP` / `INT_SESSION` / `DROP_REPORT_ENABLE` / `TAIL_DROP_REPORT_ENABLE` 等の DTel 系 action は
    barefoot / vs 以外では `DTelOrch` が起動しないため、設定しても SAI に反映されない (`orchdaemon.cpp:502-530`)。

<!-- /platform -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`ACL_RULE` は YANG 未定義のため leafref は存在しない。以下はすべて実装レベルの暗黙参照。

| 参照先テーブル / リソース | 参照方向 | 条件 | 参照元 evidence |
|--------------------------|---------|------|----------------|
| `PORT\|<name>` (IN_PORTS / OUT_PORT / OUT_PORTS) | OID 解決（必須） | match フィールドにポート名を指定したとき。物理・LAG のみ受理、他は rule INACTIVE | `aclorch.cpp` L961–1034 (`gPortsOrch->getPort()`) |
| `PORT\|<name>` / LAG (REDIRECT_ACTION) | OID 解決 | `REDIRECT_ACTION` 値がポート名・LAG 名と一致するとき | `aclorch.cpp` L2085–2099 (`getRedirectObjectId()` ステップ 1) |
| `MIRROR_SESSION\|<name>` | 存在確認 + OID + refcount | `MIRROR_ACTION` / `MIRROR_INGRESS_ACTION` / `MIRROR_EGRESS_ACTION` 指定時。SESSION 不在は rule INACTIVE、inactive は遅延 install | `aclorch.cpp` L2331–2401 (`AclRuleMirror::activate()`) |
| `NEIGH`（NeighOrch） | OID + refcount | `REDIRECT_ACTION` 値が `<ip>@<intf>` 形式の next-hop のとき | `aclorch.cpp` L2102–2116 (`getRedirectObjectId()` ステップ 2) |
| `ROUTE_TABLE`（RouteOrch 管理の NH group） | OID + refcount、自動生成 | `REDIRECT_ACTION` 値が NH group 形式のとき。不在なら RouteOrch が自動作成を試みる | `aclorch.cpp` L2138–2157 (`getRedirectObjectId()` ステップ 4) |
| TunnelNhop（TunnelOrch） | OID 解決 | `REDIRECT_ACTION` 値がトンネル next-hop 形式のとき | `aclorch.cpp` L2118–2136 (`getRedirectObjectId()` ステップ 3) |
| `ACL_TABLE\|<table_name>` | SAI OID 解決（必須） | 常時。ACL_TABLE が未作成なら `it++` で待機、作成後に自動再処理 | `aclorch.cpp` L5520–5565 (`doAclRuleTask()` ガード) |
| `PORT`（PortsOrch 初期化完了） | 起動ブロック | 常時。`allPortsReady()` が false の間は全 ACL_RULE 処理をブロック | `aclorch.cpp` L4276 |
| `POLICER`（acl_loader のみ） | 読み取り（表示用） | `aclshow` コマンド実行時。orchagent (`aclorch.cpp`) は ACL_RULE から POLICER を直接参照しない | `acl_loader/main.py` L254–266 (`read_policers_info()`) |

!!! note "POLICER と ACL_RULE の関係"
    標準 `aclorch.cpp` ベースの ACL_RULE には policer action フィールドが存在しない。
    POLICER を ACL に組み合わせる場合は P4 orch (`p4orch/acl_util.cpp`) 経由となる。
    `acl_loader` は `POLICER` テーブルを **表示目的のみ** で読み取る。

!!! note "REDIRECT_ACTION の解決順序"
    `getRedirectObjectId()` (`aclorch.cpp:2078`) は次の順で解決を試みる:
    1. PortsOrch — PORT / LAG 名として解決
    2. NeighOrch — `<ip>@<intf>` next-hop として解決
    3. TunnelOrch — トンネル next-hop として解決
    4. RouteOrch — next-hop group として解決（不在時は自動生成）
    いずれも失敗すると `SAI_NULL_OBJECT_ID` → rule INACTIVE。

<!-- /cross-refs -->

<!-- constants -->
## ハードコード定数 (Phase E)

YANG 未定義テーブルのため、全定数はソースコードが正本。以下は `aclorch.h` / `aclorch.cpp` / `acl_loader/main.py` / `acl_app.go` から抽出した硬直定数一覧。

### 数値・mask 定数

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `TCP_PROTOCOL_NUM` | `6` | `TCP_FLAGS` あり + `IP_PROTOCOL` 未指定時に自動付与する TCP プロトコル番号 | `aclorch.cpp:54` |
| `MAC_EXACT_MATCH` | `"ff:ff:ff:ff:ff:ff"` | `INNER_SRC_MAC` / `INNER_DST_MAC` の SAI mask（完全一致固定） | `aclorch.cpp:56` |
| `MAX_META_DATA_VALUE` | `4095` | `META_DATA` / `META_DATA_ACTION` 最大許容値（SAI range 上限クランプ） | `aclorch.cpp:52` |
| `MLNX_MAX_RANGES_COUNT` | `16` | Mellanox プラットフォームの ACL range オブジェクト上限 | `aclorch.h:109` |
| `CLNX_MAX_RANGES_COUNT` | `16` | Centec プラットフォームの ACL range オブジェクト上限 | `aclorch.h:110` |
| `max_priority` (acl_loader デフォルト) | `10000` | `PRIORITY = max_priority − seq_id`（CLI 経路） | `acl_loader/main.py:93` |
| `MAX_PRIORITY` (acl_app.go) | `65536` | `PRIORITY = MAX_PRIORITY − seqId`（REST/gNMI 経路） | `acl_app.go:56` |

### タイマー定数

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `ACL_COUNTER_DEFAULT_POLLING_INTERVAL_MS` | `10000` ms (10 秒) | ACL stat counter flex counter ポーリング周期 | `aclorch.cpp:47` |
| `ACL_COUNTER_DEFAULT_ENABLED_STATE` | `false` | ACL stat counter 初期状態（無効） | `aclorch.cpp:48` |

### フィールド別 SAI mask 固定値

SAI match field に投入される mask は CONFIG_DB には書かれず、C++ 内部でのみ付与される。

| フィールド | mask 値 | ビット幅 | ソース |
|-----------|---------|---------|--------|
| `TCP_FLAGS` | `0x3F`（省略時フォールバック） | 6 bit | `aclorch.cpp:1061` |
| `DSCP` | `0x3F`（省略時フォールバック） | 6 bit | `aclorch.cpp:1093` |
| `IP_TYPE` | `0xFFFFFFFF` | 32 bit | `aclorch.cpp:1046` |
| `ETHER_TYPE` / `L4_SRC_PORT` / `L4_DST_PORT` | `0xFFFF` | 16 bit | `aclorch.cpp:1067` |
| `VLAN_ID` | `0xFFF` | 12 bit | `aclorch.cpp:1072` |
| `IP_PROTOCOL` / `NEXT_HEADER` / `TC` / `ICMP_TYPE` / `ICMP_CODE` / `ICMPV6_TYPE` / `ICMPV6_CODE` | `0xFF` | 8 bit | `aclorch.cpp:1099,1151,1157` |
| `TUNNEL_VNI` / `META_DATA` | `0xFFFFFFFF` | 32 bit | `aclorch.cpp:1162,1208` |
| `INNER_ETHER_TYPE` / `INNER_L4_SRC_PORT` / `INNER_L4_DST_PORT` | `0xFFFF` | 16 bit | `aclorch.cpp:1168` |
| `INNER_IP_PROTOCOL` | `0xFF` | 8 bit | `aclorch.cpp:1173` |
| `INNER_SRC_MAC` / `INNER_DST_MAC` | `ff:ff:ff:ff:ff:ff` | 48 bit | `aclorch.cpp:957` |

!!! note "TCP_FLAGS / DSCP mask は可変"
    `<data>/<mask>` 形式で明示指定した場合は指定値が優先される。`0x3F` はあくまで省略時フォールバック。
    例: `TCP_FLAGS = 0x02/0x02` と書けば mask は `0x02`（SYN bit のみ）。

!!! note "PRIORITY 計算経路差異"
    `acl_loader` (CLI) は `max_priority=10000`、REST/gNMI 経路の `acl_app.go` は `MAX_PRIORITY=65536` を使う。
    同一 sequence_id でも経路によって CONFIG_DB に書かれる PRIORITY 値が異なる点に注意。

!!! warning "ACL カウンタは初期無効"
    `ACL_COUNTER_DEFAULT_ENABLED_STATE = false` のため、`AclOrch` 起動直後は ACL stat counter の flex counter が無効。`counterpoll acl enable` または `aclshow` 経由で有効化するまでカウンタ値は収集されない。

<!-- /constants -->

<!-- ordering -->
## 書込み順依存 (Phase B)

ACL_RULE を CONFIG_DB に書き込む際に守るべき順序制約を実装から導出した。

### 先行必須テーブル (SET 時)

| 依存テーブル | 理由 | 緩和策 | evidence |
|---|---|---|---|
| `PORT` (PortsOrch 初期化完了) | `doTask()` が `allPortsReady()` false の間全ブロック | なし（自動待機） | `aclorch.cpp:4276` |
| `ACL_TABLE` (SAI 作成済み) | `getTableById()` が `SAI_NULL_OBJECT_ID` のとき `it++` 無限待機 | 自動再試行（毎イベントループ） | `aclorch.cpp:5550-5565` |
| `MIRROR_SESSION` (存在のみ必須) | `sessionExists()` が false → rule INACTIVE (ERROR ログ) | active 化は後追い可 — `MirrorSessionUpdate` イベントで遅延 install | `aclorch.cpp:2331-2347` |
| REDIRECT 先 next-hop / NH group | NH 未解決 → `SAI_NULL_OBJECT_ID` → rule INACTIVE | NH group は orchagent が自動作成を試みる | `aclorch.cpp:2090-2165` |

### SET / DEL 操作順序

| 操作 | 制約 | 理由 | evidence |
|---|---|---|---|
| MIRROR ルールの**内容変更** | `DEL` → `SET` の順が必須 | `AclRuleMirror::update()` は未実装 (`SWSS_LOG_ERROR` + `return false`) | `aclorch.cpp:2415-2420` |
| 非 MIRROR ルールの変更 | `SET` のみで差分適用可 | `set_acl_entry_attribute()` — match / action は runtime mutable | `aclorch.cpp:1466` |
| ACL_TABLE を DEL する前に ACL_RULE を DEL | **推奨**（必須ではない） | `removeAclTable()` が暗黙に全ルールを SAI から削除するが CONFIG_DB の ACL_RULE エントリは残存するため、再起動時に再投入される | `aclorch.cpp:4849-4857` |
| SAI リソース枯渇時: 既存ルール DEL → retry 自動発火 | 自動 | ルール DEL 成功時に `notifyRetry()` が同テーブルの待機キャッシュを再処理 | `aclorch.cpp:5716-5720` |

### warm-restart / cold-restart 影響

- `AclOrch` は `onWarmBootEnd()` を**実装しない**（warm-restart 非対応）。orchagent 再起動（cold）で CONFIG_DB replay により自動再構築。
- 再起動後、ACL_TABLE が再処理される前に ACL_RULE が Consumer に届いても、待機ループ（`it++`）で自動調停される。
- MIRROR ルールは MIRROR_SESSION が inactive → `activate()` が SAI entry 未作成のまま `return true` → SESSION が後から active になると `onUpdate()` で遅延 install — 再起動後も同様に動作する。

!!! warning "MIRROR ルール変更"
    `MIRROR_INGRESS_ACTION` / `MIRROR_EGRESS_ACTION` を含む ACL_RULE の変更は `SET` のみでは適用されない。必ず `DEL` → `SET` の順で操作すること (`aclorch.cpp:2415-2420`)。

<!-- /ordering -->

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

<!-- entry-points -->
## 書き込み入り口 (Direction A)

CONFIG_DB の `ACL_RULE` テーブルを書き込むコードパスを網羅する。

### CLI — acl_loader

`sonic-utilities/acl_loader/main.py` — `acl-loader update full / incremental / delete`

**full update** (`full_update()` L850):

```python
configdb.mod_entry(ACL_RULE, key, None)           # 既存全削除
configdb.mod_config({ACL_RULE: rules_info})        # 新規一括書き込み
```

入力プロトコル: JSON ファイル（OpenConfig ACL 形式）— `<filename>` 引数で指定

**incremental update** (`incremental_update()` L871):

```python
configdb.mod_entry(ACL_RULE, key, value)           # 追加
configdb.mod_entry(ACL_RULE, key, None)            # 削除
configdb.set_entry(ACL_RULE, key, value)           # 内容変更
```

dataplane ACL は full update 方式、controlplane ACL は差分更新。

**delete** (`delete()` L946):

```python
configdb.set_entry(ACL_RULE, key, None)
```

Multi-ASIC: 各 namespace の `namespace_configdb` にも同じ操作を適用。

**デフォルト deny ルール自動追加** (`createDefaultDenyAclRule()` L1138):

`full_update` の末尾で priority=0 の DROP ルールを自動追加する。

### REST / gNMI

`sonic-mgmt-common/translib/acl_app.go:1062-1418`

- REST path: `PATCH /openconfig-acl:acl/acl-sets/acl-set/{name}/{type}/acl-entries/acl-entry/{seq}`
- gNMI path: `/openconfig-acl:acl/acl-sets/acl-set[...]/acl-entries/acl-entry[seq-id=...]`
- `convertOCAclRulesToInternal()` でルール変換後、`d.SetEntry(app.ruleTs, db.Key{Comp: []string{aclKey, ruleKey}}, ...)` で CONFIG_DB の ACL_RULE に書き込み

### minigraph

なし。`minigraph.py` は ACL_RULE を生成しない（ACL_TABLE のみ）。

### db_migrator

なし。ACL_RULE の migration ステップは `db_migrator.py` に存在しない。

### build-time デフォルト

なし。`init_cfg.json.j2` および `qos_config.j2` に ACL_RULE エントリは存在しない。

### hard-coded デフォルト

`acl_loader` の `createDefaultDenyAclRule()` (L1138) が `full_update` 時に priority=0 の DROP ルールを自動追加する（これは build-time ではなく CLI 実行時の動作）。

### 死活 (runtime injection)

`orchagent` の `AclOrch` は ACL_RULE を購読するのみ（書き込みなし）。

<!-- /entry-points -->

<!-- runtime-trace -->
## 起動経路 (Direction B: CFG → APPL → SAI)

### 段階 1: Consumer 登録

`orchdaemon.cpp:410,413` で `CONFIG_DB / ACL_RULE` (`"ACL_RULE"`) と `APP_DB / ACL_RULE_TABLE` (`"ACL_RULE_TABLE"`) の `TableConnector` を作成し `AclOrch` コンストラクタに渡す。`doTask()` (`aclorch.cpp:4287`) で `table_name` が `CFG_ACL_RULE_TABLE_NAME` または `APP_ACL_RULE_TABLE_NAME` に一致すると `doAclRuleTask()` に委譲。retry キャッシュも登録 (`aclorch.cpp:4221`) 。追加コンシューマ: `MirrorOrch` (`MIRROR_*_ACTION` 連動)、`CoppOrch` (`CTRLPLANE` 種別)、`NatMgr` (`cfgmgr/natmgrd.cpp:120`)。

### 段階 2: CFG → APPL 翻訳

`ACL_RULE` も `cfgmgr` 中間層なし。`AclOrch` が `CONFIG_DB` を直接購読する。`APP_DB` への中間書き込みなし。主な変換 (`doAclRuleTask()`, `aclorch.cpp:5520`):

| CFG フィールド | 変換 | SAI 属性 |
|---|---|---|
| `PRIORITY` | uint32 そのまま | `SAI_ACL_ENTRY_ATTR_PRIORITY` |
| `PACKET_ACTION` | `aclPacketActionLookup` ルックアップ | `SAI_ACL_ENTRY_ATTR_ACTION_PACKET_ACTION` |
| `IP_TYPE` | `aclIpTypeLookup` ルックアップ | `SAI_ACL_ENTRY_ATTR_FIELD_ACL_IP_TYPE` |
| `ETHER_TYPE` | `stoul(str, &idx, 0)` hex 変換、mask `0xFFFF` | `SAI_ACL_ENTRY_ATTR_FIELD_ETHER_TYPE` |
| `MATCH_TCP_FLAGS` + `IP_PROTOCOL` 未指定 | `IP_PROTOCOL=6` を自動付与 (`aclorch.cpp:5640`) | `SAI_ACL_ENTRY_ATTR_FIELD_IP_PROTOCOL` |
| `REDIRECT_ACTION` | next-hop / mirror セッション OID 解決 | `SAI_ACL_ENTRY_ATTR_ACTION_REDIRECT` |

暗黙追加: `SAI_ACL_ENTRY_ATTR_TABLE_ID` (所属 ACL_TABLE の OID) を常に create 時に付与。

### 段階 3: APPL → SAI

`AclRule::create()` → `sai_acl_api->create_acl_entry(&m_ruleOid, gSwitchId, attrs, ...)` (`aclorch.cpp:1344`)。設定 SAI 属性: `SAI_ACL_ENTRY_ATTR_TABLE_ID`、`SAI_ACL_ENTRY_ATTR_PRIORITY`、`SAI_ACL_ENTRY_ATTR_FIELD_*` (match 群)、`SAI_ACL_ENTRY_ATTR_ACTION_*` (action 群)。ランタイム更新は `sai_acl_api->set_acl_entry_attribute(m_ruleOid, &attr)` (`aclorch.cpp:1466`) — match / action は **mutable**。

### 段階 4: タイミング・副作用

- **config reload**: warm start 非対応。reload 時は全ルールを再作成。ACL_TABLE が未作成なら `it++` で待機し、テーブル作成後に再処理される (`aclorch.cpp:5563-5565`)。
- **runtime 変更 (SET)**: 既存ルール検出時は `AclRule::update()` → `set_acl_entry_attribute()` で差分適用。match / action は runtime mutable。
- **warm-restart**: `AclOrch` は `onWarmBootEnd()` を実装しない。orchagent 全体の `warmRestoreAndSyncUp()` (`orchdaemon.cpp:872`) でリカバリ。
- **SAI resource 枯渇**: `SAI_STATUS_INSUFFICIENT_RESOURCES` 時に retry キャッシュへ退避、リソース解放後に再試行 (`aclorch.cpp:4221`)。
- **STATE_DB 書き込み**: ルール作成/削除時に `STATE_ACL_RULE_TABLE_NAME` (`"ACL_RULE_TABLE"`) へステータスを書き込む (`aclorch.cpp:3479`)。

<!-- /runtime-trace -->
<!-- glossary-links-injected: a78cb4c857bd -->
