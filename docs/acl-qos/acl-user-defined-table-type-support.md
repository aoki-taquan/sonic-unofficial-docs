---
title: ACL ユーザ定義テーブルタイプ（ACL_TABLE_TYPE と AclTableType）
description: "ACL ユーザ定義テーブルタイプ（ACL_TABLE_TYPE と AclTableType） — 従来の ACL は L3 / L3V6 / MIRROR / PFC_WD 等の 事前定義テーブルタイプ を AclOrch 内に持っており、新機能追加のたびに orchagent を改修する必要があった。"
area: acl-qos
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/acl/ACL-Table-Type-HLD.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - ACL_TABLE_TYPE
    - ACL_TABLE
    - ACL_RULE
    - CTRL_PLANE_ACL_TABLE
  cli:
    - config acl add table
  yang:
    - sonic-acl
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含みます。機能の概念・設定・運用を読み物として読みたい場合は [Topics 07 章: ACL / CoPP / Mirror](../topics/07-acl-copp-mirror/index.md) を参照。
<!-- /topics-tip -->

!!! success "裏取りステータス: Code-verified"
    現行 master で実装済みを確認。`sonic-swss/orchagent/aclorch.h:214-292` で `AclTableType` / `AclTableTypeBuilder` / `AclTableTypeParser`、`aclorch.h:591-609` で `addAclTable` / `addAclTableType` / `addAclRule` / `updateAclRule` API、`sonic-swss-common/common/schema.h:95` で `APP_ACL_TABLE_TYPE_TABLE_NAME`、`schema.h:418` で `STATE_ACL_STAGE_CAPABILITY_TABLE_NAME`、`aclorch.cpp:42,4014,4067` で `is_action_list_mandatory` フィールドの扱いを確認（verified at: 2026-05-09）。

# ACL ユーザ定義テーブルタイプ（ACL_TABLE_TYPE と AclTableType）

## 概要

