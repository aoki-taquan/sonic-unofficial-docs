---
title: ACL in SONiC（テーブル型 / マッチ・アクション / SWSS パイプライン）
area: acl-qos
verification: hld-only
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/acl/ACL-High-Level-Design.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - ACL_TABLE
    - ACL_RULE
  cli:
    - config acl
    - aclshow
    - swssconfig
  yang:
    - sonic-acl
---

!!! info "裏取りステータス: HLD-only"
    HLD は Rev 1.1 (2025-04)。`AclOrch` の現行 master 実装、L3 / Mirror / VXLAN inner src MAC rewrite といったテーブル型対応、`SAI_OBJECT_TYPE_ACL_*` の利用範囲、`aclshow` / `config acl` の sonic-utilities 取り込みは未確認。

# ACL in SONiC（テーブル型 / マッチ・アクション / SWSS パイプライン）

> 大きな HLD（38 KB）。本ページは architecturally distinctive な要素に絞る。詳細は HLD `doc/acl/ACL-High-Level-Design.md` を参照。

## 概要

SONiC の ACL は **table（型を持つ）+ rule** の二層構造。table の **type** で許される match / action と **bind 先** が決まる[^1]:

- `L3`: ingress IPv4 ACL（任意の port / LAG / Vlan に bind）
- `L3v6`: ingress IPv6 ACL
- `Mirror`: ingress traffic を mirror する用途
- カスタム拡張: 例として **VXLAN inner src MAC rewrite** 用の table（Rev 1.1 で追加）[^1]
- 他にも `MIRRORV6`, `PFCWD`, `EVERFLOW`, `DROP`, `MUX`, etc. が後発で追加されている（HLD は基礎を述べるのみ）

## 動作仕様

### スタック構造

```mermaid
flowchart LR
  CONF[config_db.json /<br/>swssconfig (.json)] --> APP[APPL_DB<br/>ACL_TABLE_TABLE<br/>ACL_RULE_TABLE]
  APP --> ORCH[AclOrch<br/>(in swss orchagent)]
  ORCH --> SR[SAI Redis]
  SR --> SDB[ASIC_DB]
  SDB --> SYN[syncd]
  SYN --> SAI[SAI ACL API<br/>(switch driver)]
  SAI --> ASIC[ASIC TCAM]
```

要点[^1]:

- `swssconfig` は静的 config（json）を APPL_DB に流し込む。動的設定は `config acl` 系 CLI が CONFIG_DB→APPL_DB を経由
- `AclOrch` が APPL_DB の subscribe で table / rule の create/update/delete を SAI に翻訳

### CONFIG_DB / APPL_DB スキーマ

```
CONFIG_DB ACL_TABLE|<table_name>
  type   = "L3" | "L3v6" | "MIRROR" | ...
  policy_desc = "..."
  ports  = "Ethernet0,PortChannel001,..."   # bind 対象
  stage  = "ingress" | "egress"

CONFIG_DB ACL_RULE|<table_name>|<rule_name>
  PRIORITY      = <int>
  PACKET_ACTION = "DROP" | "FORWARD"
  ETHER_TYPE    = ...
  SRC_IP / DST_IP / IP_PROTOCOL / L4_*_PORT 等
```

> `ports` は table の type に応じて port / LAG / VLAN / 全 switch から選ぶ。

### Match / Action（type 別の差）

table の **type** が match / action の **集合** を決める[^1]。例として:

| Type | 主な match | 主な action |
|------|-----------|-------------|
| `L3` | `SRC_IP`, `DST_IP`, `IP_PROTOCOL`, `L4_SRC_PORT`, `L4_DST_PORT`, `ETHER_TYPE`, `TCP_FLAGS`, `IN_PORTS` 等 | `PACKET_ACTION=FORWARD/DROP`, （Phase 3 以降）counter, ranges |
| `L3v6` | 同上 + IPv6 系 | 同上 |
| `MIRROR` | L3 と同種 + ranges 等 | `MIRROR_INGRESS_ACTION` 等 |
| custom（VXLAN inner src MAC rewrite, Rev 1.1）| inner header の特定フィールド | inner src MAC を書き換え[^1] |

