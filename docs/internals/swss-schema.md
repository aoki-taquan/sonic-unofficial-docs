---
title: swss-schema（APPL_DB / STATE_DB の中心スキーマ参照）
description: swss-schema（APPL_DB / STATE_DB の中心スキーマ参照） — SONiC の APPL_DB / STATE_DB
  に存在する主要テーブルを、RFC 5234 ABNF 構文 で機械可読に定義する sonic-swss リポジトリ内の参照ドキュメント。
area: internals
verification: code-verified
last_verified: 2026-05-11
sources:
- repo: sonic-net/sonic-swss
  path: doc/swss-schema.md
  ref: 4305596145e57e15e4c6a1a3902c0bc6c44a09c5
related:
  config_db:
  - VLAN
  - VNET
  - ACL_TABLE
  - VLAN_SUB_INTERFACE
  - VLAN_INTERFACE
  - VLAN_MEMBER
  - ACL_RULE
  cli:
  - config vlan
  - show vlan
  - config vnet
  - show bfd
  - show arp
  - show acl
  - config acl
  yang:
  - sonic-vlan
  - sonic-vlan-sub-interface
  - sonic-vnet
  - sonic-srv6
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含みます。機能の概念・設定・運用を読み物として読みたい場合は [Topics 20 章: SWSS / SAI / Redis](../topics/20-swss-sai-redis/index.md) を参照。
<!-- /topics-tip -->