従来の [ACL](../reference/glossary.md#term-acl) は `L3` / `L3V6` / `MIRROR` / `PFC_WD` 等の **事前定義テーブルタイプ** を `AclOrch` 内に持っており、新機能追加のたびに [orchagent](../reference/glossary.md#term-orchagent) を改修する必要があった。さらに事前定義タイプが固定的に持つマッチフィールド集合は、用途次第で **必要以上の HW リソースを消費** していた[^1]。

本機能は **ユーザがマッチ／アクション／バインドポイントを自由に定義した ACL テーブルタイプを [CONFIG_DB](../reference/glossary.md#term-config_db) から作れる** ようにする。新タイプは `ACL_TABLE_TYPE` テーブルに定義し、`ACL_TABLE` の `TYPE` フィールドからその名前を参照する。

組み込みタイプ（`L3`、`MIRROR` 等）は **特殊扱いが必要なため** orchagent 側に残る[^1]（特に `MIRROR` / `MIRRORV6`）。

## 動作仕様

### CONFIG_DB スキーマ

```abnf
key:           ACL_TABLE_TYPE:<name>     ; ユーザ任意の名前
matches      = match-list                ; ACL_RULE と同じマッチ識別子
actions      = action-list               ; ACL_RULE と同じアクション識別子
bind_points  = bind-points-list          ; "PORT" / "PORTCHANNEL"
```

具体例[^1]:

```json
{
  "ACL_TABLE_TYPE": {
    "CUSTOM_L3": {
      "MATCHES":     ["IN_PORTS","OUT_PORTS","SRC_IP"],
      "ACTIONS":     ["PACKET_ACTION","MIRROR_INGRESS_ACTION"],
      "BIND_POINTS": ["PORT","PORTCHANNEL"]
    }
  },
  "ACL_TABLE": {
    "DATAACL": { "STAGE": "INGRESS", "TYPE": "CUSTOM_L3", "PORTS": ["Ethernet0","PortChannel1"] }
  },
  "ACL_RULE": {
    "DATAACL|RULE0": { "PRIORITY": "999", "PACKET_ACTION": "DROP", "SRC_IP": "1.1.1.1/32" }
  }
}
```

### YANG

`ACL_TABLE_TYPE` 用コンテナを追加し、`ACL_TABLE.type` を **`union(leafref to ACL_TABLE_TYPE_NAME, builtin acl_table_type)`** に拡張する[^1]。組み込み名と任意名を共存させるため。

```yang
container ACL_TABLE_TYPE {
  list ACL_TABLE_TYPE_LIST {
    key "ACL_TABLE_TYPE_NAME";
    leaf-list MATCHES     { mandatory true; type string; }
    leaf-list ACTIONS     { type string; default ""; }
    leaf-list BIND_POINTS {
      mandatory true;
      type enumeration { enum PORT; enum PORTCHANNEL; }
    }
  }
}
```

### コントロールプレーン ACL の分離

データプレーン（HW）ACL と紛らわしいので、`CTRL_PLANE_ACL_TABLE` を **別テーブル** として独立させる[^1]:

```json
"CTRL_PLANE_ACL_TABLE": {
  "SSH_ONLY": { "policy_desc": "SSH only", "services": ["SSH"], "stage": "ingress" }
}
```

### STATE_DB の Capability 公開

`AclOrch` 起動時に [SAI](../reference/glossary.md#term-sai) から取得した capability を [STATE_DB](../reference/glossary.md#term-state_db) に書く[^1]:

```text
ACL_STAGE_CAPABILITY|<INGRESS|EGRESS>
  is_action_list_mandatory = true|false
  action_list = "PACKET_ACTION,MIRROR_INGRESS_ACTION,REDIRECT_ACTION"
```

`is_action_list_mandatory=true` のステージでは、ACL テーブル作成時に `actions` リスト指定が必須となる。orchagent はテーブル作成時に **action 一覧と capability を突合** する[^1]。

### `init_cfg.json` の活用

`L3` / `L3V6` 等の従来タイプを将来的に **`init_cfg.json` に移植** することで「組み込みハードコード」を減らす方針が言及されている[^1]。当面は orchagent 側にコードとして残る。

### Orchagent: `AclTableType` データ構造

```cpp
struct AclTableType {
    std::string                             m_name;
    std::set<sai_acl_bind_point_type_t>     m_bpoint_types;
    std::set<sai_attribute_id_t>            m_matches;
    std::set<sai_acl_action_type_t>         m_acl_actions;
};

class AclTable {
public:
    AclTable(AclOrch *pAclOrch, std::string id, const AclTableType& type);
    bool validateAddType(const AclTableType& type);
private:
    AclTableType m_type;
};
```

`AclOrch` は `ACL_TABLE_TYPE` を購読し、`AclTable` 生成時にこの型を渡す[^1]。

### ACL ルールオブジェクトモデルの統合

従来は `AclRuleL3` / `AclRuleL3V6` 等の派生クラスがマッチ/アクションごとの validation を持っていた。ユーザ定義タイプではこれが事前に決まらないため、**1 つの汎用 `AclRuleBase` がすべてのマッチ・アクションを扱い、`AclTable` の SAI 属性集合に対して generic validate** する設計に統合する[^1]:

```cpp
class AclRule {
public:
    virtual bool create();
    virtual bool remove();
    virtual bool update(const AclRule& updatedRule);
    virtual bool validate(const AclCapabilities& capabilities);
protected:
    uint32_t          m_priority;
    AclEntryAttrMap   m_matches;
    AclEntryAttrMap   m_actions;
private:
    std::string       m_name;
    sai_object_id_t   m_oid {SAI_NULL_OBJECT_ID};
    const AclTable&   m_table;
};
```

`create` / `update` / `remove` は `public virtual` で宣言されており、派生クラスでオーバーライド可能。ただし直接呼び出しではなく AclOrch の public API（`addAclRule` 等）経由での利用が想定されており、[CRM](../reference/glossary.md#term-crm) / Flex Counter 管理が AclOrch に集約される設計となっている[^1]。

### AclOrch 公開 API

```cpp
bool addAclTable   (shared_ptr<AclTable> aclTable);
bool removeAclTable(string aclTableName);
bool updateAclTable(shared_ptr<AclTable> aclTable);   // 注: 更新できるのはバインドされた port のみ

bool addAclRule    (shared_ptr<AclRule> aclRule, string aclTableName);
bool removeAclRule (string aclTableName, string aclRuleName);
bool updateAclRule (shared_ptr<AclRule> updatedAclRule);
```

`updateAclRule` は他 orch（`pfcwdorch` / `pbhorch` / `macsecorch`）の用途向け。CONFIG_DB から来る ACL ルール変更は **remove + recreate** で扱われる[^1]。

<!-- evidence:
source: sonic-net/SONiC/doc/acl/ACL-Table-Type-HLD.md#L308-L362 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  The create/update/remove methods are protected allowing the child classes to be overwritten for custom behavior...
  bool addAclTable(shared_ptr<AclTable> aclTable); ...
  NOTE: Updating ACL table allows only for updating ports bound to it.
  NOTE: ACL rules coming from CONFIG DB are updated by removal and re-creation, an updateAclRule is mostly used for other orch's use cases.
reasoning: 公開 API と更新セマンティクスの根拠。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/SONiC/doc/acl/ACL-Table-Type-HLD.md#L308-L362 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)"

    **出典**:

    `sonic-net/SONiC/doc/acl/ACL-Table-Type-HLD.md#L308-L362 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)`

    **抜粋**:

    ```text
    The create/update/remove methods are protected allowing the child classes to be overwritten for custom behavior...
    bool addAclTable(shared_ptr<AclTable> aclTable); ...
    NOTE: Updating ACL table allows only for updating ports bound to it.
    NOTE: ACL rules coming from CONFIG DB are updated by removal and re-creation, an updateAclRule is mostly used for other orch's use cases.
    ```

    **判断根拠**: 公開 API と更新セマンティクスの根拠。

<!-- evidence-rendered:end -->

### フロー

| フロー | 概要 |
|--------|------|
| Create | `ACL_TABLE_TYPE` 受領 → `AclTableType` 作成 → 該当 `ACL_TABLE` の `validateAddType` 通過 → SAI ACL テーブル作成 |
| Update | テーブルタイプ自体の更新は **未サポート**（matches / actions / bind points の変更不可）。port バインドのみ更新可 |
| Remove | 参照する `ACL_TABLE` が無くなったら type も削除可。orchagent はキャッシュからも消す |

### CLI

CLI は ACL_TABLE_TYPE 名を CONFIG_DB に対して検証し、actions が STATE_DB 公開 capability に含まれているかも検証する[^1]:

```bash
sudo config acl add table DATAACL L3 --ports Ethernet0,Ethernet4 --stage ingress
```

新規 CLI（カスタムタイプ自体を作るコマンド）は **本 [HLD](../reference/glossary.md#term-hld) では追加しない**[^1]。CONFIG_DB / [config_db.json](../reference/glossary.md#term-config_db.json) 直接編集または [gNMI](../reference/glossary.md#term-gnmi) から作る前提。

## 設定

### 設定例（既出）

`CUSTOM_L3` を定義して `DATAACL` テーブルがそれを使うパターンを参照。

## 制限事項

- **table type の matches / actions / bind_points は CREATE-only**: テーブルタイプを変えるには、テーブル＋ルールも作り直しが必要[^1]。
- **組み込みタイプは残る**: `L3` / `MIRROR` 等は依然 orchagent ハードコード。完全な汎用化ではない[^1]。
- **CLI からカスタムタイプは作れない**: CLI 改修は本 HLD のスコープ外。`config_db.json` 直接編集または gNMI ルート[^1]。
- **[YANG](../reference/glossary.md#term-yang) validation の限界**: STATE_DB（capability）への validation 連動は YANG infra の対応次第。Open Question として残る[^1]。
- **マッチ capability の SAI クエリ**: `sai_query_attribute_capability` は CREATE/SET/GET 実装の有無は返すが「サポートか否か」を直接返さない。HLD は Open Question として残している[^1]。

## 干渉する機能

- **`pfcwdorch` / `pbhorch` / `macsecorch`**: 公開 API（`addAclRule` 等）を使う想定。これら orch のコードパスにも影響。
- **Everflow (Mirror)**: `MIRROR` / `MIRRORV6` 組み込みタイプは独立扱いのまま。User-defined と混ぜて使うときの作法に注意[^1]。
- **CRM / Flex Counter**: AclOrch が ACL counter / range オブジェクトのライフサイクルも管理する。AclRule の create/update/remove で連動して作成・破棄される[^1]。
- **`init_cfg.json`**: 既定の組み込みタイプを `init_cfg.json` に移すと、新規プラットフォームでもデフォルトタイプが揃う。

## トラブルシューティング

- ACL テーブル作成が失敗: STATE_DB の `ACL_STAGE_CAPABILITY|<stage>` を見て、要求した actions が `action_list` に入っているか確認。`is_action_list_mandatory=true` で actions が空ならエラー[^1]。
- table type 削除できない: 参照する `ACL_TABLE` が残っている可能性。YANG validation または orchagent ログで確認。
- ルール挙動が古い派生クラス通りでない: 新方式は単一 `AclRuleBase` で動的に validate する設計。古い `AclRuleL3` 等の挙動を期待しないこと[^1]。

確認コマンド例:

```bash
# STATE_DB の stage capability と user-defined table type 定義を確認
redis-cli -n 6 keys 'ACL_STAGE_CAPABILITY|*'
redis-cli -n 6 hgetall 'ACL_STAGE_CAPABILITY|INGRESS'
redis-cli -n 4 keys 'ACL_TABLE_TYPE|*'
redis-cli -n 4 hgetall 'ACL_TABLE_TYPE|<name>'
```

## 引用元

[^1]: `sonic-net/SONiC` `doc/acl/ACL-Table-Type-HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: ACL / CoPP / Mirror / Packet Action](../topics/07-acl-copp-mirror/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: c3f7b90f3488 -->
