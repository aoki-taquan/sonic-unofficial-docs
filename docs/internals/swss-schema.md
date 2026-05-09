---
title: swss-schema（APPL_DB / STATE_DB の中心スキーマ参照）
area: internals
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-swss
    path: doc/swss-schema.md
    ref: 4305596145e57e15e4c6a1a3902c0bc6c44a09c5
related:
  config_db: []
  cli: []
  yang: []
---

!!! warning "裏取りステータス: HLD-only / リファレンス文書"
    本ファイルは sonic-swss リポジトリ内の **生きたスキーマ参照ドキュメント** で、APPL_DB / STATE_DB の中心テーブルの ABNF 定義を集約している。本ページは概観のみで、最新の各テーブル詳細は [sonic-swss/doc/swss-schema.md](https://github.com/sonic-net/sonic-swss/blob/master/doc/swss-schema.md) を参照することを推奨する。54KB 超のため要点のみ抜粋。

# swss-schema（APPL_DB / STATE_DB の中心スキーマ参照）

## 概要

SONiC の APPL_DB / STATE_DB に存在する主要テーブルを、**RFC 5234 ABNF 構文** で機械可読に定義する `sonic-swss` リポジトリ内の参照ドキュメント[^1]。orchagent / *syncd / *mgrd 系プロセス間で受け渡されるテーブルの正規定義として、サブシステムを跨いで参照される。

開発者・Verifier はこのファイルを APPL_DB / STATE_DB スキーマの一次情報として扱う。CONFIG_DB スキーマは別途 `sonic-buildimage/src/sonic-yang-models/` 配下の YANG モデルが正規。

## 動作仕様

### 共通トークン

```text
name                    = 1*DIGIT/1*ALPHA
ref_hash_key_reference  = "[" hash_key "]"   ; 別 DB キーへの参照
hash_key                = name               ; 既存キー名
```

### 主要 APPL_DB テーブル（抜粋）

ファイル冒頭から並ぶ代表テーブル：

- **`PORT_TABLE`**: 物理ポート（CPU / loopback は除外）。`admin_status` / `oper_status` / `lanes` / `mac` / `alias` / `speed` / `mtu` / `fec` / `autoneg` / `preemphasis` / FEC・SerDes 用 hex リスト / Path Tracing 用フィールド / QoS マッピング reference 等[^1]。
- **`INTF_TABLE`**: 論理ネットワークインタフェース。`<ifname>:<IPprefix>` 形式キー、`scope` (global/local)、`if_mtu`、`family`。
- **`VLAN_TABLE` / `VLAN_MEMBER_TABLE`**: VLAN 定義とメンバ。
- **`LAG_TABLE` / `LAG_MEMBER_TABLE`**: Port-Channel 定義とメンバ。
- **`ROUTE_TABLE`**: 経路。`nexthop` / `intf` / `vni_label` / `router_mac` / `blackhole` / SRv6 関連 (`segment` / `seg_src` / `vpn_sid` / `policy`)。
- **`NEIGH_TABLE`**: ARP/ND エントリ。`<ifname>:<ip>` キー。
- **`FDB_TABLE`**: L2 FDB エントリ。
- **`MIRROR_SESSION_TABLE`**: ミラーリングセッション。
- **`ACL_TABLE` / `ACL_RULE_TABLE`**: ACL の APPL_DB 投影。
- **`COPP_TABLE`**: control-plane policer。
- **`BFD_SESSION_TABLE`**: BFD セッション。
- **`VNET_ROUTE_TUNNEL_TABLE` / `VXLAN_TUNNEL_TABLE`**: VxLAN / VNET。
- **`SRV6_*`**: SRv6 関連（SID list、my_sid、policy）。

### 主要 STATE_DB テーブル

- **`PORT_TABLE` (STATE_DB)**: oper 状態のうち SAI/syncd 由来分。
- **`NEIGH_STATE_TABLE` / `INTERFACE_TABLE`**: oper 状態。
- **`BFD_SESSION_TABLE` (STATE_DB)**: BFD の oper state（`Up` / `Down`）。
- **`WARM_RESTART_TABLE`**: warm restart 各サブシステムの restart_count 等。
- **`ADVERTISE_NETWORK_TABLE`**: BGP に向けた広報 hint。
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
- 全テーブルを網羅的にここで再掲はしない（54KB のうちの中心テーブルのみピックアップ）。**完全な定義は HLD `sonic-net/sonic-swss/doc/swss-schema.md` を参照。**

## 干渉する機能

- **CONFIG_DB / sonic-yang-models**: 設定面のスキーマは別途 YANG が正規。本ドキュメントは状態・運用面 (APPL_DB / STATE_DB) を扱う。
- **`sonic-swss-common/common/schema.h`**: 実装側の定数定義（テーブル名・フィールド名）の正規ソース。本 .md と乖離した場合は `.h` 側を信用する。
- **CONFIG_DB 由来の APPL_DB 投影**: `*Mgr` プロセスが CONFIG_DB → APPL_DB 投影を行うため、テーブル名や field 名が概念的に対応していても、層を跨ぐと微妙に変わる場合がある（例: CONFIG_DB `PORT|...` → APPL_DB `PORT_TABLE:...`）。

## トラブルシューティング

- 期待する APPL_DB エントリが無い → CONFIG_DB → APPL_DB の投影を担う `*mgrd`（intfmgrd / vlanmgrd / portmgrd 等）の状態を確認。
- フィールド名が違って見える → `swss-schema.md` と `swss-common/schema.h` の **両方** を見て、どちらが最新かを確認する。
- 自分のページが参照する APPL_DB スキーマが本書と食い違う → 直近の sonic-swss master コミットの `doc/swss-schema.md` で再確認するのが望ましい。

## 引用元

[^1]: `sonic-net/sonic-swss` `doc/swss-schema.md` @ `4305596145e57e15e4c6a1a3902c0bc6c44a09c5`