!!! success "裏取りステータス: Code-verified / リファレンス文書"
    本ファイルは sonic-swss リポジトリ内の **生きたスキーマ参照ドキュメント** で、APPL_DB / STATE_DB の中心テーブルの ABNF 定義を集約している。本ページは概観のみで、最新の各テーブル詳細は [sonic-swss/doc/swss-schema.md](https://github.com/sonic-net/sonic-swss/blob/master/doc/swss-schema.md) を参照することを推奨する。54KB 超のため要点のみ抜粋。

# swss-schema（APPL_DB / STATE_DB の中心スキーマ参照）

## 概要

[SONiC](../reference/glossary.md#term-sonic) の [APPL_DB](../reference/glossary.md#term-appl_db) / [STATE_DB](../reference/glossary.md#term-state_db) に存在する主要テーブルを、**RFC 5234 ABNF 構文** で機械可読に定義する `sonic-swss` リポジトリ内の参照ドキュメント[^1]。[orchagent](../reference/glossary.md#term-orchagent) / *[syncd](../reference/glossary.md#term-syncd) / *mgrd 系プロセス間で受け渡されるテーブルの正規定義として、サブシステムを跨いで参照される。

開発者・Verifier はこのファイルを APPL_DB / STATE_DB スキーマの一次情報として扱う。[CONFIG_DB](../reference/glossary.md#term-config_db) スキーマは別途 `sonic-buildimage/src/sonic-yang-models/` 配下の [YANG](../reference/glossary.md#term-yang) モデルが正規。

## 動作仕様

### 共通トークン

```text
name                    = 1*DIGIT/1*ALPHA
ref_hash_key_reference  = "[" hash_key "]"   ; 別 DB キーへの参照
hash_key                = name               ; 既存キー名
```

### 主要 APPL_DB テーブル（抜粋）

ファイル冒頭から並ぶ代表テーブル：

- **`PORT_TABLE`**: 物理ポート（CPU / loopback は除外）。`admin_status` / `oper_status` / `lanes` / `mac` / `alias` / `speed` / `mtu` / `fec` / `autoneg` / `preemphasis` / FEC・[SerDes](../reference/glossary.md#term-serdes) 用 hex リスト / Path Tracing 用フィールド / [QoS](../reference/glossary.md#term-qos) マッピング reference 等[^1]。
- **`INTF_TABLE`**: 論理ネットワークインタフェース。`<ifname>:<IPprefix>` 形式キー、`scope` (global/local)、`if_mtu`、`family`。
- **`VLAN_TABLE` / `VLAN_MEMBER_TABLE`**: [VLAN](../reference/glossary.md#term-vlan) 定義とメンバ。
- **`LAG_TABLE` / `LAG_MEMBER_TABLE`**: Port-Channel 定義とメンバ。
- **`ROUTE_TABLE`**: 経路。`nexthop` / `intf` / `vni_label` / `router_mac` / `blackhole` / [SRv6](../reference/glossary.md#term-srv6) 関連 (`segment` / `seg_src` / `vpn_sid` / `policy`)。
- **`NEIGH_TABLE`**: [ARP](../reference/glossary.md#term-arp)/ND エントリ。`<ifname>:<ip>` キー。
- **`FDB_TABLE`**: L2 [FDB](../reference/glossary.md#term-fdb) エントリ。
- **`MIRROR_SESSION_TABLE`**: ミラーリングセッション。
- **`ACL_TABLE` / `ACL_RULE_TABLE`**: [ACL](../reference/glossary.md#term-acl) の APPL_DB 投影。
- **`COPP_TABLE`**: control-plane policer。
- **`BFD_SESSION_TABLE`**: [BFD](../reference/glossary.md#term-bfd) セッション。
- **`VNET_ROUTE_TUNNEL_TABLE` / `VXLAN_TUNNEL_TABLE`**: VxLAN / [VNET](../reference/glossary.md#term-vnet)。
- **`SRV6_*`**: SRv6 関連（SID list、my_sid、policy）。

### 主要 STATE_DB テーブル

- **`PORT_TABLE` (STATE_DB)**: oper 状態のうち [SAI](../reference/glossary.md#term-sai)/syncd 由来分。
- **`NEIGH_STATE_TABLE` / `INTERFACE_TABLE`**: oper 状態。
- **`BFD_SESSION_TABLE` (STATE_DB)**: BFD の oper state（`Up` / `Down`）。
- **`WARM_RESTART_TABLE`**: warm restart 各サブシステムの restart_count 等。
- **`ADVERTISE_NETWORK_TABLE`**: [BGP](../reference/glossary.md#term-bgp) に向けた広報 hint。
- **`*_CAPABILITIES`**: 各機能の capability 公開（mirror / hash / debug counter 等）。

### ABNF 例

```text
;Defines layer 2 ports
key            = PORT_TABLE:ifname
admin_status   = "down" / "up"
oper_status    = "down" / "up"
lanes          = list of lanes
mac            = 12HEXDIG
alias          = 1*64VCHAR
speed          = 1*6DIGIT      ; Mbps
mtu            = 1*4DIGIT
fec            = 1*64VCHAR
autoneg        = BIT
```

## 設定

### 関連する CONFIG_DB

CONFIG_DB スキーマは sonic-yang-models が正規。本ドキュメントの対象は APPL_DB / STATE_DB のみ。

### 関連する CLI

直接の CLI は無い。`redis-cli -n 0|6 ...` で APPL_DB / STATE_DB を直接覗くか、`sonic-cli/swssloglevel` 等で読む。

### 関連する YANG

YANG はこのスキーマの対象外。CONFIG_DB 側のみ YANG モデルが存在する。

### 設定例

実エントリの確認例：

```bash
redis-cli -n 0 keys 'PORT_TABLE:*'
redis-cli -n 0 hgetall 'PORT_TABLE:Ethernet0'
redis-cli -n 6 keys 'BFD_SESSION_TABLE|*'
```

## 制限事項

- **生きたドキュメント**であるため、master が更新されるたびにフィールドが追加・変更される。本ページに列挙した内容は執筆時点（commit `4305596145e57e15e4c6a1a3902c0bc6c44a09c5`）のスナップショット。
- ABNF 表記はあくまで **人間とパーサ向けの参考形式** で、orchagent 等の実装はこのファイルを直接読まない。実装側の `swss-common/schema.h` が定数定義の正規ソース。
- 全テーブルを網羅的にここで再掲はしない（54KB のうちの中心テーブルのみピックアップ）。**完全な定義は [HLD](../reference/glossary.md#term-hld) `sonic-net/sonic-swss/doc/swss-schema.md` を参照。**
- **`ConsumerStateTable` の KEY_SET メソッドで DEL メッセージが欠落する問題** ([sonic-swss#1812](https://github.com/sonic-net/sonic-swss/issues/1812)): `ProducerStateTable` / `ConsumerStateTable` を使って swss / orchagent にメッセージを届ける際、KEY_SET メソッドを経由した場合 DEL メッセージが `ConsumerStateTable::pops` で取得できないことがある。インターフェースの高速 DEL/SET（削除後即再作成）を行う場合に発生しやすい。この問題は `ProducerTable` ではなく `ProducerStateTable` を使用している場合のみ該当する。
- **APPLY_VIEW 前の buffer profile 属性照会** ([sonic-swss#2231](https://github.com/sonic-net/sonic-swss/issues/2231)): zero-buffer pool 構成で起動時 INIT_VIEW → APPLY_VIEW 切替前に buffer profile 属性を SAI に照会すると、プロファイルが存在しない状態での照会となり問題が発生する可能性がある。buffer 関連の設定は APPLY_VIEW 完了後に orchagent が実施することが前提であり、初期化シーケンスの実装には注意が必要。
- **netlink NLE_DUMP_INTR (errno=-33)** ([sonic-swss#353](https://github.com/sonic-net/sonic-swss/issues/353)): netlink ソケット読み取り時に `error=-33` が記録される場合、これは `NLE_DUMP_INTR`（`NLM_F_DUMP_INTR` フラグ）を意味し、netlink dump が中断された（メッセージが不完全）ことを示す。`intfsyncd` / `neighsyncd` 等の netlink 監視デーモンが同エラーを無視すると、ネットワーク状態の一部が APP_DB に反映されない可能性がある。このエラーを受け取ったら dump をリトライする必要がある。

## 干渉する機能

- **CONFIG_DB / sonic-yang-models**: 設定面のスキーマは別途 YANG が正規。本ドキュメントは状態・運用面 (APPL_DB / STATE_DB) を扱う。
- **`sonic-swss-common/common/schema.h`**: 実装側の定数定義（テーブル名・フィールド名）の正規ソース。本 .md と乖離した場合は `.h` 側を信用する。
- **CONFIG_DB 由来の APPL_DB 投影**: `*Mgr` プロセスが CONFIG_DB → APPL_DB 投影を行うため、テーブル名や field 名が概念的に対応していても、層を跨ぐと微妙に変わる場合がある（例: CONFIG_DB `PORT|...` → APPL_DB `PORT_TABLE:...`）。

## トラブルシューティング

- 期待する APPL_DB エントリが無い → CONFIG_DB → APPL_DB の投影を担う `*mgrd`（[intfmgrd](../reference/glossary.md#term-intfmgrd) / [vlanmgrd](../reference/glossary.md#term-vlanmgrd) / [portmgrd](../reference/glossary.md#term-portmgrd) 等）の状態を確認。
- フィールド名が違って見える → `swss-schema.md` と `swss-common/schema.h` の **両方** を見て、どちらが最新かを確認する。
- 自分のページが参照する APPL_DB スキーマが本書と食い違う → 直近の [sonic-swss](../reference/glossary.md#term-sonic-swss) master コミットの `doc/swss-schema.md` で再確認するのが望ましい。

## 引用元

[^1]: `sonic-net/sonic-swss` `doc/swss-schema.md` @ `4305596145e57e15e4c6a1a3902c0bc6c44a09c5`

## 裏取りメモ (batch 30, 2026-05-11)

実コードと突合し本ページが指す `sonic-swss/doc/swss-schema.md` 内の主要 APPL_DB テーブル群が現行 master に実在することを確認:

- `sonic-swss/doc/swss-schema.md` には `### PORT_TABLE` / `### INTF_TABLE` / `### VLAN_TABLE` / `### LAG_TABLE` / `### ROUTE_TABLE` / `### NEXTHOP_GROUP_TABLE` / `### CLASS_BASED_NEXT_HOP_GROUP_TABLE` / `### FC_TO_NHG_INDEX_MAP_TABLE` / `### NEIGH_TABLE` / `### SRV6_SID_LIST_TABLE` / `### SRV6_MY_SID_TABLE` / `### FDB_TABLE` / `### QUEUE_TABLE` 等のセクションが定義されており、本ページが主張する「ABNF による APPL_DB / STATE_DB 中心スキーマの集約」と一致。
- `APP_NEXTHOP_GROUP_TABLE_NAME` は `sonic-swss/fpmsyncd/routesync.cpp:157` で実際に [ProducerStateTable](../reference/glossary.md#term-producerstatetable) として open されており、HLD と実装の双方が NEXTHOP_GROUP_TABLE を APPL_DB の正規エントリとして扱っている裏取り。

本ページは個別テーブルへの入口として位置付けられたリファレンスで、実テーブル詳細はリンク先の生きた HLD を参照する旨を冒頭で明示しており、参照ドキュメントとしての記述は実体と整合する。

<!-- glossary-links-injected: 8ba32e5aa69d -->
