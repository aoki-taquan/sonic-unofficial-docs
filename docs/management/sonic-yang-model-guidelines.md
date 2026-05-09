---
title: SONiC YANG モデル記述ガイドライン（ABNF.json → sonic-*.yang）
area: management
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/mgmt/SONiC_YANG_Model_Guidelines.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli: []
  yang:
    - sonic-acl
    - sonic-vlan
    - sonic-port
    - sonic-interface
---

!!! warning "裏取りステータス: HLD-only"
    本ガイドラインは `sonic-yang-models` の記述ルール集。`sonic-ext` 拡張 (`map-list` / `db-name` / `key-delim`)、CVL / Mgmt Framework との連携、ABNF.json と現行 sonic-yang-models の整合性は未裏取り。

# SONiC YANG モデル記述ガイドライン（ABNF.json → `sonic-*.yang`）

## 概要

SONiC の YANG モデルは **ABNF.json** で表現された Redis スキーマを RFC 7950 準拠の YANG に写像したもの。Configuration Validation Library (CVL) と SONiC Mgmt Framework が NB API・設定検証で利用する[^1]。本ドキュメントはそのモデルを書く際のガイドライン 21 項[^1] を構造化したもの。

## ガイドライン要約

### ファイル / トップレベル構造

| # | ルール |
|---|--------|
| 1 | 1 機能 1 ファイル。`sonic-{feature}.yang`（例: `sonic-acl.yang` / `sonic-vlan.yang`） |
| 2 | トップレベル container を `sonic-{feature}` という同名で 1 つ置く |
| 3 | namespace は `http://github.com/sonic-net/{model-name}` |
| 4 | 変更時は `revision <YYYY-MM-DD>` を必ず追加し description で何を変えたか記録 |

### ABNF.json からの写像

| # | ルール |
|---|--------|
| 5 | ABNF.json の primary section（dictionary）を YANG `container` にする（`VLAN`、`VLAN_MEMBER` 等そのまま） |
| 6 | `leaf` 名は ABNF キーと **大文字小文字込みで一致**（`PACKET_ACTION`、`IP_TYPE` など） |
| 7 | `leaf type` は **IETF 既存型を優先**（`inet:ipv4-prefix` 等）。SONiC 独自型は共通 header にまとめる |
| 8 | データ階層を ABNF と揃える。例外を作るならコメントで理由を残す |
| 9 | ABNF の primary key は YANG の `key`。Container 名で表すか list の key で表すかは設計判断 |
| 10 | テーブル間参照は `leafref` を使う（例: `ACL_RULE.table_name` → `ACL_TABLE.table_name`） |

### マッピングテーブル / 参照

| # | ルール |
|---|--------|
| 11 | Redis のマッピングテーブル（例: `TC_TO_QUEUE_MAP`）は `list` の入れ子で表現し、外側 list に **`sonic-ext:map-list "true";`** を付ける |
| 12 | ABNF の `ref_hash_key_reference` は `leafref` で表現 |

### 制約 / バリデーション

| # | ルール |
|---|--------|
| 13 | 複雑な相関制約は `must` で書く。例: ルール削除時にテーブルにポートが残っていない、等 |
| 14 | `length` / `pattern` / `range` / `must` には **`error-message` と `error-app-tag`** を付与（NB アプリのエラー表示で使う） |
| 15 | 制約は実コード（`.h` の `#define` 等）または LLD から導出する。例: `IP_TYPE` の enum は `aclorch.h` の `IP_TYPE_*` から生成 |
| 16 | `must` / `when` / `pattern` 条件には背景コメントを必ず添える |

### List 設計

| # | ルール |
|---|--------|
| 17 | ABNF が単一 dict で複数行を持つ場合は `<TABLE>_LIST` という list で表現（例: `PORTCHANNEL_INTERFACE_LIST`） |
| 18 | 1 ABNF テーブルを複数 list に分割する場合は **キー要素数または型を変えて衝突しないように**。同じキー名・要素数・型の 2 list は禁止 |