### `swssconfig` の入力 JSON

`swssconfig` は静的 ACL を起動時に流す。**`OP` フィールド** で `SET` / `DEL` を指示し、APPL_DB のキーパターンで table / rule を判別する[^1]。

### Phase 構成（HLD の歴史）

HLD は実装スケジュールを 3 phase に分けている[^1]:

- **Phase 1**: L3 / Mirror table、基本 match / action、create/delete
- **Phase 2**: counter、table/rule の **update**、設定変更動的反映
- **Phase 3**: ACL ranges（範囲指定）、port / LAG への bind、ACL mirroring の細部

これらは「current master では当然全部入っている」前提だが、**ベンダ SAI の対応範囲はバラつきがある**。capability query で確認することが推奨。

### Mirror state 連動

Mirror テーブルは `MIRROR_SESSION` の状態に追従する。session が ready で無いときは ACL rule も effective でない[^1]。

<!-- evidence:
source: sonic-net/SONiC/doc/acl/ACL-High-Level-Design.md#L83-L91 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  | 0.1 | | Andriy Moroz | Initial version |
  | 0.4 | 20-Dec-2016 | Oleksandr Ivantsiv | Update data structures |
  | 1.1 | 08-Apr-2025 | Anish Narsian | VXLAN inner src mac rewrite support |
reasoning: 改訂履歴と最新 (2025-04) で VXLAN inner src MAC rewrite が追加されたことの根拠。
-->

## 設定

### 関連する CONFIG_DB

| Table | Key | フィールド |
|-------|-----|------------|
| `ACL_TABLE` | `<table_name>` | `type`, `ports`, `stage`, `policy_desc` |
| `ACL_RULE` | `<table_name>\|<rule_name>` | `PRIORITY`, `PACKET_ACTION`, match キーワード |

### 関連する CLI

| Command | 用途 |
|---------|------|
| `config acl add table <name> <type>` | table 作成 |
| `config acl add rule <table> <rule>` | rule 追加 |
| `config acl remove ...` | 削除 |
| `aclshow [-a] [-t <table>] [-r <rule>]` | hit カウンタ |
| `swssconfig <file.json>` | 静的 ACL ロード |

### 設定例

```bash
config acl add table BLACKLIST L3 -p Ethernet0,Ethernet4 -s ingress
config acl add rule BLACKLIST DENY_BAD --priority 10 \
  --src-ip 192.0.2.0/24 --action DROP
aclshow -a
```

## 制限事項

- table type ごとに許される match / action は固定。**type を後から変える運用は不可**[^1]
- `egress` ステージは ASIC によって match できる set が大きく狭まる
- VXLAN inner src MAC rewrite 等のカスタム type はベンダ SAI 拡張に依存
- TCAM 容量は ASIC 依存。スケール上限は SKU 別の表（`SWITCH_CAPABILITY` 経由）で要確認

## 干渉する機能

- **Mirror セッション**: Mirror table は `MIRROR_SESSION` と密結合
- **EVERFLOW / DSCP-based mirror**: Mirror 上に積み重ねる別 HLD
- **PFCWD / DROP / MUX 等の用途別 ACL**: 同じ ACL_TABLE 機構を type 違いで再利用
- **ACL Flex Counters**: Phase 2 から導入
- **port / LAG**: `ports` で bind。LAG 解体時の rebind は AclOrch 側ロジック

## トラブルシューティング

```bash
# ACL の中身
redis-cli -n 4 KEYS "ACL_TABLE|*"
redis-cli -n 4 KEYS "ACL_RULE|*"

# APPL_DB / ASIC_DB に降りたか
redis-cli -n 0 KEYS "ACL_*"
redis-cli -n 1 KEYS "ASIC_STATE:SAI_OBJECT_TYPE_ACL_*" | head

# ヒット数
aclshow -a

# capability
redis-cli -n 6 HGETALL "SWITCH_CAPABILITY|switch" | grep -i ACL
```

## 引用元

[^1]: `sonic-net/SONiC` `doc/acl/ACL-High-Level-Design.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