### State data / RPC / Notification

| # | ルール |
|---|--------|
| 19 | 状態系 (read-only) は `config false;` で別 container。CONFIG_DB 以外の DB なら `sonic-ext:db-name "<DB>"`、key 区切りが `\|` でなければ `sonic-ext:key-delim "<sep>"` を付ける |
| 20 | clear 等の動作命令は **custom RPC**（input / output は省略可）。設定変更を伴う RPC は禁止 |
| 21 | 非同期イベントは `notification`（例: `link_event`） |

## 代表的なパターン

### `must` / `when` で IP_TYPE と prefix 型を整合させる例

```yang
choice ip_prefix {
  case ip4_prefix {
    when "boolean(IP_TYPE[.='ANY' or .='IP' or .='IPV4' or .='IPV4ANY' or .='ARP'])";
    leaf SRC_IP { type inet:ipv4-prefix; }
    leaf DST_IP { type inet:ipv4-prefix; }
  }
  case ip6_prefix {
    when "boolean(IP_TYPE[.='ANY' or .='IP' or .='IPV6' or .='IPV6ANY'])";
    leaf SRC_IPV6 { type inet:ipv6-prefix; }
    leaf DST_IPV6 { type inet:ipv6-prefix; }
  }
}
```

`IP_TYPE` が IPv4 系 / IPv6 系のどちらかでだけ対応する prefix leaf を有効化する[^1]。

### 1 テーブルを複数 list に分けるとき（許可される例）

```text
INTERFACE table:
  "Ethernet1"                   -> { vrf-name: vrf1 }       # キー要素 1
  "Ethernet1|10.184.230.211/31" -> { ... }                  # キー要素 2
```

YANG では **キー要素数で区別** して `INTERFACE_LIST` (key=ifname) と `INTERFACE_IPADDR_LIST` (key="ifname ip_addr") に分割する[^1]。

### 状態データ container の書き方

```yang
container state {
  sonic-ext:db-name "APPL_DB";
  sonic-ext:key-delim ":";
  config false;
  description "State data";
  leaf MATCHED_PACKETS { type yang:counter64; }
  leaf MATCHED_OCTETS  { type yang:counter64; }
}
```

### custom RPC

```yang
rpc clear-stats {
  input {
    leaf aclname  { type string; }
    leaf rulename { type string; }
  }
}
```

### notification

```yang
notification link_event {
  leaf port {
    type leafref {
      path "../../PORT/PORT_LIST/ifname";
    }
  }
}
```

<!-- evidence:
source: sonic-net/SONiC/doc/mgmt/SONiC_YANG_Model_Guidelines.md#L500-L600 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  ### 18. In some cases it may be required to split an ABNF table into multiple YANG lists ...
  Strategies for Ensuring Unique and Unambiguous Keys: Utilize composite keys that have a different number of key elements ...
reasoning: 2023 年 12 月の Rev 1.1 で追加された list キー衝突回避ルール
-->

## 関連ファイル

- 共通型: `sonic-head` / `sonic-common` 等の include 元
- ACL の完整なサンプル: 本 HLD 末尾に `sonic-acl.yang` を例示[^1]

## 制限事項

- 本ガイドラインは **SONiC YANG（southbound 検証 + NB 向け）** を対象。OpenConfig YANG とは別系統
- ABNF.json と完全 1:1 ではなく、`map-list` 等の SONiC 拡張で構造を変えるケースがある

## 干渉する機能

- **CVL**: 本ガイドライン準拠 YANG が無いと `must` / `when` の検証が効かない
- **SONiC Management Framework**: 同 YANG を NB のスキーマとして再利用するため、命名・階層の食い違いは NB API のブレに直結

## 引用元

[^1]: [sonic-net/SONiC doc/mgmt/SONiC_YANG_Model_Guidelines.md @ 49bab5b](https://github.com/sonic-net/SONiC/blob/49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06/doc/mgmt/SONiC_YANG_Model_Guidelines.md)
